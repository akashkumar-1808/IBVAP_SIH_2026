"""
Normalized Evidence Representation and Extraction for IBVAP Fusion Engine.

Extracts structured, traceable evidence items from multi-layer upstream observations:
- Phase 4 Tracking (Track persistence, kinematics)
- Phase 5 Environment (Visibility, lighting, image degradation)
- Phase 6 / Pre-Phase 8 World Border & Spatial Intelligence (Side, crossing, buffer)
- Phase 7 Behavioral Analytics (Loitering, approach, occupancy, breach)

Architecture Decision: DEC-0007
"""

from enum import Enum
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from backend.app.schemas.common import TargetClass, VisibilityQuality, LightingCondition, ZoneType
from ..tracking.schemas import TrackState, TrackStatus
from ..environment.schemas import EnvironmentState
from ..spatial.schemas import SpatialState, MovementDirection, BorderSide, CrossingStatus, SpatialConfidence
from ..behavior.schemas import BehaviorPrimitive, BehaviorType
from .schemas import FusionReasonCode


class EvidenceType(str, Enum):
    """Categorical classification of fused evidence."""
    OBJECT_CLASS = "object_class"
    TRACK_PERSISTENCE = "track_persistence"
    MOVEMENT_DIRECTION = "movement_direction"
    ZONE_MEMBERSHIP = "zone_membership"
    BORDER_SIDE = "border_side"
    BORDER_CROSSING = "border_crossing"
    BEHAVIOR_PRIMITIVE = "behavior_primitive"
    ENVIRONMENT_QUALITY = "environment_quality"
    CALIBRATION_CONFIDENCE = "calibration_confidence"
    OPTIONAL_INTELLIGENCE = "optional_intelligence"
    CROSS_CAMERA_ASSOCIATION = "cross_camera_association"
    SECTOR_NORMALITY = "sector_normality"
    EVIDENCE_REQUEST_STATUS = "evidence_request_status"


