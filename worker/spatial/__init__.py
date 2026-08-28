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
)
from .geometry import (
    point_in_polygon,
    segments_intersect,
    calculate_movement_direction,
)
from .engine import SpatialEngine
from .visualizer import draw_spatial_overlay
from .exceptions import SpatialError, InvalidGeometryError, ConfigurationError

__all__ = [
    "SpatialEngineInterface",
    "SpatialEngine",
    "MovementDirection",
    "SpatialTransitionType",
    "FenceCrossingEvent",
    "SpatialState",
    "ZoneType",
    "Point2D",
    "ZonePolygon",
    "VirtualFence",
    "CameraSpatialConfig",
    "point_in_polygon",
    "segments_intersect",
    "calculate_movement_direction",
    "draw_spatial_overlay",
    "SpatialError",
    "InvalidGeometryError",
    "ConfigurationError",
]
