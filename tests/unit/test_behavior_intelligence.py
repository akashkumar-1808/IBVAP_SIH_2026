from datetime import datetime, timedelta, timezone
import pytest

from backend.app.schemas.common import TargetClass
from backend.app.schemas.events import BoundingBox, TrackState
from worker.spatial.schemas import (
    SpatialState,
    MovementDirection,
    ZoneType,
    BorderSide,
    CrossingStatus,
    FenceCrossingEvent,
)
from worker.behavior.schemas import (
    BehaviorConfig,
    BehaviorType,
    BehaviorStatus,
    ReasonCode,
)
from worker.behavior.engine import BehaviorEngine
from worker.behavior.speed import SpeedAnomalyDetector
from worker.behavior.approach import ApproachDetector
from worker.behavior.loitering import LoiteringDetector
from worker.behavior.occupancy import OccupancyDetector, FenceBreachDetector


@pytest.fixture
def base_timestamp():
    return datetime(2026, 9, 9, 12, 0, 0, tzinfo=timezone.utc)


def make_track(
    track_id: int,
    camera_id: str = "cam_01",
    center_xy: tuple = (120.0, 140.0),
    speed: float = 10.0,
    confidence: float = 0.90,
    keypoints=None,
    keypoint_scores=None,
) -> TrackState:
    bbox = BoundingBox(
        x1=center_xy[0] - 20.0,
        y1=center_xy[1] - 40.0,
        x2=center_xy[0] + 20.0,
        y2=center_xy[1] + 40.0,
    )
    track = TrackState(
        track_id=track_id,
        camera_id=camera_id,
        class_id=TargetClass.PERSON,
        bbox=bbox,
        center_xy=center_xy,
        speed_pixels_per_sec=speed,
        confidence_history=[confidence],
        keypoints=keypoints,
    )
    if keypoint_scores is not None:
        track.keypoint_scores = keypoint_scores
    return track


def test_approach_detector_deterministic(base_timestamp):
    config = BehaviorConfig(
        persistent_approach_seconds=3.0,
        persistent_approach_min_distance_px=20.0,
        repeated_approach_window_sec=10.0,
    )
    detector = ApproachDetector(config)

    track = make_track(
        track_id=1,
        camera_id="cam_01",
        center_xy=(120.0, 140.0),
        speed=15.0,
        confidence=0.92,
        keypoints=[(120.0, 110.0), (122.0, 115.0)],
        keypoint_scores=[0.95, 0.85],
    )
    spatial = SpatialState(
        track_id=1,
        camera_id="cam_01",
        timestamp_utc=base_timestamp,
        direction=MovementDirection.TOWARD,
        current_zone_id="buffer_zone",
        border_distance_m=12.5,
    )

    # 1. Under duration threshold -> no primitive
    p, r = detector.evaluate(
        track=track,
        spatial=spatial,
        approach_start_time=base_timestamp,
        approach_start_pos=(100.0, 100.0),
        last_approach_completed_time=None,
        timestamp_utc=base_timestamp + timedelta(seconds=1.5),
    )
    assert p is None
    assert r is None

    # 2. Exceeds duration and distance threshold -> persistent approach primitive
    p, r = detector.evaluate(
        track=track,
        spatial=spatial,
        approach_start_time=base_timestamp,
        approach_start_pos=(100.0, 50.0),  # moved >20px
        last_approach_completed_time=None,
        timestamp_utc=base_timestamp + timedelta(seconds=3.5),
    )
    assert p is not None
    assert p.behavior_type == BehaviorType.PERSISTENT_APPROACH
    assert p.confidence == 0.92
    assert "Persistent movement toward threat vector" in p.triggering_condition
    assert p.supporting_data["has_pose"] is True
    assert p.supporting_data["pose_keypoints_count"] == 2
    assert p.supporting_data["border_distance_m"] == 12.5
    assert r is None

    # 3. Repeated approach within window
    last_completed = base_timestamp - timedelta(seconds=5.0)
    p2, r2 = detector.evaluate(
        track=track,
        spatial=spatial,
        approach_start_time=base_timestamp,
        approach_start_pos=(100.0, 50.0),
        last_approach_completed_time=last_completed,
        timestamp_utc=base_timestamp + timedelta(seconds=3.5),
    )
    assert p2 is not None
    assert r2 is not None
    assert r2.behavior_type == BehaviorType.REPEATED_APPROACH
    assert "Repeated approach within" in r2.triggering_condition


def test_loitering_detector_deterministic(base_timestamp):
    config = BehaviorConfig(
        loitering_seconds=5.0,
        loitering_max_displacement_px=30.0,
    )
    detector = LoiteringDetector(config)

    track = make_track(
        track_id=2,
        camera_id="cam_01",
        center_xy=(220.0, 240.0),
        speed=2.0,
        confidence=0.88,
    )
    spatial = SpatialState(
        track_id=2,
        camera_id="cam_01",
        timestamp_utc=base_timestamp,
        current_zone_id="restricted_sector_1",
    )

    # Dwell below threshold
    res = detector.evaluate(
        track=track,
        spatial=spatial,
        zone_entry_time=base_timestamp,
        first_position_in_zone=(220.0, 240.0),
        timestamp_utc=base_timestamp + timedelta(seconds=3.0),
    )
    assert res is None

    # Dwell above threshold with bounded displacement
    res = detector.evaluate(
        track=track,
        spatial=spatial,
        zone_entry_time=base_timestamp,
        first_position_in_zone=(215.0, 235.0),  # ~7px displacement
        timestamp_utc=base_timestamp + timedelta(seconds=6.0),
    )
    assert res is not None
    assert res.behavior_type == BehaviorType.LOITERING
    assert res.duration_seconds == 6.0
    assert res.confidence == 0.88
    assert "exceeded threshold" in res.triggering_condition
    assert res.supporting_data["has_pose"] is False


