"""
Speed Anomaly Detector for IBVAP Behaviour Intelligence.

Deterministic, explainable rule:
Triggers when an active tracked target's estimated speed exceeds the configured
contextual threshold (e.g., rapid movement toward border/geofence).
"""

from typing import Optional, Dict, Any
from datetime import datetime

from ..tracking.schemas import TrackState
from ..spatial.schemas import SpatialState, MovementDirection
from .schemas import (
    BehaviorPrimitive,
    BehaviorType,
    BehaviorStatus,
    ReasonCode,
    BehaviorConfig,
)


class SpeedAnomalyDetector:
    """
    Evaluates whether a target's speed exceeds configured contextual safety thresholds.
    """

    def __init__(self, config: BehaviorConfig):
        self.config = config

    def evaluate(
        self,
        track: TrackState,
        spatial: Optional[SpatialState],
        timestamp_utc: datetime,
    ) -> Optional[BehaviorPrimitive]:
        """
        Evaluates track speed against contextual thresholds.
        """
        if not getattr(self.config, "enable_speed_anomaly", True):
            return None

        speed = float(getattr(track, "speed_pixels_per_sec", 0.0))
        threshold = float(getattr(self.config, "speed_anomaly_threshold_px_per_sec", 60.0))

        if speed <= threshold:
            return None

        # Contextual verification: check zone and direction
        direction_str = "UNCERTAIN"
        zone_id = None
        if spatial:
            if spatial.direction:
                direction_str = spatial.direction.value.upper()
            if spatial.current_zone_id:
                zone_id = spatial.current_zone_id
            elif spatial.border_side:
                zone_id = spatial.border_side.value.upper()
        elif track.current_zone_id:
            zone_id = track.current_zone_id

        conf = track.confidence_history[-1] if track.confidence_history else 0.90

        # Optional pose summary if present
        pose_data: Dict[str, Any] = {"has_pose": False}
        if getattr(track, "keypoints", None) is not None:
            pose_data["has_pose"] = True
            pose_data["pose_keypoints_count"] = getattr(track.keypoints, "num_keypoints", 17)
            pose_data["pose_confidence"] = getattr(track.keypoints, "confidence", 1.0)

        trigger_msg = (
            f"Observed speed {speed:.1f} px/s exceeded contextual threshold {threshold:.1f} px/s "
            f"(Direction: {direction_str}, Target: {track.class_id.value.upper()})"
        )

        b_id = f"{track.camera_id}_t{track.track_id}_speed_anomaly"

        return BehaviorPrimitive(
            behavior_id=b_id,
            camera_id=track.camera_id,
            track_id=track.track_id,
            behavior_type=BehaviorType.SPEED_ANOMALY,
            status=BehaviorStatus.ACTIVE,
            timestamp_utc=timestamp_utc,
            first_observed_utc=timestamp_utc,
            last_observed_utc=timestamp_utc,
            duration_seconds=0.0,
            zone_id=zone_id,
            confidence=round(conf, 2),
            triggering_condition=trigger_msg,
            reason_codes=[ReasonCode.SPEED_THRESHOLD_EXCEEDED],
            supporting_data={
                "observed_speed_px_per_sec": round(speed, 2),
                "threshold_px_per_sec": round(threshold, 2),
                "velocity_xy": track.velocity_xy,
                "direction": direction_str,
                "target_class": track.class_id.value,
                **pose_data,
            },
        )
