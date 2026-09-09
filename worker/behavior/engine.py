import logging
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timezone

from .base import BehaviorEngineInterface
from .schemas import (
    BehaviorPrimitive,
    BehaviorType,
    BehaviorStatus,
    ReasonCode,
    BehaviorConfig,
)
from .loitering import LoiteringDetector
from .approach import ApproachDetector
from .occupancy import OccupancyDetector, FenceBreachDetector
from .speed import SpeedAnomalyDetector
from ..tracking.schemas import TrackState
from ..spatial.schemas import SpatialState, MovementDirection, ZoneType
from ..environment.schemas import EnvironmentState
from .exceptions import InvalidBehaviorConfigError

logger = logging.getLogger(__name__)


class TrackTemporalMemory:
    """Bounded temporal memory and behavioral state for a single track on a camera."""

    def __init__(self, track_id: int, camera_id: str):
        self.track_id = track_id
        self.camera_id = camera_id

        # Zone tracking
        self.current_zone_id: Optional[str] = None
        self.zone_entry_time: Optional[datetime] = None
        self.first_position_in_zone: Optional[Tuple[float, float]] = None

        # Approach tracking
        self.approach_start_time: Optional[datetime] = None
        self.approach_start_pos: Optional[Tuple[float, float]] = None
        self.last_approach_completed_time: Optional[datetime] = None

        # Active behaviors: {behavior_id: BehaviorPrimitive}
        self.active_behaviors: Dict[str, BehaviorPrimitive] = {}


