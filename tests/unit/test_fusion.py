"""
Unit tests for IBVAP Phase 8 Multi-Modal Evidence Fusion & Event Intelligence Engine.

Covers all 15+ required scenarios:
1. Person in SAFE zone -> INFO/LOW priority, no intrusion alert
2. Person enters warning buffer -> WARNING_BUFFER reason code
3. Person persistent approach -> PERSISTENT_APPROACH reason code, elevated score
4. Person border crossing -> BORDER_CROSSING event
5. Person crosses + restricted occupancy -> HIGH/CRITICAL event
6. Invalid spatial calibration -> SPATIAL_CALIBRATION_INVALID uncertainty flag, score capped
7. Animal in monitored region -> ANIMAL reason code, no human intrusion conclusion
8. Shadow false detection (1 frame, low persistence) -> suppressed from high priority
9. Pole false detection -> suppressed
10. Short-lived noisy detection -> suppressed
11. Multi-frame sustained event -> Exactly 1 active EventRecord with updating duration (deduplication)
12. Event resolution -> Lifecycle transitions ACTIVE -> RESOLVED
13. Event cooldown -> Cooldown prevents transient re-triggers
14. Conflicting evidence -> Deterministic handling
15. Missing optional evidence (ANPR/FRS) -> Flawless execution
16. Bounded score [0, 100] across extreme inputs
"""

import pytest
from datetime import datetime, timezone, timedelta

from worker.fusion import (
    FusionEngine,
    FusionConfig,
    EventRecord,
    EventType,
    EventStatus,
    FusionReasonCode,
    EvidenceType,
    EvidenceItem,
    calculate_risk_score,
    map_score_to_priority,
)
from worker.tracking.schemas import TrackState, TrajectoryPoint, TargetClass, BoundingBox, TrackStatus
from worker.spatial.schemas import SpatialState, MovementDirection, BorderSide, CrossingStatus, SpatialConfidence
from worker.environment.schemas import EnvironmentState, VisibilityQuality, LightingCondition, WeatherHint, TerrainProfile
from worker.behavior.schemas import BehaviorPrimitive, BehaviorType, BehaviorStatus
from backend.app.schemas.common import EventPriority


# ── Test Helpers ──────────────────────────────────────────────────────────────

def _make_track(
    track_id: int = 1,
    camera_id: str = "cam_01",
    class_id: TargetClass = TargetClass.PERSON,
    num_frames: int = 5,
    base_time: datetime = None,
) -> TrackState:
    t0 = base_time or datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    traj = [
        TrajectoryPoint(x=100.0, y=100.0 + i * 5.0, timestamp_utc=t0 + timedelta(milliseconds=i * 33), frame_id=i)
        for i in range(num_frames)
    ]
    curr_pos = (traj[-1].x, traj[-1].y)
    return TrackState(
        track_id=track_id,
        camera_id=camera_id,
        class_id=class_id,
        bbox=BoundingBox(x_min=curr_pos[0] - 15, y_min=curr_pos[1] - 40, x_max=curr_pos[0] + 15, y_max=curr_pos[1]),
        center_xy=curr_pos,
        status=TrackStatus.TRACKED,
        first_seen=t0,
        last_seen=traj[-1].timestamp_utc,
        trajectory=traj,
    )


def _make_spatial(
    track_id: int = 1,
    camera_id: str = "cam_01",
    border_side: BorderSide = BorderSide.PERMITTED,
    crossing_status: CrossingStatus = CrossingStatus.NONE,
    direction: MovementDirection = MovementDirection.UNCERTAIN,
    spatial_confidence: SpatialConfidence = SpatialConfidence.VALID,
    timestamp_utc: datetime = None,
) -> SpatialState:
    t0 = timestamp_utc or datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    return SpatialState(
        camera_id=camera_id,
        track_id=track_id,
        timestamp_utc=t0,
        border_side=border_side,
        crossing_status=crossing_status,
        direction=direction,
        spatial_confidence=spatial_confidence,
    )


