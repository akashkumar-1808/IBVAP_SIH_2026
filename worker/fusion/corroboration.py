"""
Evidence-on-Demand & Corroboration Engine.

Holds low-certainty or emerging event candidates in an internal pending state,
actively awaiting corroborating evidence (continued persistence, border breach, or neighbour camera handoff).
Safe timeout into INSUFFICIENT_EVIDENCE eliminates alert spam without losing true incidents.

Architecture Decision: DEC-0009
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field

from worker.tracking.schemas import TrackState
from worker.spatial.schemas import SpatialState, CrossingStatus
from worker.cross_camera.schemas import BorderTrack

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CorroborationReason(str, Enum):
    """Reason why an emerging event candidate requires corroboration before alert escalation."""
    WAIT_FOR_PERSISTENCE = "wait_for_persistence"
    WAIT_FOR_NEIGHBOUR_CAMERA = "wait_for_neighbour_camera"
    WAIT_FOR_BORDER_CONFIRMATION = "wait_for_border_confirmation"
    WAIT_FOR_BEHAVIOUR_COMPLETION = "wait_for_behaviour_completion"


class RequestStatus(str, Enum):
    """Lifecycle status of an EvidenceRequest."""
    PENDING = "pending"
    FULFILLED = "fulfilled"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class EvidenceRequest(BaseModel):
    """Internal demand for corroborating evidence before escalating an event."""
    request_id: str
    candidate_event_id: str
    track_id: int
    camera_id: str
    reason: CorroborationReason
    requested_source: str = "frame_persistence"
    created_at_utc: datetime = Field(default_factory=_utc_now)
    expiry_utc: datetime = Field(default_factory=_utc_now)
    status: RequestStatus = RequestStatus.PENDING
    fulfillment_details: Optional[str] = None


class CorroborationEngine:
    """
    Manages active EvidenceRequests and evaluates multi-camera, spatial,
    and temporal streams to fulfill requests or gracefully expire them.
    """

    def __init__(self):
        self.requests: Dict[str, EvidenceRequest] = {}
        self._next_id: int = 1

    def create_request(
        self,
        candidate_event_id: str,
        track_id: int,
        camera_id: str,
        reason: CorroborationReason,
        ttl_seconds: float = 8.0,
        requested_source: str = "camera_handoff",
        current_time_utc: Optional[datetime] = None,
    ) -> EvidenceRequest:
        """Issues a new internal EvidenceRequest."""
        now = current_time_utc or datetime.now(timezone.utc)
        req_id = f"ev_req_{self._next_id:04d}"
        self._next_id += 1

        req = EvidenceRequest(
            request_id=req_id,
            candidate_event_id=candidate_event_id,
            track_id=track_id,
            camera_id=camera_id,
            reason=reason,
            requested_source=requested_source,
            created_at_utc=now,
            expiry_utc=now + timedelta(seconds=ttl_seconds),
            status=RequestStatus.PENDING,
        )
        self.requests[req_id] = req
        logger.info(f"Issued EvidenceRequest '{req_id}' for candidate '{candidate_event_id}' ({reason.value})")
        return req

    def evaluate_corroboration(
        self,
        track: TrackState,
        spatial_state: Optional[SpatialState] = None,
        border_track: Optional[BorderTrack] = None,
        current_time_utc: Optional[datetime] = None,
    ) -> List[EvidenceRequest]:
        """
        Evaluates active pending requests against latest observations.
        Returns list of newly updated (fulfilled or expired) requests.
        """
        now = current_time_utc or track.last_seen or datetime.now(timezone.utc)
        updated: List[EvidenceRequest] = []

        for req in list(self.requests.values()):
            if req.status != RequestStatus.PENDING:
                continue

            # Check track match
            if req.track_id != track.track_id and (not border_track or track.track_id not in border_track.local_tracks.values()):
                # Check expiration
                if now > req.expiry_utc:
                    req.status = RequestStatus.EXPIRED
                    req.fulfillment_details = f"Request timed out after {(now - req.created_at_utc).total_seconds():.1f}s without corroboration."
                    updated.append(req)
                continue

            # 1. Evaluate WAIT_FOR_PERSISTENCE
            if req.reason == CorroborationReason.WAIT_FOR_PERSISTENCE:
                if track.age_frames >= 12 or (track.last_seen - track.first_seen).total_seconds() >= 1.0:
                    req.status = RequestStatus.FULFILLED
                    req.fulfillment_details = f"Track persistence confirmed ({track.age_frames} frames)."
                    updated.append(req)
                    continue

            # 2. Evaluate WAIT_FOR_BORDER_CONFIRMATION
            elif req.reason == CorroborationReason.WAIT_FOR_BORDER_CONFIRMATION:
                if spatial_state and spatial_state.crossing_status == CrossingStatus.CONFIRMED_CROSSING:
                    req.status = RequestStatus.FULFILLED
                    req.fulfillment_details = "World border physical crossing confirmed by spatial intelligence."
                    updated.append(req)
                    continue

            # 3. Evaluate WAIT_FOR_NEIGHBOUR_CAMERA
            elif req.reason == CorroborationReason.WAIT_FOR_NEIGHBOUR_CAMERA:
                if border_track and len(border_track.camera_sequence) > 1:
                    req.status = RequestStatus.FULFILLED
                    req.fulfillment_details = f"Cross-camera handoff confirmed across {border_track.camera_sequence}."
                    updated.append(req)
                    continue

            # 4. Check for Timeout Expiry
            if now > req.expiry_utc:
                req.status = RequestStatus.EXPIRED
                req.fulfillment_details = f"Corroboration request expired without sufficient evidence after {(now - req.created_at_utc).total_seconds():.1f}s."
                updated.append(req)

        return updated

    def get_pending_requests_for_event(self, event_id: str) -> List[EvidenceRequest]:
        """Returns all pending requests for a given candidate event."""
        return [r for r in self.requests.values() if r.candidate_event_id == event_id and r.status == RequestStatus.PENDING]

    def reset(self) -> None:
        """Resets all request states."""
        self.requests.clear()
        self._next_id = 1
