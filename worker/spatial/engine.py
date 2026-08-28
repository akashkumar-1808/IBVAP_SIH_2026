import logging
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timezone

from .base import SpatialEngineInterface
from .schemas import (
    SpatialState,
    SpatialTransitionType,
    MovementDirection,
    FenceCrossingEvent,
    ZoneType,
    ZonePolygon,
    VirtualFence,
    CameraSpatialConfig,
)
from .geometry import (
    point_in_polygon,
    segments_intersect,
    calculate_movement_direction,
)
from .exceptions import InvalidGeometryError, ConfigurationError
from ..tracking.schemas import TrackState

logger = logging.getLogger(__name__)

# Precedence order when polygons overlap: CRITICAL has highest precedence, SAFE lowest
ZONE_PRECEDENCE = {
    ZoneType.CRITICAL: 4,
    ZoneType.RESTRICTED: 3,
    ZoneType.BUFFER: 2,
    ZoneType.SAFE: 1,
}


class TrackSpatialTracker:
    """Maintains spatial history and state transitions for a single object track."""

    def __init__(self, track_id: int, camera_id: str):
        self.track_id = track_id
        self.camera_id = camera_id
        self.previous_zone_id: Optional[str] = None
        self.previous_zone_type: Optional[ZoneType] = None
        self.fences_crossed_history: List[str] = []
        self.last_state: Optional[SpatialState] = None


