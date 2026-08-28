from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from .common import StreamStatus, TerrainProfile
from .spatial import CameraSpatialConfig


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CameraCreate(BaseModel):
    id: str = Field(..., description="Unique camera identifier, e.g. cam_01")
    name: str = Field(..., description="Human-readable camera name")
    stream_url: str = Field(..., description="RTSP URL, video file path, or device ID")
    location: Optional[str] = Field(None, description="Geographic or sector location description")
    terrain_profile: TerrainProfile = Field(default=TerrainProfile.OPEN_GROUND)
    fps_target: int = Field(default=10, ge=1, le=30)
    is_active: bool = True


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    stream_url: Optional[str] = None
    location: Optional[str] = None
    terrain_profile: Optional[TerrainProfile] = None
    fps_target: Optional[int] = None
    is_active: Optional[bool] = None


class CameraResponse(BaseModel):
    id: str
    name: str
    stream_url: str
    location: Optional[str]
    terrain_profile: TerrainProfile
    fps_target: int
    is_active: bool
    status: StreamStatus = StreamStatus.OFFLINE
    last_frame_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utc_now)
    spatial_config: Optional[CameraSpatialConfig] = None
