"""
Incident Story & Behaviour-to-Event Sequential Narrative.

Constructs an explainable chronological transition timeline for an active threat entity:
e.g. Detected -> Approaching -> Warning Buffer -> Border Crossed -> Restricted Occupancy -> Cross-Cam Handoff.

Architecture Decision: DEC-0009
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from worker.spatial.schemas import BorderSide
from backend.app.schemas.common import BehaviorType


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IncidentStep(BaseModel):
    """An individual sequential transition event in the incident timeline."""
    step_index: int
    timestamp_utc: datetime = Field(default_factory=_utc_now)
    camera_id: str
    state_type: str  # e.g. 'DETECTED', 'PERSISTENT', 'APPROACHING', 'WARNING_BUFFER', 'BORDER_CROSSED', 'RESTRICTED_OCCUPANCY', 'CROSS_CAM_HANDOFF'
    description: str
    spatial_side: Optional[BorderSide] = None
    behavior_type: Optional[Any] = None
    risk_score: float = 0.0


class IncidentStory(BaseModel):
    """
    Complete sequential narrative connecting tracking, spatial transitions,
    behaviors, and multi-camera observations into a unified incident context.
    """
    story_id: str
    track_id: int
    border_track_id: Optional[str] = None
    steps: List[IncidentStep] = Field(default_factory=list)
    created_at_utc: datetime = Field(default_factory=_utc_now)
    last_updated_utc: datetime = Field(default_factory=_utc_now)

    def add_step(
        self,
        camera_id: str,
        state_type: str,
        description: str,
        timestamp_utc: Optional[datetime] = None,
        spatial_side: Optional[BorderSide] = None,
        behavior_type: Optional[BehaviorType] = None,
        risk_score: float = 0.0,
    ) -> IncidentStep:
        """Appends a new chronological state transition to the incident timeline."""
        ts = timestamp_utc or datetime.now(timezone.utc)
        step = IncidentStep(
            step_index=len(self.steps) + 1,
            timestamp_utc=ts,
            camera_id=camera_id,
            state_type=state_type,
            description=description,
            spatial_side=spatial_side,
            behavior_type=behavior_type,
            risk_score=risk_score,
        )
        self.steps.append(step)
        self.last_updated_utc = ts
        return step

    def get_narrative(self) -> str:
        """Formats the sequence of steps into a human-readable chronological summary."""
        if not self.steps:
            return "No activity recorded."
        parts = []
        for s in self.steps:
            t_str = s.timestamp_utc.strftime("%H:%M:%S")
            parts.append(f"[{t_str} | {s.camera_id}] {s.state_type}: {s.description}")
        return " ->\n".join(parts)
