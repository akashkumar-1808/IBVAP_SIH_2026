from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel, Field
from .common import ZoneType


class Point2D(BaseModel):
    x: float
    y: float


class ZonePolygon(BaseModel):
    id: str
    name: str
    type: ZoneType = ZoneType.RESTRICTED
    severity_weight: float = Field(default=1.0, ge=0.0, le=2.0)
    polygon: List[Tuple[float, float]] = Field(
        ..., description="List of (x, y) coordinates normalized or pixel coordinates"
    )
    is_active: bool = True


class VirtualFence(BaseModel):
    id: str
    name: str
    start_point: Tuple[float, float] = Field(..., description="(x, y) start coordinate")
    end_point: Tuple[float, float] = Field(..., description="(x, y) end coordinate")
    crossing_direction_angle: Optional[float] = Field(
        None, description="Angle in degrees (0-360) defining protected crossing vector"
    )
    severity_weight: float = Field(default=1.5, ge=0.0, le=2.0)
    is_active: bool = True


class CameraSpatialConfig(BaseModel):
    camera_id: str
    zones: List[ZonePolygon] = Field(default_factory=list)
    fences: List[VirtualFence] = Field(default_factory=list)
    expected_threat_vector: Optional[Tuple[float, float]] = Field(
        None, description="Normalized 2D direction vector [dx, dy] pointing toward the border/protected area"
    )
