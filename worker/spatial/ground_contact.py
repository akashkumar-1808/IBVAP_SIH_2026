"""
Ground-contact point estimation for IBVAP spatial intelligence.

Estimates where a tracked object contacts the ground plane from its bounding box,
then optionally maps that pixel to world coordinates using camera calibration.

Architecture Decision: DEC-0006
"""

import logging
import numpy as np
from typing import Optional, Tuple

from .world_schemas import (
    GroundContactPoint,
    GroundReferenceMethod,
    SpatialConfidence,
    WorldPoint,
)
from ..tracking.schemas import TrackState, TargetClass
from .exceptions import SpatialError

logger = logging.getLogger(__name__)


def estimate_ground_contact(
    track: TrackState,
    method: Optional[GroundReferenceMethod] = None,
) -> GroundContactPoint:
    """
    Estimates the ground-contact point from a tracked object's bounding box.

    Default methods by class:
    - PERSON: BOTTOM_CENTER (feet approximation)
    - VEHICLE: BOTTOM_CENTER (tire contact approximation)
    - ANIMAL: BOTTOM_CENTER
    - UNKNOWN: CENTER (conservative)

    For heavily occluded objects (small bbox area or lost track), confidence is marked UNCERTAIN.
    """
    # Select method based on target class if not explicitly provided
    if method is None:
        if track.class_id == TargetClass.UNKNOWN:
            method = GroundReferenceMethod.CENTER
        else:
            method = GroundReferenceMethod.BOTTOM_CENTER

    bbox = track.bbox

    if method == GroundReferenceMethod.BOTTOM_CENTER:
        gx = (bbox.x_min + bbox.x_max) / 2.0
        gy = bbox.y_max  # Bottom edge
    elif method == GroundReferenceMethod.CENTER:
        gx = (bbox.x_min + bbox.x_max) / 2.0
        gy = (bbox.y_min + bbox.y_max) / 2.0
    else:
        # CUSTOM — fall back to bottom-center
        gx = (bbox.x_min + bbox.x_max) / 2.0
        gy = bbox.y_max

    # Assess confidence
    bbox_area = (bbox.x_max - bbox.x_min) * (bbox.y_max - bbox.y_min)
    if bbox_area < 100:  # Very small bbox → likely occluded or noisy
        confidence = SpatialConfidence.UNCERTAIN
    elif track.status.value == "lost":
        confidence = SpatialConfidence.UNCERTAIN
    else:
        confidence = SpatialConfidence.VALID

    return GroundContactPoint(
        pixel_xy=(gx, gy),
        source_track_id=track.track_id,
        method=method,
        confidence=confidence,
    )


def image_to_world_ground(
    ground_contact_pixel: Tuple[float, float],
    H_inv: np.ndarray,
) -> WorldPoint:
    """
    Maps a pixel ground-contact point to world coordinates using the inverse homography.

    This assumes the ground surface is approximately planar (PLANAR_GROUND mode).
    """
    pt = np.array([ground_contact_pixel[0], ground_contact_pixel[1], 1.0], dtype=np.float64)
    result = H_inv @ pt
    w = result[2]
    if abs(w) < 1e-10:
        raise SpatialError("Inverse projection produced degenerate homogeneous coordinate (w ≈ 0)")
    return WorldPoint(x=float(result[0] / w), y=float(result[1] / w))
