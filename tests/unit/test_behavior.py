import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from worker.behavior import (
    BehaviorEngine,
    BehaviorConfig,
    BehaviorType,
    BehaviorStatus,
    ReasonCode,
    BehaviorPrimitive,
)
from worker.spatial.schemas import (
    SpatialState,
    MovementDirection,
    ZoneType,
    SpatialTransitionType,
    FenceCrossingEvent,
)
from worker.tracking.schemas import (
    TrackState,
    TrajectoryPoint,
    TargetClass,
    BoundingBox,
    TrackStatus,
)


def _make_track(
    track_id: int,
    center_xy: tuple,
    target_class: TargetClass = TargetClass.PERSON,
    camera_id: str = "cam_beh_test",
    timestamp: datetime = None,
) -> TrackState:
    ts = timestamp or datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    return TrackState(
        track_id=track_id,
        camera_id=camera_id,
        class_id=target_class,
        bbox=BoundingBox(x_min=center_xy[0] - 10, y_min=center_xy[1] - 20, x_max=center_xy[0] + 10, y_max=center_xy[1] + 20),
        center_xy=center_xy,
        status=TrackStatus.TRACKED,
        first_seen=ts,
        last_seen=ts,
        trajectory=[TrajectoryPoint(x=center_xy[0], y=center_xy[1], timestamp_utc=ts, frame_id=1)],
    )


def test_loitering_detection_dwell_and_displacement():
    config = BehaviorConfig(loitering_seconds=3.0, loitering_max_displacement_px=30.0)
    engine = BehaviorEngine(default_config=config)
    camera_id = "cam_loiter_test"
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Frame 0: Enters zone at (100, 100) -> No loitering yet
    tr0 = _make_track(1, (100.0, 100.0), camera_id=camera_id, timestamp=t0)
    sp0 = SpatialState(camera_id=camera_id, track_id=1, timestamp_utc=t0, current_zone_id="z_buf", current_zone_type=ZoneType.BUFFER)
    beh0 = engine.process([tr0], [sp0], t0)
    loit0 = [b for b in beh0 if b.behavior_type == BehaviorType.LOITERING]
    assert len(loit0) == 0

    # Frame 1: 2 seconds in (dwell = 2.0s < 3.0s) -> No loitering yet
    t1 = t0 + timedelta(seconds=2.0)
    tr1 = _make_track(1, (105.0, 102.0), camera_id=camera_id, timestamp=t1)
    sp1 = SpatialState(camera_id=camera_id, track_id=1, timestamp_utc=t1, current_zone_id="z_buf", current_zone_type=ZoneType.BUFFER)
    beh1 = engine.process([tr1], [sp1], t1)
    loit1 = [b for b in beh1 if b.behavior_type == BehaviorType.LOITERING]
    assert len(loit1) == 0

    # Frame 2: 4 seconds in, small displacement (10px <= 30px) -> LOITERING triggered
    t2 = t0 + timedelta(seconds=4.0)
    tr2 = _make_track(1, (108.0, 106.0), camera_id=camera_id, timestamp=t2)
    sp2 = SpatialState(camera_id=camera_id, track_id=1, timestamp_utc=t2, current_zone_id="z_buf", current_zone_type=ZoneType.BUFFER)
    beh2 = engine.process([tr2], [sp2], t2)
    loit2 = [b for b in beh2 if b.behavior_type == BehaviorType.LOITERING]
    assert len(loit2) == 1
    assert loit2[0].status == BehaviorStatus.ACTIVE
    assert loit2[0].duration_seconds >= 4.0
    assert ReasonCode.DWELL_TIME_EXCEEDED in loit2[0].reason_codes
    assert ReasonCode.LOW_DISPLACEMENT in loit2[0].reason_codes


