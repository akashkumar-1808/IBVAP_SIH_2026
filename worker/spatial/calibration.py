"""
Camera calibration engine for IBVAP world-border model.

Provides planar homography computation, world-to-image and image-to-world
projection, calibration validation, and border section projection.

Architecture Decision: DEC-0006
"""

import logging
import math
from typing import List, Tuple, Optional
import numpy as np
import cv2

from .world_schemas import (
    CameraCalibration,
    CalibrationCorrespondence,
    CalibrationStatus,
    CalibrationModel,
    TerrainMode,
    BorderSection,
    ProjectedBorder,
    WorldPoint,
    SpatialConfidence,
)
from .exceptions import SpatialError, InvalidGeometryError, ConfigurationError

logger = logging.getLogger(__name__)

# Maximum acceptable mean reprojection error (pixels) for CALIBRATED status
MAX_ACCEPTABLE_REPROJ_ERROR = 5.0


class CalibrationError(SpatialError):
    """Raised when calibration computation or validation fails."""
    pass


class TerrainModeNotImplementedError(SpatialError):
    """Raised when TERRAIN_3D mode is requested but not yet implemented."""
    pass


def compute_homography(
    correspondences: List[CalibrationCorrespondence],
) -> Tuple[np.ndarray, float]:
    """
    Computes a planar homography matrix from world-to-image point correspondences.

    Requires at least 4 non-collinear correspondences.
    Uses OpenCV findHomography with RANSAC for robustness.

    Returns:
        (H_matrix, mean_reprojection_error)
    """
    if len(correspondences) < 4:
        raise CalibrationError(
            f"At least 4 correspondences required for homography; got {len(correspondences)}"
        )

    # Build source (world) and destination (image) point arrays
    src_pts = np.array(
        [[c.world_point.x, c.world_point.y] for c in correspondences],
        dtype=np.float64,
    )
    dst_pts = np.array(
        [[c.image_point[0], c.image_point[1]] for c in correspondences],
        dtype=np.float64,
    )

    # Check for collinearity: at least 3 points must not be collinear
    _check_non_collinear(src_pts, label="world")
    _check_non_collinear(dst_pts, label="image")

    # Compute homography
    method = cv2.RANSAC if len(correspondences) > 4 else 0
    H, mask = cv2.findHomography(src_pts, dst_pts, method=method, ransacReprojThreshold=3.0)

    if H is None:
        raise CalibrationError("Homography computation failed — degenerate point configuration")

    # Verify finite
    if not np.all(np.isfinite(H)):
        raise CalibrationError("Computed homography contains non-finite values")

    # Compute mean reprojection error
    reproj_error = _compute_reprojection_error(src_pts, dst_pts, H)

    return H, reproj_error


def _check_non_collinear(pts: np.ndarray, label: str = "points") -> None:
    """Verifies that the point set contains at least 3 non-collinear points."""
    if len(pts) < 3:
        return  # Will be caught by minimum correspondence check

    for i in range(len(pts) - 2):
        for j in range(i + 1, len(pts) - 1):
            for k in range(j + 1, len(pts)):
                # Cross product of vectors (j-i) and (k-i)
                v1 = pts[j] - pts[i]
                v2 = pts[k] - pts[i]
                cross = abs(v1[0] * v2[1] - v1[1] * v2[0])
                if cross > 1e-6:
                    return  # Found non-collinear triple

    raise CalibrationError(f"All {label} points are collinear — cannot compute homography")


def _compute_reprojection_error(
    src_pts: np.ndarray,
    dst_pts: np.ndarray,
    H: np.ndarray,
) -> float:
    """Computes mean Euclidean reprojection error."""
    n = len(src_pts)
    src_h = np.hstack([src_pts, np.ones((n, 1))])  # [x, y, 1]
    projected = (H @ src_h.T).T  # [n, 3]

    # Normalize by homogeneous coordinate
    w = projected[:, 2:3]
    w = np.where(np.abs(w) < 1e-10, 1e-10, w)
    projected_xy = projected[:, :2] / w

    errors = np.sqrt(np.sum((projected_xy - dst_pts) ** 2, axis=1))
    return float(np.mean(errors))


def project_world_to_image(
    world_point: WorldPoint,
    H: np.ndarray,
) -> Tuple[float, float]:
    """Projects a world-space point to image-space pixel coordinates using homography H."""
    pt = np.array([world_point.x, world_point.y, 1.0], dtype=np.float64)
    result = H @ pt
    w = result[2]
    if abs(w) < 1e-10:
        raise CalibrationError("Projection produced degenerate homogeneous coordinate (w ≈ 0)")
    return float(result[0] / w), float(result[1] / w)


