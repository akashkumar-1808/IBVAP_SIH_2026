from enum import Enum
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class BehaviorType(str, Enum):
    LOITERING = "loitering"
    PERSISTENT_APPROACH = "persistent_approach"
    RESTRICTED_OCCUPANCY = "restricted_occupancy"
    FENCE_BREACH = "fence_breach"
    REPEATED_APPROACH = "repeated_approach"


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
    REPEATED_APPROACH = "repeated_approach"


class BehaviorConfig(BaseModel):
    """Camera-specific configurable temporal and spatial thresholds for behavior reasoning."""
    loitering_seconds: float = Field(default=5.0, ge=1.0, description="Dwell time in zone before loitering is triggered")
    loitering_max_displacement_px: float = Field(default=40.0, ge=5.0, description="Maximum net displacement radius to classify as stationary dwell")
    persistent_approach_seconds: float = Field(default=3.0, ge=0.5, description="Duration of sustained movement along threat vector")
    persistent_approach_min_distance_px: float = Field(default=30.0, ge=5.0, description="Minimum net distance toward threat vector required")
    repeated_approach_window_sec: float = Field(default=30.0, ge=5.0, description="Window to identify repeated approach attempts")
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
    reason_codes: List[ReasonCode] = Field(default_factory=list)
    supporting_data: Dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "BehaviorType",
    "BehaviorStatus",
    "ReasonCode",
    "BehaviorConfig",
    "BehaviorPrimitive",
]
