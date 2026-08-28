import math
from typing import Optional, List, Tuple
from datetime import datetime
from ..tracking.schemas import TrackState
from ..spatial.schemas import SpatialState, ZoneType
from .schemas import BehaviorPrimitive, BehaviorType, BehaviorStatus, ReasonCode, BehaviorConfig


class LoiteringDetector:
    """
    Evaluates loitering behavior based on zone dwell time and low spatial displacement.
    """

    def __init__(self, config: BehaviorConfig):
        self.config = config

    def evaluate(
        self,
        track: TrackState,
        spatial: SpatialState,
        zone_entry_time: Optional[datetime],
        first_position_in_zone: Optional[Tuple[float, float]],
        timestamp_utc: datetime,
    ) -> Optional[BehaviorPrimitive]:
        # Track must be currently inside a zone (RESTRICTED, BUFFER, or CRITICAL)
        if spatial.current_zone_id is None or zone_entry_time is None or first_position_in_zone is None:
            return None

        # Dwell duration inside the zone
        dwell_seconds = (timestamp_utc - zone_entry_time).total_seconds()
        if dwell_seconds < self.config.loitering_seconds:
            return None

        # Calculate displacement from the point where the track entered the zone
        curr_pos = track.center_xy
        dx = curr_pos[0] - first_position_in_zone[0]
        dy = curr_pos[1] - first_position_in_zone[1]
        displacement = math.hypot(dx, dy)

        if displacement > self.config.loitering_max_displacement_px:
            return None

        # Loitering criteria satisfied
        behavior_id = f"{spatial.camera_id}_t{track.track_id}_loitering_{spatial.current_zone_id}"
        return BehaviorPrimitive(
            behavior_id=behavior_id,
            camera_id=spatial.camera_id,
            track_id=track.track_id,
            behavior_type=BehaviorType.LOITERING,
            status=BehaviorStatus.ACTIVE,
            timestamp_utc=timestamp_utc,
            first_observed_utc=zone_entry_time,
            last_observed_utc=timestamp_utc,
            duration_seconds=round(dwell_seconds, 2),
            zone_id=spatial.current_zone_id,
            reason_codes=[ReasonCode.DWELL_TIME_EXCEEDED, ReasonCode.LOW_DISPLACEMENT],
            supporting_data={
                "displacement_px": round(displacement, 2),
                "max_allowed_displacement_px": self.config.loitering_max_displacement_px,
                "zone_dwell_seconds": round(dwell_seconds, 2),
            },
        )