def _make_env(
    visibility: VisibilityQuality = VisibilityQuality.GOOD,
    lighting: LightingCondition = LightingCondition.DAY,
    quality_score: float = 0.85,
) -> EnvironmentState:
    return EnvironmentState(
        camera_id="cam_01",
        timestamp_utc=datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc),
        visibility=visibility,
        lighting=lighting,
        weather=WeatherHint.CLEAR,
        terrain=TerrainProfile.OPEN_GROUND,
        luminance_mean=120.0,
        contrast_rms=45.0,
        blur_score=110.0,
        noise_variance=5.0,
        quality_score=quality_score,
    )


# ── 1. Person in SAFE Zone ───────────────────────────────────────────────────

def test_person_in_safe_zone():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track = _make_track(track_id=1, class_id=TargetClass.PERSON, num_frames=5, base_time=t0)
    spatial = _make_spatial(track_id=1, border_side=BorderSide.PERMITTED, timestamp_utc=t0)
    env = _make_env()

    events = engine.process([track], [spatial], env, [], "cam_01", t0)
    # Person in safe zone without breach behavior should produce no critical/high event
    for ev in events:
        assert ev.priority in (EventPriority.INFO, EventPriority.LOW)
        assert ev.risk_score < 40.0
        assert FusionReasonCode.SAFE_ZONE_ONLY in ev.reason_codes or FusionReasonCode.PERSON_DETECTED in ev.reason_codes


# ── 2. Person in Warning Buffer ──────────────────────────────────────────────

def test_person_in_warning_buffer():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track = _make_track(track_id=1, class_id=TargetClass.PERSON, num_frames=5, base_time=t0)
    spatial = _make_spatial(track_id=1, border_side=BorderSide.WARNING_BUFFER, timestamp_utc=t0)
    env = _make_env()

    events = engine.process([track], [spatial], env, [], "cam_01", t0)
    assert len(events) == 1
    ev = events[0]
    assert FusionReasonCode.WARNING_BUFFER_ENTRY in ev.reason_codes
    assert ev.risk_score > 30.0  # Elevated above base info level


# ── 3. Person Persistent Approach ────────────────────────────────────────────

def test_person_persistent_approach():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track = _make_track(track_id=1, class_id=TargetClass.PERSON, num_frames=10, base_time=t0)
    spatial = _make_spatial(track_id=1, border_side=BorderSide.WARNING_BUFFER, direction=MovementDirection.TOWARD, timestamp_utc=t0)
    behavior = BehaviorPrimitive(
        behavior_id="b_app_1",
        camera_id="cam_01",
        track_id=1,
        behavior_type=BehaviorType.PERSISTENT_APPROACH,
        timestamp_utc=t0,
        first_observed_utc=t0,
        last_observed_utc=t0,
        duration_seconds=3.5,
    )
    env = _make_env()

    events = engine.process([track], [spatial], env, [behavior], "cam_01", t0)
    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == EventType.PERSISTENT_APPROACH
    assert FusionReasonCode.PERSISTENT_APPROACH_DETECTED in ev.reason_codes
    assert ev.priority in (EventPriority.MEDIUM, EventPriority.HIGH)


# ── 4. Person Border Crossing ────────────────────────────────────────────────

def test_person_border_crossing():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track = _make_track(track_id=1, class_id=TargetClass.PERSON, num_frames=8, base_time=t0)
    spatial = _make_spatial(
        track_id=1,
        border_side=BorderSide.RESTRICTED,
        crossing_status=CrossingStatus.CONFIRMED_CROSSING,
        timestamp_utc=t0,
    )
    env = _make_env()

    events = engine.process([track], [spatial], env, [], "cam_01", t0)
    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == EventType.BORDER_CROSSING
    assert FusionReasonCode.BORDER_CROSSED in ev.reason_codes
    assert ev.priority in (EventPriority.HIGH, EventPriority.CRITICAL)


# ── 5. Person Crosses and Remains on Restricted Side ─────────────────────────

