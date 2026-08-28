from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel, Field
from .common import TargetClass, TrackStatus, BehaviorType, EventPriority, VisibilityQuality


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class Detection(BaseModel):
    camera_id: str
    frame_id: int
    timestamp_utc: datetime = Field(default_factory=_utc_now)
    class_id: TargetClass
    confidence: float = Field(..., ge=0.0, le=1.0, description="Raw detector output confidence [0, 1]")
    bbox: BoundingBox
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrajectoryPoint(BaseModel):
    x: float
    y: float
    timestamp_utc: datetime
    frame_id: int


class TrackState(BaseModel):
    track_id: int
    camera_id: str
    class_id: TargetClass
    bbox: BoundingBox
    center_xy: Tuple[float, float]
    velocity_xy: Tuple[float, float] = (0.0, 0.0)
    speed_pixels_per_sec: float = 0.0
    direction_angle: Optional[float] = None
    age_frames: int = 1
    consecutive_invisible_frames: int = 0
    status: TrackStatus = TrackStatus.CANDIDATE
    first_seen: datetime = Field(default_factory=_utc_now)
    last_seen: datetime = Field(default_factory=_utc_now)
    confidence_history: List[float] = Field(default_factory=list)
    trajectory: List[TrajectoryPoint] = Field(default_factory=list)
    current_zone_id: Optional[str] = None
    dwell_time_seconds: float = 0.0
    behavior: BehaviorType = BehaviorType.NORMAL


class EvidenceMetadata(BaseModel):
    event_id: str
    camera_id: str
    timestamp_utc: datetime = Field(default_factory=_utc_now)
    snapshot_path: str
    video_clip_path: Optional[str] = None
    frame_width: int
    frame_height: int
    pre_event_seconds: float = 5.0
    post_event_seconds: float = 5.0
    sha256_checksum: Optional[str] = None


class EventRecord(BaseModel):
    id: str = Field(..., description="Unique UUID for the security event")
    camera_id: str
    timestamp_utc: datetime = Field(default_factory=_utc_now)
    event_type: BehaviorType
    priority: EventPriority
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Calibrated risk priority score [0, 100]")
    target_class: TargetClass
    track_id: int
    detection_confidence: float = Field(..., ge=0.0, le=1.0)
    track_persistence_frames: int
    dwell_time_seconds: float
    zone_id: Optional[str] = None
    fence_id: Optional[str] = None
    environment_quality: VisibilityQuality = VisibilityQuality.GOOD
    reason_codes: List[str] = Field(..., description="Explainable machine-readable rule triggers")
    explanation_summary: str = Field(..., description="Human-readable factual reasoning summary")
    uncertainty_flags: List[str] = Field(default_factory=list)
    evidence: Optional[EvidenceMetadata] = None
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
