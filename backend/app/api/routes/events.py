"""
Event management and evidence query REST API routes.

Architecture Decision: DEC-0007 / DEC-0008
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from ...db.repositories import EventRepository, EvidenceRepository
from ...schemas.evidence import EvidencePackageResponse, EvidenceRecordSchema

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["Events"])

event_repo = EventRepository()
evidence_repo = EvidenceRepository()


class AcknowledgeRequest(BaseModel):
    acknowledged_by: str = "operator"


@router.get("", response_model=List[Dict[str, Any]])
def list_events(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    priority: Optional[str] = Query(None, description="Filter by priority tier"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Retrieve security events with optional multi-criteria filtering."""
    try:
        return event_repo.query_events(
            camera_id=camera_id,
            priority=priority,
            event_type=event_type,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.error(f"Failed to query events: {exc}")
        raise HTTPException(status_code=500, detail="Internal database error querying events.")


@router.get("/{event_id}", response_model=Dict[str, Any])
def get_event(event_id: str):
    """Retrieve single event by event ID."""
    ev = event_repo.get_by_id(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Event with ID '{event_id}' not found.")
    return ev


@router.get("/{event_id}/evidence", response_model=EvidencePackageResponse)
def get_event_evidence(event_id: str):
    """
    Retrieve all structured evidence items, media references, and sealed audit manifest for an event.
    """
    ev = event_repo.get_by_id(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Event with ID '{event_id}' not found.")

    camera_id = ev.get("camera_id", "unknown")
    evidence_records = evidence_repo.get_by_event_id(event_id)

    # Check for manifest on disk if available
    manifest_data = None
    local_manifest_path = os.path.join("storage", "evidence", camera_id, event_id, "manifest.json")
    if os.path.exists(local_manifest_path):
        try:
            with open(local_manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
        except Exception:
            pass

    status_str = "sealed" if evidence_records else "pending"
    sha256_seal = manifest_data.get("sealed_at_utc") if manifest_data else None

    return EvidencePackageResponse(
        event_id=event_id,
        camera_id=camera_id,
        status=status_str,
        is_sealed=True if evidence_records else False,
        sha256_seal=sha256_seal,
        created_at_utc=ev.get("created_at") or ev.get("timestamp_utc"),
        evidence_records=evidence_records,
        manifest=manifest_data,
    )


@router.post("/{event_id}/acknowledge", response_model=Dict[str, Any])
def acknowledge_event(event_id: str, req: AcknowledgeRequest):
    """Mark an actionable event as operator-acknowledged."""
    updated = event_repo.acknowledge_event(event_id=event_id, acknowledged_by=req.acknowledged_by)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found or could not be updated.")
    return updated
