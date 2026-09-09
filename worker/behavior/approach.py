import math
from typing import Optional, List, Tuple
from datetime import datetime
from ..tracking.schemas import TrackState
from ..spatial.schemas import SpatialState, MovementDirection
from .schemas import BehaviorPrimitive, BehaviorType, BehaviorStatus, ReasonCode, BehaviorConfig


class ApproachDetector:
    """
    Evaluates persistent approach and repeated approach temporal patterns.
    """

    def __init__(self, config: BehaviorConfig):
        self.config = config

    def evaluate(
        self,
        track: TrackState,
        spatial: SpatialState,
        approach_start_time: Optional[datetime],
        approach_start_pos: Optional[Tuple[float, float]],
        last_approach_completed_time: Optional[datetime],
        timestamp_utc: datetime,
    ) -> Tuple[Optional[BehaviorPrimitive], Optional[BehaviorPrimitive]]:
        """
        Evaluates active track motion.
        Returns: (persistent_approach_behavior, repeated_approach_behavior)
        """
        if spatial.direction != MovementDirection.TOWARD or approach_start_time is None or approach_start_pos is None:
            return None, None

        duration_sec = (timestamp_utc - approach_start_time).total_seconds()
        if duration_sec < self.config.persistent_approach_seconds:
            return None, None

        # Distance moved during approach
        curr_pos = track.center_xy
        dx = curr_pos[0] - approach_start_pos[0]
        dy = curr_pos[1] - approach_start_pos[1]
        dist_moved = math.hypot(dx, dy)

        if dist_moved < self.config.persistent_approach_min_distance_px:
            return None, None

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

        zone_id = spatial.current_zone_id or (spatial.border_side.value if getattr(spatial, "border_side", None) else None)

        # Persistent approach active
        p_id = f"{spatial.camera_id}_t{track.track_id}_persistent_approach"
        p_supporting = {
            "approach_duration_seconds": round(duration_sec, 2),
            "approach_distance_px": round(dist_moved, 2),
            "speed_pixels_per_sec": round(getattr(track, "speed_pixels_per_sec", 0.0), 2),
            **pose_data,
        }
        if getattr(spatial, "border_distance_m", None) is not None:
            p_supporting["border_distance_m"] = spatial.border_distance_m

        p_behavior = BehaviorPrimitive(
            behavior_id=p_id,
            camera_id=spatial.camera_id,
            track_id=track.track_id,
            behavior_type=BehaviorType.PERSISTENT_APPROACH,
            status=BehaviorStatus.ACTIVE,
            timestamp_utc=timestamp_utc,
            first_observed_utc=approach_start_time,
            last_observed_utc=timestamp_utc,
            duration_seconds=round(duration_sec, 2),
            zone_id=zone_id,
            reason_codes=[ReasonCode.PERSISTENT_TOWARD],
            confidence=conf,
            triggering_condition=f"Persistent movement toward threat vector for {round(duration_sec, 2)}s (distance: {round(dist_moved, 1)}px)",
            supporting_data=p_supporting,
        )

        # Check for repeated approach pattern
        r_behavior = None
        if last_approach_completed_time is not None:
            gap_seconds = (approach_start_time - last_approach_completed_time).total_seconds()
            if 0.0 < gap_seconds <= self.config.repeated_approach_window_sec:
                r_id = f"{spatial.camera_id}_t{track.track_id}_repeated_approach"
                r_supporting = {
                    "interval_since_last_approach_sec": round(gap_seconds, 2),
                    "approach_duration_seconds": round(duration_sec, 2),
                    "speed_pixels_per_sec": round(getattr(track, "speed_pixels_per_sec", 0.0), 2),
                    **pose_data,
                }
                r_behavior = BehaviorPrimitive(
                    behavior_id=r_id,
                    camera_id=spatial.camera_id,
                    track_id=track.track_id,
                    behavior_type=BehaviorType.REPEATED_APPROACH,
                    status=BehaviorStatus.ACTIVE,
                    timestamp_utc=timestamp_utc,
                    first_observed_utc=approach_start_time,
                    last_observed_utc=timestamp_utc,
                    duration_seconds=round(duration_sec, 2),
                    zone_id=zone_id,
                    reason_codes=[ReasonCode.REPEATED_APPROACH, ReasonCode.PERSISTENT_TOWARD],
                    confidence=conf,
                    triggering_condition=f"Repeated approach within {round(gap_seconds, 1)}s window (duration: {round(duration_sec, 2)}s)",
                    supporting_data=r_supporting,
                )

        return p_behavior, r_behavior