class BehaviorEngine(BehaviorEngineInterface):
    """
    Production Behavioral Analytics Engine for IBVAP.
    Consumes TrackState[] and SpatialState[] to generate explainable temporal BehaviorPrimitive instances.
    """

    def __init__(self, default_config: Optional[BehaviorConfig] = None):
        self._default_config = default_config or BehaviorConfig()
        self._camera_configs: Dict[str, BehaviorConfig] = {}
        self._camera_track_memories: Dict[str, Dict[int, TrackTemporalMemory]] = {}
        self._detectors: Dict[str, Dict[str, Any]] = {}

    def configure(self, camera_id: str, config: BehaviorConfig) -> None:
        if not camera_id:
            raise InvalidBehaviorConfigError("Camera ID must be a non-empty string.")

        self._camera_configs[camera_id] = config
        self._detectors[camera_id] = {
            "loitering": LoiteringDetector(config),
            "approach": ApproachDetector(config),
            "occupancy": OccupancyDetector(config),
            "fence": FenceBreachDetector(config),
            "speed": SpeedAnomalyDetector(config),
        }
        if camera_id not in self._camera_track_memories:
            self._camera_track_memories[camera_id] = {}

        logger.info(f"BehaviorEngine configured for camera '{camera_id}' with loiter_thresh={config.loitering_seconds}s.")

    def _get_or_init_camera(self, camera_id: str) -> Tuple[BehaviorConfig, Dict[str, Any], Dict[int, TrackTemporalMemory]]:
        if camera_id not in self._camera_configs:
            self.configure(camera_id, self._default_config)
        return (
            self._camera_configs[camera_id],
            self._detectors[camera_id],
            self._camera_track_memories[camera_id],
        )

    def process(
        self,
        tracks: List[TrackState],
        spatial_states: List[SpatialState],
        timestamp_utc: datetime,
        environment_state: Optional[EnvironmentState] = None,
    ) -> List[BehaviorPrimitive]:
        """
        Evaluates active tracks and spatial states, outputting canonical explainable BehaviorPrimitive records.
        """
        if not tracks:
            return []

        camera_id = tracks[0].camera_id
        config, detectors, track_mem_map = self._get_or_init_camera(camera_id)

        # Index spatial states by track_id
        spatial_map: Dict[int, SpatialState] = {st.track_id: st for st in spatial_states}
        active_primitives: List[BehaviorPrimitive] = []

        for track in tracks:
            t_id = track.track_id
            spatial = spatial_map.get(t_id)
            if not spatial:
                continue

            if t_id not in track_mem_map:
                track_mem_map[t_id] = TrackTemporalMemory(track_id=t_id, camera_id=camera_id)

            mem = track_mem_map[t_id]

            effective_zone = spatial.current_zone_id or (
                spatial.border_side.value
                if getattr(spatial, "border_side", None) and spatial.border_side.value in ("warning_buffer", "restricted")
                else None
            )

            # -------------------------------------------------------------
            # 1. Update Zone Entry / Exit Temporal State
            # -------------------------------------------------------------
            if effective_zone != mem.current_zone_id:
                # Exited previous zone -> complete zone-dependent behaviors
                if mem.current_zone_id is not None:
                    for b_id in list(mem.active_behaviors.keys()):
                        if mem.active_behaviors[b_id].behavior_type in (BehaviorType.LOITERING, BehaviorType.RESTRICTED_OCCUPANCY):
                            mem.active_behaviors[b_id].status = BehaviorStatus.COMPLETED
                            mem.active_behaviors[b_id].last_observed_utc = timestamp_utc
                            del mem.active_behaviors[b_id]

                # Entered new zone
                mem.current_zone_id = effective_zone
                if effective_zone is not None:
                    mem.zone_entry_time = timestamp_utc
                    mem.first_position_in_zone = track.center_xy
                else:
                    mem.zone_entry_time = None
                    mem.first_position_in_zone = None

            # -------------------------------------------------------------
            # 2. Update Direction & Approach Temporal State
            # -------------------------------------------------------------
            if spatial.direction == MovementDirection.TOWARD:
                if mem.approach_start_time is None:
                    mem.approach_start_time = timestamp_utc
                    mem.approach_start_pos = track.center_xy
            else:
                if mem.approach_start_time is not None:
                    # If approach was sustained for at least threshold, record completion timestamp
                    dur = (timestamp_utc - mem.approach_start_time).total_seconds()
                    if dur >= config.persistent_approach_seconds:
                        mem.last_approach_completed_time = timestamp_utc

                    # Complete active approach behaviors
                    for b_id in list(mem.active_behaviors.keys()):
                        if mem.active_behaviors[b_id].behavior_type in (BehaviorType.PERSISTENT_APPROACH, BehaviorType.REPEATED_APPROACH):
                            mem.active_behaviors[b_id].status = BehaviorStatus.COMPLETED
                            mem.active_behaviors[b_id].last_observed_utc = timestamp_utc
                            del mem.active_behaviors[b_id]

                    mem.approach_start_time = None
                    mem.approach_start_pos = None

            # -------------------------------------------------------------
            # 3. Evaluate Behavioral Detectors
            # -------------------------------------------------------------
            # A. Loitering
            loiter_primitive = detectors["loitering"].evaluate(
                track=track,
                spatial=spatial,
                zone_entry_time=mem.zone_entry_time,
                first_position_in_zone=mem.first_position_in_zone,
                timestamp_utc=timestamp_utc,
            )
            if loiter_primitive:
                self._upsert_primitive(mem, loiter_primitive, active_primitives)

            # B. Approach (Persistent & Repeated)
            pers_app, rep_app = detectors["approach"].evaluate(
                track=track,
                spatial=spatial,
                approach_start_time=mem.approach_start_time,
                approach_start_pos=mem.approach_start_pos,
                last_approach_completed_time=mem.last_approach_completed_time,
                timestamp_utc=timestamp_utc,
            )
            if pers_app:
                self._upsert_primitive(mem, pers_app, active_primitives)
            if rep_app:
                self._upsert_primitive(mem, rep_app, active_primitives)

            # C. Restricted Occupancy
            occ_primitive = detectors["occupancy"].evaluate(
                track=track,
                spatial=spatial,
                zone_entry_time=mem.zone_entry_time,
                timestamp_utc=timestamp_utc,
            )
            if occ_primitive:
                self._upsert_primitive(mem, occ_primitive, active_primitives)

            # D. Fence Breach & Border Crossing
            fence_primitives = detectors["fence"].evaluate(
                track=track,
                spatial=spatial,
                timestamp_utc=timestamp_utc,
            )
            for fp in fence_primitives:
                self._upsert_primitive(mem, fp, active_primitives)

            # E. Speed Anomaly
            if "speed" in detectors:
                speed_primitive = detectors["speed"].evaluate(
                    track=track,
                    spatial=spatial,
                    timestamp_utc=timestamp_utc,
                )
                if speed_primitive:
                    self._upsert_primitive(mem, speed_primitive, active_primitives)
                else:
                    for b_id in list(mem.active_behaviors.keys()):
                        if mem.active_behaviors[b_id].behavior_type == BehaviorType.SPEED_ANOMALY:
                            mem.active_behaviors[b_id].status = BehaviorStatus.COMPLETED
                            mem.active_behaviors[b_id].last_observed_utc = timestamp_utc
                            del mem.active_behaviors[b_id]

        # -------------------------------------------------------------
        # 4. Prune Expired Tracks
        # -------------------------------------------------------------
        active_track_ids = {t.track_id for t in tracks}
        dead_ids = [tid for tid in track_mem_map.keys() if tid not in active_track_ids]
        for tid in dead_ids:
            del track_mem_map[tid]

        return active_primitives

    def _upsert_primitive(
        self,
        mem: TrackTemporalMemory,
        new_primitive: BehaviorPrimitive,
        output_list: List[BehaviorPrimitive],
    ) -> None:
        """De-duplicates active behaviors, updating duration, confidence, and timestamps on sustained events."""
        b_id = new_primitive.behavior_id
        if b_id in mem.active_behaviors:
            existing = mem.active_behaviors[b_id]
            existing.last_observed_utc = new_primitive.last_observed_utc
            existing.duration_seconds = new_primitive.duration_seconds
            existing.supporting_data = new_primitive.supporting_data
            existing.confidence = new_primitive.confidence
            existing.triggering_condition = new_primitive.triggering_condition
            output_list.append(existing)
        else:
            mem.active_behaviors[b_id] = new_primitive
            output_list.append(new_primitive)

    def get_active_behaviors(self, camera_id: str) -> List[BehaviorPrimitive]:
        active = []
        track_map = self._camera_track_memories.get(camera_id, {})
        for mem in track_map.values():
            active.extend(mem.active_behaviors.values())
        return active

    def reset(self, camera_id: Optional[str] = None) -> None:
        if camera_id:
            if camera_id in self._camera_track_memories:
                self._camera_track_memories[camera_id].clear()
        else:
            for c_map in self._camera_track_memories.values():
                c_map.clear()
            self._camera_track_memories.clear()
        logger.info(f"BehaviorEngine reset for camera: {camera_id or 'ALL'}")

    def close(self) -> None:
        self.reset()
