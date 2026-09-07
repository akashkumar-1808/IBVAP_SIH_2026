"""
Data contracts and configuration schemas for IBVAP Multi-Modal Evidence Fusion Engine.

Architecture Decision: DEC-0007
"""

from enum import Enum
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from backend.app.schemas.common import TargetClass, EventPriority, VisibilityQuality, LightingCondition
from backend.app.schemas.events import EvidenceMetadata
from ..behavior.schemas import BehaviorType


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventType(str, Enum):
    """Controlled canonical event vocabulary for IBVAP."""
    BORDER_CROSSING = "border_crossing"
    RESTRICTED_ZONE_INTRUSION = "restricted_zone_intrusion"
    PERSISTENT_APPROACH = "persistent_approach"
    LOITERING = "loitering"
    REPEATED_APPROACH = "repeated_approach"
    RESTRICTED_OCCUPANCY = "restricted_occupancy"
    FENCE_BREACH = "fence_breach"
    OBJECT_OBSERVED = "object_observed"
    # Operational Stream Health & Continuity Events
    STREAM_INTERRUPTION = "stream_interruption"
    STREAM_RECOVERED = "stream_recovered"
    CAMERA_STALE = "camera_stale"
    CAMERA_OFFLINE = "camera_offline"


class EventStatus(str, Enum):
    """Lifecycle state of a security event."""
    CANDIDATE = "candidate"
    ACTIVE = "active"
    CONFIRMED = "confirmed"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class FusionReasonCode(str, Enum):
    """Explainable machine-readable reason codes derived strictly from system evidence."""
    # Target class evidence
    PERSON_DETECTED = "person_detected"
    VEHICLE_DETECTED = "vehicle_detected"
    ANIMAL_DETECTED = "animal_detected"
    UNKNOWN_OBJECT_DETECTED = "unknown_object_detected"

    # Track persistence & dynamics
    PERSISTENT_TRACK = "persistent_track"
    SHORT_LIVED_TRACK = "short_lived_track"
    HIGH_SPEED_MOVEMENT = "high_speed_movement"

    # Spatial & World-Border evidence
    TOWARD_PROTECTED_REGION = "toward_protected_region"
    WARNING_BUFFER_ENTRY = "warning_buffer_entry"
    BORDER_LINE_CONTACT = "border_line_contact"
    BORDER_CROSSED = "border_crossed"
    RESTRICTED_ZONE_ENTRY = "restricted_zone_entry"
    CRITICAL_ZONE_ENTRY = "critical_zone_entry"
    SAFE_ZONE_ONLY = "safe_zone_only"

    # Temporal Behavior evidence
    RESTRICTED_OCCUPANCY = "restricted_occupancy"
    LOITERING_DETECTED = "loitering_detected"
    PERSISTENT_APPROACH_DETECTED = "persistent_approach_detected"
    REPEATED_APPROACH_DETECTED = "repeated_approach_detected"
    FENCE_BREACH_DETECTED = "fence_breach_detected"

    # Environmental Context & Uncertainty
    EXCELLENT_VISIBILITY = "excellent_visibility"
    LOW_VISUAL_QUALITY = "low_visual_quality"
    NIGHT_OPERATION = "night_operation"
    SPATIAL_CALIBRATION_INVALID = "spatial_calibration_invalid"
    GROUND_POINT_UNCERTAIN = "ground_point_uncertain"
    EVIDENCE_CONFLICT = "evidence_conflict"

    # Stream Continuity & Trust Evidence
    STREAM_QUALITY_DEGRADED = "stream_quality_degraded"
    STREAM_INTERRUPTION_RECENT = "stream_interruption_recent"
    TRACK_RECOVERED_AFTER_GAP = "track_recovered_after_gap"
    TRACK_CONTINUITY_UNCERTAIN = "track_continuity_uncertain"

    # Multi-Camera & Sector Intelligence (DEC-0009)
    CROSS_CAMERA_CORROBORATED = "cross_camera_corroborated"
    CROSS_CAMERA_HANDOFF_CONFIRMED = "cross_camera_handoff_confirmed"
    SECTOR_ACTIVITY_UNUSUAL = "sector_activity_unusual"
    EVIDENCE_REQUEST_FULFILLED = "evidence_request_fulfilled"
    INSUFFICIENT_EVIDENCE_EXPIRED = "insufficient_evidence_expired"


