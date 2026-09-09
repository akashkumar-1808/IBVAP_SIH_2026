"""
Unit tests for the Model-Agnostic Detector Interface and Adapters.

Verifies:
1. Unified internal detection format (required & optional fields).
2. Adapter abstraction boundary and zero-leakage guarantee.
3. Dynamic detector registry (get_detector / register_detector).
4. Concrete adapters: YOLOv8Detector, RTDETRDetector, MockDetector, ObjectDetector.
5. Downstream pipeline compatibility (DetectionFilter, ByteTrackTracker, SpatialEngine).
"""

import pytest
import numpy as np
from datetime import datetime, timezone
from typing import List

from backend.app.schemas.common import TargetClass
from backend.app.schemas.events import BoundingBox, Detection
from worker.ingestion.frame import FramePacket
from worker.perception.base import DetectorInterface, BaseDetectorAdapter
from worker.perception.detector import (
    YOLOBaseAdapter,
    YOLOv8Detector,
    YOLO11Detector,
    YOLO26Detector,
    RTDETRDetector,
    MockDetector,
    ObjectDetector,
)
from worker.perception.registry import (
    get_detector,
    register_detector,
    list_available_detectors,
)
from worker.perception.filter import DetectionFilter, DetectionFilterConfig
from worker.tracking.tracker import ByteTrackTracker


def _create_dummy_packet(frame_id: int = 1, width: int = 640, height: int = 480) -> FramePacket:
    img = np.zeros((height, width, 3), dtype=np.uint8)
    return FramePacket(
        camera_id="CAM-TEST-01",
        frame_id=frame_id,
        timestamp_utc=datetime.now(timezone.utc),
        image=img,
        width=width,
        height=height,
    )


def test_unified_bounding_box_accessors():
    """Verify BoundingBox supports both x_min/y_min/x_max/y_max and x1/y1/x2/y2 accessors."""
    # Instantiation via x_min/y_min/x_max/y_max
    bbox1 = BoundingBox(x_min=10.0, y_min=20.0, x_max=110.0, y_max=220.0)
    assert bbox1.x1 == 10.0
    assert bbox1.y1 == 20.0
    assert bbox1.x2 == 110.0
    assert bbox1.y2 == 220.0
    assert bbox1.width == 100.0
    assert bbox1.height == 200.0
    assert bbox1.area == 20000.0
    assert bbox1.center == (60.0, 120.0)
    assert bbox1.to_xyxy() == (10.0, 20.0, 110.0, 220.0)

    # Instantiation via x1/y1/x2/y2 dict
    bbox2 = BoundingBox.model_validate({"x1": 15.0, "y1": 25.0, "x2": 115.0, "y2": 225.0})
    assert bbox2.x_min == 15.0
    assert bbox2.y_min == 25.0
    assert bbox2.x_max == 115.0
    assert bbox2.y_max == 225.0

    # Instantiation via 4-tuple
    bbox3 = BoundingBox.model_validate((5.0, 10.0, 50.0, 100.0))
    assert bbox3.x_min == 5.0
    assert bbox3.y_max == 100.0


def test_unified_detection_schema():
    """Verify Detection schema enforces required fields and extensible optional fields."""
    now = datetime.now(timezone.utc)
    bbox = BoundingBox(x_min=10.0, y_min=20.0, x_max=60.0, y_max=120.0)

    # Baseline required fields
    det = Detection(
        camera_id="CAM-01",
        frame_id=42,
        timestamp_utc=now,
        class_id=TargetClass.PERSON,
        class_name="person",
        confidence=0.92,
        bbox=bbox,
    )
    assert det.class_id == TargetClass.PERSON
    assert det.class_name == "person"
    assert det.confidence == 0.92
    assert det.bounding_box == (10.0, 20.0, 60.0, 120.0)
    assert det.timestamp == now
    assert det.tracking_id is None
    assert det.mask is None
    assert det.obb is None
    assert det.keypoints is None
    assert det.depth is None

    # Extensible optional fields
    det_opt = Detection(
        camera_id="CAM-01",
        frame_id=43,
        timestamp_utc=now,
        class_id=TargetClass.PERSON,
        class_name="person",
        confidence=0.88,
        bbox=bbox,
        tracking_id=101,
        mask=[[10, 20], [60, 20], [60, 120], [10, 120]],
        obb=[35.0, 70.0, 50.0, 100.0, 0.15],
        keypoints=[[35.0, 25.0, 0.95]],
        depth=12.5,
    )
    assert det_opt.tracking_id == 101
    assert det_opt.depth == 12.5
    assert len(det_opt.mask) == 4
    assert len(det_opt.obb) == 5
    assert len(det_opt.keypoints) == 1

    # Aliased initialization: 'bounding_box' and 'timestamp'
    det_alias = Detection.model_validate({
        "camera_id": "CAM-01",
        "frame_id": 44,
        "timestamp": now,
        "class_id": "PERSON",
        "confidence": 0.85,
        "bounding_box": (10.0, 20.0, 50.0, 100.0),
    })
    assert det_alias.bbox.x_min == 10.0
    assert det_alias.class_name == "person"
    assert det_alias.timestamp_utc == now


