"""
Comprehensive 20-Scenario Unit Test Suite for IBVAP MVP Differentiation.

Evaluates:
1. valid camera handoff
2. impossible camera handoff
3. temporal mismatch
4. direction mismatch
5. uncertain association
6. sector normal activity
7. sector unusual activity
8. cold-start baseline
9. behavior relationship
10. evidence request creation
11. evidence request fulfillment
12. evidence request expiry
13. reassessment
14. insufficient evidence
15. shadow regression
16. pole regression
17. animal regression
18. invalid calibration
19. duplicate event prevention
20. full 2-3 camera replay scenario

Architecture Decision: DEC-0009
"""

import pytest
import numpy as np
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime, timezone, timedelta

from worker.cross_camera import (
    CrossCameraAssociator,
    CameraTopology,
    CameraTransitionRule,
    BorderTrack,
    AssociationState,
    AssociationSignal,
)
from worker.sector import (
    SectorNormalityEngine,
    SectorProfile,
    SectorContext,
    NormalityStatus,
)
from worker.fusion import (
    FusionEngine,
    FusionConfig,
    EventRecord,
    EventType,
    EventPriority,
    EventStatus,
    FusionReasonCode,
    IncidentStory,
    IncidentStep,
    CorroborationEngine,
    EvidenceRequest,
    CorroborationReason,
    RequestStatus,
    calculate_risk_score,
)
from worker.tracking.schemas import (
    TrackState,
    TargetClass,
    BoundingBox,
    TrajectoryPoint,
    TrackStatus,
)
from worker.spatial.schemas import (
    SpatialState,
    MovementDirection,
    BorderSide,
    CrossingStatus,
    SpatialConfidence,
)
from worker.behavior.schemas import BehaviorPrimitive, BehaviorType
from worker.environment.schemas import EnvironmentState
from backend.app.schemas.common import VisibilityQuality, LightingCondition, ZoneType


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_track(
    track_id: int = 1,
    camera_id: str = "CAM-01",
    target_class: TargetClass = TargetClass.PERSON,
    first_seen: Optional[datetime] = None,
    last_seen: Optional[datetime] = None,
    age_frames: int = 10,
) -> TrackState:
    t0 = first_seen or datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)
    t1 = last_seen or (t0 + timedelta(seconds=1.5))
    return TrackState(
        track_id=track_id,
        camera_id=camera_id,
        class_id=target_class,
        bbox=BoundingBox(x_min=100.0, y_min=100.0, x_max=150.0, y_max=200.0),
        center_xy=(125.0, 150.0),
        status=TrackStatus.TRACKED,
        first_seen=t0,
        last_seen=t1,
        age_frames=age_frames,
        confidence_history=[0.92] * age_frames,
        trajectory=[TrajectoryPoint(x=125.0, y=150.0, timestamp_utc=t0 + timedelta(milliseconds=i*100), frame_id=i) for i in range(age_frames)],
    )


# ── 1. Valid Camera Handoff ──────────────────────────────────────────────────

def test_1_valid_camera_handoff():
    topology = CameraTopology()
    topology.add_rule(CameraTransitionRule(
        source_camera_id="CAM-01",
        target_camera_id="CAM-02",
        min_transit_seconds=0.5,
        max_transit_seconds=10.0,
        expected_direction=MovementDirection.TOWARD,
    ))
    associator = CrossCameraAssociator(topology=topology)

    t0 = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)
    track1 = _make_track(track_id=7, camera_id="CAM-01", first_seen=t0, last_seen=t0 + timedelta(seconds=2.0))
    spatial1 = SpatialState(camera_id="CAM-01", track_id=7, timestamp_utc=t0 + timedelta(seconds=2.0), direction=MovementDirection.TOWARD)

    bt1 = associator.process_track(track1, "CAM-01", spatial_state=spatial1, current_time_utc=t0 + timedelta(seconds=2.0))
    assert bt1.border_track_id == "BT-100"
    assert bt1.camera_sequence == ["CAM-01"]

    # Hand off to CAM-02 2.5s later (physically feasible)
    t_handoff = t0 + timedelta(seconds=4.5)
    track2 = _make_track(track_id=12, camera_id="CAM-02", first_seen=t_handoff, last_seen=t_handoff + timedelta(seconds=1.0))
    spatial2 = SpatialState(camera_id="CAM-02", track_id=12, timestamp_utc=t_handoff, direction=MovementDirection.TOWARD)

    bt2 = associator.process_track(track2, "CAM-02", spatial_state=spatial2, current_time_utc=t_handoff)
    assert bt2.border_track_id == "BT-100"
    assert bt2.camera_sequence == ["CAM-01", "CAM-02"]
    assert bt2.association_state in (AssociationState.CONFIRMED, AssociationState.LIKELY)
    assert AssociationSignal.TEMPORAL_MATCH in bt2.signals


