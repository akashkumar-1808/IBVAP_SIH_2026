"""
Border side determination and crossing detection logic for IBVAP.

Provides world-space side classification (permitted/buffer/restricted),
crossing candidate detection from track trajectory, and multi-frame
crossing confirmation with jitter resistance.

Architecture Decision: DEC-0006
"""

import logging
import math
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timezone

from .world_schemas import (
    BorderSection,
    BorderSide,
    CrossingStatus,
    CrossingEvent,
    GroundContactPoint,
    WorldPoint,
    SpatialConfidence,
)
from .exceptions import SpatialError

logger = logging.getLogger(__name__)


def _signed_distance_to_polyline(
    point: Tuple[float, float],
    polyline: List[WorldPoint],
    normal: Tuple[float, float],
) -> float:
    """
    Computes the signed perpendicular distance from a point to the nearest
    segment of the border polyline.

    Positive = on the side of the normal (permitted side).
    Negative = on the opposite side (restricted side).
    Zero = on the border line.
    """
    if len(polyline) < 2:
        return 0.0

    px, py = point
    min_dist_sq = float("inf")
    nearest_proj = (0.0, 0.0)

    for i in range(len(polyline) - 1):
        ax, ay = polyline[i].x, polyline[i].y
        bx, by = polyline[i + 1].x, polyline[i + 1].y

        dx = bx - ax
        dy = by - ay
        seg_len_sq = dx * dx + dy * dy

        if seg_len_sq < 1e-12:
            # Degenerate segment
            proj_x, proj_y = ax, ay
        else:
            t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len_sq))
            proj_x = ax + t * dx
            proj_y = ay + t * dy

        dist_sq = (px - proj_x) ** 2 + (py - proj_y) ** 2
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            nearest_proj = (proj_x, proj_y)

    min_dist = math.sqrt(min_dist_sq)

    # Determine sign using the normal vector
    nx, ny = normal
    n_len = math.hypot(nx, ny)
    if n_len < 1e-9:
        return min_dist  # No valid normal → unsigned

    # Vector from nearest border point to the query point
    to_point_x = px - nearest_proj[0]
    to_point_y = py - nearest_proj[1]

    # Dot product with normal: positive = same side as normal (permitted)
    dot = to_point_x * (nx / n_len) + to_point_y * (ny / n_len)

    return min_dist if dot >= 0 else -min_dist


def determine_side(
    world_point: Tuple[float, float],
    border_section: BorderSection,
    border_line_tolerance: float = 0.5,
) -> BorderSide:
    """
    Determines which side of the border a world-space point lies on.

    Uses signed distance from the border polyline:
    - Positive (toward normal) = PERMITTED side
    - Within buffer distance = WARNING_BUFFER
    - Within border tolerance = BORDER_LINE
    - Negative (away from normal) = RESTRICTED side

    Args:
        world_point: (x, y) in world coordinates
        border_section: The border section to test against
        border_line_tolerance: Distance threshold to classify as ON the border line
    """
    signed_dist = _signed_distance_to_polyline(
        world_point,
        border_section.points,
        border_section.permitted_side_normal,
    )

    abs_dist = abs(signed_dist)

    # On the border line itself
    if abs_dist <= border_line_tolerance:
        return BorderSide.BORDER_LINE

    if signed_dist > 0:
        # Permitted side
        if abs_dist <= border_section.warning_buffer_distance:
            return BorderSide.WARNING_BUFFER
        return BorderSide.PERMITTED
    else:
        # Restricted side
        return BorderSide.RESTRICTED


def check_crossing(
    previous_side: BorderSide,
    current_side: BorderSide,
) -> CrossingStatus:
    """
    Checks if a side transition constitutes a crossing candidate.

    A crossing candidate is generated when:
    - Previous side was PERMITTED (or WARNING_BUFFER) and current side is RESTRICTED
    - Previous side was RESTRICTED and current side is PERMITTED (or WARNING_BUFFER)

    Single-frame noise and UNKNOWN states do NOT generate crossings.
    """
    if previous_side == BorderSide.UNKNOWN or current_side == BorderSide.UNKNOWN:
        return CrossingStatus.NONE

    if previous_side == current_side:
        return CrossingStatus.NONE

    # Meaningful side transitions
    permitted_sides = {BorderSide.PERMITTED, BorderSide.WARNING_BUFFER}
    restricted_sides = {BorderSide.RESTRICTED}

    if previous_side in permitted_sides and current_side in restricted_sides:
        return CrossingStatus.CROSSING_CANDIDATE

    if previous_side in restricted_sides and current_side in permitted_sides:
        return CrossingStatus.CROSSING_CANDIDATE

    # Transitions within permitted zone (e.g., PERMITTED → WARNING_BUFFER) are not crossings
    return CrossingStatus.NONE


