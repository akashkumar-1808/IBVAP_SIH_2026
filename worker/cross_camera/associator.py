"""
Cross-Camera Associator & Persistent Border Track Manager.

Links camera-local TrackStates into continuous, multi-camera BorderTracks
using explainable topological, temporal, direction, and spatial constraints.

Architecture Decision: DEC-0009
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta

from .schemas import (
    BorderTrack,
    CameraTopology,
    CameraTransitionRule,
    AssociationState,
    AssociationSignal,
)
from worker.tracking.schemas import TrackState, TargetClass
from worker.spatial.schemas import SpatialState, MovementDirection

logger = logging.getLogger(__name__)


class CrossCameraAssociator:
    """
    Manages continuous border-level track identity across multiple cameras.
    Does NOT claim facial/biometric ReID certainty; derives defensible spatial-temporal continuity.
    """

    def __init__(
        self,
        topology: Optional[CameraTopology] = None,
        max_idle_seconds: float = 30.0,
    ):
        self.topology = topology or CameraTopology()
        self.max_idle_seconds = max_idle_seconds
        self.border_tracks: Dict[str, BorderTrack] = {}
        self._next_id: int = 100

    def register_topology_rule(self, rule: CameraTransitionRule) -> None:
        """Adds a valid directed camera transition constraint to the topology."""
        self.topology.add_rule(rule)

    def process_track(
        self,
        track: TrackState,
        camera_id: str,
        spatial_state: Optional[SpatialState] = None,
        current_time_utc: Optional[datetime] = None,
    ) -> BorderTrack:
        """
        Associates a camera-local track to an existing BorderTrack or initializes a new one.
        """
        now = current_time_utc or track.last_seen or datetime.now(timezone.utc)
        self._prune_inactive_tracks(now)

        # 1. Check if this local track is already associated in this camera
        for bt in self.border_tracks.values():
            if bt.is_active and bt.local_tracks.get(camera_id) == track.track_id:
                # Update existing BorderTrack
                bt.last_seen_utc = now
                bt.current_camera_id = camera_id
                bt.total_duration_seconds = (now - bt.first_seen_utc).total_seconds()
                return bt

        # 2. Search candidate BorderTracks from topologically adjacent cameras for handoff
        best_candidate: Optional[BorderTrack] = None
        best_confidence: float = 0.0
        best_signals: List[AssociationSignal] = []

        for bt in self.border_tracks.values():
            if not bt.is_active or bt.current_camera_id == camera_id:
                continue

            # Check if transition from bt.current_camera_id to camera_id is valid in topology
            rule = self.topology.find_rule(bt.current_camera_id, camera_id)
            if not rule:
                continue

            # Evaluate temporal feasibility: Delta t = t_current - t_last_seen
            delta_t = (track.first_seen - bt.last_seen_utc).total_seconds()
            if delta_t < rule.min_transit_seconds or delta_t > rule.max_transit_seconds:
                continue

            signals: List[AssociationSignal] = [
                AssociationSignal.TOPOLOGY_ADJACENT,
                AssociationSignal.TEMPORAL_MATCH,
            ]
            conf = 0.50

            # Class match
            if track.class_id == bt.class_id:
                signals.append(AssociationSignal.CLASS_MATCH)
                conf += 0.25
            elif bt.class_id != TargetClass.UNKNOWN and track.class_id != TargetClass.UNKNOWN:
                # Direct class mismatch (e.g. Person vs Vehicle)
                continue

            # Direction match
            if spatial_state and rule.expected_direction:
                if spatial_state.direction == rule.expected_direction:
                    signals.append(AssociationSignal.DIRECTION_MATCH)
                    conf += 0.15
                elif spatial_state.direction != MovementDirection.UNCERTAIN:
                    # Direction contradiction
                    conf -= 0.20

            # Spatial corridor continuity
            if spatial_state and spatial_state.border_side:
                signals.append(AssociationSignal.BORDER_CORRIDOR_CONTINUITY)
                conf += 0.10

            conf = max(0.0, min(1.0, conf))

            if conf > best_confidence:
                best_confidence = conf
                best_candidate = bt
                best_signals = signals

        # 3. If a viable candidate exists above threshold, associate handoff
        if best_candidate and best_confidence >= 0.40:
            best_candidate.camera_sequence.append(camera_id)
            best_candidate.local_tracks[camera_id] = track.track_id
            best_candidate.last_seen_utc = now
            best_candidate.current_camera_id = camera_id
            best_candidate.signals = best_signals
            best_candidate.association_confidence = best_confidence
            best_candidate.total_duration_seconds = (now - best_candidate.first_seen_utc).total_seconds()

            if best_confidence >= 0.75:
                best_candidate.association_state = AssociationState.CONFIRMED
            elif best_confidence >= 0.50:
                best_candidate.association_state = AssociationState.LIKELY
            else:
                best_candidate.association_state = AssociationState.UNCERTAIN

            logger.info(
                f"Associated local track {camera_id}:{track.track_id} with BorderTrack '{best_candidate.border_track_id}' "
                f"({best_candidate.association_state.value}, conf={best_confidence:.2f})"
            )
            return best_candidate

        # 4. Otherwise, instantiate a new BorderTrack
        new_bt_id = f"BT-{self._next_id}"
        self._next_id += 1

        new_bt = BorderTrack(
            border_track_id=new_bt_id,
            camera_sequence=[camera_id],
            local_tracks={camera_id: track.track_id},
            first_seen_utc=track.first_seen or now,
            last_seen_utc=now,
            current_camera_id=camera_id,
            class_id=track.class_id,
            association_state=AssociationState.UNCERTAIN,
            association_confidence=0.5,
            signals=[AssociationSignal.TOPOLOGY_ADJACENT],
            total_duration_seconds=0.0,
            is_active=True,
        )
        self.border_tracks[new_bt_id] = new_bt
        return new_bt

    def _prune_inactive_tracks(self, now: datetime) -> None:
        """Marks old inactive BorderTracks as ENDED."""
        for bt in self.border_tracks.values():
            if bt.is_active and (now - bt.last_seen_utc).total_seconds() > self.max_idle_seconds:
                bt.is_active = False
                bt.association_state = AssociationState.ENDED

    def reset(self) -> None:
        """Resets all active border track state."""
        self.border_tracks.clear()
        self._next_id = 100
