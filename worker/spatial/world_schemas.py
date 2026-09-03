"""
World-space border model schemas for IBVAP spatial intelligence.

These schemas define the global border representation, camera registration,
camera calibration, projected border, ground-contact point, side determination,
and crossing detection contracts.

Architecture Decision: DEC-0006
"""

from enum import Enum
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ── Enumerations ──────────────────────────────────────────────────────────────


class CoordinateReference(str, Enum):
    """Coordinate system used for world-space border definition."""
    LOCAL_CARTESIAN = "local_cartesian"
    GPS_WGS84 = "gps_wgs84"


class TerrainMode(str, Enum):
    """Terrain model assumption for the border section."""
    PLANAR_GROUND = "planar_ground"
    TERRAIN_3D = "terrain_3d"


class CalibrationStatus(str, Enum):
    """Validity state of a camera's calibration profile."""
    CALIBRATED = "calibrated"
    UNCALIBRATED = "uncalibrated"
    STALE = "stale"
    RECALIBRATION_REQUIRED = "recalibration_required"
    INVALID = "invalid"


class CalibrationModel(str, Enum):
    """Mathematical model used for world-to-image mapping."""
    PLANAR_HOMOGRAPHY = "planar_homography"
    TERRAIN_3D_PROJECTION = "terrain_3d_projection"


class BorderSide(str, Enum):
    """Semantic classification of a point's relationship to a border."""
    PERMITTED = "permitted"
    WARNING_BUFFER = "warning_buffer"
    BORDER_LINE = "border_line"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class CrossingStatus(str, Enum):
    """State of a border crossing event."""
    NONE = "none"
    CROSSING_CANDIDATE = "crossing_candidate"
    CONFIRMED_CROSSING = "confirmed_crossing"


class GroundReferenceMethod(str, Enum):
    """Method used to estimate an object's ground-contact point from its bounding box."""
    BOTTOM_CENTER = "bottom_center"
    CENTER = "center"
    CUSTOM = "custom"


class SpatialConfidence(str, Enum):
    """Confidence level of a spatial measurement or classification."""
    VALID = "valid"
    LOW_CONFIDENCE = "low_confidence"
    UNCERTAIN = "uncertain"
    INVALID = "invalid"


# ── World-Space Models ────────────────────────────────────────────────────────


class WorldPoint(BaseModel):
    """A point in world/local Cartesian coordinate space."""
    x: float
    y: float
    z: Optional[float] = None  # Optional elevation; None for 2D planar models


class BorderSection(BaseModel):
    """
    A manageable section of the global border represented in world coordinates.
    The border is defined as an ordered polyline of world points.
    The permitted_side_normal defines which side of the border is friendly territory.
    """
    id: str = Field(..., description="Unique identifier for this border section")
    name: str = Field(..., description="Human-readable name")
    coordinate_reference: CoordinateReference = CoordinateReference.LOCAL_CARTESIAN
    points: List[WorldPoint] = Field(..., min_length=2, description="Ordered world-coordinate vertices defining the border polyline")
    permitted_side_normal: Tuple[float, float] = Field(
        ..., description="2D normal vector pointing toward the permitted/friendly side"
    )
    warning_buffer_distance: float = Field(
        default=5.0, ge=0.0,
        description="Buffer width in world units on the permitted side"
    )
    terrain_mode: TerrainMode = TerrainMode.PLANAR_GROUND
    version: str = Field(default="1.0", description="Semantic version of this border section definition")


# ── Camera Registration ──────────────────────────────────────────────────────


class CameraRegistration(BaseModel):
    """
    Registration record linking a camera to the border model.
    Declares which border sections the camera can observe and its calibration state.
    """
    camera_id: str
    location: Optional[WorldPoint] = Field(None, description="Camera position in world coordinates, if known")
    height_meters: Optional[float] = Field(None, ge=0.0, description="Camera mounting height in metres, if known")
    orientation_deg: Optional[float] = Field(None, description="Camera heading in degrees (0=North), if known")
    visible_border_sections: List[str] = Field(default_factory=list, description="IDs of border sections this camera can observe")
    calibration_profile_id: Optional[str] = None
    calibration_version: Optional[str] = None
    calibration_status: CalibrationStatus = CalibrationStatus.UNCALIBRATED


