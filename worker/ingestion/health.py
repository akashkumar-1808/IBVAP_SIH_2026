from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class StreamHealthState(str, Enum):
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StreamHealthMetrics(BaseModel):
    camera_id: str
    state: StreamHealthState = StreamHealthState.DISCONNECTED
    fps_measured: float = 0.0
    total_frames_read: int = 0
    total_frames_dropped: int = 0
    reconnect_attempts: int = 0
    last_frame_timestamp: Optional[datetime] = None
    last_error_message: Optional[str] = None
    updated_at: datetime = Field(default_factory=_utc_now)