# ── 2. Impossible Camera Handoff ─────────────────────────────────────────────

def test_2_impossible_camera_handoff():
    topology = CameraTopology()
    topology.add_rule(CameraTransitionRule(source_camera_id="CAM-01", target_camera_id="CAM-02"))
    associator = CrossCameraAssociator(topology=topology)

    t0 = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)
    track1 = _make_track(track_id=1, camera_id="CAM-01", first_seen=t0, last_seen=t0 + timedelta(seconds=2.0))
    bt1 = associator.process_track(track1, "CAM-01", current_time_utc=t0 + timedelta(seconds=2.0))

    # CAM-09 track appears (no topology connection)
    track_distant = _make_track(track_id=5, camera_id="CAM-09", first_seen=t0 + timedelta(seconds=3.0))
    bt_distant = associator.process_track(track_distant, "CAM-09", current_time_utc=t0 + timedelta(seconds=3.0))

    assert bt_distant.border_track_id != bt1.border_track_id
    assert bt_distant.camera_sequence == ["CAM-09"]


# ── 3. Temporal Mismatch ─────────────────────────────────────────────────────

def test_3_temporal_mismatch():
    topology = CameraTopology()
    topology.add_rule(CameraTransitionRule(
        source_camera_id="CAM-01",
        target_camera_id="CAM-02",
        min_transit_seconds=2.0,
        max_transit_seconds=10.0,
    ))
    associator = CrossCameraAssociator(topology=topology)

    t0 = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)
    track1 = _make_track(track_id=1, camera_id="CAM-01", first_seen=t0, last_seen=t0 + timedelta(seconds=1.0))
    associator.process_track(track1, "CAM-01", current_time_utc=t0 + timedelta(seconds=1.0))

    # Appears on CAM-02 60 seconds later (timed out)
    t_late = t0 + timedelta(seconds=65.0)
    track_late = _make_track(track_id=2, camera_id="CAM-02", first_seen=t_late)
    bt_late = associator.process_track(track_late, "CAM-02", current_time_utc=t_late)

    assert bt_late.border_track_id != "BT-100"


# ── 4. Direction Mismatch ────────────────────────────────────────────────────

def test_4_direction_mismatch():
    topology = CameraTopology()
    topology.add_rule(CameraTransitionRule(
        source_camera_id="CAM-01",
        target_camera_id="CAM-02",
        expected_direction=MovementDirection.TOWARD,
    ))
    associator = CrossCameraAssociator(topology=topology)

    t0 = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)
    track1 = _make_track(track_id=1, camera_id="CAM-01", first_seen=t0, last_seen=t0 + timedelta(seconds=1.0))
    associator.process_track(track1, "CAM-01", current_time_utc=t0 + timedelta(seconds=1.0))

    # Second track is moving AWAY
    t2 = t0 + timedelta(seconds=3.0)
    track2 = _make_track(track_id=2, camera_id="CAM-02", first_seen=t2)
    spatial_away = SpatialState(camera_id="CAM-02", track_id=2, timestamp_utc=t2, direction=MovementDirection.AWAY)

    bt2 = associator.process_track(track2, "CAM-02", spatial_state=spatial_away, current_time_utc=t2)
    assert bt2.association_confidence <= 0.65


# ── 5. Uncertain Association ─────────────────────────────────────────────────

