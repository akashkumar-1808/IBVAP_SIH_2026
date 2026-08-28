import pytest
from datetime import datetime
from backend.app.schemas import (
    TargetClass,
    LightingCondition,
    VisibilityQuality,
    StreamStatus,
    ZoneType,
    BehaviorType,
    EventPriority,
    EnvironmentState,
    ZonePolygon,
    VirtualFence,
    CameraSpatialConfig,
    CameraCreate,
    BoundingBox,
    Detection,
    TrackState,
    EventRecord,
)


def test_environment_state_defaults():
    env = EnvironmentState(camera_id="cam_test")
    assert env.camera_id == "cam_test"
    assert env.lighting == LightingCondition.UNKNOWN
    assert env.visibility == VisibilityQuality.GOOD
    assert 0.0 <= env.quality_score <= 1.0
    assert env.is_enhancement_applied is False


def test_spatial_zone_polygon():
    zone = ZonePolygon(
        id="zone_01",
        name="Sector A Border",
        type=ZoneType.RESTRICTED,
        polygon=[(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)],
    )
    assert zone.id == "zone_01"
    assert len(zone.polygon) == 4
    assert zone.severity_weight == 1.0


def test_detection_and_bounding_box():
    bbox = BoundingBox(x_min=10.0, y_min=20.0, x_max=50.0, y_max=90.0)
    det = Detection(
        camera_id="cam_01",
        frame_id=105,
        class_id=TargetClass.PERSON,
        confidence=0.88,
        bbox=bbox,
    )
    assert det.class_id == TargetClass.PERSON
    assert det.confidence == 0.88
    assert det.bbox.x_max == 50.0


def test_event_record_validation():
    event = EventRecord(
        id="evt_12345",
        camera_id="cam_01",
        event_type=BehaviorType.RESTRICTED_ENTRY,
        priority=EventPriority.HIGH,
        risk_score=85.5,
        target_class=TargetClass.PERSON,
        track_id=42,
        detection_confidence=0.91,
        track_persistence_frames=25,
        dwell_time_seconds=6.2,
        zone_id="zone_01",
        reason_codes=["PERSISTENT_TRACK", "RESTRICTED_ZONE_ENTRY"],
        explanation_summary="Person entered restricted perimeter sector A and dwelled for 6.2s.",
    )
    assert event.priority == EventPriority.HIGH
    assert event.risk_score == 85.5
    assert len(event.reason_codes) == 2