def test_person_restricted_occupancy_breach():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track = _make_track(track_id=1, class_id=TargetClass.PERSON, num_frames=15, base_time=t0)
    spatial = _make_spatial(
        track_id=1,
        border_side=BorderSide.RESTRICTED,
        crossing_status=CrossingStatus.CONFIRMED_CROSSING,
        timestamp_utc=t0,
    )
    behavior = BehaviorPrimitive(
        behavior_id="b_occ_1",
        camera_id="cam_01",
        track_id=1,
        behavior_type=BehaviorType.RESTRICTED_OCCUPANCY,
        timestamp_utc=t0,
        first_observed_utc=t0,
        last_observed_utc=t0,
        duration_seconds=5.0,
    )
    env = _make_env()

    events = engine.process([track], [spatial], env, [behavior], "cam_01", t0)
    assert len(events) == 1
    ev = events[0]
    assert ev.risk_score >= 70.0
    assert ev.priority in (EventPriority.HIGH, EventPriority.CRITICAL)


# ── 6. Invalid Calibration Protection ────────────────────────────────────────

def test_invalid_calibration_suppresses_confirmed_breach():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track = _make_track(track_id=1, class_id=TargetClass.PERSON, num_frames=5, base_time=t0)
    spatial = _make_spatial(
        track_id=1,
        border_side=BorderSide.RESTRICTED,
        crossing_status=CrossingStatus.CONFIRMED_CROSSING,
        spatial_confidence=SpatialConfidence.INVALID,  # Camera calibration invalid!
        timestamp_utc=t0,
    )
    env = _make_env()

    events = engine.process([track], [spatial], env, [], "cam_01", t0)
    assert len(events) == 1
    ev = events[0]
    assert "SPATIAL_CALIBRATION_INVALID" in ev.uncertainty_flags
    # Score must be capped when spatial calibration is invalid
    assert ev.risk_score < 70.0
    assert ev.priority != EventPriority.CRITICAL


# ── 7. Animal Detection Handling ─────────────────────────────────────────────

def test_animal_in_monitored_region():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track = _make_track(track_id=2, class_id=TargetClass.ANIMAL, num_frames=10, base_time=t0)
    spatial = _make_spatial(track_id=2, border_side=BorderSide.WARNING_BUFFER, timestamp_utc=t0)
    behavior = BehaviorPrimitive(
        behavior_id="b_loiter_animal",
        camera_id="cam_01",
        track_id=2,
        behavior_type=BehaviorType.LOITERING,
        timestamp_utc=t0,
        first_observed_utc=t0,
        last_observed_utc=t0,
        duration_seconds=10.0,
    )
    env = _make_env()

    events = engine.process([track], [spatial], env, [behavior], "cam_01", t0)
    for ev in events:
        assert ev.target_class == TargetClass.ANIMAL
        assert FusionReasonCode.ANIMAL_DETECTED in ev.reason_codes
        # Animal loitering in buffer must not become a critical human intrusion
        assert ev.priority in (EventPriority.INFO, EventPriority.LOW)


# ── 8. Shadow False Detection (1 frame, low persistence) ──────────────────────

def test_shadow_false_detection_suppressed():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    # 1-frame transient track (simulating shadow / noise false alarm)
    track = _make_track(track_id=99, class_id=TargetClass.PERSON, num_frames=1, base_time=t0)
    spatial = _make_spatial(track_id=99, border_side=BorderSide.PERMITTED, timestamp_utc=t0)
    env = _make_env()

    events = engine.process([track], [spatial], env, [], "cam_01", t0)
    # Weak single-frame false detection must not produce HIGH event
    for ev in events:
        assert ev.priority in (EventPriority.INFO, EventPriority.LOW)
        assert ev.risk_score < 35.0


# ── 9. Pole False Detection (Stationary, No Approach) ─────────────────────────

def test_pole_false_detection_suppressed():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    # Stationary false detection in safe zone
    track = _make_track(track_id=88, class_id=TargetClass.PERSON, num_frames=5, base_time=t0)
    track.speed_pixels_per_sec = 0.0
    spatial = _make_spatial(track_id=88, border_side=BorderSide.PERMITTED, direction=MovementDirection.UNCERTAIN, timestamp_utc=t0)
    env = _make_env()

    events = engine.process([track], [spatial], env, [], "cam_01", t0)
    for ev in events:
        assert ev.priority in (EventPriority.INFO, EventPriority.LOW)