def test_5_uncertain_association():
    topology = CameraTopology()
    topology.add_rule(CameraTransitionRule(source_camera_id="CAM-01", target_camera_id="CAM-02", min_transit_seconds=0.1, max_transit_seconds=20.0))
    associator = CrossCameraAssociator(topology=topology)

    t0 = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)
    track_unknown = _make_track(track_id=1, camera_id="CAM-01", target_class=TargetClass.UNKNOWN, first_seen=t0, last_seen=t0 + timedelta(seconds=1.0))
    associator.process_track(track_unknown, "CAM-01", current_time_utc=t0 + timedelta(seconds=1.0))

    t2 = t0 + timedelta(seconds=5.0)
    track_person = _make_track(track_id=2, camera_id="CAM-02", target_class=TargetClass.PERSON, first_seen=t2)
    bt2 = associator.process_track(track_person, "CAM-02", current_time_utc=t2)

    assert bt2.association_state in (AssociationState.LIKELY, AssociationState.UNCERTAIN)
    assert bt2.association_confidence < 0.75


# ── 6. Sector Normal Activity ────────────────────────────────────────────────

def test_6_sector_normal_activity():
    engine = SectorNormalityEngine()
    t_day = datetime(2026, 8, 30, 14, 0, 0, tzinfo=timezone.utc)
    ctx = engine.evaluate_activity("sector_north_alpha", t_day, TargetClass.PERSON, observed_count=1)

    assert ctx.status == NormalityStatus.NORMAL
    assert ctx.hour_of_day == 14
    assert ctx.expected_rate >= 1.0


# ── 7. Sector Unusual Activity ───────────────────────────────────────────────

def test_7_sector_unusual_activity():
    engine = SectorNormalityEngine()
    t_night = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)
    ctx = engine.evaluate_activity("sector_north_alpha", t_night, TargetClass.PERSON, observed_count=2)

    assert ctx.status == NormalityStatus.UNUSUAL
    assert ctx.hour_of_day == 2
    assert ctx.deviation_ratio >= 3.0


# ── 8. Cold-Start Baseline ───────────────────────────────────────────────────

def test_8_cold_start_baseline():
    engine = SectorNormalityEngine()
    new_prof = SectorProfile(sector_id="sector_brand_new", min_samples_for_baseline=10, sample_count=2)
    engine.register_profile(new_prof)

    t_now = datetime(2026, 8, 30, 3, 0, 0, tzinfo=timezone.utc)
    ctx = engine.evaluate_activity("sector_brand_new", t_now, TargetClass.PERSON)

    assert ctx.status == NormalityStatus.COLD_START
    assert "cold-start" in ctx.reason.lower()


# ── 9. Behaviour Relationship / Incident Story ──────────────────────────────

def test_9_behavior_relationship():
    story = IncidentStory(story_id="story_001", track_id=10, border_track_id="BT-101")
    t0 = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)

    story.add_step("CAM-01", "DETECTED", "Person detected approaching boundary", t0, BorderSide.PERMITTED, None)
    story.add_step("CAM-01", "WARNING_BUFFER", "Entered buffer zone", t0 + timedelta(seconds=1.0), BorderSide.PERMITTED, BehaviorType.PERSISTENT_APPROACH)
    story.add_step("CAM-02", "BORDER_CROSSED", "Crossed physical border line", t0 + timedelta(seconds=2.5), BorderSide.RESTRICTED, BehaviorType.FENCE_BREACH)
    story.add_step("CAM-03", "RESTRICTED_OCCUPANCY", "Continued movement in restricted zone", t0 + timedelta(seconds=4.0), BorderSide.RESTRICTED, BehaviorType.RESTRICTED_OCCUPANCY)

    narrative = story.get_narrative()
    assert len(story.steps) == 4
    assert "DETECTED" in narrative
    assert "BORDER_CROSSED" in narrative
    assert "RESTRICTED_OCCUPANCY" in narrative
    assert "CAM-01" in narrative and "CAM-02" in narrative and "CAM-03" in narrative


# ── 10. Evidence Request Creation ───────────────────────────────────────────

def test_10_evidence_request_creation():
    engine = CorroborationEngine()
    t0 = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)

    req = engine.create_request(
        candidate_event_id="evt_cand_01",
        track_id=5,
        camera_id="CAM-01",
        reason=CorroborationReason.WAIT_FOR_BORDER_CONFIRMATION,
        ttl_seconds=5.0,
        current_time_utc=t0,
    )

    assert req.request_id == "ev_req_0001"
    assert req.status == RequestStatus.PENDING
    assert req.expiry_utc == t0 + timedelta(seconds=5.0)


# ── 11. Evidence Request Fulfillment ─────────────────────────────────────────

