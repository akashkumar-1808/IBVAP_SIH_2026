"""
Pydantic schemas and contracts for Cross-Camera Topology and Persistent Border-Level Tracking.

Architecture Decision: DEC-0009
"""

from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from backend.app.schemas.common import TargetClass
from worker.spatial.schemas import MovementDirection, BorderSide


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AssociationState(str, Enum):
    """Categorical confidence level of cross-camera object association."""
    CONFIRMED = "confirmed"    # High-confidence topology, temporal, direction & class match
    LIKELY = "likely"          # Feasible match with minor temporal or angle variance
    UNCERTAIN = "uncertain"    # Marginal temporal or trajectory alignment
    ENDED = "ended"            # Track exited the monitored border corridor


class AssociationSignal(str, Enum):
    """Explicit explainable evidence signals contributing to association."""
    TOPOLOGY_ADJACENT = "topology_adjacent"
    TEMPORAL_MATCH = "temporal_match"
    DIRECTION_MATCH = "direction_match"
    CLASS_MATCH = "class_match"
    SPEED_FEASIBLE = "speed_feasible"
    BORDER_CORRIDOR_CONTINUITY = "border_corridor_continuity"


class CameraTransitionRule(BaseModel):
    """Defines physical transit feasibility constraints between two adjacent cameras."""
    source_camera_id: str
    target_camera_id: str
    min_transit_seconds: float = Field(default=0.2, ge=0.0, description="Minimum physically plausible travel time")
    max_transit_seconds: float = Field(default=15.0, ge=0.5, description="Maximum travel time before continuity breaks")
    expected_direction: Optional[MovementDirection] = None
    border_section_ids: List[str] = Field(default_factory=list, description="Associated border sections spanned")
    description: Optional[str] = None


class CameraTopology(BaseModel):
    """Represents the directed spatial adjacency graph of the border surveillance network."""
    transitions: Dict[str, List[CameraTransitionRule]] = Field(
        default_factory=dict,
        description="Map from source_camera_id to valid adjacent target camera transition rules"
    )

    def add_rule(self, rule: CameraTransitionRule) -> None:
        if rule.source_camera_id not in self.transitions:
            self.transitions[rule.source_camera_id] = []
        self.transitions[rule.source_camera_id].append(rule)

    def get_rules_for_source(self, source_camera_id: str) -> List[CameraTransitionRule]:
        return self.transitions.get(source_camera_id, [])

    def find_rule(self, source_camera_id: str, target_camera_id: str) -> Optional[CameraTransitionRule]:
        for r in self.get_rules_for_source(source_camera_id):
            if r.target_camera_id == target_camera_id:
                return r
        return None

    def is_transition_valid(self, source_camera_id: str, target_camera_id: str) -> bool:
        return self.find_rule(source_camera_id, target_camera_id) is not None


class BorderTrack(BaseModel):
    """
    Higher-level border entity tracking continuous activity across multiple physical cameras.
    Avoids claiming facial/biometric ReID certainty; uses explainable spatial-temporal continuity.
    """
    border_track_id: str = Field(..., description="Unique global border-level track identifier (e.g. 'BT-101')")
    camera_sequence: List[str] = Field(default_factory=list, description="Chronological sequence of cameras observing this entity")
    local_tracks: Dict[str, int] = Field(default_factory=dict, description="Map of {camera_id: local_track_id}")
    first_seen_utc: datetime = Field(default_factory=_utc_now)
    last_seen_utc: datetime = Field(default_factory=_utc_now)
    current_camera_id: str
    class_id: TargetClass
    association_state: AssociationState = AssociationState.UNCERTAIN
    association_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    signals: List[AssociationSignal] = Field(default_factory=list)
    trajectory_summary: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    total_duration_seconds: float = 0.0
