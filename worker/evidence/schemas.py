"""
Data contracts and configuration schemas for IBVAP Structured Evidence Storage & Packaging.

Architecture Decision: DEC-0008
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from backend.app.schemas.common import TargetClass, EventPriority, VisibilityQuality, LightingCondition
from ..fusion.schemas import EventType, FusionReasonCode


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceStatus(str, Enum):
    """Lifecycle state of an evidence package."""
    RECORDING = "recording"
    PACKAGED = "packaged"
    SEALED = "sealed"
    PARTIAL = "partial"
    STORED = "stored"
    FAILED = "failed"


class EvidencePackageConfig(BaseModel):
    """Configuration parameters for evidence package extraction and storage."""
    pre_event_seconds: float = Field(default=5.0, ge=0.5, le=30.0, description="Duration of pre-event video buffer")
    post_event_seconds: float = Field(default=5.0, ge=0.5, le=30.0, description="Duration of post-event video buffer")
    fps: float = Field(default=25.0, ge=1.0, le=60.0, description="Target encoding FPS for video clips")
    snapshot_quality: int = Field(default=95, ge=50, le=100, description="JPEG compression quality [50, 100]")
    storage_root: str = Field(default="storage/evidence", description="Local filesystem storage root")
    auto_upload_supabase: bool = Field(default=False, description="Whether to asynchronously upload to Supabase Storage")
    auto_persist_db: bool = Field(default=False, description="Whether to persist EvidenceRecords in PostgreSQL")


class ArtifactChecksum(BaseModel):
    """Cryptographic integrity fingerprint of an individual evidence artifact."""
    file_name: str
    file_type: str = Field(..., description="e.g. 'image/jpeg', 'video/mp4', 'application/json'")
    file_size_bytes: int
    sha256_hash: str = Field(..., description="Hex-encoded SHA-256 hash")


class EvidenceManifest(BaseModel):
    """
    Immutable audit manifest sealed with cryptographic hashes of all package artifacts.
    Guarantees non-repudiation and forensic integrity.
    """
    event_id: str
    camera_id: str
    track_id: int
    event_type: EventType
    priority: EventPriority
    risk_score: float
    target_class: TargetClass
    created_at_utc: datetime
    first_observed_utc: datetime
    last_observed_utc: datetime
    duration_seconds: float
    reason_codes: List[FusionReasonCode] = Field(default_factory=list)
    explanation_summary: str
    environment_quality: VisibilityQuality = VisibilityQuality.GOOD
    lighting: LightingCondition = LightingCondition.DAY
    artifacts: List[ArtifactChecksum] = Field(default_factory=list)
    model_versions: Dict[str, str] = Field(default_factory=dict)
    sealed_at_utc: datetime = Field(default_factory=_utc_now)
    system_version: str = "IBVAP-v1.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidencePackage(BaseModel):
    """
    Complete structured Evidence Package containing all physical media paths and audit manifest.
    """
    id: str = Field(..., description="Unique package identifier (usually matches event_id)")
    event_id: str
    camera_id: str
    status: EvidenceStatus = EvidenceStatus.SEALED
    package_dir: str
    snapshot_path: Optional[str] = None
    annotated_snapshot_path: Optional[str] = None
    pre_event_clip_path: Optional[str] = None
    incident_clip_path: Optional[str] = None
    manifest_path: Optional[str] = None
    manifest: Optional[EvidenceManifest] = None
    created_at_utc: datetime = Field(default_factory=_utc_now)
    is_sealed: bool = True
    sha256_seal: Optional[str] = None

    @property
    def package_id(self) -> str:
        """Alias for id."""
        return self.id


__all__ = [
    "EvidenceStatus",
    "EvidencePackageConfig",
    "ArtifactChecksum",
    "EvidenceManifest",
    "EvidencePackage",
]
