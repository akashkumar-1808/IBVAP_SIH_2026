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
        # Zone resolution
        zone_id = spatial.current_zone_id or (spatial.border_side.value if getattr(spatial, "border_side", None) and spatial.border_side.value in ("warning_buffer", "restricted") else None)

        # Track must be currently inside a zone (RESTRICTED, BUFFER, or CRITICAL)
        if zone_id is None or zone_entry_time is None or first_position_in_zone is None:
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

        # Track confidence and pose telemetry
        conf = round(track.confidence_history[-1], 2) if getattr(track, "confidence_history", None) and len(track.confidence_history) > 0 else 0.90
        pose_data = {}
        if getattr(track, "keypoints", None) is not None:
            pose_data["has_pose"] = True
            pose_data["pose_keypoints_count"] = len(track.keypoints)
            if getattr(track, "keypoint_scores", None) and len(track.keypoint_scores) > 0:
                pose_data["pose_mean_confidence"] = round(float(sum(track.keypoint_scores) / len(track.keypoint_scores)), 2)
        else:
            pose_data["has_pose"] = False

        supporting = {
            "displacement_px": round(displacement, 2),
            "max_allowed_displacement_px": self.config.loitering_max_displacement_px,
            "zone_dwell_seconds": round(dwell_seconds, 2),
            "speed_pixels_per_sec": round(getattr(track, "speed_pixels_per_sec", 0.0), 2),
            **pose_data,
        }
        if getattr(spatial, "border_distance_m", None) is not None:
            supporting["border_distance_m"] = spatial.border_distance_m

        # Loitering criteria satisfied
        behavior_id = f"{spatial.camera_id}_t{track.track_id}_loitering_{zone_id}"
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
            zone_id=zone_id,
            reason_codes=[ReasonCode.DWELL_TIME_EXCEEDED, ReasonCode.LOW_DISPLACEMENT],
            confidence=conf,
            triggering_condition=f"Dwell time {round(dwell_seconds, 2)}s in zone '{zone_id}' exceeded threshold {self.config.loitering_seconds}s (displacement: {round(displacement, 1)}px <= {self.config.loitering_max_displacement_px}px)",
            supporting_data=supporting,
        )

