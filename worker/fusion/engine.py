"""
Production Multi-Modal Evidence Fusion Engine for IBVAP.

Fuses Tracking, World-Border Spatial Intelligence, Environmental Context,
and Behavioral Analytics into prioritized, explainable, deduplicated EventRecords.

Architecture Decision: DEC-0007
"""

import uuid
import logging
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timezone, timedelta

from .base import FusionEngineInterface
from .schemas import (
    EventRecord,
    EventType,
    EventStatus,
    FusionReasonCode,
    FusionConfig,
    EvidenceReference,
)
from .evidence import EvidenceExtractor, EvidenceItem
from .scoring import (
    calculate_risk_score,
    map_score_to_priority,
    determine_primary_event_type,
    generate_factual_summary,
)
from .exceptions import InvalidFusionConfigError
from ..tracking.schemas import TrackState
from ..spatial.schemas import SpatialState, SpatialConfidence
from ..environment.schemas import EnvironmentState
from ..behavior.schemas import BehaviorPrimitive
from backend.app.schemas.common import EventPriority, TargetClass, VisibilityQuality, LightingCondition

logger = logging.getLogger(__name__)


class FusionEngine(FusionEngineInterface):
    """
    Production Multi-Modal Evidence Fusion Engine.

    Guarantees:
    1. Deterministic, rule-based mathematical scoring [0, 100].
    2. Event deduplication across sustained frames (single EventRecord with evolving duration).
    3. Multi-frame cooldown to prevent alert storms.
    4. Safe handling of invalid camera calibration and environmental uncertainty.
    5. Pure factual human-readable explanations without hallucination.
    """

    def __init__(self, default_config: Optional[FusionConfig] = None):
        self._default_config = default_config or FusionConfig()
        self._camera_configs: Dict[str, FusionConfig] = {}
        # Active events map: {camera_id: {track_id: EventRecord}}
        self._active_events: Dict[str, Dict[int, EventRecord]] = {}
        # Cooldown map: {camera_id: {f"{track_id}_{event_type}": last_resolved_utc}}
        self._cooldowns: Dict[str, Dict[str, datetime]] = {}
        # Historical / resolved events cache (bounded)
        self._historical_events: Dict[str, List[EventRecord]] = {}

    def configure(self, camera_id: str, config: FusionConfig) -> None:
        """Registers custom weights and operational thresholds for a camera."""
        if not camera_id:
            raise InvalidFusionConfigError("Camera ID must be a non-empty string.")

        # Validate weights sum
        weight_sum = config.weight_class + config.weight_spatial + config.weight_behavior + config.weight_environment
        if not (0.7 <= weight_sum <= 1.3):
            raise InvalidFusionConfigError(f"Component weights must sum close to 1.0 (got {weight_sum:.3f})")

        self._camera_configs[camera_id] = config
        if camera_id not in self._active_events:
            self._active_events[camera_id] = {}
        if camera_id not in self._cooldowns:
            self._cooldowns[camera_id] = {}
        if camera_id not in self._historical_events:
            self._historical_events[camera_id] = []

        logger.info(f"FusionEngine configured for camera '{camera_id}' with threshold_high={config.threshold_high_max}.")

    def _get_or_init_camera(self, camera_id: str) -> Tuple[FusionConfig, Dict[int, EventRecord], Dict[str, datetime], List[EventRecord]]:
        if camera_id not in self._camera_configs:
            self.configure(camera_id, self._default_config)
        return (
            self._camera_configs[camera_id],
            self._active_events[camera_id],
            self._cooldowns[camera_id],
            self._historical_events[camera_id],
        )

    def process(
        self,
        tracks: List[TrackState],
        spatial_states: List[SpatialState],
        environment_state: Optional[EnvironmentState],
        behavior_primitives: List[BehaviorPrimitive],
        camera_id: str,
        timestamp_utc: datetime,
    ) -> List[EventRecord]:
        """
        Processes active multi-modal observations and produces or updates EventRecord instances.
        """
        config, active_map, cooldown_map, history_list = self._get_or_init_camera(camera_id)

        # Index spatial states and behaviors by track_id
        spatial_map: Dict[int, SpatialState] = {st.track_id: st for st in spatial_states}
        behavior_map: Dict[int, List[BehaviorPrimitive]] = {}
        for b in behavior_primitives:
            behavior_map.setdefault(b.track_id, []).append(b)

        current_frame_events: List[EventRecord] = []
        active_track_ids = set()

        # Environmental context summary
        env_summary = "Daytime clear visibility"
        env_vis = VisibilityQuality.GOOD
        env_light = LightingCondition.DAY
        if environment_state:
            env_vis = environment_state.visibility
            env_light = environment_state.lighting
            env_summary = f"{environment_state.lighting.value.capitalize()}, {environment_state.visibility.value} visibility (quality={environment_state.quality_score:.2f})"

        for track in tracks:
            t_id = track.track_id
            active_track_ids.add(t_id)
            spatial = spatial_map.get(t_id)
            behaviors = behavior_map.get(t_id, [])

            # 1. Extract Normalized Evidence Items
            evidence_items = EvidenceExtractor.extract_evidence(
                track=track,
                spatial=spatial,
                environment=environment_state,
                behaviors=behaviors,
                camera_id=camera_id,
                timestamp_utc=timestamp_utc,
            )

            # 2. Compute Deterministic Risk Priority Score
            score, reason_codes, uncertainty_flags = calculate_risk_score(evidence_items, config)
            priority = map_score_to_priority(score, config)
            event_type = determine_primary_event_type(evidence_items)

            # Build EvidenceReferences
            evidence_refs = [
                EvidenceReference(
                    evidence_type=ev.evidence_type.value,
                    source_module=ev.source_module,
                    timestamp_utc=ev.timestamp_utc,
                    confidence=ev.confidence,
                    reason_code=ev.reason_code.value,
                    details=ev.metadata,
                )
                for ev in evidence_items
            ]

            # 3. Determine if Event Warranted
            # An event is active if score > threshold_info_max or has non-trivial spatial/behavior evidence
            is_actionable = (score > config.threshold_info_max) or (event_type != EventType.OBJECT_OBSERVED)

            if is_actionable:
                if t_id in active_map:
                    # -------------------------------------------------------------
                    # DEDUPLICATION: Update Existing Active EventRecord
                    # -------------------------------------------------------------
                    existing_ev = active_map[t_id]
                    existing_ev.updated_at = timestamp_utc
                    existing_ev.last_observed_utc = timestamp_utc
                    existing_ev.duration_seconds = max(0.0, (timestamp_utc - existing_ev.first_observed_utc).total_seconds())
                    existing_ev.risk_score = score
                    existing_ev.priority = priority
                    existing_ev.event_type = event_type
                    existing_ev.reason_codes = reason_codes
                    existing_ev.evidence_references = evidence_refs
                    existing_ev.uncertainty_flags = uncertainty_flags
                    existing_ev.track_persistence_frames = len(track.trajectory)
                    existing_ev.explanation_summary = generate_factual_summary(
                        event_type=event_type,
                        target_class=track.class_id,
                        priority=priority,
                        score=score,
                        reason_codes=reason_codes,
                        uncertainty_flags=uncertainty_flags,
                        environment_summary=env_summary,
                    )
                    current_frame_events.append(existing_ev)
                else:
                    # -------------------------------------------------------------
                    # Check Cooldown Before Creating New Event
                    # -------------------------------------------------------------
                    cooldown_key = f"{t_id}_{event_type.value}"
                    last_resolved = cooldown_map.get(cooldown_key)
                    in_cooldown = False
                    if last_resolved:
                        if (timestamp_utc - last_resolved).total_seconds() < config.event_cooldown_seconds:
                            in_cooldown = True

                    if not in_cooldown:
                        new_ev = EventRecord(
                            id=f"evt_{uuid.uuid4().hex[:12]}",
                            camera_id=camera_id,
                            track_id=t_id,
                            event_type=event_type,
                            priority=priority,
                            risk_score=score,
                            status=EventStatus.ACTIVE,
                            target_class=track.class_id,
                            created_at=timestamp_utc,
                            updated_at=timestamp_utc,
                            first_observed_utc=timestamp_utc,
                            last_observed_utc=timestamp_utc,
                            duration_seconds=0.0,
                            detection_confidence=track.confidence_history[-1] if track.confidence_history else 0.80,
                            track_persistence_frames=len(track.trajectory),
                            zone_id=spatial.current_zone_id if spatial else None,
                            border_section_id=spatial.metadata.get("border_section_id") if spatial else None,
                            environment_quality=env_vis,
                            lighting=env_light,
                            reason_codes=reason_codes,
                            evidence_references=evidence_refs,
                            uncertainty_flags=uncertainty_flags,
                            explanation_summary=generate_factual_summary(
                                event_type=event_type,
                                target_class=track.class_id,
                                priority=priority,
                                score=score,
                                reason_codes=reason_codes,
                                uncertainty_flags=uncertainty_flags,
                                environment_summary=env_summary,
                            ),
                        )
                        active_map[t_id] = new_ev
                        current_frame_events.append(new_ev)
            else:
                # Score dropped below threshold: Resolve existing event if present
                if t_id in active_map:
                    resolved_ev = active_map.pop(t_id)
                    resolved_ev.status = EventStatus.RESOLVED
                    resolved_ev.last_observed_utc = timestamp_utc
                    cooldown_map[f"{t_id}_{resolved_ev.event_type.value}"] = timestamp_utc
                    history_list.append(resolved_ev)

        # -------------------------------------------------------------
        # 4. Prune / Resolve Disappeared Tracks
        # -------------------------------------------------------------
        dead_ids = [tid for tid in active_map if tid not in active_track_ids]
        for tid in dead_ids:
            resolved_ev = active_map.pop(tid)
            resolved_ev.status = EventStatus.RESOLVED
            resolved_ev.last_observed_utc = timestamp_utc
            cooldown_map[f"{tid}_{resolved_ev.event_type.value}"] = timestamp_utc
            history_list.append(resolved_ev)

        # Trim bounded history cache
        if len(history_list) > 200:
            del history_list[:len(history_list) - 200]

        return current_frame_events

    def get_active_events(self, camera_id: Optional[str] = None) -> List[EventRecord]:
        """Returns all currently active EventRecords for a camera (or all cameras)."""
        if camera_id:
            return list(self._active_events.get(camera_id, {}).values())
        all_active = []
        for cam_map in self._active_events.values():
            all_active.extend(cam_map.values())
        return all_active

    def acknowledge_event(self, event_id: str, acknowledged_by: str, timestamp_utc: datetime) -> bool:
        """Marks an active or historical event as acknowledged by an operator."""
        for cam_map in self._active_events.values():
            for ev in cam_map.values():
                if ev.id == event_id:
                    ev.is_acknowledged = True
                    ev.acknowledged_by = acknowledged_by
                    ev.acknowledged_at = timestamp_utc
                    return True

        for history in self._historical_events.values():
            for ev in history:
                if ev.id == event_id:
                    ev.is_acknowledged = True
                    ev.acknowledged_by = acknowledged_by
                    ev.acknowledged_at = timestamp_utc
                    return True

        return False

    def reset(self, camera_id: Optional[str] = None) -> None:
        """Resets active events and history for a camera (or all cameras)."""
        if camera_id:
            if camera_id in self._active_events:
                self._active_events[camera_id].clear()
            if camera_id in self._cooldowns:
                self._cooldowns[camera_id].clear()
            if camera_id in self._historical_events:
                self._historical_events[camera_id].clear()
        else:
            for c_map in self._active_events.values():
                c_map.clear()
            self._active_events.clear()
            for cd_map in self._cooldowns.values():
                cd_map.clear()
            self._cooldowns.clear()
            for h_list in self._historical_events.values():
                h_list.clear()
            self._historical_events.clear()

        logger.info(f"FusionEngine reset for camera: {camera_id or 'ALL'}")

    def close(self) -> None:
        self.reset()