class FusionConfig(BaseModel):
    """Configurable weights, thresholds, and operational parameters for Evidence Fusion."""
    # Component weights (must sum to ~1.0)
    weight_class: float = Field(default=0.20, ge=0.0, le=1.0)
    weight_spatial: float = Field(default=0.35, ge=0.0, le=1.0)
    weight_behavior: float = Field(default=0.30, ge=0.0, le=1.0)
    weight_environment: float = Field(default=0.15, ge=0.0, le=1.0)

    # Base class severity scores [0, 1]
    class_score_person: float = Field(default=1.0, ge=0.0, le=1.0)
    class_score_vehicle: float = Field(default=0.8, ge=0.0, le=1.0)
    class_score_animal: float = Field(default=0.25, ge=0.0, le=1.0)
    class_score_unknown: float = Field(default=0.4, ge=0.0, le=1.0)

    # Spatial severity scores [0, 1]
    spatial_score_border_crossed: float = Field(default=1.0, ge=0.0, le=1.0)
    spatial_score_restricted: float = Field(default=0.9, ge=0.0, le=1.0)
    spatial_score_critical: float = Field(default=1.0, ge=0.0, le=1.0)
    spatial_score_warning_buffer: float = Field(default=0.5, ge=0.0, le=1.0)
    spatial_score_safe: float = Field(default=0.1, ge=0.0, le=1.0)

    # Behavior severity scores [0, 1]
    behavior_score_fence_breach: float = Field(default=1.0, ge=0.0, le=1.0)
    behavior_score_restricted_occupancy: float = Field(default=0.9, ge=0.0, le=1.0)
    behavior_score_repeated_approach: float = Field(default=0.85, ge=0.0, le=1.0)
    behavior_score_persistent_approach: float = Field(default=0.75, ge=0.0, le=1.0)
    behavior_score_loitering: float = Field(default=0.60, ge=0.0, le=1.0)

    # Priority thresholds [0, 100]
    threshold_info_max: float = Field(default=30.0, ge=0.0, le=100.0)
    threshold_low_max: float = Field(default=50.0, ge=0.0, le=100.0)
    threshold_medium_max: float = Field(default=75.0, ge=0.0, le=100.0)
    threshold_high_max: float = Field(default=90.0, ge=0.0, le=100.0)

    # Tracking & Environmental scaling factors
    min_track_persistence_frames: int = Field(default=3, ge=1)
    suppress_transient_tracks: bool = True
    bad_weather_discount: float = Field(default=0.15, ge=0.0, le=0.5)
    event_cooldown_seconds: float = Field(default=10.0, ge=1.0)
    event_timeout_seconds: float = Field(default=4.0, ge=1.0)


class EvidenceReference(BaseModel):
    """Traceable link to a specific evidence item contributing to an event."""
    evidence_type: str
    source_module: str
    timestamp_utc: datetime = Field(default_factory=_utc_now)
    confidence: Optional[float] = None
    reason_code: str
    details: Dict[str, Any] = Field(default_factory=dict)


class EventRecord(BaseModel):
    """
    Canonical Explainable Event Record generated by Phase 8 Fusion Engine.
    Fully structured, deterministic, auditable, and traceable to concrete evidence.
    """
    id: str = Field(..., description="Unique deterministic or UUID identifier for the security event")
    camera_id: str
    track_id: int
    border_track_id: Optional[str] = None
    event_type: EventType
    priority: EventPriority
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Calibrated risk priority score [0, 100]")
    status: EventStatus = EventStatus.ACTIVE
    target_class: TargetClass
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    first_observed_utc: datetime = Field(default_factory=_utc_now)
    last_observed_utc: datetime = Field(default_factory=_utc_now)
    duration_seconds: float = 0.0

    # Supporting contextual summaries
    detection_confidence: float = Field(..., ge=0.0, le=1.0)
    track_persistence_frames: int = 1
    zone_id: Optional[str] = None
    border_section_id: Optional[str] = None
    environment_quality: VisibilityQuality = VisibilityQuality.GOOD
    lighting: LightingCondition = LightingCondition.DAY
    corroboration_status: Optional[str] = None

    # Machine-readable reasons & evidence traceability
    reason_codes: List[FusionReasonCode] = Field(default_factory=list)
    evidence_references: List[EvidenceReference] = Field(default_factory=list)
    uncertainty_flags: List[str] = Field(default_factory=list)
    explanation_summary: str = Field(..., description="Human-readable factual summary generated from structured evidence")

    # Optional media metadata
    evidence_metadata: Optional[EvidenceMetadata] = None
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


__all__ = [
    "EventType",
    "EventStatus",
    "FusionReasonCode",
    "FusionConfig",
    "EvidenceReference",
    "EventRecord",
]
