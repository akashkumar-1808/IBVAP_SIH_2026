"""
Unit tests for multi-family Ultralytics YOLO support (YOLOv8, YOLO11, YOLO26).

Verifies:
1. Central ModelConfig and path resolution across families.
2. Dynamic instantiation of YOLOv8Detector, YOLO11Detector, and YOLO26Detector.
3. Single-load lifecycle and incremental frame-by-frame processing.
4. Normalized Detection output and class mapping preservation.
5. Strict isolation of YOLO26 as a 2D object detector (no behavior leakage).
6. Explicit compatibility error handling without silent model substitution.
"""

import os
import pytest
import numpy as np
from datetime import datetime, timezone
from typing import List

from backend.app.schemas.common import TargetClass
from backend.app.schemas.events import Detection, BoundingBox
from worker.ingestion.frame import FramePacket
from worker.perception.config import ModelConfig, resolve_model_config, resolve_model_weights
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
    create_detector_from_config,
    list_available_detectors,
)
from worker.perception.exceptions import (
    ModelCompatibilityError,
    ModelLoadError,
    InvalidInputError,
)
from worker.perception.filter import DetectionFilter, DetectionFilterConfig
from worker.tracking.tracker import ByteTrackTracker


def _create_frame(frame_id: int = 1, width: int = 640, height: int = 480) -> FramePacket:
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # Add a simulated bright square in center to allow mock or edge features
    img[100:200, 100:200, :] = 200
    return FramePacket(
        camera_id="CAM-MULTI-01",
        frame_id=frame_id,
        timestamp_utc=datetime.now(timezone.utc),
        image=img,
        width=width,
        height=height,
    )


def test_central_model_config_resolution():
    """Verify central resolve_model_config handles defaults and environment overrides."""
    # Default resolution
    cfg_default = resolve_model_config()
    assert cfg_default.model_type == "yolov8"
    assert cfg_default.confidence_threshold == 0.35
    assert cfg_default.iou_threshold == 0.45

    # Explicit resolution for YOLO11
    cfg_11 = resolve_model_config(model_type="yolo11", confidence_threshold=0.50)
    assert cfg_11.model_type == "yolo11"
    assert cfg_11.confidence_threshold == 0.50
    assert "yolo11" in cfg_11.model_weights

    # Explicit resolution for YOLO26
    cfg_26 = resolve_model_config(model_type="yolo26", confidence_threshold=0.40)
    assert cfg_26.model_type == "yolo26"
    assert cfg_26.confidence_threshold == 0.40
    assert "yolo26" in cfg_26.model_weights

    # Environment variable overrides
    os.environ["MODEL_TYPE"] = "yolo26"
    os.environ["CONFIDENCE_THRESHOLD"] = "0.42"
    try:
        cfg_env = resolve_model_config()
        assert cfg_env.model_type == "yolo26"
        assert cfg_env.confidence_threshold == 0.42
    finally:
        del os.environ["MODEL_TYPE"]
        del os.environ["CONFIDENCE_THRESHOLD"]


def test_model_family_registration_and_instantiation():
    """Verify YOLOv8, YOLO11, and YOLO26 are registered and instantiable."""
    available = list_available_detectors()
    assert "yolov8" in available
    assert "yolo11" in available
    assert "yolo26" in available
    assert "rtdetr" in available

    det_v8 = get_detector("yolov8")
    assert isinstance(det_v8, YOLOv8Detector)
    assert det_v8.model_type == "yolov8"

    det_11 = get_detector("yolo11")
    assert isinstance(det_11, YOLO11Detector)
    assert det_11.model_type == "yolo11"

    det_26 = get_detector("yolo26")
    assert isinstance(det_26, YOLO26Detector)
    assert det_26.model_type == "yolo26"

    # Instantiate from ModelConfig
    cfg = ModelConfig(model_type="yolo26", confidence_threshold=0.38, iou_threshold=0.50)
    det_from_cfg = create_detector_from_config(cfg)
    assert isinstance(det_from_cfg, YOLO26Detector)
    assert det_from_cfg.confidence_threshold == 0.38
    assert det_from_cfg.iou_threshold == 0.50


def test_single_load_and_incremental_processing():
    """Verify that models are loaded once and process frames incrementally without reloading."""
    # Test using MockDetector subclass to strictly verify load count
    class TrackingMock(MockDetector):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.load_count = 0

        def load(self, model_path=None):
            self.load_count += 1
            self._is_loaded = True
            return True

    det = TrackingMock(
        model_name="mock_single_load",
        mock_detections=[{"bbox_xyxy": (10.0, 10.0, 50.0, 50.0), "confidence": 0.90, "class_name": "person"}],
    )

    # Initial explicit load
    det.load()
    assert det.load_count == 1
    assert det._is_loaded is True

    # Process 5 sequential frames
    for f_id in range(1, 6):
        pkt = _create_frame(frame_id=f_id)
        res = det.infer(pkt)
        assert len(res) == 1
        assert res[0].frame_id == f_id
        # Model must NOT be reloaded on each frame!
        assert det.load_count == 1

    meta = det.get_metadata()
    assert meta["total_inferences"] == 5
    assert det.load_count == 1


