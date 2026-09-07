"""
Risk Priority Scoring, Priority Tier Classification, and Factual Explanation Generator.

Deterministic mathematical evaluation of multi-modal evidence into:
1. Bounded Risk Priority Score [0, 100]
2. Discrete EventPriority tiers (INFO, LOW, MEDIUM, HIGH, CRITICAL)
3. Factual, auditable human-readable explanation summaries strictly from structured facts.

Architecture Decision: DEC-0007
"""

import math
from typing import List, Tuple, Optional, Dict, Any

from backend.app.schemas.common import TargetClass, EventPriority, VisibilityQuality, LightingCondition
from .schemas import EventType, FusionReasonCode, FusionConfig
from .evidence import EvidenceItem, EvidenceType


def calculate_risk_score(
    evidence_items: List[EvidenceItem],
    config: FusionConfig,
) -> Tuple[float, List[FusionReasonCode], List[str]]:
    """
    Computes a deterministic, bounded risk priority score in [0.0, 100.0]
    from normalized evidence items.

    Returns:
        (risk_score, reason_codes, uncertainty_flags)
    """
    if not evidence_items:
        return 0.0, [], []

    reason_codes: List[FusionReasonCode] = []
    uncertainty_flags: List[str] = []

    # 1. Target Class Score [0, 1]
    class_score = 0.0
    for ev in evidence_items:
        if ev.evidence_type == EvidenceType.OBJECT_CLASS:
            reason_codes.append(ev.reason_code)
            if ev.reason_code == FusionReasonCode.PERSON_DETECTED:
                class_score = max(class_score, config.class_score_person)
            elif ev.reason_code == FusionReasonCode.VEHICLE_DETECTED:
                class_score = max(class_score, config.class_score_vehicle)
            elif ev.reason_code == FusionReasonCode.ANIMAL_DETECTED:
                class_score = max(class_score, config.class_score_animal)
            else:
                class_score = max(class_score, config.class_score_unknown)

    # 2. Track Persistence Modifier [0.3, 1.0]
    persistence_modifier = 0.4
    for ev in evidence_items:
        if ev.evidence_type == EvidenceType.TRACK_PERSISTENCE:
            reason_codes.append(ev.reason_code)
            if ev.reason_code == FusionReasonCode.PERSISTENT_TRACK:
                persistence_frames = ev.value if isinstance(ev.value, (int, float)) else 5
                persistence_modifier = min(1.0, 0.5 + (persistence_frames / 20.0))
            elif ev.reason_code == FusionReasonCode.SHORT_LIVED_TRACK:
                persistence_modifier = 0.35

    # 3. Spatial Severity Score [0, 1]
    spatial_score = 0.0
    has_spatial_evidence = False
    is_spatial_invalid = False

    for ev in evidence_items:
        if ev.evidence_type in (EvidenceType.BORDER_SIDE, EvidenceType.BORDER_CROSSING, EvidenceType.ZONE_MEMBERSHIP, EvidenceType.MOVEMENT_DIRECTION):
            has_spatial_evidence = True
            reason_codes.append(ev.reason_code)

            if ev.reason_code == FusionReasonCode.BORDER_CROSSED:
                spatial_score = max(spatial_score, config.spatial_score_border_crossed)
            elif ev.reason_code in (FusionReasonCode.RESTRICTED_ZONE_ENTRY, FusionReasonCode.CRITICAL_ZONE_ENTRY):
                spatial_score = max(spatial_score, config.spatial_score_restricted)
            elif ev.reason_code in (FusionReasonCode.WARNING_BUFFER_ENTRY, FusionReasonCode.BORDER_LINE_CONTACT):
                spatial_score = max(spatial_score, config.spatial_score_warning_buffer)
            elif ev.reason_code == FusionReasonCode.TOWARD_PROTECTED_REGION:
                spatial_score = max(spatial_score, 0.45)
            elif ev.reason_code == FusionReasonCode.SAFE_ZONE_ONLY:
                spatial_score = max(spatial_score, config.spatial_score_safe)

        if ev.evidence_type == EvidenceType.CALIBRATION_CONFIDENCE:
            is_spatial_invalid = True
            reason_codes.append(ev.reason_code)
            uncertainty_flags.append("SPATIAL_CALIBRATION_INVALID")

    # If spatial calibration is invalid, cap spatial score to avoid false breach alert
    if is_spatial_invalid:
        spatial_score = min(spatial_score, 0.35)

    if not has_spatial_evidence:
        spatial_score = 0.1  # Minimal default if in monitored scene

    # 4. Behavioral Severity Score [0, 1]
    behavior_score = 0.0
    has_behavior_evidence = False

    for ev in evidence_items:
        if ev.evidence_type == EvidenceType.BEHAVIOR_PRIMITIVE:
            has_behavior_evidence = True
            reason_codes.append(ev.reason_code)

            if ev.reason_code == FusionReasonCode.FENCE_BREACH_DETECTED:
                behavior_score = max(behavior_score, config.behavior_score_fence_breach)
            elif ev.reason_code == FusionReasonCode.RESTRICTED_OCCUPANCY:
                behavior_score = max(behavior_score, config.behavior_score_restricted_occupancy)
            elif ev.reason_code == FusionReasonCode.REPEATED_APPROACH_DETECTED:
                behavior_score = max(behavior_score, config.behavior_score_repeated_approach)
            elif ev.reason_code == FusionReasonCode.PERSISTENT_APPROACH_DETECTED:
                behavior_score = max(behavior_score, config.behavior_score_persistent_approach)
            elif ev.reason_code == FusionReasonCode.LOITERING_DETECTED:
                behavior_score = max(behavior_score, config.behavior_score_loitering)

    if not has_behavior_evidence:
        behavior_score = 0.0

    # 5. Environmental Modifier & Context [0, 1]
    environment_factor = 0.5  # Neutral default
    for ev in evidence_items:
        if ev.evidence_type == EvidenceType.ENVIRONMENT_QUALITY:
            reason_codes.append(ev.reason_code)
            if ev.reason_code == FusionReasonCode.LOW_VISUAL_QUALITY:
                uncertainty_flags.append("LOW_VISUAL_QUALITY")
                environment_factor = 0.35  # Reduced certainty
            elif ev.reason_code == FusionReasonCode.NIGHT_OPERATION:
                # Night is context: increases operational scrutiny if spatial/behavior is active
                if spatial_score > 0.4 or behavior_score > 0.4:
                    environment_factor = 0.75
            elif ev.reason_code == FusionReasonCode.EXCELLENT_VISIBILITY:
                environment_factor = 0.60

    # 6. Multi-Camera Corroboration & Sector Context Modifiers (DEC-0009)
    has_cross_cam_corroboration = False
    has_sector_deviation = False
    is_corroboration_expired = False
    stream_trust_factor = 1.0

    for ev in evidence_items:
        if ev.evidence_type == EvidenceType.CROSS_CAMERA_ASSOCIATION:
            reason_codes.append(ev.reason_code)
            has_cross_cam_corroboration = True
        elif ev.evidence_type == EvidenceType.SECTOR_NORMALITY:
            reason_codes.append(ev.reason_code)
            has_sector_deviation = True
        elif ev.evidence_type == EvidenceType.EVIDENCE_REQUEST_STATUS:
            reason_codes.append(ev.reason_code)
            if ev.reason_code == FusionReasonCode.INSUFFICIENT_EVIDENCE_EXPIRED:
                is_corroboration_expired = True
        elif ev.evidence_type == EvidenceType.STREAM_CONTINUITY:
            reason_codes.append(ev.reason_code)
            if ev.reason_code == FusionReasonCode.STREAM_QUALITY_DEGRADED:
                uncertainty_flags.append("STREAM_QUALITY_DEGRADED")
                stream_trust_factor = min(stream_trust_factor, max(0.4, ev.confidence))
            elif ev.reason_code == FusionReasonCode.STREAM_INTERRUPTION_RECENT:
                uncertainty_flags.append("STREAM_INTERRUPTION_RECENT")
                stream_trust_factor = min(stream_trust_factor, 0.75)
            elif ev.reason_code == FusionReasonCode.TRACK_CONTINUITY_UNCERTAIN:
                uncertainty_flags.append("TRACK_CONTINUITY_UNCERTAIN")
                stream_trust_factor = min(stream_trust_factor, 0.60)

    # -------------------------------------------------------------
    # Transparent Weighted Fusion Formula
    # -------------------------------------------------------------
    # Raw components
    w_c = config.weight_class
    w_s = config.weight_spatial
    w_b = config.weight_behavior
    w_e = config.weight_environment

    # Effective score:
    # (w_class * S_class * persistence_modifier) + (w_spatial * S_spatial) + (w_behavior * S_behavior) + (w_env * S_env)
    base_activity = (w_s * spatial_score) + (w_b * behavior_score)
    combined = (w_c * class_score * persistence_modifier) + base_activity + (w_e * environment_factor * min(1.0, base_activity + 0.2))

    # Scale to [0, 100] and modulate with stream trust factor
    total_weights = w_c + w_s + w_b + w_e
    normalized_score = (combined / total_weights) * 100.0 * stream_trust_factor

    # Cross-camera handoff & multi-camera persistence boost (only when base activity is active)
    if has_cross_cam_corroboration and base_activity > 0.3:
        normalized_score += 6.0

    # Sector deviation context boost (supporting evidence only)
    if has_sector_deviation and base_activity > 0.2:
        normalized_score += 4.0

    # Confirmed border crossing elevation (for human/vehicle with valid calibration)
    if (FusionReasonCode.BORDER_CROSSED in reason_codes or FusionReasonCode.FENCE_BREACH_DETECTED in reason_codes) and not is_spatial_invalid:
        if class_score >= 0.7:  # Person or Vehicle
            normalized_score = max(normalized_score, config.threshold_medium_max + 5.0)

    # Single-frame shadow / short-lived suppression:
    # If track persistence is short and no sustained behavior, cap score at low tier
    if persistence_modifier < 0.4 and behavior_score < 0.5 and spatial_score < 0.8:
        normalized_score = min(normalized_score, config.threshold_info_max)

    # Corroboration timeout / expired evidence: cap score at INFO
    if is_corroboration_expired:
        normalized_score = min(normalized_score, config.threshold_info_max)

    # Animal suppression: animal in safe/buffer zone cannot exceed LOW threshold
    if class_score <= config.class_score_animal and spatial_score < 0.8:
        normalized_score = min(normalized_score, config.threshold_low_max - 5.0)

    # Strictly bound in [0.0, 100.0]
    final_score = float(max(0.0, min(100.0, round(normalized_score, 2))))

    # Deduplicate reason codes preserving order
    deduped_reasons: List[FusionReasonCode] = []
    seen = set()
    for r in reason_codes:
        if r not in seen:
            seen.add(r)
            deduped_reasons.append(r)

    return final_score, deduped_reasons, list(set(uncertainty_flags))