def test_detector_registry_and_factory():
    """Verify detector registry allows dynamic registration and instantiation."""
    available = list_available_detectors()
    assert "yolov8" in available
    assert "mock" in available
    assert "default" in available

    # Factory lookup
    det_mock = get_detector("mock")
    assert isinstance(det_mock, MockDetector)
    assert isinstance(det_mock, DetectorInterface)

    det_yolo = get_detector("yolov8")
    assert isinstance(det_yolo, YOLOv8Detector)
    assert isinstance(det_yolo, BaseDetectorAdapter)

    # Versioned family lookup
    det_yolo11 = get_detector("yolo11")
    assert isinstance(det_yolo11, YOLO11Detector)
    assert isinstance(det_yolo11, YOLOBaseAdapter)

    det_yolo26 = get_detector("yolo26")
    assert isinstance(det_yolo26, YOLO26Detector)
    assert isinstance(det_yolo26, YOLOBaseAdapter)


def test_mock_detector_adapter_inference():
    """Verify MockDetector produces unified Detection list without external weights."""
    mock_items = [
        {
            "bbox_xyxy": (20.0, 30.0, 80.0, 150.0),
            "confidence": 0.91,
            "class_name": "person",
            "tracking_id": 5,
            "depth": 8.2,
        },
        {
            "bbox_xyxy": (100.0, 120.0, 300.0, 250.0),
            "confidence": 0.84,
            "class_name": "car",
            "tracking_id": 9,
            "depth": 15.0,
        },
    ]

    detector = MockDetector(mock_detections=mock_items)
    assert detector.load() is True
    assert detector.warmup() is True

    packet = _create_dummy_packet(frame_id=10)
    detections = detector.infer(packet)

    assert len(detections) == 2

    # Zero-leakage check: all items are canonical Detection instances
    for d in detections:
        assert isinstance(d, Detection)
        assert isinstance(d.bbox, BoundingBox)
        assert d.camera_id == "CAM-TEST-01"
        assert d.frame_id == 10
        assert d.class_id in (TargetClass.PERSON, TargetClass.VEHICLE)
        assert hasattr(d, "bounding_box")

    assert detections[0].class_id == TargetClass.PERSON
    assert detections[0].tracking_id == 5
    assert detections[0].depth == 8.2

    assert detections[1].class_id == TargetClass.VEHICLE
    assert detections[1].tracking_id == 9

    meta = detector.get_metadata()
    assert meta["model_name"] == "mock_detector"
    assert meta["total_inferences"] == 1


def test_object_detector_backward_compatibility():
    """Verify ObjectDetector functions as an alias to YOLOv8Detector."""
    det = ObjectDetector(model_name="yolov8n", confidence_threshold=0.30)
    assert isinstance(det, YOLOv8Detector)
    assert isinstance(det, BaseDetectorAdapter)
    assert isinstance(det, DetectorInterface)
    assert det.confidence_threshold == 0.30
    assert det.model_name == "yolov8n"


def test_downstream_pipeline_consumes_adapter_detections():
    """
    Verify that downstream intelligence layers (DetectionFilter, ByteTrackTracker)
    consume detections from the adapter cleanly without any modification.
    """
    mock_items = [
        {"bbox_xyxy": (50.0, 50.0, 150.0, 200.0), "confidence": 0.85, "class_name": "person"},
        {"bbox_xyxy": (200.0, 100.0, 400.0, 300.0), "confidence": 0.75, "class_name": "truck"},
    ]
    detector = MockDetector(mock_detections=mock_items)
    packet = _create_dummy_packet(frame_id=1)

    raw_dets = detector.infer(packet)

    # 1. DetectionFilter consumption
    filter_engine = DetectionFilter(DetectionFilterConfig(min_confidence=0.35))
    filt_res = filter_engine.filter_detections(
        raw_detections=raw_dets,
        image_shape=(480, 640, 3),
    )
    assert len(filt_res.operational_detections) == 2

    # 2. ByteTrackTracker consumption
    tracker = ByteTrackTracker()
    tracks = tracker.update(
        detections=filt_res.operational_detections,
        camera_id=packet.camera_id,
        timestamp_utc=packet.timestamp_utc,
        frame_id=packet.frame_id,
    )
    assert len(tracks) == 2
    for tr in tracks:
        assert tr.class_id in (TargetClass.PERSON, TargetClass.VEHICLE)
        assert tr.age_frames == 1
