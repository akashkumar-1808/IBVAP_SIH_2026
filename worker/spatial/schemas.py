from enum import Enum
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from backend.app.schemas.common import ZoneType
from backend.app.schemas.spatial import Point2D, ZonePolygon, VirtualFence, CameraSpatialConfig
from .world_schemas import BorderSide, CrossingStatus, GroundContactPoint, SpatialConfidence


class MovementDirection(str, Enum):
    TOWARD = "toward"
    AWAY = "away"
    PARALLEL = "parallel"
    UNCERTAIN = "uncertain"


class SpatialTransitionType(str, Enum):
    NONE = "none"
    ZONE_ENTERED = "zone_entered"
    ZONE_EXITED = "zone_exited"


class FenceCrossingEvent(BaseModel):
    fence_id: str
    track_id: int
    camera_id: str
    timestamp_utc: datetime
    previous_position: Tuple[float, float]
    current_position: Tuple[float, float]
    crossing_point: Optional[Tuple[float, float]] = None
    crossing_direction: MovementDirection = MovementDirection.UNCERTAIN


class SpatialState(BaseModel):
    camera_id: str
    track_id: int
    timestamp_utc: datetime
    current_zone_id: Optional[str] = None
    current_zone_type: Optional[ZoneType] = None
    previous_zone_id: Optional[str] = None
    transition: SpatialTransitionType = SpatialTransitionType.NONE
    direction: MovementDirection = MovementDirection.UNCERTAIN
    fences_crossed: List[str] = Field(default_factory=list)
    crossing_events: List[FenceCrossingEvent] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # ── World-Border Model Extensions (Optional, backward-compatible) ──
    border_side: Optional[BorderSide] = None
    crossing_status: CrossingStatus = CrossingStatus.NONE
    ground_contact: Optional[GroundContactPoint] = None
    calibration_version: Optional[str] = None
    spatial_confidence: SpatialConfidence = SpatialConfidence.VALID
    border_distance_m: Optional[float] = None


__all__ = [
    "MovementDirection",
    "SpatialTransitionType",
    "FenceCrossingEvent",
    "SpatialState",
    "ZoneType",
    "Point2D",
    "ZonePolygon",
    "VirtualFence",
    "CameraSpatialConfig",
    "BorderSide",
    "CrossingStatus",
    "GroundContactPoint",
    "SpatialConfidence",
]