def project_image_to_world(
    image_point: Tuple[float, float],
    H_inv: np.ndarray,
) -> WorldPoint:
    """Projects an image-space pixel to world-space coordinates using inverse homography."""
    pt = np.array([image_point[0], image_point[1], 1.0], dtype=np.float64)
    result = H_inv @ pt
    w = result[2]
    if abs(w) < 1e-10:
        raise CalibrationError("Inverse projection produced degenerate homogeneous coordinate (w ≈ 0)")
    return WorldPoint(x=float(result[0] / w), y=float(result[1] / w))


def validate_calibration(calibration: CameraCalibration) -> CalibrationStatus:
    """
    Validates a calibration profile and returns the appropriate status.

    Checks:
    - Sufficient correspondences (≥ 4)
    - Non-degenerate geometry (non-collinear points)
    - Finite coordinates
    - Valid image dimensions
    - Transform existence (homography is computable)
    - Reprojection error within acceptable bounds
    """
    # Check terrain mode
    if calibration.calibration_model == CalibrationModel.TERRAIN_3D_PROJECTION:
        raise TerrainModeNotImplementedError(
            "TERRAIN_3D calibration model is not yet implemented. "
            "Only PLANAR_HOMOGRAPHY is supported in this prototype."
        )

    # Sufficient correspondences
    if len(calibration.correspondences) < 4:
        return CalibrationStatus.INVALID

    # Valid image dimensions
    if calibration.image_width <= 0 or calibration.image_height <= 0:
        return CalibrationStatus.INVALID

    # Finite coordinates
    for corr in calibration.correspondences:
        if not (math.isfinite(corr.world_point.x) and math.isfinite(corr.world_point.y)):
            return CalibrationStatus.INVALID
        if not (math.isfinite(corr.image_point[0]) and math.isfinite(corr.image_point[1])):
            return CalibrationStatus.INVALID

    # Try computing homography
    try:
        H, reproj_error = compute_homography(calibration.correspondences)
    except (CalibrationError, InvalidGeometryError):
        return CalibrationStatus.INVALID

    # Reprojection error check
    if reproj_error > MAX_ACCEPTABLE_REPROJ_ERROR:
        return CalibrationStatus.STALE  # High error = stale / unreliable

    return CalibrationStatus.CALIBRATED


def project_border_to_camera(
    border_section: BorderSection,
    calibration: CameraCalibration,
    H: Optional[np.ndarray] = None,
) -> ProjectedBorder:
    """
    Projects a world-space border section into camera image coordinates.

    If H is not provided, it is computed from calibration correspondences.
    """
    if border_section.terrain_mode == TerrainMode.TERRAIN_3D:
        raise TerrainModeNotImplementedError(
            "TERRAIN_3D border projection is not yet implemented. "
            "Only PLANAR_GROUND mode is supported."
        )

    if H is None:
        H, _ = compute_homography(calibration.correspondences)

    # Project border points
    projected_pts: List[Tuple[float, float]] = []
    validity = SpatialConfidence.VALID

    for wp in border_section.points:
        try:
            px, py = project_world_to_image(wp, H)
            # Check if projected point is within reasonable image bounds (with margin)
            margin = 500  # Allow points slightly outside frame
            if not (-margin <= px <= calibration.image_width + margin and
                    -margin <= py <= calibration.image_height + margin):
                validity = SpatialConfidence.LOW_CONFIDENCE
            projected_pts.append((px, py))
        except CalibrationError:
            validity = SpatialConfidence.INVALID
            projected_pts.append((0.0, 0.0))

    # Project warning buffer boundary (offset border by buffer distance along normal)
    buffer_pts: Optional[List[Tuple[float, float]]] = None
    if border_section.warning_buffer_distance > 0:
        nx, ny = border_section.permitted_side_normal
        n_len = math.hypot(nx, ny)
        if n_len > 1e-6:
            nx_unit = nx / n_len
            ny_unit = ny / n_len
            buf_dist = border_section.warning_buffer_distance
            buffer_world_pts = [
                WorldPoint(x=wp.x + nx_unit * buf_dist, y=wp.y + ny_unit * buf_dist)
                for wp in border_section.points
            ]
            buffer_pts = []
            for bwp in buffer_world_pts:
                try:
                    bx, by = project_world_to_image(bwp, H)
                    buffer_pts.append((bx, by))
                except CalibrationError:
                    buffer_pts.append((0.0, 0.0))
                    validity = SpatialConfidence.LOW_CONFIDENCE

    return ProjectedBorder(
        camera_id=calibration.camera_id,
        border_section_id=border_section.id,
        projected_points=projected_pts,
        warning_buffer_points=buffer_pts,
        validity=validity,
        calibration_version=calibration.calibration_version,
    )
