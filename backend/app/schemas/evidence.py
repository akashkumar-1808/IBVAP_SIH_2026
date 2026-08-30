"""
Pydantic data schemas for backend Evidence management and verification APIs.

Architecture Decision: DEC-0008
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from .common import TargetClass, EventPriority


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceType(str, Enum):
    SNAPSHOT_RAW = "snapshot_raw"
    SNAPSHOT_ANNOTATED = "snapshot_annotated"
    PRE_EVENT_CLIP = "pre_event_clip"
    INCIDENT_CLIP = "incident_clip"
    MANIFEST = "manifest"


class EvidenceRecordSchema(BaseModel):
    """Schema representing an individual stored evidence item in PostgreSQL."""
    id: str
    event_id: str
    camera_id: str
    track_id: Optional[int] = None
    evidence_type: str
    storage_reference: str
    source_reference: Optional[str] = None
    start_time_utc: Optional[datetime] = None
    end_time_utc: Optional[datetime] = None
    file_size_bytes: int = 0
    mime_type: str
    sha256: str
    status: str = "sealed"
    model_versions: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)


class EvidencePackageResponse(BaseModel):
    """Aggregated response containing all evidence items and manifest for an event."""
    event_id: str
    camera_id: str
    status: str
    is_sealed: bool
    sha256_seal: Optional[str] = None
    created_at_utc: datetime
    evidence_records: List[EvidenceRecordSchema] = Field(default_factory=list)
    manifest: Optional[Dict[str, Any]] = None


class IntegrityVerificationResponse(BaseModel):
    """Response returned by on-demand SHA-256 integrity verification endpoint."""
    evidence_id: str
    file_name: str
    stored_sha256: str
    calculated_sha256: str
    is_valid: bool
    status: str
    verified_at_utc: datetime = Field(default_factory=_utc_now)
    details: Optional[str] = None