def map_score_to_priority(
    score: float,
    config: FusionConfig,
) -> EventPriority:
    """Maps a risk score [0, 100] into discrete operational EventPriority tiers."""
    if score <= config.threshold_info_max:
        return EventPriority.INFO
    elif score <= config.threshold_low_max:
        return EventPriority.LOW
    elif score <= config.threshold_medium_max:
        return EventPriority.MEDIUM
    elif score <= config.threshold_high_max:
        return EventPriority.HIGH
    else:
        return EventPriority.CRITICAL


def determine_primary_event_type(
    evidence_items: List[EvidenceItem],
) -> EventType:
    """Selects the canonical primary EventType representing the operational state."""
    reasons = {ev.reason_code for ev in evidence_items}

    if FusionReasonCode.BORDER_CROSSED in reasons:
        return EventType.BORDER_CROSSING
    if FusionReasonCode.FENCE_BREACH_DETECTED in reasons:
        return EventType.FENCE_BREACH
    if FusionReasonCode.RESTRICTED_ZONE_ENTRY in reasons or FusionReasonCode.RESTRICTED_OCCUPANCY in reasons:
        return EventType.RESTRICTED_ZONE_INTRUSION
    if FusionReasonCode.REPEATED_APPROACH_DETECTED in reasons:
        return EventType.REPEATED_APPROACH
    if FusionReasonCode.PERSISTENT_APPROACH_DETECTED in reasons:
        return EventType.PERSISTENT_APPROACH
    if FusionReasonCode.LOITERING_DETECTED in reasons:
        return EventType.LOITERING

    return EventType.OBJECT_OBSERVED