def test_crossing_detector_virtual_fence_and_world_border(base_timestamp):
    config = BehaviorConfig()
    detector = FenceBreachDetector(config)

    track = make_track(
        track_id=3,
        camera_id="cam_01",
        center_xy=(320.0, 340.0),
        confidence=0.95,
    )

    # 1. Virtual Fence Crossing
    ev = FenceCrossingEvent(
        fence_id="fence_alpha",
        track_id=3,
        camera_id="cam_01",
        crossing_direction=MovementDirection.TOWARD,
        crossing_point=(320.0, 340.0),
        previous_position=(310.0, 330.0),
        current_position=(330.0, 350.0),
        timestamp_utc=base_timestamp,
    )
    spatial_fence = SpatialState(
        track_id=3,
        camera_id="cam_01",
        timestamp_utc=base_timestamp,
        crossing_events=[ev],
    )
    primitives = detector.evaluate(track, spatial_fence, base_timestamp)
    assert len(primitives) == 1
    assert primitives[0].behavior_type == BehaviorType.FENCE_BREACH
    assert "Confirmed crossing across virtual fence" in primitives[0].triggering_condition
    assert primitives[0].confidence == 0.95

    # 2. Calibrated World Border Crossing
    spatial_border = SpatialState(
        track_id=3,
        camera_id="cam_01",
        timestamp_utc=base_timestamp,
        crossing_status=CrossingStatus.CONFIRMED_CROSSING,
        border_side=BorderSide.RESTRICTED,
    )
    primitives_border = detector.evaluate(track, spatial_border, base_timestamp)
    assert len(primitives_border) == 1
    assert primitives_border[0].behavior_type == BehaviorType.BORDER_CROSSING
    assert "Confirmed border crossing into restricted sector" in primitives_border[0].triggering_condition


def test_speed_anomaly_detector(base_timestamp):
    config = BehaviorConfig(
        speed_anomaly_threshold_px_per_sec=50.0,
        enable_speed_anomaly=True,
    )
    detector = SpeedAnomalyDetector(config)

    # 1. Normal speed
    track_normal = make_track(
        track_id=4,
        camera_id="cam_01",
        center_xy=(120.0, 140.0),
        speed=20.0,
    )
    spatial = SpatialState(track_id=4, camera_id="cam_01", timestamp_utc=base_timestamp)
    assert detector.evaluate(track_normal, spatial, base_timestamp) is None

    # 2. Anomalous high speed (e.g. running or fast vehicle)
    track_fast = make_track(
        track_id=4,
        camera_id="cam_01",
        center_xy=(120.0, 140.0),
        speed=85.5,
        confidence=0.91,
    )
    track_fast.velocity_xy = (50.0, 70.0)
    primitive = detector.evaluate(track_fast, spatial, base_timestamp)
    assert primitive is not None
    assert primitive.behavior_type == BehaviorType.SPEED_ANOMALY
    assert primitive.confidence == 0.91
    assert "exceeded contextual threshold" in primitive.triggering_condition
    assert primitive.supporting_data["observed_speed_px_per_sec"] == 85.5



def test_behavior_engine_integration(base_timestamp):
    config = BehaviorConfig(
        loitering_seconds=2.0,
        loitering_max_displacement_px=50.0,
        speed_anomaly_threshold_px_per_sec=60.0,
        persistent_approach_seconds=2.0,
    )
    engine = BehaviorEngine(default_config=config)

    # Frame 1: Track appears at speed
    t1 = base_timestamp
    track1 = make_track(
        track_id=10,
        camera_id="cam_01",
        center_xy=(100.0, 100.0),
        speed=75.0,
        confidence=0.94,
    )
    spatial1 = SpatialState(
        track_id=10,
        camera_id="cam_01",
        timestamp_utc=t1,
        direction=MovementDirection.TOWARD,
        current_zone_id="restricted_buffer",
        current_zone_type=ZoneType.RESTRICTED,
    )

    out1 = engine.process([track1], [spatial1], t1)
    # Speed anomaly and restricted occupancy should trigger
    types1 = {b.behavior_type for b in out1}
    assert BehaviorType.SPEED_ANOMALY in types1
    assert BehaviorType.RESTRICTED_OCCUPANCY in types1

    # Frame 2: 2.5 seconds later, sustained toward direction and dwelling in restricted zone
    t2 = base_timestamp + timedelta(seconds=2.5)
    track2 = make_track(
        track_id=10,
        camera_id="cam_01",
        center_xy=(130.0, 130.0),
        speed=25.0,  # slowed down
        confidence=0.95,
    )
    spatial2 = SpatialState(
        track_id=10,
        camera_id="cam_01",
        timestamp_utc=t2,
        direction=MovementDirection.TOWARD,
        current_zone_id="restricted_buffer",
        current_zone_type=ZoneType.RESTRICTED,
    )

    out2 = engine.process([track2], [spatial2], t2)
    types2 = {b.behavior_type for b in out2}
    # Speed anomaly should now have cleared (speed dropped to 25)
    assert BehaviorType.SPEED_ANOMALY not in types2
    # Loitering, approach, and restricted occupancy should be active
    assert BehaviorType.PERSISTENT_APPROACH in types2
    assert BehaviorType.LOITERING in types2
    assert BehaviorType.RESTRICTED_OCCUPANCY in types2

    # Verify explainable triggering conditions and confidence are retained
    for p in out2:
        assert p.confidence >= 0.90
        assert p.triggering_condition is not None
        assert len(p.triggering_condition) > 0
        assert p.camera_id == "cam_01"
        assert p.track_id == 10
