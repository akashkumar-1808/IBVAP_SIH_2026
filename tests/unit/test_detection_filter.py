import cv2
"""
Unit tests for Basic Detection Quality and Operational Stabilization Filter.
Verifies TargetClass.UNKNOWN isolation, geometric checks, camera motion estimation,
and adaptive confidence gating.
"""

import numpy as np
import pytest
from datetime import datetime, timezone

from backend.app.schemas.common import TargetClass
from backend.app.schemas.events import BoundingBox, Detection
from worker.perception.filter import (
    DetectionFilter,
    DetectionFilterConfig,
    CameraMotionEstimator,
    CameraMotionState,
    CameraMotionInfo,
)


def _make_detection(
    class_id: TargetClass = TargetClass.PERSON,
    confidence: float = 0.85,
    x_min: float = 100.0,
    y_min: float = 100.0,
    x_max: float = 200.0,
    y_max: float = 300.0,
    raw_class: str = "person",
) -> Detection:
    return Detection(
        camera_id="TEST-CAM-01",
        frame_id=1,
        timestamp_utc=datetime.now(timezone.utc),
        class_id=class_id,
        confidence=confidence,
        bbox=BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max),
        metadata={"raw_class_name": raw_class},
    )


def test_unknown_class_rejected_from_operational_but_preserved_in_raw():
    """Verifies TargetClass.UNKNOWN is never sent to ByteTrack, but preserved in raw_detections."""
    filter_obj = DetectionFilter()

    det_person = _make_detection(class_id=TargetClass.PERSON, confidence=0.90, raw_class="person")
    det_unknown = _make_detection(class_id=TargetClass.UNKNOWN, confidence=0.95, raw_class="backpack")
    det_vehicle = _make_detection(class_id=TargetClass.VEHICLE, confidence=0.80, raw_class="car")

    raw = [det_person, det_unknown, det_vehicle]
    result = filter_obj.filter_detections(raw, image_shape=(1080, 1920))

    assert len(result.raw_detections) == 3
    assert len(result.operational_detections) == 2
    assert len(result.filtered_out_detections) == 1

    # Check operational target classes
    op_classes = [d.class_id for d in result.operational_detections]
    assert TargetClass.PERSON in op_classes
    assert TargetClass.VEHICLE in op_classes
    assert TargetClass.UNKNOWN not in op_classes

    # Stats validation
    assert result.stats["unknown_class_rejected"] == 1
    assert result.stats["total_operational"] == 2


def test_valid_target_classes_allowed():
    """Verifies PERSON, VEHICLE, and ANIMAL all pass quality filter."""
    filter_obj = DetectionFilter()

    raw = [
        _make_detection(class_id=TargetClass.PERSON, confidence=0.75, raw_class="person"),
        _make_detection(class_id=TargetClass.VEHICLE, confidence=0.70, raw_class="truck"),
        _make_detection(class_id=TargetClass.ANIMAL, confidence=0.65, raw_class="dog"),
    ]

    result = filter_obj.filter_detections(raw, image_shape=(1080, 1920))
    assert len(result.operational_detections) == 3


def test_geometric_validation_rejects_invalid_boxes():
    """Verifies zero-width, inverted, sub-minimum, and out-of-bounds boxes are filtered out."""
    filter_obj = DetectionFilter(DetectionFilterConfig(min_bbox_width=10.0, min_bbox_height=10.0, min_bbox_area=100.0))

    # 1. Zero/inverted width
    det_zero_w = _make_detection(x_min=100.0, x_max=100.0, y_min=100.0, y_max=200.0)
    # 2. Inverted height
    det_inv_h = _make_detection(x_min=50.0, x_max=100.0, y_min=200.0, y_max=100.0)
    # 3. Tiny box below min area (e.g. 5x5 = 25 px)
    det_tiny = _make_detection(x_min=50.0, x_max=55.0, y_min=50.0, y_max=55.0)
    # 4. Completely outside frame
    det_out = _make_detection(x_min=2000.0, x_max=2100.0, y_min=100.0, y_max=200.0)
    # 5. Valid normal box
    det_valid = _make_detection(x_min=50.0, x_max=150.0, y_min=50.0, y_max=200.0)

    raw = [det_zero_w, det_inv_h, det_tiny, det_out, det_valid]
    result = filter_obj.filter_detections(raw, image_shape=(1080, 1920))

    assert len(result.operational_detections) == 1
    assert result.operational_detections[0].confidence == det_valid.confidence
    assert result.stats["geometric_invalid_rejected"] == 4


def test_confidence_threshold_stationary_camera():
    """Verifies stationary camera uses baseline min_confidence."""
    filter_obj = DetectionFilter(DetectionFilterConfig(min_confidence=0.40))

    det_low = _make_detection(confidence=0.30)
    det_borderline = _make_detection(confidence=0.45)
    det_high = _make_detection(confidence=0.85)

    motion = CameraMotionInfo(state=CameraMotionState.STABLE, is_moving=False)
    result = filter_obj.filter_detections([det_low, det_borderline, det_high], (1080, 1920), camera_motion=motion)

    assert len(result.operational_detections) == 2
    assert result.stats["low_confidence_rejected"] == 1


def test_camera_motion_adaptive_confidence_gating():
    """Verifies moving camera requires higher confidence (>=0.60) to suppress transient shake noise."""
    filter_obj = DetectionFilter(DetectionFilterConfig(min_confidence=0.35, moving_camera_min_confidence=0.60))

    det_weak = _make_detection(confidence=0.45)  # valid when stable, suppressed when moving
    det_strong = _make_detection(confidence=0.80)  # valid in both states

    # 1. Stationary Camera: both pass
    stable_motion = CameraMotionInfo(state=CameraMotionState.STABLE, is_moving=False)
    stable_result = filter_obj.filter_detections([det_weak, det_strong], (1080, 1920), camera_motion=stable_motion)
    assert len(stable_result.operational_detections) == 2

    # 2. Moving Camera: weak detection suppressed from operational tracking
    moving_motion = CameraMotionInfo(state=CameraMotionState.MOVING, is_moving=True, motion_magnitude=4.2)
    moving_result = filter_obj.filter_detections([det_weak, det_strong], (1080, 1920), camera_motion=moving_motion)
    assert len(moving_result.operational_detections) == 1
    assert moving_result.operational_detections[0].confidence == 0.80
    assert moving_result.stats["low_confidence_rejected"] == 1


def test_camera_motion_estimator_static_vs_translated():
    """Verifies CameraMotionEstimator detects stationary vs translated camera frames."""
    estimator = CameraMotionEstimator(motion_threshold=2.0)

    # Frame 1: Base synthetic gradient frame with rich corners
    h, w = 480, 640
    frame1 = np.zeros((h, w, 3), dtype=np.uint8)
    for i in range(10, 400, 40):
        for j in range(10, 600, 40):
            cv2.rectangle(frame1, (j, i), (j + 20, i + 20), (200, 200, 200), -1)

    info1 = estimator.update(frame1)
    assert info1.state == CameraMotionState.STABLE
    assert info1.is_moving is False

    # Frame 2: Identical frame (stationary)
    info2 = estimator.update(frame1)
    assert info2.state == CameraMotionState.STABLE
    assert info2.motion_magnitude < 0.5

    # Frame 3: Translated frame (simulated camera pan of 15 pixels)
    M = np.float32([[1, 0, 15], [0, 1, 0]])
    frame3 = cv2.warpAffine(frame1, M, (w, h))

    info3 = estimator.update(frame3)
    # Motion should be detected
    assert info3.motion_magnitude > 1.5