def generate_factual_summary(
    event_type: EventType,
    target_class: TargetClass,
    priority: EventPriority,
    score: float,
    reason_codes: List[FusionReasonCode],
    uncertainty_flags: List[str],
    environment_summary: str = "Normal daytime visibility",
) -> str:
    """
    Generates a deterministic human-readable explanation summary strictly from structured facts.
    No LLM or speculative hallucination is used.
    """
    class_label = target_class.value.upper()
    event_label = event_type.value.replace("_", " ").upper()

    lines = [
        f"[{priority.value} PRIORITY — Score {score:.1f}/100] {event_label}: {class_label} detected.",
    ]

    # Structured reasons
    bullet_reasons = []
    for r in reason_codes:
        if r == FusionReasonCode.PERSON_DETECTED:
            bullet_reasons.append("Person target identified")
        elif r == FusionReasonCode.VEHICLE_DETECTED:
            bullet_reasons.append("Vehicle target identified")
        elif r == FusionReasonCode.ANIMAL_DETECTED:
            bullet_reasons.append("Animal target identified (non-human movement)")
        elif r == FusionReasonCode.PERSISTENT_TRACK:
            bullet_reasons.append("Persistent multi-frame track confirmed")
        elif r == FusionReasonCode.SHORT_LIVED_TRACK:
            bullet_reasons.append("Transient / short-lived track observation")
        elif r == FusionReasonCode.BORDER_CROSSED:
            bullet_reasons.append("Real-world border boundary crossed")
        elif r == FusionReasonCode.WARNING_BUFFER_ENTRY:
            bullet_reasons.append("Entered calibrated warning buffer perimeter")
        elif r == FusionReasonCode.RESTRICTED_ZONE_ENTRY or r == FusionReasonCode.RESTRICTED_OCCUPANCY:
            bullet_reasons.append("Active presence inside restricted zone")
        elif r == FusionReasonCode.TOWARD_PROTECTED_REGION:
            bullet_reasons.append("Continuous trajectory directed toward protected boundary")
        elif r == FusionReasonCode.PERSISTENT_APPROACH_DETECTED:
            bullet_reasons.append("Persistent sustained approach toward threat vector")
        elif r == FusionReasonCode.LOITERING_DETECTED:
            bullet_reasons.append("Stationary dwell / loitering detected exceeding threshold")
        elif r == FusionReasonCode.FENCE_BREACH_DETECTED:
            bullet_reasons.append("Virtual barrier trajectory crossing verified")

    if bullet_reasons:
        lines.append("Evidence Factors: " + "; ".join(bullet_reasons) + ".")

    lines.append(f"Environmental Context: {environment_summary}.")

    if uncertainty_flags:
        lines.append("Uncertainty Flags: " + ", ".join(uncertainty_flags) + ".")

    return " ".join(lines)
