"""
Evidence item management and cryptographic integrity verification REST API routes.

Architecture Decision: DEC-0008
"""

import os
import hashlib
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from ...db.repositories import EvidenceRepository
from ...db.storage import evidence_storage
from ...schemas.evidence import (
    EvidenceRecordSchema,
    IntegrityVerificationResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/evidence", tags=["Evidence"])

evidence_repo = EvidenceRepository()


@router.get("/{evidence_id}", response_model=Dict[str, Any])
def get_evidence_record(evidence_id: str):
    """Retrieve single evidence record metadata by evidence ID."""
    rec = evidence_repo.get_by_id(evidence_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Evidence record '{evidence_id}' not found.")
    return rec


@router.get("/{evidence_id}/verify", response_model=IntegrityVerificationResponse)
def verify_evidence_integrity(evidence_id: str):
    """
    On-demand cryptographic SHA-256 integrity verification.
    Recalculates file hash and compares against the immutable database/manifest fingerprint.
    """
    rec = evidence_repo.get_by_id(evidence_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Evidence record '{evidence_id}' not found.")

    storage_ref = rec.get("storage_reference", "")
    stored_sha256 = rec.get("sha256", "")
    file_name = os.path.basename(storage_ref)

    if not os.path.exists(storage_ref):
        return IntegrityVerificationResponse(
            evidence_id=evidence_id,
            file_name=file_name,
            stored_sha256=stored_sha256,
            calculated_sha256="",
            is_valid=False,
            status="missing_file",
            details=f"Physical file missing at '{storage_ref}'",
        )

    # Compute SHA-256
    sha256 = hashlib.sha256()
    with open(storage_ref, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    calculated_sha256 = sha256.hexdigest()

    is_valid = (calculated_sha256 == stored_sha256)
    status_str = "verified" if is_valid else "tamper_detected"
    details_str = "Cryptographic integrity intact (PASS)" if is_valid else f"Hash mismatch: stored={stored_sha256[:12]}... computed={calculated_sha256[:12]}... (FAIL)"

    return IntegrityVerificationResponse(
        evidence_id=evidence_id,
        file_name=file_name,
        stored_sha256=stored_sha256,
        calculated_sha256=calculated_sha256,
        is_valid=is_valid,
        status=status_str,
        details=details_str,
    )


@router.get("/{evidence_id}/signed-url", response_model=Dict[str, Any])
def get_evidence_signed_url(evidence_id: str, expires_in_seconds: int = 3600):
    """
    Generates a secure temporary signed URL for an evidence snapshot or video clip.
    Falls back to local file URI if running in local-only mode.
    """
    rec = evidence_repo.get_by_id(evidence_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Evidence record '{evidence_id}' not found.")

    storage_ref = rec.get("storage_reference", "")
    camera_id = rec.get("camera_id", "")
    event_id = rec.get("event_id", "")
    file_name = os.path.basename(storage_ref)

    cloud_path = f"{camera_id}/{event_id}/{file_name}"
    signed_url = None

    if evidence_storage.is_available():
        signed_url = evidence_storage.get_signed_url(cloud_path, expires_in_seconds=expires_in_seconds)

    return {
        "evidence_id": evidence_id,
        "file_name": file_name,
        "is_cloud_available": signed_url is not None,
        "signed_url": signed_url,
        "local_storage_reference": storage_ref,
    }