def test_loitering_rejected_with_large_displacement():
    config = BehaviorConfig(loitering_seconds=3.0, loitering_max_displacement_px=30.0)
    engine = BehaviorEngine(default_config=config)
    camera_id = "cam_displace_test"
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Frame 0: Enters at (100, 100)
    tr0 = _make_track(1, (100.0, 100.0), camera_id=camera_id, timestamp=t0)
    sp0 = SpatialState(camera_id=camera_id, track_id=1, timestamp_utc=t0, current_zone_id="z_buf", current_zone_type=ZoneType.BUFFER)
    engine.process([tr0], [sp0], t0)

    # Frame 1: 4 seconds in, but moved 150px across zone -> NO loitering
    t1 = t0 + timedelta(seconds=4.0)
    tr1 = _make_track(1, (250.0, 100.0), camera_id=camera_id, timestamp=t1)
    sp1 = SpatialState(camera_id=camera_id, track_id=1, timestamp_utc=t1, current_zone_id="z_buf", current_zone_type=ZoneType.BUFFER)
    beh1 = engine.process([tr1], [sp1], t1)
    loit = [b for b in beh1 if b.behavior_type == BehaviorType.LOITERING]
    assert len(loit) == 0


def test_persistent_and_repeated_approach():
    config = BehaviorConfig(persistent_approach_seconds=2.0, persistent_approach_min_distance_px=20.0, repeated_approach_window_sec=10.0)
    engine = BehaviorEngine(default_config=config)
    camera_id = "cam_approach_test"
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Frame 0: Starts moving TOWARD at (100, 100)
    tr0 = _make_track(1, (100.0, 100.0), camera_id=camera_id, timestamp=t0)
    sp0 = SpatialState(camera_id=camera_id, track_id=1, timestamp_utc=t0, direction=MovementDirection.TOWARD)
    engine.process([tr0], [sp0], t0)

    # Frame 1: 2.5 seconds later, moved +50px TOWARD -> PERSISTENT_APPROACH triggered
    t1 = t0 + timedelta(seconds=2.5)
    tr1 = _make_track(1, (150.0, 100.0), camera_id=camera_id, timestamp=t1)
    sp1 = SpatialState(camera_id=camera_id, track_id=1, timestamp_utc=t1, direction=MovementDirection.TOWARD)
    beh1 = engine.process([tr1], [sp1], t1)
    app1 = [b for b in beh1 if b.behavior_type == BehaviorType.PERSISTENT_APPROACH]
    assert len(app1) == 1
    assert app1[0].duration_seconds >= 2.5
    assert ReasonCode.PERSISTENT_TOWARD in app1[0].reason_codes

    # Frame 2: 4.0 seconds (Track moves AWAY) -> First approach completed
    t2 = t0 + timedelta(seconds=4.0)
    tr2 = _make_track(1, (140.0, 100.0), camera_id=camera_id, timestamp=t2)
    sp2 = SpatialState(camera_id=camera_id, track_id=1, timestamp_utc=t2, direction=MovementDirection.AWAY)
    engine.process([tr2], [sp2], t2)

    # Frame 3: 6.0 seconds (Track starts moving TOWARD again)
    t3 = t0 + timedelta(seconds=6.0)
    tr3 = _make_track(1, (140.0, 100.0), camera_id=camera_id, timestamp=t3)
    sp3 = SpatialState(camera_id=camera_id, track_id=1, timestamp_utc=t3, direction=MovementDirection.TOWARD)
    engine.process([tr3], [sp3], t3)

    # Frame 4: 8.5 seconds (Sustains 2nd approach for 2.5s within 10s repeat window) -> REPEATED_APPROACH
    t4 = t0 + timedelta(seconds=8.5)
    tr4 = _make_track(1, (190.0, 100.0), camera_id=camera_id, timestamp=t4)
    sp4 = SpatialState(camera_id=camera_id, track_id=1, timestamp_utc=t4, direction=MovementDirection.TOWARD)
    beh4 = engine.process([tr4], [sp4], t4)
    rep_app = [b for b in beh4 if b.behavior_type == BehaviorType.REPEATED_APPROACH]
    assert len(rep_app) == 1
    assert ReasonCode.REPEATED_APPROACH in rep_app[0].reason_codes