# ── 10. Short-Lived Noisy Detection ──────────────────────────────────────────

def test_short_lived_detection():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track = _make_track(track_id=77, class_id=TargetClass.UNKNOWN, num_frames=1, base_time=t0)
    spatial = _make_spatial(track_id=77, border_side=BorderSide.PERMITTED, timestamp_utc=t0)
    env = _make_env()

    events = engine.process([track], [spatial], env, [], "cam_01", t0)
    for ev in events:
        assert ev.priority == EventPriority.INFO


# ── 11. Multi-Frame Sustained Event Deduplication ────────────────────────────

def test_event_deduplication_across_frames():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    env = _make_env()

    # Frame 0
    tr0 = _make_track(track_id=1, class_id=TargetClass.PERSON, num_frames=5, base_time=t0)
    sp0 = _make_spatial(track_id=1, border_side=BorderSide.WARNING_BUFFER, timestamp_utc=t0)
    ev0 = engine.process([tr0], [sp0], env, [], "cam_01", t0)[0]
    initial_id = ev0.id

    # Frame 1 (1 second later)
    t1 = t0 + timedelta(seconds=1.0)
    tr1 = _make_track(track_id=1, class_id=TargetClass.PERSON, num_frames=6, base_time=t0)
    sp1 = _make_spatial(track_id=1, border_side=BorderSide.WARNING_BUFFER, timestamp_utc=t1)
    ev1 = engine.process([tr1], [sp1], env, [], "cam_01", t1)[0]

    # Must be the SAME EventRecord updated in place
    assert ev1.id == initial_id
    assert ev1.duration_seconds == pytest.approx(1.0, abs=0.1)

    # Frame 2 (5 seconds later)
    t2 = t0 + timedelta(seconds=5.0)
    tr2 = _make_track(track_id=1, class_id=TargetClass.PERSON, num_frames=10, base_time=t0)
    sp2 = _make_spatial(track_id=1, border_side=BorderSide.WARNING_BUFFER, timestamp_utc=t2)
    ev2 = engine.process([tr2], [sp2], env, [], "cam_01", t2)[0]

    assert ev2.id == initial_id
    assert ev2.duration_seconds == pytest.approx(5.0, abs=0.1)
    assert len(engine.get_active_events("cam_01")) == 1


# ── 12. Event Resolution ─────────────────────────────────────────────────────

def test_event_resolution_on_track_exit():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    env = _make_env()

    # Frame 0: Track is active in warning buffer -> generates EventRecord
    tr0 = _make_track(track_id=1, class_id=TargetClass.PERSON, num_frames=5, base_time=t0)
    sp0 = _make_spatial(track_id=1, border_side=BorderSide.WARNING_BUFFER, timestamp_utc=t0)
    events = engine.process([tr0], [sp0], env, [], "cam_01", t0)
    assert len(events) == 1
    assert len(engine.get_active_events("cam_01")) == 1

    # Frame 1: Track disappears (empty tracks list) -> event resolves
    t1 = t0 + timedelta(seconds=1.0)
    events_after = engine.process([], [], env, [], "cam_01", t1)
    assert len(events_after) == 0
    assert len(engine.get_active_events("cam_01")) == 0


# ── 13. Event Cooldown ───────────────────────────────────────────────────────

def test_event_cooldown_suppression():
    config = FusionConfig(event_cooldown_seconds=10.0)
    engine = FusionEngine(default_config=config)
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    env = _make_env()

    # Step 1: Trigger event for Track 1
    tr = _make_track(track_id=1, class_id=TargetClass.PERSON, num_frames=5, base_time=t0)
    sp = _make_spatial(track_id=1, border_side=BorderSide.WARNING_BUFFER, timestamp_utc=t0)
    evs = engine.process([tr], [sp], env, [], "cam_01", t0)
    assert len(evs) == 1

    # Step 2: Track exits -> event resolves
    t1 = t0 + timedelta(seconds=1.0)
    engine.process([], [], env, [], "cam_01", t1)

    # Step 3: Track reappears 3 seconds later (within 10s cooldown window)
    t2 = t0 + timedelta(seconds=4.0)
    evs_cooldown = engine.process([tr], [sp], env, [], "cam_01", t2)
    # Should be suppressed during cooldown
    assert len(evs_cooldown) == 0