def test_11_evidence_request_fulfillment():
    engine = CorroborationEngine()
    t0 = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)
    engine.create_request("evt_cand_02", track_id=8, camera_id="CAM-01", reason=CorroborationReason.WAIT_FOR_BORDER_CONFIRMATION, current_time_utc=t0)

    track = _make_track(track_id=8, camera_id="CAM-01")
    spatial = SpatialState(camera_id="CAM-01", track_id=8, timestamp_utc=t0 + timedelta(seconds=1.0), crossing_status=CrossingStatus.CONFIRMED_CROSSING)

    updated = engine.evaluate_corroboration(track, spatial_state=spatial, current_time_utc=t0 + timedelta(seconds=1.0))
    assert len(updated) == 1
    assert updated[0].status == RequestStatus.FULFILLED
    assert "crossing confirmed" in updated[0].fulfillment_details.lower()


# ── 12. Evidence Request Expiry ──────────────────────────────────────────────

def test_12_evidence_request_expiry():
    engine = CorroborationEngine()
    t0 = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)
    engine.create_request("evt_cand_03", track_id=9, camera_id="CAM-01", reason=CorroborationReason.WAIT_FOR_PERSISTENCE, ttl_seconds=3.0, current_time_utc=t0)

    # 4 seconds later without track persisting (short track)
    t_expired = t0 + timedelta(seconds=4.0)
    track = _make_track(track_id=9, camera_id="CAM-01", first_seen=t0, last_seen=t0 + timedelta(milliseconds=100), age_frames=2)
    updated = engine.evaluate_corroboration(track, current_time_utc=t_expired)

    assert len(updated) == 1
    assert updated[0].status == RequestStatus.EXPIRED


# ── 13. Reassessment on Fulfilled Request ────────────────────────────────────

def test_13_reassessment():
    fusion = FusionEngine()
    t0 = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)

    # Candidate with confirmed crossing
    track = _make_track(track_id=15, camera_id="CAM-01", target_class=TargetClass.PERSON, age_frames=15)
    spatial = SpatialState(camera_id="CAM-01", track_id=15, timestamp_utc=t0, border_side=BorderSide.RESTRICTED, crossing_status=CrossingStatus.CONFIRMED_CROSSING)

    events = fusion.process(
        tracks=[track],
        spatial_states=[spatial],
        environment_state=None,
        behavior_primitives=[],
        camera_id="CAM-01",
        timestamp_utc=t0,
    )

    assert len(events) == 1
    assert events[0].risk_score >= 75.0
    assert events[0].priority in (EventPriority.HIGH, EventPriority.CRITICAL)


# ── 14. Insufficient Evidence on Expired Request ─────────────────────────────

def test_14_insufficient_evidence():
    fusion = FusionEngine()
    t0 = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)

    # Short track with expired corroboration
    track = _make_track(track_id=20, camera_id="CAM-01", target_class=TargetClass.UNKNOWN, age_frames=2)
    fusion.corroboration_engine.requests["req_exp"] = EvidenceRequest(
        request_id="req_exp", candidate_event_id="cand_20", track_id=20, camera_id="CAM-01",
        reason=CorroborationReason.WAIT_FOR_PERSISTENCE, status=RequestStatus.EXPIRED,
    )

    events = fusion.process(
        tracks=[track],
        spatial_states=[],
        environment_state=None,
        behavior_primitives=[],
        camera_id="CAM-01",
        timestamp_utc=t0,
    )

    for ev in events:
        assert ev.risk_score <= 30.0
        assert ev.priority == EventPriority.INFO


# ── 15. Shadow Regression (No High Priority) ─────────────────────────────────

def test_15_shadow_regression():
    fusion = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track_shadow = _make_track(track_id=99, camera_id="CAM-01", target_class=TargetClass.UNKNOWN, age_frames=2)
    env_poor = EnvironmentState(
        camera_id="CAM-01", timestamp_utc=t0, lighting=LightingCondition.LOW_LIGHT,
        visibility=VisibilityQuality.POOR, quality_score=0.35, blur_score=25.0
    )

    events = fusion.process(
        tracks=[track_shadow],
        spatial_states=[],
        environment_state=env_poor,
        behavior_primitives=[],
        camera_id="CAM-01",
        timestamp_utc=t0,
    )

    for ev in events:
        assert ev.priority != EventPriority.HIGH
        assert ev.priority != EventPriority.CRITICAL
        assert ev.risk_score <= 30.0


