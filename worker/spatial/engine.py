"""
IBVAP Spatial Intelligence Engine — Production Implementation.

Supports two modes:
1. WORLD-BORDER MODE (calibrated cameras): Uses world-space border sections,
   camera calibration (planar homography), ground-contact points, signed-distance
   side determination, and multi-frame crossing confirmation.
2. LEGACY IMAGE-SPACE MODE (uncalibrated cameras): Falls back to the Phase 6
   pixel-space zone/fence logic for backward compatibility.

Architecture Decision: DEC-0006 (world-owned border model)
"""

import logging
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timezone
import numpy as np

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
    BorderSide,
    CrossingStatus,
    SpatialConfidence,
)
from .world_schemas import (
    BorderSection,
    CameraRegistration,
    CameraCalibration,
    CalibrationStatus,
    ProjectedBorder,
    GroundContactPoint,
    CrossingEvent,
    TerrainMode,
)
from .geometry import (
    point_in_polygon,
    segments_intersect,
    calculate_movement_direction,
)
from .calibration import (
    compute_homography,
    project_world_to_image,
    project_image_to_world,
    validate_calibration,
    project_border_to_camera,
    CalibrationError,
    TerrainModeNotImplementedError,
)
from .ground_contact import estimate_ground_contact, image_to_world_ground
from .border_logic import determine_side, check_crossing, CrossingConfirmation
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
    Production Spatial Intelligence Engine for IBVAP.

    Supports both world-border mode (calibrated cameras with global border sections)
    and legacy image-space mode (uncalibrated cameras with manual pixel zones/fences).
    """

    def __init__(self, crossing_confirmation_frames: int = 3):
        # Legacy image-space state
        self._camera_configs: Dict[str, CameraSpatialConfig] = {}
        self._track_states: Dict[str, Dict[int, TrackSpatialTracker]] = {}

        # World-border state
        self._border_sections: Dict[str, BorderSection] = {}
        self._camera_registrations: Dict[str, CameraRegistration] = {}
        self._camera_calibrations: Dict[str, CameraCalibration] = {}
        self._homography_matrices: Dict[str, np.ndarray] = {}  # camera_id → H
        self._homography_inverses: Dict[str, np.ndarray] = {}  # camera_id → H_inv
        self._projected_borders: Dict[str, Dict[str, ProjectedBorder]] = {}  # camera_id → {section_id → ProjectedBorder}
        self._crossing_confirmations: Dict[str, CrossingConfirmation] = {}  # camera_id → CrossingConfirmation
        self._crossing_confirmation_frames = crossing_confirmation_frames

    # ── World-Border API ──────────────────────────────────────────────────

    def register_border_section(self, section: BorderSection) -> None:
        """Registers a world-space border section."""
        if section.terrain_mode == TerrainMode.TERRAIN_3D:
            raise TerrainModeNotImplementedError(
                "TERRAIN_3D is not yet implemented. Only PLANAR_GROUND is supported."
            )
        if len(section.points) < 2:
            raise InvalidGeometryError(f"Border section '{section.id}' requires at least 2 points")
        self._border_sections[section.id] = section
        logger.info(f"Registered border section '{section.id}' ({len(section.points)} points)")

    def register_camera(self, registration: CameraRegistration) -> None:
        """Registers a camera with its border section associations."""
        self._camera_registrations[registration.camera_id] = registration
        logger.info(
            f"Registered camera '{registration.camera_id}' "
            f"(sections: {registration.visible_border_sections}, status: {registration.calibration_status.value})"
        )

    def register_calibration(self, calibration: CameraCalibration) -> None:
        """
        Registers and validates a camera calibration profile.
        Computes and caches the homography matrix and its inverse.
        """
        status = validate_calibration(calibration)
        calibration.status = status

        if status == CalibrationStatus.INVALID:
            logger.warning(f"Calibration for camera '{calibration.camera_id}' is INVALID")
            self._camera_calibrations[calibration.camera_id] = calibration
            return

        # Compute and cache homography
        try:
            H, reproj_error = compute_homography(calibration.correspondences)
            calibration.reprojection_error = reproj_error
            self._homography_matrices[calibration.camera_id] = H
            self._homography_inverses[calibration.camera_id] = np.linalg.inv(H)
            self._camera_calibrations[calibration.camera_id] = calibration

            # Update registration status
            if calibration.camera_id in self._camera_registrations:
                self._camera_registrations[calibration.camera_id].calibration_status = status
                self._camera_registrations[calibration.camera_id].calibration_version = calibration.calibration_version

            # Initialize crossing confirmation for this camera
            if calibration.camera_id not in self._crossing_confirmations:
                self._crossing_confirmations[calibration.camera_id] = CrossingConfirmation(
                    confirmation_frames=self._crossing_confirmation_frames
                )

            logger.info(
                f"Calibration registered for camera '{calibration.camera_id}' "
                f"(status={status.value}, reproj_error={reproj_error:.4f}px)"
            )
        except (CalibrationError, np.linalg.LinAlgError) as e:
            calibration.status = CalibrationStatus.INVALID
            self._camera_calibrations[calibration.camera_id] = calibration
            logger.error(f"Calibration failed for camera '{calibration.camera_id}': {e}")

    def project_border(self, camera_id: str, section_id: str) -> Optional[ProjectedBorder]:
        """Projects a world border section into camera image coordinates."""
        section = self._border_sections.get(section_id)
        calibration = self._camera_calibrations.get(camera_id)
        H = self._homography_matrices.get(camera_id)

        if section is None or calibration is None or H is None:
            return None

        if calibration.status in (CalibrationStatus.INVALID, CalibrationStatus.UNCALIBRATED):
            return None

        try:
            proj = project_border_to_camera(section, calibration, H)
            # Cache the projection
            if camera_id not in self._projected_borders:
                self._projected_borders[camera_id] = {}
            self._projected_borders[camera_id][section_id] = proj
            return proj
        except (CalibrationError, TerrainModeNotImplementedError) as e:
            logger.warning(f"Border projection failed for camera '{camera_id}', section '{section_id}': {e}")
            return None

    def get_ground_reference_point(self, track: TrackState) -> GroundContactPoint:
        """Estimates the ground-contact point for a tracked object."""
        return estimate_ground_contact(track)

    def get_side_relationship(
        self, camera_id: str, track: TrackState, section_id: str,
    ) -> BorderSide:
        """
        Determines which side of a border section a tracked object is on.
        Requires calibrated camera with valid homography.
        """
        section = self._border_sections.get(section_id)
        H_inv = self._homography_inverses.get(camera_id)

        if section is None or H_inv is None:
            return BorderSide.UNKNOWN

        # Get ground-contact point in pixels
        gc = estimate_ground_contact(track)

        # Map to world coordinates
        try:
            world_pt = image_to_world_ground(gc.pixel_xy, H_inv)
            return determine_side((world_pt.x, world_pt.y), section)
        except Exception:
            return BorderSide.UNKNOWN

    def check_crossing_event(
        self, camera_id: str, track_id: int,
    ) -> Optional[CrossingEvent]:
        """Returns the latest crossing event for a track, if any."""
        # This is read from the confirmation engine during process_tracks
        return None  # Individual query not needed; process_tracks populates SpatialState

    # ── Legacy Image-Space API ────────────────────────────────────────────

    def configure_camera(self, config: CameraSpatialConfig) -> None:
        """Validates and registers camera-specific spatial zones and virtual fences (legacy mode)."""
        if not config.camera_id:
            raise ConfigurationError("CameraSpatialConfig must specify a valid camera_id")

        for zone in config.zones:
            if len(zone.polygon) < 3:
                raise InvalidGeometryError(f"Zone '{zone.id}' must have at least 3 vertices (found {len(zone.polygon)})")
            for pt in zone.polygon:
                if not (isinstance(pt[0], (int, float)) and isinstance(pt[1], (int, float))):
                    raise InvalidGeometryError(f"Zone '{zone.id}' contains non-numeric coordinates: {pt}")

        for fence in config.fences:
            if len(fence.start_point) != 2 or len(fence.end_point) != 2:
                raise InvalidGeometryError(f"Virtual fence '{fence.id}' must specify 2D start and end points")

        self._camera_configs[config.camera_id] = config
        if config.camera_id not in self._track_states:
            self._track_states[config.camera_id] = {}

        logger.info(f"SpatialEngine configured for camera '{config.camera_id}': {len(config.zones)} zones, {len(config.fences)} fences.")

    # ── Unified Processing ────────────────────────────────────────────────

    def process_tracks(
        self,
        tracks: List[TrackState],
        camera_id: str,
        timestamp_utc: datetime,
    ) -> List[SpatialState]:
        """
        Processes active object tracks against spatial geometry.

        If the camera has a valid world-border calibration, uses world-space
        border logic (ground-contact → world projection → side determination → crossing).

        Otherwise, falls back to legacy image-space zone/fence logic.
        """
        has_world_border = self._has_world_border(camera_id)

        if has_world_border:
            return self._process_world_border(tracks, camera_id, timestamp_utc)
        else:
            return self._process_legacy(tracks, camera_id, timestamp_utc)

    def _has_world_border(self, camera_id: str) -> bool:
        """Checks if a camera has valid world-border calibration."""
        cal = self._camera_calibrations.get(camera_id)
        if cal is None or cal.status in (CalibrationStatus.INVALID, CalibrationStatus.UNCALIBRATED):
            return False
        reg = self._camera_registrations.get(camera_id)
        if reg is None or not reg.visible_border_sections:
            return False
        # Check at least one border section exists
        return any(sid in self._border_sections for sid in reg.visible_border_sections)

    def _process_world_border(
        self,
        tracks: List[TrackState],
        camera_id: str,
        timestamp_utc: datetime,
    ) -> List[SpatialState]:
        """Processes tracks using the world-border model."""
        reg = self._camera_registrations[camera_id]
        cal = self._camera_calibrations[camera_id]
        H_inv = self._homography_inverses.get(camera_id)
        confirmation = self._crossing_confirmations.get(camera_id)

        if H_inv is None or confirmation is None:
            return self._process_legacy(tracks, camera_id, timestamp_utc)

        # Ensure track state exists
        if camera_id not in self._track_states:
            self._track_states[camera_id] = {}
        camera_track_map = self._track_states[camera_id]

        # Also run legacy processing for zone/fence info if config exists
        legacy_config = self._camera_configs.get(camera_id)

        results: List[SpatialState] = []

        for track in tracks:
            t_id = track.track_id
            if t_id not in camera_track_map:
                camera_track_map[t_id] = TrackSpatialTracker(track_id=t_id, camera_id=camera_id)

            tracker_mem = camera_track_map[t_id]

            # 1. Ground-contact point
            gc = estimate_ground_contact(track)

            # 2. Map to world coordinates
            try:
                world_pt = image_to_world_ground(gc.pixel_xy, H_inv)
                gc.world_xy = (world_pt.x, world_pt.y)
                confidence = gc.confidence
            except Exception:
                world_pt = None
                confidence = SpatialConfidence.INVALID

            # 3. Side determination for each visible border section
            best_side = BorderSide.UNKNOWN
            best_crossing_status = CrossingStatus.NONE
            crossing_event: Optional[CrossingEvent] = None

            for section_id in reg.visible_border_sections:
                section = self._border_sections.get(section_id)
                if section is None or world_pt is None:
                    continue

                side = determine_side((world_pt.x, world_pt.y), section)
                best_side = side  # Use last visible section (typically one)

                # 4. Crossing confirmation
                event = confirmation.update(
                    track_id=t_id,
                    border_section_id=section_id,
                    current_side=side,
                    camera_id=camera_id,
                    timestamp_utc=timestamp_utc,
                    ground_point=gc,
                    calibration_version=cal.calibration_version,
                )
                if event is not None:
                    crossing_event = event
                    best_crossing_status = event.crossing_status

            # 5. Legacy zone/fence processing (if config exists)
            curr_pos = track.center_xy
            current_zone_id = None
            current_zone_type = None
            transition = SpatialTransitionType.NONE
            fences_crossed: List[str] = []
            fence_crossing_events: List[FenceCrossingEvent] = []
            direction = MovementDirection.UNCERTAIN

            if legacy_config:
                current_zone_id, current_zone_type, transition, fences_crossed, fence_crossing_events, direction = \
                    self._evaluate_legacy_for_track(track, legacy_config, tracker_mem, timestamp_utc)
            elif len(track.trajectory) >= 2:
                # Compute direction from trajectory even without legacy config
                p_prev = (track.trajectory[-2].x, track.trajectory[-2].y)
                p_curr = (track.trajectory[-1].x, track.trajectory[-1].y)
                config = self._camera_configs.get(camera_id)
                threat_vec = config.expected_threat_vector if config else None
                direction = calculate_movement_direction(p_prev, p_curr, threat_vec)

            # Map border_side to zone_type for behavior engine compatibility
            if best_side == BorderSide.RESTRICTED and current_zone_type is None:
                current_zone_type = ZoneType.RESTRICTED
            elif best_side == BorderSide.WARNING_BUFFER and current_zone_type is None:
                current_zone_type = ZoneType.BUFFER

            # 6. Build SpatialState
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
                crossing_events=fence_crossing_events,
                metadata={
                    "total_fences_crossed": list(tracker_mem.fences_crossed_history),
                    "mode": "world_border",
                },
                border_side=best_side,
                crossing_status=best_crossing_status,
                ground_contact=gc,
                calibration_version=cal.calibration_version,
                spatial_confidence=confidence,
            )

            tracker_mem.previous_zone_id = current_zone_id
            tracker_mem.previous_zone_type = current_zone_type
            tracker_mem.last_state = state
            results.append(state)

        # Prune dead tracks
        active_ids = {t.track_id for t in tracks}
        dead_ids = [tid for tid in camera_track_map.keys() if tid not in active_ids]
        for tid in dead_ids:
            del camera_track_map[tid]
        confirmation.prune_tracks(active_ids)

        return results

    def _process_legacy(
        self,
        tracks: List[TrackState],
        camera_id: str,
        timestamp_utc: datetime,
    ) -> List[SpatialState]:
        """Legacy image-space processing (Phase 6 backward-compatible path)."""
        config = self._camera_configs.get(camera_id)
        if config is None:
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

            current_zone_id, current_zone_type, transition, fences_crossed, crossing_events, direction = \
                self._evaluate_legacy_for_track(track, config, tracker_mem, timestamp_utc)

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
                    "matching_zones_count": 0,
                    "mode": "legacy_image_space",
                },
            )

            tracker_mem.previous_zone_id = current_zone_id
            tracker_mem.previous_zone_type = current_zone_type
            tracker_mem.last_state = state
            results.append(state)

        # Prune dead tracks
        active_ids = {t.track_id for t in tracks}
        dead_ids = [tid for tid in camera_track_map.keys() if tid not in active_ids]
        for tid in dead_ids:
            del camera_track_map[tid]

        return results

    def _evaluate_legacy_for_track(
        self,
        track: TrackState,
        config: CameraSpatialConfig,
        tracker_mem: TrackSpatialTracker,
        timestamp_utc: datetime,
    ) -> Tuple[Optional[str], Optional[ZoneType], SpatialTransitionType, List[str], List[FenceCrossingEvent], MovementDirection]:
        """Evaluates legacy zone/fence geometry for a single track."""
        curr_pos = track.center_xy

        # 1. Zone membership with precedence
        matching_zones: List[ZonePolygon] = []
        for zone in config.zones:
            if zone.is_active and point_in_polygon(curr_pos, zone.polygon):
                matching_zones.append(zone)
        matching_zones.sort(key=lambda z: ZONE_PRECEDENCE.get(z.type, 0), reverse=True)

        current_zone_id = matching_zones[0].id if matching_zones else None
        current_zone_type = matching_zones[0].type if matching_zones else None

        # 2. Zone transition
        transition = SpatialTransitionType.NONE
        if tracker_mem.previous_zone_id != current_zone_id:
            if current_zone_id is not None:
                transition = SpatialTransitionType.ZONE_ENTERED
            elif tracker_mem.previous_zone_id is not None:
                transition = SpatialTransitionType.ZONE_EXITED

        # 3. Virtual fence crossing
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
                        cross_dir = calculate_movement_direction(p1, p2, config.expected_threat_vector)
                        ev = FenceCrossingEvent(
                            fence_id=fence.id,
                            track_id=track.track_id,
                            camera_id=track.camera_id,
                            timestamp_utc=timestamp_utc,
                            previous_position=p1,
                            current_position=p2,
                            crossing_point=ix_pt,
                            crossing_direction=cross_dir,
                        )
                        crossing_events.append(ev)
                        if fence.id not in tracker_mem.fences_crossed_history:
                            tracker_mem.fences_crossed_history.append(fence.id)

        # 4. Movement direction
        if len(track.trajectory) >= 2:
            p_prev = (track.trajectory[-2].x, track.trajectory[-2].y)
            p_curr = (track.trajectory[-1].x, track.trajectory[-1].y)
            direction = calculate_movement_direction(p_prev, p_curr, config.expected_threat_vector)
        else:
            direction = MovementDirection.UNCERTAIN

        return current_zone_id, current_zone_type, transition, fences_crossed, crossing_events, direction

    # ── Existing Interface Methods ────────────────────────────────────────

    def get_spatial_state(self, camera_id: str, track_id: int) -> Optional[SpatialState]:
        camera_map = self._track_states.get(camera_id)
        if camera_map and track_id in camera_map:
            return camera_map[track_id].last_state
        return None

    def reset(self, camera_id: Optional[str] = None) -> None:
        if camera_id:
            if camera_id in self._track_states:
                self._track_states[camera_id].clear()
            if camera_id in self._crossing_confirmations:
                self._crossing_confirmations[camera_id].reset()
        else:
            for c_map in self._track_states.values():
                c_map.clear()
            self._track_states.clear()
            for cc in self._crossing_confirmations.values():
                cc.reset()
        logger.info(f"SpatialEngine reset for camera: {camera_id or 'ALL'}")

    def close(self) -> None:
        self.reset()
