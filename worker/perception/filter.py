"""
Basic Detection Stabilization and Quality Filter for IBVAP Perception.

Filters raw YOLO detections before reaching ByteTrack:
1. Filters out TargetClass.UNKNOWN detections from operational tracking,
   while preserving all raw detections for forensic logging and diagnostics.
2. Applies basic quality and geometric validation (non-zero area, valid image bounds,
   minimum size thresholds).
3. Performs lightweight camera motion estimation (STABLE vs. MOVING).
4. When camera is moving, applies conservative confidence gating to suppress
   transient background artifacts from immediately creating candidate tracks.

Architecture Decision: DEC-0012
"""

import cv2
import numpy as np
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional, Dict, Any, Set

from .schemas import Detection, BoundingBox, TargetClass

logger = logging.getLogger(__name__)


class CameraMotionState(str, Enum):
    STABLE = "STABLE"
    MOVING = "MOVING"


@dataclass
class CameraMotionInfo:
    state: CameraMotionState = CameraMotionState.STABLE
    is_moving: bool = False
    motion_magnitude: float = 0.0
    valid_features_count: int = 0


@dataclass
class DetectionFilterConfig:
    min_confidence: float = 0.35
    moving_camera_min_confidence: float = 0.60
    min_bbox_width: float = 8.0
    min_bbox_height: float = 8.0
    min_bbox_area: float = 64.0
    allowed_operational_classes: Set[TargetClass] = field(
        default_factory=lambda: {TargetClass.PERSON, TargetClass.VEHICLE, TargetClass.ANIMAL}
    )
    motion_threshold_pixels: float = 2.5
    motion_smoothing_alpha: float = 0.6


@dataclass
class FilterResult:
    raw_detections: List[Detection]
    operational_detections: List[Detection]
    filtered_out_detections: List[Detection]
    camera_motion: CameraMotionInfo
    stats: Dict[str, Any] = field(default_factory=dict)


class CameraMotionEstimator:
    """
    Ultra-lightweight inter-frame motion estimator.
    Downscales frames to a low-res thumbnail (~160x120) and computes sparse feature displacement.
    Execution latency is typically <0.4ms on CPU.
    """

    def __init__(
        self,
        motion_threshold: float = 2.5,
        smoothing_alpha: float = 0.6,
        thumbnail_size: Tuple[int, int] = (160, 120),
    ):
        self.motion_threshold = motion_threshold
        self.smoothing_alpha = smoothing_alpha
        self.thumbnail_size = thumbnail_size
        self._prev_gray: Optional[np.ndarray] = None
        self._smoothed_motion: float = 0.0

    def reset(self) -> None:
        self._prev_gray = None
        self._smoothed_motion = 0.0

    def update(self, frame: np.ndarray) -> CameraMotionInfo:
        if frame is None or frame.size == 0:
            return CameraMotionInfo(
                state=CameraMotionState.STABLE,
                is_moving=False,
                motion_magnitude=self._smoothed_motion,
                valid_features_count=0,
            )

        # Convert to small grayscale thumbnail
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        small_gray = cv2.resize(gray, self.thumbnail_size, interpolation=cv2.INTER_LINEAR)

        if self._prev_gray is None:
            self._prev_gray = small_gray
            return CameraMotionInfo(
                state=CameraMotionState.STABLE,
                is_moving=False,
                motion_magnitude=0.0,
                valid_features_count=0,
            )

        # Detect good features in previous thumbnail
        p0 = cv2.goodFeaturesToTrack(
            self._prev_gray,
            maxCorners=50,
            qualityLevel=0.05,
            minDistance=10,
            blockSize=5,
        )

        motion_mag = 0.0
        valid_features = 0

        if p0 is not None and len(p0) >= 4:
            p1, st, err = cv2.calcOpticalFlowPyrLK(
                self._prev_gray,
                small_gray,
                p0,
                None,
                winSize=(15, 15),
                maxLevel=2,
                criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03),
            )

            if p1 is not None and st is not None:
                good_old = p0[st == 1]
                good_new = p1[st == 1]

                if len(good_old) >= 4:
                    displacement = np.linalg.norm(good_new - good_old, axis=1)
                    motion_mag = float(np.median(displacement))
                    valid_features = len(good_old)

        self._prev_gray = small_gray

        # Exponential smoothing
        self._smoothed_motion = (
            self.smoothing_alpha * motion_mag + (1.0 - self.smoothing_alpha) * self._smoothed_motion
        )

        is_moving = self._smoothed_motion >= self.motion_threshold
        state = CameraMotionState.MOVING if is_moving else CameraMotionState.STABLE

        return CameraMotionInfo(
            state=state,
            is_moving=is_moving,
            motion_magnitude=round(self._smoothed_motion, 2),
            valid_features_count=valid_features,
        )