# ── 16. Pole Regression (Stationary Object) ──────────────────────────────────

def test_16_pole_regression():
    fusion = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track_pole = _make_track(track_id=101, camera_id="CAM-01", target_class=TargetClass.UNKNOWN, age_frames=30)
    spatial_safe = SpatialState(camera_id="CAM-01", track_id=101, timestamp_utc=t0, border_side=BorderSide.PERMITTED, direction=MovementDirection.UNCERTAIN)

    events = fusion.process(
        tracks=[track_pole],
        spatial_states=[spatial_safe],
        environment_state=None,
        behavior_primitives=[],
        camera_id="CAM-01",
        timestamp_utc=t0,
    )

    for ev in events:
        assert ev.priority != EventPriority.HIGH
        assert ev.priority != EventPriority.CRITICAL


# ── 17. Animal Regression (Wildlife in Buffer) ───────────────────────────────

def test_17_animal_regression():
    fusion = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track_animal = _make_track(track_id=102, camera_id="CAM-01", target_class=TargetClass.ANIMAL, age_frames=20)
    spatial_buffer = SpatialState(camera_id="CAM-01", track_id=102, timestamp_utc=t0, border_side=BorderSide.PERMITTED, direction=MovementDirection.PARALLEL)

    events = fusion.process(
        tracks=[track_animal],
        spatial_states=[spatial_buffer],
        environment_state=None,
        behavior_primitives=[],
        camera_id="CAM-01",
        timestamp_utc=t0,
    )

    for ev in events:
        assert ev.priority in (EventPriority.INFO, EventPriority.LOW)
        assert ev.risk_score < 50.0


# ── 18. Invalid Calibration Safety ───────────────────────────────────────────

def test_18_invalid_calibration():
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track = _make_track(track_id=103, camera_id="CAM-01", target_class=TargetClass.PERSON, age_frames=15)
    spatial_invalid = SpatialState(
        camera_id="CAM-01", track_id=103, timestamp_utc=t0,
        border_side=BorderSide.RESTRICTED,
        crossing_status=CrossingStatus.CONFIRMED_CROSSING,
        spatial_confidence=SpatialConfidence.INVALID,
    )

    from worker.fusion.evidence import EvidenceExtractor
    ev_items = EvidenceExtractor.extract_evidence(track, spatial_invalid, None, [], "CAM-01", t0)
    score, reasons, flags = calculate_risk_score(ev_items, FusionConfig())

    assert "SPATIAL_CALIBRATION_INVALID" in flags
    assert FusionReasonCode.BORDER_CROSSED not in reasons
    # Invalid calibration caps score and prevents unchecked escalation
    assert score <= 70.0


# ── 19. Duplicate Event Prevention ───────────────────────────────────────────

def test_19_duplicate_event_prevention():
    fusion = FusionEngine()
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track = _make_track(track_id=201, camera_id="CAM-01", target_class=TargetClass.PERSON, age_frames=10)
    spatial = SpatialState(camera_id="CAM-01", track_id=201, timestamp_utc=t0, border_side=BorderSide.RESTRICTED, crossing_status=CrossingStatus.CONFIRMED_CROSSING)

    # Frame 1
    ev1 = fusion.process([track], [spatial], None, [], "CAM-01", t0)
    assert len(ev1) == 1
    ev_id = ev1[0].id

    # Frame 2 (sustained observation)
    t1 = t0 + timedelta(seconds=1.0)
    track.last_seen = t1
    ev2 = fusion.process([track], [spatial], None, [], "CAM-01", t1)

    assert len(ev2) == 1
    assert ev2[0].id == ev_id
    assert ev2[0].duration_seconds == 1.0


# ── 20. Full 2-3 Camera Replay Scenario ──────────────────────────────────────

