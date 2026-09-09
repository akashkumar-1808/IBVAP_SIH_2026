from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator
from .common import TargetClass, TrackStatus, BehaviorType, EventPriority, VisibilityQuality


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @model_validator(mode="before")
    @classmethod
    def _remap_coords(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "x1" in data and "x_min" not in data:
                data["x_min"] = data["x1"]
            if "y1" in data and "y_min" not in data:
                data["y_min"] = data["y1"]
            if "x2" in data and "x_max" not in data:
                data["x_max"] = data["x2"]
            if "y2" in data and "y_max" not in data:
                data["y_max"] = data["y2"]
        elif isinstance(data, (list, tuple)) and len(data) == 4:
            return {
                "x_min": float(data[0]),
                "y_min": float(data[1]),
                "x_max": float(data[2]),
                "y_max": float(data[3]),
            }
        return data

    @property
    def x1(self) -> float:
        return self.x_min

    @property
    def y1(self) -> float:
        return self.y_min

    @property
    def x2(self) -> float:
        return self.x_max

    @property
    def y2(self) -> float:
        return self.y_max

    @property
    def width(self) -> float:
        return max(0.0, self.x_max - self.x_min)

    @property
    def height(self) -> float:
        return max(0.0, self.y_max - self.y_min)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x_min + self.x_max) / 2.0, (self.y_min + self.y_max) / 2.0)

    def to_xyxy(self) -> Tuple[float, float, float, float]:
        return (self.x_min, self.y_min, self.x_max, self.y_max)


class PoseKeypoint(BaseModel):
    name: str
    x: float
    y: float
    confidence: float = 0.0
    visible: bool = True

    def to_xy(self) -> Tuple[float, float]:
        return (self.x, self.y)


COCO_POSE_KEYPOINTS = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]

SKELETON_CONNECTIONS = [
    ("nose", "left_eye"),
    ("nose", "right_eye"),
    ("left_eye", "left_ear"),
    ("right_eye", "right_ear"),
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
]


class HumanPose(BaseModel):
    keypoints: Dict[str, PoseKeypoint] = Field(default_factory=dict)
    confidence: float = 0.0
    num_keypoints: int = 0

    @property
    def nose(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("nose")

    @property
    def left_eye(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("left_eye")

    @property
    def right_eye(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("right_eye")

    @property
    def left_ear(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("left_ear")

    @property
    def right_ear(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("right_ear")

    @property
    def left_shoulder(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("left_shoulder")

    @property
    def right_shoulder(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("right_shoulder")

    @property
    def left_elbow(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("left_elbow")

    @property
    def right_elbow(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("right_elbow")

    @property
    def left_wrist(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("left_wrist")

    @property
    def right_wrist(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("right_wrist")

    @property
    def left_hip(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("left_hip")

    @property
    def right_hip(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("right_hip")

    @property
    def left_knee(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("left_knee")

    @property
    def right_knee(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("right_knee")

    @property
    def left_ankle(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("left_ankle")

    @property
    def right_ankle(self) -> Optional[PoseKeypoint]:
        return self.keypoints.get("right_ankle")


class Detection(BaseModel):
    camera_id: str
    frame_id: int
    timestamp_utc: datetime = Field(default_factory=_utc_now)
    class_id: TargetClass
    class_name: str = ""
    confidence: float = Field(..., ge=0.0, le=1.0, description="Raw detector output confidence [0, 1]")
    bbox: BoundingBox

    # Optional fields for model-agnostic extension
    tracking_id: Optional[int] = None
    mask: Optional[Any] = None
    obb: Optional[List[float]] = None
    keypoints: Optional[Any] = None
    depth: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _populate_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "bounding_box" in data and "bbox" not in data:
                data["bbox"] = data["bounding_box"]
            if "timestamp" in data and "timestamp_utc" not in data:
                data["timestamp_utc"] = data["timestamp"]
            if "class_id" in data and isinstance(data["class_id"], str):
                val = data["class_id"].lower().strip()
                try:
                    data["class_id"] = TargetClass(val)
                except ValueError:
                    pass
            if not data.get("class_name") and "class_id" in data:
                cid = data["class_id"]
                data["class_name"] = cid.value if hasattr(cid, "value") else str(cid)
        return data

    @property
    def bounding_box(self) -> Tuple[float, float, float, float]:
        """Unified (x1, y1, x2, y2) tuple representation."""
        return (self.bbox.x_min, self.bbox.y_min, self.bbox.x_max, self.bbox.y_max)

    @property
    def timestamp(self) -> Optional[datetime]:
        """Alias for timestamp_utc."""
        return self.timestamp_utc


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
    keypoints: Optional[Any] = None
    keypoint_scores: Optional[List[float]] = None


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