class EvidenceItem(BaseModel):
    """Normalized atomic evidence unit with provenance and reason code."""
    evidence_type: EvidenceType
    source_module: str
    value: Any
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    weight: float = Field(default=1.0, ge=0.0, le=2.0)
    reason_code: FusionReasonCode
    timestamp_utc: datetime
    track_id: Optional[int] = None
    camera_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceExtractor:
    """Extracts and normalizes multi-modal evidence items for an individual track."""

    @staticmethod
    def extract_evidence(
        track: TrackState,
        spatial: Optional[SpatialState],
        environment: Optional[EnvironmentState],
        behaviors: List[BehaviorPrimitive],
        camera_id: str,
        timestamp_utc: datetime,
        border_track: Optional[Any] = None,
        sector_context: Optional[Any] = None,
        evidence_requests: Optional[List[Any]] = None,
    ) -> List[EvidenceItem]:
        evidence_list: List[EvidenceItem] = []

        # -------------------------------------------------------------
        # 1. Object Class Evidence
        # -------------------------------------------------------------
        latest_conf = track.confidence_history[-1] if track.confidence_history else 0.80
        if track.class_id == TargetClass.PERSON:
            evidence_list.append(EvidenceItem(
                evidence_type=EvidenceType.OBJECT_CLASS,
                source_module="perception",
                value=track.class_id.value,
                confidence=latest_conf,
                reason_code=FusionReasonCode.PERSON_DETECTED,
                timestamp_utc=timestamp_utc,
                track_id=track.track_id,
                camera_id=camera_id,
            ))
        elif track.class_id == TargetClass.VEHICLE:
            evidence_list.append(EvidenceItem(
                evidence_type=EvidenceType.OBJECT_CLASS,
                source_module="perception",
                value=track.class_id.value,
                confidence=latest_conf,
                reason_code=FusionReasonCode.VEHICLE_DETECTED,
                timestamp_utc=timestamp_utc,
                track_id=track.track_id,
                camera_id=camera_id,
            ))
        elif track.class_id == TargetClass.ANIMAL:
            evidence_list.append(EvidenceItem(
                evidence_type=EvidenceType.OBJECT_CLASS,
                source_module="perception",
                value=track.class_id.value,
                confidence=latest_conf,
                reason_code=FusionReasonCode.ANIMAL_DETECTED,
                timestamp_utc=timestamp_utc,
                track_id=track.track_id,
                camera_id=camera_id,
            ))
        else:
            evidence_list.append(EvidenceItem(
                evidence_type=EvidenceType.OBJECT_CLASS,
                source_module="perception",
                value="unknown",
                confidence=latest_conf,
                reason_code=FusionReasonCode.UNKNOWN_OBJECT_DETECTED,
                timestamp_utc=timestamp_utc,
                track_id=track.track_id,
                camera_id=camera_id,
            ))

        # -------------------------------------------------------------
        # 2. Track Persistence & Kinematics Evidence
        # -------------------------------------------------------------
        persistence_frames = len(track.trajectory)
        if persistence_frames >= 3:
            evidence_list.append(EvidenceItem(
                evidence_type=EvidenceType.TRACK_PERSISTENCE,
                source_module="tracking",
                value=persistence_frames,
                confidence=min(1.0, persistence_frames / 10.0),
                reason_code=FusionReasonCode.PERSISTENT_TRACK,
                timestamp_utc=timestamp_utc,
                track_id=track.track_id,
                camera_id=camera_id,
                metadata={"age_frames": track.age_frames, "speed": track.speed_pixels_per_sec},
            ))
        else:
            evidence_list.append(EvidenceItem(
                evidence_type=EvidenceType.TRACK_PERSISTENCE,
                source_module="tracking",
                value=persistence_frames,
                confidence=0.4,
                reason_code=FusionReasonCode.SHORT_LIVED_TRACK,
                timestamp_utc=timestamp_utc,
                track_id=track.track_id,
                camera_id=camera_id,
            ))

        # -------------------------------------------------------------
        # 3. Spatial & World Border Evidence
        # -------------------------------------------------------------
        if spatial:
            # Direction
            if spatial.direction == MovementDirection.TOWARD:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.MOVEMENT_DIRECTION,
                    source_module="spatial",
                    value=spatial.direction.value,
                    confidence=0.85,
                    reason_code=FusionReasonCode.TOWARD_PROTECTED_REGION,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                ))

            # World Border Side & Crossing
            if spatial.border_side == BorderSide.RESTRICTED:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.BORDER_SIDE,
                    source_module="spatial",
                    value=spatial.border_side.value,
                    confidence=0.95 if spatial.spatial_confidence == SpatialConfidence.VALID else 0.4,
                    reason_code=FusionReasonCode.RESTRICTED_ZONE_ENTRY,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                ))
            elif spatial.border_side == BorderSide.WARNING_BUFFER:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.BORDER_SIDE,
                    source_module="spatial",
                    value=spatial.border_side.value,
                    confidence=0.90 if spatial.spatial_confidence == SpatialConfidence.VALID else 0.4,
                    reason_code=FusionReasonCode.WARNING_BUFFER_ENTRY,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                ))
            elif spatial.border_side == BorderSide.BORDER_LINE:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.BORDER_SIDE,
                    source_module="spatial",
                    value=spatial.border_side.value,
                    confidence=0.90,
                    reason_code=FusionReasonCode.BORDER_LINE_CONTACT,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                ))
            elif spatial.border_side == BorderSide.PERMITTED:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.BORDER_SIDE,
                    source_module="spatial",
                    value=spatial.border_side.value,
                    confidence=1.0,
                    reason_code=FusionReasonCode.SAFE_ZONE_ONLY,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                ))

            # Confirmed border crossing
            if spatial.crossing_status == CrossingStatus.CONFIRMED_CROSSING:
                if spatial.spatial_confidence != SpatialConfidence.INVALID:
                    evidence_list.append(EvidenceItem(
                        evidence_type=EvidenceType.BORDER_CROSSING,
                        source_module="spatial",
                        value=spatial.crossing_status.value,
                        confidence=0.98 if spatial.spatial_confidence == SpatialConfidence.VALID else 0.5,
                        reason_code=FusionReasonCode.BORDER_CROSSED,
                        timestamp_utc=timestamp_utc,
                        track_id=track.track_id,
                        camera_id=camera_id,
                    ))

            # Legacy Zone Membership (if active)
            if spatial.current_zone_type == ZoneType.CRITICAL:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.ZONE_MEMBERSHIP,
                    source_module="spatial",
                    value=ZoneType.CRITICAL.value,
                    confidence=0.95,
                    reason_code=FusionReasonCode.CRITICAL_ZONE_ENTRY,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                ))
            elif spatial.current_zone_type == ZoneType.RESTRICTED:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.ZONE_MEMBERSHIP,
                    source_module="spatial",
                    value=ZoneType.RESTRICTED.value,
                    confidence=0.90,
                    reason_code=FusionReasonCode.RESTRICTED_ZONE_ENTRY,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                ))

            # Spatial Calibration Uncertainty Flag
            if spatial.spatial_confidence in (SpatialConfidence.INVALID, SpatialConfidence.UNCERTAIN):
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.CALIBRATION_CONFIDENCE,
                    source_module="spatial",
                    value=spatial.spatial_confidence.value,
                    confidence=0.2,
                    reason_code=FusionReasonCode.SPATIAL_CALIBRATION_INVALID,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                ))

        # -------------------------------------------------------------
        # 4. Temporal Behavior Evidence
        # -------------------------------------------------------------
        for b in behaviors:
            if b.track_id != track.track_id:
                continue

            if b.behavior_type == BehaviorType.FENCE_BREACH:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.BEHAVIOR_PRIMITIVE,
                    source_module="behavior",
                    value=b.behavior_type.value,
                    confidence=0.98,
                    reason_code=FusionReasonCode.FENCE_BREACH_DETECTED,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                    metadata={"duration": b.duration_seconds},
                ))
            elif b.behavior_type == BehaviorType.RESTRICTED_OCCUPANCY:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.BEHAVIOR_PRIMITIVE,
                    source_module="behavior",
                    value=b.behavior_type.value,
                    confidence=0.90,
                    reason_code=FusionReasonCode.RESTRICTED_OCCUPANCY,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                    metadata={"duration": b.duration_seconds},
                ))
            elif b.behavior_type == BehaviorType.PERSISTENT_APPROACH:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.BEHAVIOR_PRIMITIVE,
                    source_module="behavior",
                    value=b.behavior_type.value,
                    confidence=0.85,
                    reason_code=FusionReasonCode.PERSISTENT_APPROACH_DETECTED,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                    metadata={"duration": b.duration_seconds},
                ))
            elif b.behavior_type == BehaviorType.REPEATED_APPROACH:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.BEHAVIOR_PRIMITIVE,
                    source_module="behavior",
                    value=b.behavior_type.value,
                    confidence=0.88,
                    reason_code=FusionReasonCode.REPEATED_APPROACH_DETECTED,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                ))
            elif b.behavior_type == BehaviorType.LOITERING:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.BEHAVIOR_PRIMITIVE,
                    source_module="behavior",
                    value=b.behavior_type.value,
                    confidence=0.80,
                    reason_code=FusionReasonCode.LOITERING_DETECTED,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                    metadata={"duration": b.duration_seconds},
                ))

        # -------------------------------------------------------------
        # 5. Environmental Context Evidence
        # -------------------------------------------------------------
        if environment:
            if environment.visibility in (VisibilityQuality.POOR, VisibilityQuality.INSUFFICIENT) or environment.blur_score < 40.0:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.ENVIRONMENT_QUALITY,
                    source_module="environment",
                    value=environment.visibility.value,
                    confidence=0.5,
                    reason_code=FusionReasonCode.LOW_VISUAL_QUALITY,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                    metadata={"lighting": environment.lighting.value, "quality_score": environment.quality_score},
                ))
            elif environment.visibility == VisibilityQuality.EXCELLENT:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.ENVIRONMENT_QUALITY,
                    source_module="environment",
                    value=environment.visibility.value,
                    confidence=1.0,
                    reason_code=FusionReasonCode.EXCELLENT_VISIBILITY,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                ))

            if environment.lighting == LightingCondition.NIGHT:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.ENVIRONMENT_QUALITY,
                    source_module="environment",
                    value=environment.lighting.value,
                    confidence=0.8,
                    reason_code=FusionReasonCode.NIGHT_OPERATION,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                ))

        # -------------------------------------------------------------
        # 6. Multi-Camera Persistent Border Track Evidence (DEC-0009)
        # -------------------------------------------------------------
        if border_track:
            if len(border_track.camera_sequence) > 1 and border_track.association_confidence >= 0.50:
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.CROSS_CAMERA_ASSOCIATION,
                    source_module="cross_camera",
                    value=border_track.border_track_id,
                    confidence=border_track.association_confidence,
                    weight=1.2,
                    reason_code=FusionReasonCode.CROSS_CAMERA_CORROBORATED,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                    metadata={
                        "camera_sequence": border_track.camera_sequence,
                        "state": border_track.association_state.value,
                    },
                ))
            if border_track.association_state == "confirmed":
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.CROSS_CAMERA_ASSOCIATION,
                    source_module="cross_camera",
                    value=border_track.border_track_id,
                    confidence=border_track.association_confidence,
                    weight=1.0,
                    reason_code=FusionReasonCode.CROSS_CAMERA_HANDOFF_CONFIRMED,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                ))

        # -------------------------------------------------------------
        # 7. Sector Context & Normality Baseline Evidence (DEC-0009)
        # -------------------------------------------------------------
        if sector_context:
            if sector_context.status == "unusual":
                evidence_list.append(EvidenceItem(
                    evidence_type=EvidenceType.SECTOR_NORMALITY,
                    source_module="sector",
                    value=sector_context.reason or "Unusual sector activity",
                    confidence=0.85,
                    weight=1.0,
                    reason_code=FusionReasonCode.SECTOR_ACTIVITY_UNUSUAL,
                    timestamp_utc=timestamp_utc,
                    track_id=track.track_id,
                    camera_id=camera_id,
                    metadata={"deviation_ratio": sector_context.deviation_ratio},
                ))

        # -------------------------------------------------------------
        # 8. Evidence-on-Demand & Corroboration Requests (DEC-0009)
        # -------------------------------------------------------------
        if evidence_requests:
            for req in evidence_requests:
                if req.status == "fulfilled":
                    evidence_list.append(EvidenceItem(
                        evidence_type=EvidenceType.EVIDENCE_REQUEST_STATUS,
                        source_module="corroboration",
                        value=req.fulfillment_details or "Corroboration verified",
                        confidence=0.95,
                        weight=1.1,
                        reason_code=FusionReasonCode.EVIDENCE_REQUEST_FULFILLED,
                        timestamp_utc=timestamp_utc,
                        track_id=track.track_id,
                        camera_id=camera_id,
                    ))
                elif req.status == "expired":
                    evidence_list.append(EvidenceItem(
                        evidence_type=EvidenceType.EVIDENCE_REQUEST_STATUS,
                        source_module="corroboration",
                        value=req.fulfillment_details or "Corroboration timed out",
                        confidence=0.30,
                        weight=0.5,
                        reason_code=FusionReasonCode.INSUFFICIENT_EVIDENCE_EXPIRED,
                        timestamp_utc=timestamp_utc,
                        track_id=track.track_id,
                        camera_id=camera_id,
                    ))

        return evidence_list