def test_20_full_2_3_camera_scenario():
    """
    Demonstrates full end-to-end multi-camera differentiation:
    CAM-01 -> Person approaches border
    CAM-02 -> Border crossing corroborated across handoff
    CAM-03 -> Restricted occupancy with sector deviation
    -> Produces unified BorderTrack and high-confidence EventRecord.
    """
    fusion = FusionEngine()
    topology = CameraTopology()
    topology.add_rule(CameraTransitionRule(source_camera_id="CAM-01", target_camera_id="CAM-02", min_transit_seconds=0.5, max_transit_seconds=8.0))
    topology.add_rule(CameraTransitionRule(source_camera_id="CAM-02", target_camera_id="CAM-03", min_transit_seconds=0.5, max_transit_seconds=8.0))
    fusion.cross_camera_associator.topology = topology

    t0 = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)

    # Step 1: CAM-01 Approach
    track1 = _make_track(track_id=1, camera_id="CAM-01", first_seen=t0, last_seen=t0 + timedelta(seconds=2.0))
    spatial1 = SpatialState(camera_id="CAM-01", track_id=1, timestamp_utc=t0 + timedelta(seconds=2.0), border_side=BorderSide.PERMITTED, direction=MovementDirection.TOWARD)
    behavior1 = [
        BehaviorPrimitive(
            behavior_id="bp_1",
            track_id=1,
            camera_id="CAM-01",
            behavior_type=BehaviorType.PERSISTENT_APPROACH,
            first_observed_utc=t0,
            last_observed_utc=t0 + timedelta(seconds=2.0),
            timestamp_utc=t0 + timedelta(seconds=2.0),
            duration_seconds=2.0,
        )
    ]

    ev_cam1 = fusion.process([track1], [spatial1], None, behavior1, "CAM-01", t0 + timedelta(seconds=2.0), sector_id="sector_north_alpha")

    # Step 2: CAM-02 Border Crossing
    t_cam2 = t0 + timedelta(seconds=4.0)
    track2 = _make_track(track_id=2, camera_id="CAM-02", first_seen=t_cam2, last_seen=t_cam2 + timedelta(seconds=2.0))
    spatial2 = SpatialState(camera_id="CAM-02", track_id=2, timestamp_utc=t_cam2 + timedelta(seconds=2.0), border_side=BorderSide.RESTRICTED, crossing_status=CrossingStatus.CONFIRMED_CROSSING)
    behavior2 = [
        BehaviorPrimitive(
            behavior_id="bp_2",
            track_id=2,
            camera_id="CAM-02",
            behavior_type=BehaviorType.FENCE_BREACH,
            first_observed_utc=t_cam2,
            last_observed_utc=t_cam2 + timedelta(seconds=2.0),
            timestamp_utc=t_cam2 + timedelta(seconds=2.0),
            duration_seconds=2.0,
        )
    ]

    ev_cam2 = fusion.process([track2], [spatial2], None, behavior2, "CAM-02", t_cam2 + timedelta(seconds=2.0), sector_id="sector_north_alpha")

    # Step 3: CAM-03 Restricted Penetration
    t_cam3 = t0 + timedelta(seconds=7.5)
    track3 = _make_track(track_id=3, camera_id="CAM-03", first_seen=t_cam3, last_seen=t_cam3 + timedelta(seconds=2.0))
    spatial3 = SpatialState(camera_id="CAM-03", track_id=3, timestamp_utc=t_cam3 + timedelta(seconds=2.0), border_side=BorderSide.RESTRICTED, crossing_status=CrossingStatus.CONFIRMED_CROSSING)
    behavior3 = [
        BehaviorPrimitive(
            behavior_id="bp_3",
            track_id=3,
            camera_id="CAM-03",
            behavior_type=BehaviorType.RESTRICTED_OCCUPANCY,
            first_observed_utc=t_cam3,
            last_observed_utc=t_cam3 + timedelta(seconds=2.0),
            timestamp_utc=t_cam3 + timedelta(seconds=2.0),
            duration_seconds=2.0,
        )
    ]

    ev_cam3 = fusion.process([track3], [spatial3], None, behavior3, "CAM-03", t_cam3 + timedelta(seconds=2.0), sector_id="sector_north_alpha")

    assert len(ev_cam3) == 1
    event = ev_cam3[0]

    assert event.priority in (EventPriority.HIGH, EventPriority.CRITICAL)
    assert event.risk_score >= 85.0
    assert FusionReasonCode.CROSS_CAMERA_CORROBORATED in event.reason_codes
    assert FusionReasonCode.SECTOR_ACTIVITY_UNUSUAL in event.reason_codes
    assert event.border_track_id == "BT-100"