def test_normalized_detection_output_and_class_mapping():
    """Verify all detector adapters produce normalized Detection objects with accurate class mapping."""
    mock_items = [
        {"bbox_xyxy": (10.0, 20.0, 80.0, 150.0), "confidence": 0.95, "class_name": "person"},
        {"bbox_xyxy": (120.0, 80.0, 300.0, 240.0), "confidence": 0.88, "class_name": "car"},
        {"bbox_xyxy": (400.0, 300.0, 500.0, 420.0), "confidence": 0.76, "class_name": "dog"},
    ]
    det = MockDetector(mock_detections=mock_items)

    packet = _create_frame(frame_id=101)
    dets = det.infer(packet)

    assert len(dets) == 3

    # Check 1: PERSON mapping
    assert dets[0].class_id == TargetClass.PERSON
    assert dets[0].class_name == "person"
    assert dets[0].bounding_box == (10.0, 20.0, 80.0, 150.0)
    assert dets[0].bbox.x1 == 10.0
    assert dets[0].bbox.y1 == 20.0

    # Check 2: VEHICLE mapping
    assert dets[1].class_id == TargetClass.VEHICLE
    assert dets[1].class_name == "car"

    # Check 3: ANIMAL mapping
    assert dets[2].class_id == TargetClass.ANIMAL
    assert dets[2].class_name == "dog"


def test_confidence_filtering():
    """Verify confidence filtering threshold correctly drops low-confidence detections."""
    mock_items = [
        {"bbox_xyxy": (10.0, 10.0, 50.0, 50.0), "confidence": 0.90, "class_name": "person"},
        {"bbox_xyxy": (60.0, 60.0, 100.0, 100.0), "confidence": 0.40, "class_name": "car"},
        {"bbox_xyxy": (120.0, 120.0, 180.0, 180.0), "confidence": 0.20, "class_name": "dog"},
    ]

    # Detector with high confidence threshold (0.50)
    det_high = MockDetector(confidence_threshold=0.50, mock_detections=mock_items)
    pkt = _create_frame(frame_id=1)
    res_high = det_high.infer(pkt)
    assert len(res_high) == 1
    assert res_high[0].confidence == 0.90

    # Detector with lower threshold (0.35)
    det_low = MockDetector(confidence_threshold=0.35, mock_detections=mock_items)
    res_low = det_low.infer(pkt)
    assert len(res_low) == 2


def test_yolo26_object_detection_isolation():
    """
    Verify that YOLO26 is integrated strictly for 2D object detection.
    Ensure no direct behavior detection is claimed on the detector itself,
    and that downstream tracker correctly processes YOLO26 detections.
    """
    det_26 = YOLO26Detector(
        model_name="yolo26_sim",
        model_path="models/detector/yolo26n.pt",
        confidence_threshold=0.35,
    )
    assert det_26.model_type == "yolo26"

    # Verify adapter docstring and metadata explicitly note 2D object detection
    assert "object detection" in det_26.__class__.__doc__.lower()
    meta = det_26.get_metadata()
    assert meta["model_type"] == "yolo26"

    # Feed synthetic detections from YOLO26 adapter into ByteTrack to verify downstream independence
    mock_dets = [
        det_26.create_unified_detection(
            frame_packet=_create_frame(frame_id=1),
            bbox_xyxy=(50.0, 50.0, 120.0, 200.0),
            confidence=0.89,
            raw_class_name="person",
        )
    ]
    tracker = ByteTrackTracker()
    tracks = tracker.update(mock_dets, camera_id="CAM-01", timestamp_utc=datetime.now(timezone.utc), frame_id=1)
    assert len(tracks) == 1
    assert tracks[0].class_id == TargetClass.PERSON
    assert tracks[0].track_id == 1


def test_explicit_compatibility_error_handling():
    """
    Verify that an invalid architecture or incompatible model raises ModelCompatibilityError
    or ModelLoadError without silently substituting another model.
    """
    class IncompatibleRuntimeAdapter(YOLOBaseAdapter):
        def load(self, model_path=None):
            # Simulate Ultralytics unsupported model architecture exception
            exc = ValueError("Model architecture 'YOLO99-Unrecognized' is not supported by Ultralytics v8.4.37")
            raise ModelCompatibilityError(f"Compatibility error: {exc}")

    det_incompat = IncompatibleRuntimeAdapter(
        model_name="yolo99_future",
        model_type="yolo99",
        model_path="models/detector/yolo99.pt",
    )

    with pytest.raises(ModelCompatibilityError) as exc_info:
        det_incompat.load()

    assert "Compatibility error" in str(exc_info.value)
    assert det_incompat._is_loaded is False


def test_yolov8_and_yolo11_functional_with_adapter():
    """Verify that YOLOv8 and YOLO11 load and infer valid detections on dummy frame."""
    # YOLOv8
    det_v8 = YOLOv8Detector(model_name="yolov8n", confidence_threshold=0.35)
    det_v8.load()
    assert det_v8._is_loaded is True
    pkt = _create_frame(frame_id=1)
    dets_v8 = det_v8.infer(pkt)
    assert isinstance(dets_v8, list)

    # YOLO11
    det_11 = YOLO11Detector(model_name="yolo11n", confidence_threshold=0.35)
    det_11.load()
    assert det_11._is_loaded is True
    dets_11 = det_11.infer(pkt)
    assert isinstance(dets_11, list)