class SpatialEngine(SpatialEngineInterface):
    """
    Production Spatial Intelligence Engine for 2D camera-space geometric reasoning.
    Evaluates zone membership, virtual fence crossings, and movement direction.
    """

    def __init__(self):
        self._camera_configs: Dict[str, CameraSpatialConfig] = {}
        self._track_states: Dict[str, Dict[int, TrackSpatialTracker]] = {}  # {camera_id: {track_id: tracker}}

    def configure_camera(self, config: CameraSpatialConfig) -> None:
        """Validates and registers camera-specific spatial zones and virtual fences."""
        if not config.camera_id:
            raise ConfigurationError("CameraSpatialConfig must specify a valid camera_id")

        # Validate zones
        for zone in config.zones:
            if len(zone.polygon) < 3:
                raise InvalidGeometryError(f"Zone '{zone.id}' must have at least 3 vertices (found {len(zone.polygon)})")
            for pt in zone.polygon:
                if not (isinstance(pt[0], (int, float)) and isinstance(pt[1], (int, float))):
                    raise InvalidGeometryError(f"Zone '{zone.id}' contains non-numeric coordinates: {pt}")

        # Validate fences
        for fence in config.fences:
            if len(fence.start_point) != 2 or len(fence.end_point) != 2:
                raise InvalidGeometryError(f"Virtual fence '{fence.id}' must specify 2D start and end points")

        self._camera_configs[config.camera_id] = config
        if config.camera_id not in self._track_states:
            self._track_states[config.camera_id] = {}

        logger.info(f"SpatialEngine configured for camera '{config.camera_id}': {len(config.zones)} zones, {len(config.fences)} fences.")

    def process_tracks(
        self,
        tracks: List[TrackState],
        camera_id: str,
        timestamp_utc: datetime,
    ) -> List[SpatialState]:
        """Processes active object tracks against camera spatial geometry."""
        config = self._camera_configs.get(camera_id)
        if config is None:
            # If no custom configuration exists, create default empty config
            config = CameraSpatialConfig(camera_id=camera_id)
            self.configure_camera(config)

        if camera_id not in self._track_states:
            self._track_states[camera_id] = {}

        camera_track_map = self._track_states[camera_id]
        results: List[SpatialState] = []

        for track in tracks:
            t_id = track.track_id
            if t_id not in camera_track_map:
                camera_track_map[t_id] = TrackSpatialTracker(track_id=t_id, camera_id=camera_id)

            tracker_mem = camera_track_map[t_id]
            curr_pos = track.center_xy

            # -------------------------------------------------------------
            # 1. Point-in-Polygon Zone Membership with Precedence
            # -------------------------------------------------------------
            matching_zones: List[ZonePolygon] = []
            for zone in config.zones:
                if zone.is_active and point_in_polygon(curr_pos, zone.polygon):
                    matching_zones.append(zone)

            # Sort by precedence (highest first)
            matching_zones.sort(key=lambda z: ZONE_PRECEDENCE.get(z.type, 0), reverse=True)

            current_zone_id = matching_zones[0].id if matching_zones else None
            current_zone_type = matching_zones[0].type if matching_zones else None

            # -------------------------------------------------------------
            # 2. Zone Transition Detection
            # -------------------------------------------------------------
            transition = SpatialTransitionType.NONE
            if tracker_mem.previous_zone_id != current_zone_id:
                if current_zone_id is not None:
                    transition = SpatialTransitionType.ZONE_ENTERED
                elif tracker_mem.previous_zone_id is not None:
                    transition = SpatialTransitionType.ZONE_EXITED

            # -------------------------------------------------------------
            # 3. Virtual Fence Crossing Detection
            # -------------------------------------------------------------
            crossing_events: List[FenceCrossingEvent] = []
            fences_crossed: List[str] = []

            if len(track.trajectory) >= 2:
                p1 = (track.trajectory[-2].x, track.trajectory[-2].y)
                p2 = (track.trajectory[-1].x, track.trajectory[-1].y)

                for fence in config.fences:
                    if fence.is_active:
                        q1 = fence.start_point
                        q2 = fence.end_point
                        crossed, ix_pt = segments_intersect(p1, p2, q1, q2)

                        if crossed:
                            fences_crossed.append(fence.id)
                            # Evaluate crossing direction relative to threat vector
                            cross_dir = calculate_movement_direction(p1, p2, config.expected_threat_vector)
                            ev = FenceCrossingEvent(
                                fence_id=fence.id,
                                track_id=t_id,
                                camera_id=camera_id,
                                timestamp_utc=timestamp_utc,
                                previous_position=p1,
                                current_position=p2,
                                crossing_point=ix_pt,
                                crossing_direction=cross_dir,
                            )
                            crossing_events.append(ev)
                            if fence.id not in tracker_mem.fences_crossed_history:
                                tracker_mem.fences_crossed_history.append(fence.id)

            # -------------------------------------------------------------
            # 4. Movement Direction Calculation
            # -------------------------------------------------------------
            if len(track.trajectory) >= 2:
                p_prev = (track.trajectory[-2].x, track.trajectory[-2].y)
                p_curr = (track.trajectory[-1].x, track.trajectory[-1].y)
                direction = calculate_movement_direction(p_prev, p_curr, config.expected_threat_vector)
            else:
                direction = MovementDirection.UNCERTAIN

            # -------------------------------------------------------------
            # 5. Build Canonical SpatialState
            # -------------------------------------------------------------
            state = SpatialState(
                camera_id=camera_id,
                track_id=t_id,
                timestamp_utc=timestamp_utc,
                current_zone_id=current_zone_id,
                current_zone_type=current_zone_type,
                previous_zone_id=tracker_mem.previous_zone_id,
                transition=transition,
                direction=direction,
                fences_crossed=fences_crossed,
                crossing_events=crossing_events,
                metadata={
                    "total_fences_crossed": list(tracker_mem.fences_crossed_history),
                    "matching_zones_count": len(matching_zones),
                },
            )

            # Update tracker memory for next frame
            tracker_mem.previous_zone_id = current_zone_id
            tracker_mem.previous_zone_type = current_zone_type
            tracker_mem.last_state = state

            results.append(state)

        # Prune dead tracks that are no longer present in tracks
        active_ids = {t.track_id for t in tracks}
        dead_ids = [tid for tid in camera_track_map.keys() if tid not in active_ids]
        for tid in dead_ids:
            del camera_track_map[tid]

        return results

    def get_spatial_state(self, camera_id: str, track_id: int) -> Optional[SpatialState]:
        camera_map = self._track_states.get(camera_id)
        if camera_map and track_id in camera_map:
            return camera_map[track_id].last_state
        return None

    def reset(self, camera_id: Optional[str] = None) -> None:
        if camera_id:
            if camera_id in self._track_states:
                self._track_states[camera_id].clear()
        else:
            for c_map in self._track_states.values():
                c_map.clear()
            self._track_states.clear()
        logger.info(f"SpatialEngine reset for camera: {camera_id or 'ALL'}")

    def close(self) -> None:
        self.reset()