def test_restricted_occupancy_and_event_deduplication():
    engine = BehaviorEngine()
    camera_id = "cam_occ_test"
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Frame 0: Enters RESTRICTED zone
    tr0 = _make_track(1, (200.0, 200.0), camera_id=camera_id, timestamp=t0)
    sp0 = SpatialState(camera_id=camera_id, track_id=1, timestamp_utc=t0, current_zone_id="z_crit", current_zone_type=ZoneType.RESTRICTED)
    beh0 = engine.process([tr0], [sp0], t0)
    occ0 = [b for b in beh0 if b.behavior_type == BehaviorType.RESTRICTED_OCCUPANCY]
    assert len(occ0) == 1
    assert occ0[0].duration_seconds == 0.0

    # Frame 1: 5 seconds later in same zone -> Duration updated on SAME behavior ID, not duplicated
    t1 = t0 + timedelta(seconds=5.0)
    tr1 = _make_track(1, (205.0, 205.0), camera_id=camera_id, timestamp=t1)
    sp1 = SpatialState(camera_id=camera_id, track_id=1, timestamp_utc=t1, current_zone_id="z_crit", current_zone_type=ZoneType.RESTRICTED)
    beh1 = engine.process([tr1], [sp1], t1)
    occ1 = [b for b in beh1 if b.behavior_type == BehaviorType.RESTRICTED_OCCUPANCY]
    assert len(occ1) == 1
    assert occ1[0].behavior_id == occ0[0].behavior_id
    assert occ1[0].duration_seconds == 5.0


def test_fence_breach_conversion():
    engine = BehaviorEngine()
    camera_id = "cam_fence_breach_test"
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    tr0 = _make_track(1, (250.0, 100.0), camera_id=camera_id, timestamp=t0)
    ev = FenceCrossingEvent(
        fence_id="fence_perimeter_01",
        track_id=1,
        camera_id=camera_id,
        timestamp_utc=t0,
        previous_position=(150.0, 100.0),
        current_position=(250.0, 100.0),
        crossing_point=(200.0, 100.0),
        crossing_direction=MovementDirection.TOWARD,
    )
    sp0 = SpatialState(
        camera_id=camera_id,
        track_id=1,
        timestamp_utc=t0,
        fences_crossed=["fence_perimeter_01"],
        crossing_events=[ev],
    )
    beh = engine.process([tr0], [sp0], t0)
    breach = [b for b in beh if b.behavior_type == BehaviorType.FENCE_BREACH]
    assert len(breach) == 1
    assert breach[0].fence_id == "fence_perimeter_01"
    assert ReasonCode.FENCE_CROSSED in breach[0].reason_codes


def test_camera_isolation_behavior():
    engine = BehaviorEngine()
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Track 1 on Camera A
    tr_a = _make_track(1, (100.0, 100.0), camera_id="cam_A", timestamp=t0)
    sp_a = SpatialState(camera_id="cam_A", track_id=1, timestamp_utc=t0, current_zone_id="z_A", current_zone_type=ZoneType.RESTRICTED)
    engine.process([tr_a], [sp_a], t0)

    # Track 1 on Camera B (same track ID, different camera)
    tr_b = _make_track(1, (100.0, 100.0), camera_id="cam_B", timestamp=t0)
    sp_b = SpatialState(camera_id="cam_B", track_id=1, timestamp_utc=t0, current_zone_id="z_B", current_zone_type=ZoneType.SAFE)
    engine.process([tr_b], [sp_b], t0)

    active_a = engine.get_active_behaviors("cam_A")
    active_b = engine.get_active_behaviors("cam_B")

    assert len(active_a) == 1
    assert active_a[0].behavior_type == BehaviorType.RESTRICTED_OCCUPANCY
    assert len(active_b) == 0  # In SAFE zone, no restricted occupancy
