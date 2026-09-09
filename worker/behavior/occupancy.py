from typing import Optional, List
from datetime import datetime
from ..tracking.schemas import TrackState
from ..spatial.schemas import SpatialState, ZoneType, CrossingStatus, BorderSide
from .schemas import BehaviorPrimitive, BehaviorType, BehaviorStatus, ReasonCode, BehaviorConfig


class OccupancyDetector:
    """
    Evaluates restricted-zone occupancy behavior.
    Emits a single sustained active behavior with increasing duration instead of duplicate events per frame.
    """

    def __init__(self, config: BehaviorConfig):
        self.config = config

    def evaluate(
        self,
        track: TrackState,
        spatial: SpatialState,
        zone_entry_time: Optional[datetime],
        timestamp_utc: datetime,
    ) -> Optional[BehaviorPrimitive]:
        # Resolve zone and restriction status
        is_restricted = (
            spatial.current_zone_type in (ZoneType.RESTRICTED, ZoneType.CRITICAL)
            or (getattr(spatial, "border_side", None) == BorderSide.RESTRICTED)
        )
        zone_id = spatial.current_zone_id or (
            spatial.border_side.value if getattr(spatial, "border_side", None) == BorderSide.RESTRICTED else None
        )

        if zone_id is None or zone_entry_time is None or not is_restricted:
            return None

        duration_sec = (timestamp_utc - zone_entry_time).total_seconds()
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
            "zone_type": spatial.current_zone_type.value if spatial.current_zone_type else "restricted",
            "occupancy_duration_sec": round(duration_sec, 2),
            "speed_pixels_per_sec": round(getattr(track, "speed_pixels_per_sec", 0.0), 2),
            **pose_data,
        }
        if getattr(spatial, "border_distance_m", None) is not None:
            supporting["border_distance_m"] = spatial.border_distance_m

        behavior_id = f"{spatial.camera_id}_t{track.track_id}_restricted_occupancy_{zone_id}"

        return BehaviorPrimitive(
            behavior_id=behavior_id,
            camera_id=spatial.camera_id,
            track_id=track.track_id,
            behavior_type=BehaviorType.RESTRICTED_OCCUPANCY,
            status=BehaviorStatus.ACTIVE,
            timestamp_utc=timestamp_utc,
            first_observed_utc=zone_entry_time,
            last_observed_utc=timestamp_utc,
            duration_seconds=round(duration_sec, 2),
            zone_id=zone_id,
            reason_codes=[ReasonCode.RESTRICTED_OCCUPANCY],
            confidence=conf,
            triggering_condition=f"Unauthorized presence detected in restricted zone '{zone_id}' (dwell duration: {round(duration_sec, 2)}s)",
            supporting_data=supporting,
        )


class FenceBreachDetector:
    """
    Converts geometric virtual fence crossings and calibrated world-border crossings
    into explainable FENCE_BREACH / BORDER_CROSSING behavior primitives.
    """

    def __init__(self, config: BehaviorConfig):
        self.config = config

    def evaluate(
        self,
        track: TrackState,
        spatial: SpatialState,
        timestamp_utc: datetime,
    ) -> List[BehaviorPrimitive]:
        primitives: List[BehaviorPrimitive] = []

        conf = round(track.confidence_history[-1], 2) if getattr(track, "confidence_history", None) and len(track.confidence_history) > 0 else 0.90
        pose_data = {}
        if getattr(track, "keypoints", None) is not None:
            pose_data["has_pose"] = True
            pose_data["pose_keypoints_count"] = len(track.keypoints)
            if getattr(track, "keypoint_scores", None) and len(track.keypoint_scores) > 0:
                pose_data["pose_mean_confidence"] = round(float(sum(track.keypoint_scores) / len(track.keypoint_scores)), 2)
        else:
            pose_data["has_pose"] = False

        # 1. Evaluate legacy virtual fence crossing events
        if spatial.crossing_events:
            for ev in spatial.crossing_events:
                b_id = f"{spatial.camera_id}_t{track.track_id}_fence_breach_{ev.fence_id}_{int(timestamp_utc.timestamp())}"
                supporting = {
                    "fence_id": ev.fence_id,
                    "crossing_direction": ev.crossing_direction.value,
                    "crossing_point": ev.crossing_point,
                    "speed_pixels_per_sec": round(getattr(track, "speed_pixels_per_sec", 0.0), 2),
                    **pose_data,
                }
                if getattr(spatial, "border_distance_m", None) is not None:
                    supporting["border_distance_m"] = spatial.border_distance_m

                primitive = BehaviorPrimitive(
                    behavior_id=b_id,
                    camera_id=spatial.camera_id,
                    track_id=track.track_id,
                    behavior_type=BehaviorType.FENCE_BREACH,
                    status=BehaviorStatus.ACTIVE,
                    timestamp_utc=timestamp_utc,
                    first_observed_utc=ev.timestamp_utc,
                    last_observed_utc=timestamp_utc,
                    duration_seconds=0.0,
                    fence_id=ev.fence_id,
                    reason_codes=[ReasonCode.FENCE_CROSSED],
                    confidence=conf,
                    triggering_condition=f"Confirmed crossing across virtual fence '{ev.fence_id}' in direction {ev.crossing_direction.value}",
                    supporting_data=supporting,
                )
                primitives.append(primitive)

        # 2. Evaluate calibrated world border crossings
        if getattr(spatial, "crossing_status", None) == CrossingStatus.CONFIRMED_CROSSING:
            b_id = f"{spatial.camera_id}_t{track.track_id}_border_crossing_{int(timestamp_utc.timestamp())}"
            border_supporting = {
                "border_side": spatial.border_side.value if spatial.border_side else "restricted",
                "speed_pixels_per_sec": round(getattr(track, "speed_pixels_per_sec", 0.0), 2),
                **pose_data,
            }
            if getattr(spatial, "border_distance_m", None) is not None:
                border_supporting["border_distance_m"] = spatial.border_distance_m

            primitive = BehaviorPrimitive(
                behavior_id=b_id,
                camera_id=spatial.camera_id,
                track_id=track.track_id,
                behavior_type=BehaviorType.BORDER_CROSSING,
                status=BehaviorStatus.ACTIVE,
                timestamp_utc=timestamp_utc,
                first_observed_utc=timestamp_utc,
                last_observed_utc=timestamp_utc,
                duration_seconds=0.0,
                zone_id=spatial.border_side.value if spatial.border_side else "restricted",
                reason_codes=[ReasonCode.BORDER_CROSSED],
                confidence=conf,
                triggering_condition="Confirmed border crossing into restricted sector across virtual international boundary",
                supporting_data=border_supporting,
            )
            primitives.append(primitive)

        return primitives

