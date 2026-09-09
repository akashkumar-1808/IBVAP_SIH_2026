from enum import Enum
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class BehaviorType(str, Enum):
    LOITERING = "loitering"
    PERSISTENT_APPROACH = "persistent_approach"
    RESTRICTED_OCCUPANCY = "restricted_occupancy"
    RESTRICTED_ENTRY = "restricted_entry"
    FENCE_BREACH = "fence_breach"
    FENCE_CROSSED = "fence_crossed"
    BORDER_CROSSING = "border_crossing"
    REPEATED_APPROACH = "repeated_approach"
    SPEED_ANOMALY = "speed_anomaly"


class BehaviorStatus(str, Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


class ReasonCode(str, Enum):
    DWELL_TIME_EXCEEDED = "dwell_time_exceeded"
    LOW_DISPLACEMENT = "low_displacement"
    PERSISTENT_TOWARD = "persistent_toward"
    RESTRICTED_OCCUPANCY = "restricted_occupancy"
    FENCE_CROSSED = "fence_crossed"
    BORDER_CROSSED = "border_crossed"
    REPEATED_APPROACH = "repeated_approach"
    SPEED_THRESHOLD_EXCEEDED = "speed_threshold_exceeded"


class BehaviorConfig(BaseModel):
    """Camera-specific configurable temporal and spatial thresholds for behavior reasoning."""
    loitering_seconds: float = Field(default=5.0, ge=1.0, description="Dwell time in zone before loitering is triggered")
    loitering_max_displacement_px: float = Field(default=40.0, ge=5.0, description="Maximum net displacement radius to classify as stationary dwell")
    persistent_approach_seconds: float = Field(default=3.0, ge=0.5, description="Duration of sustained movement along threat vector")
    persistent_approach_min_distance_px: float = Field(default=30.0, ge=5.0, description="Minimum net distance toward threat vector required")
    repeated_approach_window_sec: float = Field(default=30.0, ge=5.0, description="Window to identify repeated approach attempts")
    speed_anomaly_threshold_px_per_sec: float = Field(default=60.0, ge=10.0, description="Threshold speed to trigger speed anomaly behavior")
    enable_speed_anomaly: bool = Field(default=True, description="Enable speed anomaly detection")
    behavior_cooldown_sec: float = Field(default=5.0, ge=1.0, description="Cooldown interval before repeating non-continuous events")
    max_history_len: int = Field(default=120, ge=30, description="Maximum bounded trajectory and state history length")


class BehaviorPrimitive(BaseModel):
    """
    Canonical Explainable Behavior Primitive produced by Phase 7.
    Describes purely what the object did across time, without threat interpretation.
    """
    behavior_id: str = Field(..., description="Unique deterministic identifier for this behavior instance")
    camera_id: str
    track_id: int
    behavior_type: BehaviorType
    status: BehaviorStatus = BehaviorStatus.ACTIVE
    timestamp_utc: datetime
    first_observed_utc: datetime
    last_observed_utc: datetime
    duration_seconds: float = 0.0
    zone_id: Optional[str] = None
    fence_id: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Evidence confidence score [0, 1]")
    triggering_condition: Optional[str] = Field(default=None, description="Human-readable rule condition that triggered this behavior")
    reason_codes: List[ReasonCode] = Field(default_factory=list)
    supporting_data: Dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "BehaviorType",
    "BehaviorStatus",
    "ReasonCode",
    "BehaviorConfig",
    "BehaviorPrimitive",
]
