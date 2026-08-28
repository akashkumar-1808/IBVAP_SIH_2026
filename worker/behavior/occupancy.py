from typing import Optional, List
from datetime import datetime
from ..tracking.schemas import TrackState
from ..spatial.schemas import SpatialState, ZoneType
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
        if spatial.current_zone_id is None or zone_entry_time is None:
            return None

        # Check if zone is RESTRICTED or CRITICAL
        if spatial.current_zone_type not in (ZoneType.RESTRICTED, ZoneType.CRITICAL):
            return None

        duration_sec = (timestamp_utc - zone_entry_time).total_seconds()
        behavior_id = f"{spatial.camera_id}_t{track.track_id}_restricted_occupancy_{spatial.current_zone_id}"

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
            zone_id=spatial.current_zone_id,
            reason_codes=[ReasonCode.RESTRICTED_OCCUPANCY],
            supporting_data={
                "zone_type": spatial.current_zone_type.value if spatial.current_zone_type else "restricted",
                "occupancy_duration_sec": round(duration_sec, 2),
            },
        )


class FenceBreachDetector:
    """
    Converts geometric virtual fence crossings into explainable FENCE_BREACH behavior primitives.
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

        if not spatial.crossing_events:
            return primitives

        for ev in spatial.crossing_events:
            b_id = f"{spatial.camera_id}_t{track.track_id}_fence_breach_{ev.fence_id}_{int(timestamp_utc.timestamp())}"
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
                supporting_data={
                    "fence_id": ev.fence_id,
                    "crossing_direction": ev.crossing_direction.value,
                    "crossing_point": ev.crossing_point,
                },
            )
            primitives.append(primitive)

        return primitives