# ── 14. Conflicting Evidence ─────────────────────────────────────────────────

def test_conflicting_evidence_deterministic():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    # Conflicting: Person moving AWAY, but inside WARNING_BUFFER, with low visual quality
    track = _make_track(track_id=1, class_id=TargetClass.PERSON, num_frames=5, base_time=t0)
    spatial = _make_spatial(
        track_id=1,
        border_side=BorderSide.WARNING_BUFFER,
        direction=MovementDirection.AWAY,
        timestamp_utc=t0,
    )
    env = _make_env(visibility=VisibilityQuality.POOR, quality_score=0.3)

    events = engine.process([track], [spatial], env, [], "cam_01", t0)
    assert len(events) == 1
    ev = events[0]
    # Should resolve deterministically to a bounded score without crashing
    assert 0.0 <= ev.risk_score <= 100.0
    assert "LOW_VISUAL_QUALITY" in ev.uncertainty_flags


# ── 15. Missing Optional Evidence ────────────────────────────────────────────

def test_missing_optional_evidence_runs_flawlessly():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track = _make_track(track_id=1, class_id=TargetClass.PERSON, num_frames=5, base_time=t0)
    # No environment, no behavior primitives, no spatial state
    events = engine.process([track], [], None, [], "cam_01", t0)
    for ev in events:
        assert ev.priority == EventPriority.INFO
        assert ev.risk_score >= 0.0


# ── 16. Bounded Score Across Edge Inputs ──────────────────────────────────────

def test_risk_score_bounded_extremes():
    config = FusionConfig()

    # Extreme high evidence: Person + Persistent + Breach + Occupancy + Night
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    high_items = [
        EvidenceItem(evidence_type=EvidenceType.OBJECT_CLASS, source_module="p", value="person", reason_code=FusionReasonCode.PERSON_DETECTED, timestamp_utc=t0, camera_id="cam_01"),
        EvidenceItem(evidence_type=EvidenceType.TRACK_PERSISTENCE, source_module="t", value=50, reason_code=FusionReasonCode.PERSISTENT_TRACK, timestamp_utc=t0, camera_id="cam_01"),
        EvidenceItem(evidence_type=EvidenceType.BORDER_CROSSING, source_module="s", value="confirmed", reason_code=FusionReasonCode.BORDER_CROSSED, timestamp_utc=t0, camera_id="cam_01"),
        EvidenceItem(evidence_type=EvidenceType.BEHAVIOR_PRIMITIVE, source_module="b", value="fence_breach", reason_code=FusionReasonCode.FENCE_BREACH_DETECTED, timestamp_utc=t0, camera_id="cam_01"),
        EvidenceItem(evidence_type=EvidenceType.ENVIRONMENT_QUALITY, source_module="e", value="night", reason_code=FusionReasonCode.NIGHT_OPERATION, timestamp_utc=t0, camera_id="cam_01"),
    ]
    score_high, _, _ = calculate_risk_score(high_items, config)
    assert 0.0 <= score_high <= 100.0
    assert score_high >= 80.0

    # Empty evidence
    score_empty, _, _ = calculate_risk_score([], config)
    assert score_empty == 0.0


# ── 17. Event Acknowledgment ─────────────────────────────────────────────────

def test_event_acknowledgment():
    engine = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track = _make_track(track_id=1, class_id=TargetClass.PERSON, num_frames=5, base_time=t0)
    spatial = _make_spatial(track_id=1, border_side=BorderSide.RESTRICTED, timestamp_utc=t0)
    ev = engine.process([track], [spatial], None, [], "cam_01", t0)[0]

    assert ev.is_acknowledged is False
    ack_time = t0 + timedelta(seconds=2)
    success = engine.acknowledge_event(ev.id, "operator_alpha", ack_time)

    assert success is True
    assert ev.is_acknowledged is True
    assert ev.acknowledged_by == "operator_alpha"
    assert ev.acknowledged_at == ack_time