# ── Camera Calibration ────────────────────────────────────────────────────────


class CalibrationCorrespondence(BaseModel):
    """A single world-point ↔ image-pixel correspondence used for calibration."""
    world_point: WorldPoint
    image_point: Tuple[float, float] = Field(..., description="(x, y) pixel coordinates in the camera image")


class CameraCalibration(BaseModel):
    """
    Calibration profile for a camera, containing world-to-image correspondences
    and the computed transform metadata.
    """
    camera_id: str
    image_width: int = Field(..., gt=0)
    image_height: int = Field(..., gt=0)
    correspondences: List[CalibrationCorrespondence] = Field(
        ..., min_length=4,
        description="At least 4 non-collinear world-image correspondences"
    )
    calibration_model: CalibrationModel = CalibrationModel.PLANAR_HOMOGRAPHY
    calibration_version: str = Field(default="1.0")
    reprojection_error: Optional[float] = Field(None, ge=0.0, description="Mean reprojection error in pixels, if computed")
    distortion_coefficients: Optional[List[float]] = Field(None, description="Lens distortion coefficients, if available")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: CalibrationStatus = CalibrationStatus.UNCALIBRATED


# ── Projected Border ──────────────────────────────────────────────────────────


class ProjectedBorder(BaseModel):
    """
    The image-space projection of a world border section through a camera calibration.
    This is a DERIVED VIEW — the source of truth remains the world BorderSection.
    """
    camera_id: str
    border_section_id: str
    projected_points: List[Tuple[float, float]] = Field(
        ..., description="Projected (x, y) pixel coordinates of the border polyline in the camera image"
    )
    warning_buffer_points: Optional[List[Tuple[float, float]]] = Field(
        None, description="Projected buffer boundary pixels, if applicable"
    )
    validity: SpatialConfidence = SpatialConfidence.VALID
    calibration_version: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Ground-Contact Point ─────────────────────────────────────────────────────


class GroundContactPoint(BaseModel):
    """
    Estimated ground-contact point for a tracked object.
    This is an approximation — it does NOT claim exact foot position.
    """
    pixel_xy: Tuple[float, float] = Field(..., description="Estimated ground-contact pixel coordinates")
    world_xy: Optional[Tuple[float, float]] = Field(None, description="World-space ground position, if calibration available")
    source_track_id: int
    method: GroundReferenceMethod = GroundReferenceMethod.BOTTOM_CENTER
    confidence: SpatialConfidence = SpatialConfidence.VALID

    @property
    def x(self) -> float:
        return float(self.pixel_xy[0])

    @property
    def y(self) -> float:
        return float(self.pixel_xy[1])


# ── Crossing Event ────────────────────────────────────────────────────────────


class CrossingEvent(BaseModel):
    """
    A border crossing event detected from track trajectory analysis.
    Transitions through CROSSING_CANDIDATE → CONFIRMED_CROSSING with multi-frame confirmation.
    """
    border_section_id: str
    track_id: int
    camera_id: str
    timestamp_utc: datetime
    previous_side: BorderSide
    current_side: BorderSide
    crossing_status: CrossingStatus = CrossingStatus.CROSSING_CANDIDATE
    ground_point: Optional[GroundContactPoint] = None
    calibration_version: Optional[str] = None


__all__ = [
    "CoordinateReference",
    "TerrainMode",
    "CalibrationStatus",
    "CalibrationModel",
    "BorderSide",
    "CrossingStatus",
    "GroundReferenceMethod",
    "SpatialConfidence",
    "WorldPoint",
    "BorderSection",
    "CameraRegistration",
    "CalibrationCorrespondence",
    "CameraCalibration",
    "ProjectedBorder",
    "GroundContactPoint",
    "CrossingEvent",
]