class CrossingConfirmation:
    """
    Stateful crossing confirmation engine for a single camera.

    Transitions CROSSING_CANDIDATE → CONFIRMED_CROSSING after N consecutive frames
    on the new side. Handles jitter/noise by requiring sustained side change.

    If the object returns to its original side before confirmation, the candidate is cancelled.
    """

    def __init__(self, confirmation_frames: int = 3):
        """
        Args:
            confirmation_frames: Number of consecutive frames a track must remain
                                 on the new side to confirm a crossing.
        """
        if confirmation_frames < 1:
            raise ValueError("confirmation_frames must be >= 1")
        self.confirmation_frames = confirmation_frames

        # Per-track state: {track_id: {border_section_id: _TrackCrossingState}}
        self._states: Dict[int, Dict[str, _TrackCrossingState]] = {}

    def update(
        self,
        track_id: int,
        border_section_id: str,
        current_side: BorderSide,
        camera_id: str,
        timestamp_utc: datetime,
        ground_point: Optional[GroundContactPoint] = None,
        calibration_version: Optional[str] = None,
    ) -> Optional[CrossingEvent]:
        """
        Updates crossing state for a track and returns a CrossingEvent if confirmed.

        Returns None if no crossing is detected or if the crossing is still a candidate.
        Returns a CrossingEvent with CONFIRMED_CROSSING status only after sustained frames.
        """
        if track_id not in self._states:
            self._states[track_id] = {}

        section_states = self._states[track_id]

        if border_section_id not in section_states:
            section_states[border_section_id] = _TrackCrossingState(
                last_side=current_side,
                candidate_side=None,
                consecutive_count=0,
                candidate_from_side=None,
            )
            return None

        state = section_states[border_section_id]

        # If we already have an active candidate
        if state.candidate_side is not None:
            if current_side == state.candidate_side:
                state.consecutive_count += 1
                state.last_side = current_side

                if state.consecutive_count >= self.confirmation_frames:
                    event = CrossingEvent(
                        border_section_id=border_section_id,
                        track_id=track_id,
                        camera_id=camera_id,
                        timestamp_utc=timestamp_utc,
                        previous_side=state.candidate_from_side or BorderSide.UNKNOWN,
                        current_side=current_side,
                        crossing_status=CrossingStatus.CONFIRMED_CROSSING,
                        ground_point=ground_point,
                        calibration_version=calibration_version,
                    )
                    # Reset candidate after confirmation
                    state.candidate_side = None
                    state.consecutive_count = 0
                    state.candidate_from_side = None
                    return event
                return None
            elif current_side == BorderSide.BORDER_LINE:
                # Still on the boundary line, keep candidate alive
                state.last_side = current_side
                return None
            else:
                # Returned to original side or changed side -> cancel candidate
                state.candidate_side = None
                state.consecutive_count = 0
                state.candidate_from_side = None

        # Check for new crossing candidate
        crossing = check_crossing(state.last_side, current_side)

        if crossing == CrossingStatus.CROSSING_CANDIDATE:
            state.candidate_side = current_side
            state.candidate_from_side = state.last_side
            state.consecutive_count = 1
            state.last_side = current_side

            if self.confirmation_frames <= 1:
                event = CrossingEvent(
                    border_section_id=border_section_id,
                    track_id=track_id,
                    camera_id=camera_id,
                    timestamp_utc=timestamp_utc,
                    previous_side=state.candidate_from_side or BorderSide.UNKNOWN,
                    current_side=current_side,
                    crossing_status=CrossingStatus.CONFIRMED_CROSSING,
                    ground_point=ground_point,
                    calibration_version=calibration_version,
                )
                state.candidate_side = None
                state.consecutive_count = 0
                state.candidate_from_side = None
                return event
            return None

        state.last_side = current_side
        return None

    def reset(self, track_id: Optional[int] = None) -> None:
        """Resets crossing state for a specific track or all tracks."""
        if track_id is not None:
            self._states.pop(track_id, None)
        else:
            self._states.clear()

    def prune_tracks(self, active_track_ids: set) -> None:
        """Removes state for tracks no longer active."""
        dead = [tid for tid in self._states if tid not in active_track_ids]
        for tid in dead:
            del self._states[tid]


class _TrackCrossingState:
    """Internal mutable state for a single track's crossing progress on a border section."""

    def __init__(
        self,
        last_side: BorderSide,
        candidate_side: Optional[BorderSide],
        consecutive_count: int,
        candidate_from_side: Optional[BorderSide],
    ):
        self.last_side = last_side
        self.candidate_side = candidate_side
        self.consecutive_count = consecutive_count
        self.candidate_from_side = candidate_from_side