class DetectionFilter:
    """
    Basic Detection Quality and Operational Stabilization Filter.
    Ensures only verified, non-UNKNOWN, quality target detections proceed to ByteTrack.
    """

    def __init__(
        self,
        config: Optional[DetectionFilterConfig] = None,
        motion_estimator: Optional[CameraMotionEstimator] = None,
    ):
        self.config = config or DetectionFilterConfig()
        self.motion_estimator = motion_estimator or CameraMotionEstimator(
            motion_threshold=self.config.motion_threshold_pixels,
            smoothing_alpha=self.config.motion_smoothing_alpha,
        )

    def filter_detections(
        self,
        raw_detections: List[Detection],
        image_shape: Tuple[int, ...],
        camera_motion: Optional[CameraMotionInfo] = None,
    ) -> FilterResult:
        """
        Filters a list of raw detections for a given frame.
        """
        img_h, img_w = image_shape[:2] if len(image_shape) >= 2 else (1080, 1920)

        motion_info = camera_motion or CameraMotionInfo(
            state=CameraMotionState.STABLE,
            is_moving=False,
            motion_magnitude=0.0,
            valid_features_count=0,
        )

        # Dynamic confidence threshold based on camera motion
        effective_min_conf = (
            self.config.moving_camera_min_confidence
            if motion_info.is_moving
            else self.config.min_confidence
        )

        operational: List[Detection] = []
        filtered_out: List[Detection] = []

        unknown_count = 0
        low_conf_count = 0
        geom_invalid_count = 0

        for det in raw_detections:
            # 1. Target Class Check: UNKNOWN is never operational
            if det.class_id not in self.config.allowed_operational_classes:
                unknown_count += 1
                filtered_out.append(det)
                continue

            # 2. Geometric Sanity Check
            bbox = det.bbox
            w = bbox.x_max - bbox.x_min
            h = bbox.y_max - bbox.y_min

            if w <= 0 or h <= 0:
                geom_invalid_count += 1
                filtered_out.append(det)
                continue

            if w < self.config.min_bbox_width or h < self.config.min_bbox_height:
                geom_invalid_count += 1
                filtered_out.append(det)
                continue

            area = w * h
            if area < self.config.min_bbox_area:
                geom_invalid_count += 1
                filtered_out.append(det)
                continue

            # Check if completely outside frame boundaries
            if bbox.x_max <= 0 or bbox.y_max <= 0 or bbox.x_min >= img_w or bbox.y_min >= img_h:
                geom_invalid_count += 1
                filtered_out.append(det)
                continue

            # 3. Confidence Check (adaptive to camera movement)
            if det.confidence < effective_min_conf:
                low_conf_count += 1
                filtered_out.append(det)
                continue

            # Clamping bounding box to reasonable frame boundaries
            clamped_bbox = BoundingBox(
                x_min=max(0.0, float(bbox.x_min)),
                y_min=max(0.0, float(bbox.y_min)),
                x_max=min(float(img_w), float(bbox.x_max)),
                y_max=min(float(img_h), float(bbox.y_max)),
            )

            # Create operational detection copy with clamped bbox and filter metadata
            op_det = Detection(
                camera_id=det.camera_id,
                frame_id=det.frame_id,
                timestamp_utc=det.timestamp_utc,
                class_id=det.class_id,
                confidence=det.confidence,
                bbox=clamped_bbox,
                metadata={
                    **det.metadata,
                    "is_operational": True,
                    "camera_motion_state": motion_info.state.value,
                    "effective_min_conf": effective_min_conf,
                },
            )
            operational.append(op_det)

        stats = {
            "total_raw": len(raw_detections),
            "total_operational": len(operational),
            "total_filtered": len(filtered_out),
            "unknown_class_rejected": unknown_count,
            "low_confidence_rejected": low_conf_count,
            "geometric_invalid_rejected": geom_invalid_count,
            "camera_motion_state": motion_info.state.value,
            "motion_magnitude": motion_info.motion_magnitude,
        }

        return FilterResult(
            raw_detections=raw_detections,
            operational_detections=operational,
            filtered_out_detections=filtered_out,
            camera_motion=motion_info,
            stats=stats,
        )
