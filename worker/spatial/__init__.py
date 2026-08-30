from .base import SpatialEngineInterface
from .schemas import (
    MovementDirection,
    SpatialTransitionType,
    FenceCrossingEvent,
    SpatialState,
    ZoneType,
    Point2D,
    ZonePolygon,
    VirtualFence,
    CameraSpatialConfig,
    BorderSide,
    CrossingStatus,
    GroundContactPoint,
    SpatialConfidence,
)
from .world_schemas import (
    CoordinateReference,
    TerrainMode,
    CalibrationStatus,
    CalibrationModel,
    GroundReferenceMethod,
    WorldPoint,
    BorderSection,
    CameraRegistration,
    CalibrationCorrespondence,
    CameraCalibration,
    ProjectedBorder,
    CrossingEvent,
)
from .geometry import (
    point_in_polygon,
    segments_intersect,
    calculate_movement_direction,
)
from .calibration import (
    compute_homography,
    project_world_to_image,
    project_image_to_world,
    validate_calibration,
    project_border_to_camera,
    CalibrationError,
    TerrainModeNotImplementedError,
)
from .ground_contact import estimate_ground_contact, image_to_world_ground
from .border_logic import determine_side, check_crossing, CrossingConfirmation
from .engine import SpatialEngine
from .visualizer import draw_spatial_overlay
from .exceptions import SpatialError, InvalidGeometryError, ConfigurationError

__all__ = [
    # Engine
    "SpatialEngineInterface",
    "SpatialEngine",
    # Legacy schemas
    "MovementDirection",
    "SpatialTransitionType",
    "FenceCrossingEvent",
    "SpatialState",
    "ZoneType",
    "Point2D",
    "ZonePolygon",
    "VirtualFence",
    "CameraSpatialConfig",
    # World-border schemas
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
    # Geometry
    "point_in_polygon",
    "segments_intersect",
    "calculate_movement_direction",
    # Calibration
    "compute_homography",
    "project_world_to_image",
    "project_image_to_world",
    "validate_calibration",
    "project_border_to_camera",
    "CalibrationError",
    "TerrainModeNotImplementedError",
    # Ground contact
    "estimate_ground_contact",
    "image_to_world_ground",
    # Border logic
    "determine_side",
    "check_crossing",
    "CrossingConfirmation",
    # Visualizer
    "draw_spatial_overlay",
    # Exceptions
    "SpatialError",
    "InvalidGeometryError",
    "ConfigurationError",
]
