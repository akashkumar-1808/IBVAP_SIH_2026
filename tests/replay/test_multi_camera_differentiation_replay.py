"""
Deterministic Multi-Camera Differentiation Replay Pipeline Test for IBVAP.

Verifies end-to-end multi-camera tracking, border crossing corroboration,
sector deviation evaluation, and sealed evidence packaging across 3 simulated cameras.

Architecture Decision: DEC-0009
"""

import os
import cv2
import pytest
import numpy as np
from datetime import datetime, timezone, timedelta

from worker.cross_camera import (
    CrossCameraAssociator,
    CameraTopology,
    CameraTransitionRule,
    BorderTrack,
    AssociationState,
)
from worker.sector import (
    SectorNormalityEngine,
    SectorContext,
    NormalityStatus,
)
from worker.fusion import (
    FusionEngine,
    FusionConfig,
    EventRecord,
    EventType,
    EventPriority,
    FusionReasonCode,
)
from worker.evidence import (
    EvidencePackager,
    EvidencePackageConfig,
    EvidenceStatus,
)
from worker.tracking.schemas import (
    TrackState,
    TargetClass,
    BoundingBox,
    TrajectoryPoint,
    TrackStatus,
)
from worker.spatial.schemas import (
    SpatialState,
    MovementDirection,
    BorderSide,
    CrossingStatus,
    SpatialConfidence,
)
from worker.behavior.schemas import BehaviorPrimitive, BehaviorType


def _generate_synthetic_camera_frame(camera_id: str, frame_num: int, target_pos: tuple) -> np.ndarray:
    """Generates a synthetic camera view with clear border and moving target."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Background
    cv2.rectangle(frame, (0, 0), (640, 240), (40, 50, 40), -1)   # Safe side
    cv2.rectangle(frame, (0, 240), (640, 480), (30, 30, 50), -1) # Restricted side
    cv2.line(frame, (0, 240), (640, 240), (0, 0, 255), 2)        # Border

    # Target
    tx, ty = int(target_pos[0]), int(target_pos[1])
    cv2.rectangle(frame, (tx - 15, ty - 40), (tx + 15, ty), (0, 255, 255), 2)
    cv2.circle(frame, (tx, ty), 4, (0, 255, 0), -1)

    cv2.putText(frame, f"{camera_id} | F:{frame_num}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return frame


def test_multi_camera_differentiation_replay_pipeline(tmp_path):
    """
    Simulates 3-camera sequential border breach with full differentiation stack:
    1. CAM-01 (Approach in Permitted zone) -> spawns BorderTrack BT-100
    2. CAM-02 (Physical Border Crossing at 02:00) -> handoff confirmed, sector deviation flagged
    3. CAM-03 (Restricted Zone Penetration) -> multi-camera corroboration confirmed, high-priority event
    4. EvidencePackager seals evidence package with full multi-camera audit trail.
    """
    storage_root = str(tmp_path / "diff_replay_evidence")
    packager = EvidencePackager(EvidencePackageConfig(storage_root=storage_root))
    fusion = FusionEngine()

    # 1. Setup Camera Topology
    topology = CameraTopology()
    topology.add_rule(CameraTransitionRule(
        source_camera_id="CAM-NORTH-01",
        target_camera_id="CAM-NORTH-02",
        min_transit_seconds=0.5,
        max_transit_seconds=10.0,
        expected_direction=MovementDirection.TOWARD,
    ))
    topology.add_rule(CameraTransitionRule(
        source_camera_id="CAM-NORTH-02",
        target_camera_id="CAM-NORTH-03",
        min_transit_seconds=0.5,
        max_transit_seconds=10.0,
        expected_direction=MovementDirection.TOWARD,
    ))
    fusion.cross_camera_associator.topology = topology

    t0 = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)  # Nocturnal hour

    # -------------------------------------------------------------
    # STAGE 1: CAM-NORTH-01 (Approaching Border)
    # -------------------------------------------------------------
    cam1_frames = []
    for f in range(25):
        ts = t0 + timedelta(milliseconds=f * 40)
        img = _generate_synthetic_camera_frame("CAM-NORTH-01", f, (320, 100 + f * 4))
        packager.add_raw_frame("CAM-NORTH-01", f, ts, img)
        cam1_frames.append((f, ts, img))

    t_cam1_end = t0 + timedelta(seconds=1.0)
    track1 = TrackState(
        track_id=101, camera_id="CAM-NORTH-01", class_id=TargetClass.PERSON,
        bbox=BoundingBox(x_min=305, y_min=160, x_max=335, y_max=200), center_xy=(320.0, 180.0),
        status=TrackStatus.TRACKED, first_seen=t0, last_seen=t_cam1_end, age_frames=25,
        confidence_history=[0.95] * 25,
        trajectory=[TrajectoryPoint(x=320, y=100 + i*4, timestamp_utc=t0 + timedelta(milliseconds=i*40), frame_id=i) for i in range(25)],
    )
    spatial1 = SpatialState(
        camera_id="CAM-NORTH-01", track_id=101, timestamp_utc=t_cam1_end,
        border_side=BorderSide.PERMITTED, direction=MovementDirection.TOWARD,
        spatial_confidence=SpatialConfidence.VALID,
    )
    behavior1 = [
        BehaviorPrimitive(
            behavior_id="bp_01", track_id=101, camera_id="CAM-NORTH-01",
            behavior_type=BehaviorType.PERSISTENT_APPROACH,
            first_observed_utc=t0, last_observed_utc=t_cam1_end, timestamp_utc=t_cam1_end,
            duration_seconds=1.0,
        )
    ]

    ev_cam1 = fusion.process([track1], [spatial1], None, behavior1, "CAM-NORTH-01", t_cam1_end, sector_id="sector_north_alpha")
    assert len(ev_cam1) == 1
    assert ev_cam1[0].border_track_id == "BT-100"

    # -------------------------------------------------------------
    # STAGE 2: CAM-NORTH-02 (Border Breach at 02:00 UTC)
    # -------------------------------------------------------------
    t2_start = t0 + timedelta(seconds=2.5)  # 1.5s transit
    cam2_frames = []
    for f in range(25):
        ts = t2_start + timedelta(milliseconds=f * 40)
        img = _generate_synthetic_camera_frame("CAM-NORTH-02", f, (320, 200 + f * 4))
        packager.add_raw_frame("CAM-NORTH-02", f, ts, img)
        cam2_frames.append((f, ts, img))

    t_cam2_end = t2_start + timedelta(seconds=1.0)
    track2 = TrackState(
        track_id=202, camera_id="CAM-NORTH-02", class_id=TargetClass.PERSON,
        bbox=BoundingBox(x_min=305, y_min=240, x_max=335, y_max=280), center_xy=(320.0, 260.0),
        status=TrackStatus.TRACKED, first_seen=t2_start, last_seen=t_cam2_end, age_frames=25,
        confidence_history=[0.96] * 25,
        trajectory=[TrajectoryPoint(x=320, y=200 + i*4, timestamp_utc=t2_start + timedelta(milliseconds=i*40), frame_id=i) for i in range(25)],
    )
    spatial2 = SpatialState(
        camera_id="CAM-NORTH-02", track_id=202, timestamp_utc=t_cam2_end,
        border_side=BorderSide.RESTRICTED, crossing_status=CrossingStatus.CONFIRMED_CROSSING,
        direction=MovementDirection.TOWARD, spatial_confidence=SpatialConfidence.VALID,
    )
    behavior2 = [
        BehaviorPrimitive(
            behavior_id="bp_02", track_id=202, camera_id="CAM-NORTH-02",
            behavior_type=BehaviorType.FENCE_BREACH,
            first_observed_utc=t2_start, last_observed_utc=t_cam2_end, timestamp_utc=t_cam2_end,
            duration_seconds=1.0,
        )
    ]

    ev_cam2 = fusion.process([track2], [spatial2], None, behavior2, "CAM-NORTH-02", t_cam2_end, sector_id="sector_north_alpha")
    assert len(ev_cam2) == 1
    assert ev_cam2[0].border_track_id == "BT-100"
    assert ev_cam2[0].risk_score >= 85.0
    assert FusionReasonCode.CROSS_CAMERA_CORROBORATED in ev_cam2[0].reason_codes
    assert FusionReasonCode.SECTOR_ACTIVITY_UNUSUAL in ev_cam2[0].reason_codes

    # -------------------------------------------------------------
    # STAGE 3: CAM-NORTH-03 (Restricted Deep Occupancy)
    # -------------------------------------------------------------
    t3_start = t2_start + timedelta(seconds=3.0)
    for f in range(25):
        ts = t3_start + timedelta(milliseconds=f * 40)
        img = _generate_synthetic_camera_frame("CAM-NORTH-03", f, (320, 300 + f * 4))
        packager.add_raw_frame("CAM-NORTH-03", f, ts, img)

    t_cam3_end = t3_start + timedelta(seconds=1.0)
    track3 = TrackState(
        track_id=303, camera_id="CAM-NORTH-03", class_id=TargetClass.PERSON,
        bbox=BoundingBox(x_min=305, y_min=340, x_max=335, y_max=380), center_xy=(320.0, 360.0),
        status=TrackStatus.TRACKED, first_seen=t3_start, last_seen=t_cam3_end, age_frames=25,
        confidence_history=[0.97] * 25,
        trajectory=[TrajectoryPoint(x=320, y=300 + i*4, timestamp_utc=t3_start + timedelta(milliseconds=i*40), frame_id=i) for i in range(25)],
    )
    spatial3 = SpatialState(
        camera_id="CAM-NORTH-03", track_id=303, timestamp_utc=t_cam3_end,
        border_side=BorderSide.RESTRICTED, crossing_status=CrossingStatus.CONFIRMED_CROSSING,
        direction=MovementDirection.TOWARD, spatial_confidence=SpatialConfidence.VALID,
    )
    behavior3 = [
        BehaviorPrimitive(
            behavior_id="bp_03", track_id=303, camera_id="CAM-NORTH-03",
            behavior_type=BehaviorType.RESTRICTED_OCCUPANCY,
            first_observed_utc=t3_start, last_observed_utc=t_cam3_end, timestamp_utc=t_cam3_end,
            duration_seconds=1.0,
        )
    ]

    ev_cam3 = fusion.process([track3], [spatial3], None, behavior3, "CAM-NORTH-03", t_cam3_end, sector_id="sector_north_alpha")
    assert len(ev_cam3) == 1
    final_event = ev_cam3[0]

    assert final_event.border_track_id == "BT-100"
    assert final_event.priority in (EventPriority.HIGH, EventPriority.CRITICAL)
    assert final_event.risk_score >= 90.0

    # -------------------------------------------------------------
    # STAGE 4: Sealed Evidence Package Generation & Verification
    # -------------------------------------------------------------
    evidence_package = packager.create_package(
        event=final_event,
        track=track3,
        spatial_state=spatial3,
    )

    assert evidence_package.status in (EvidenceStatus.SEALED, EvidenceStatus.PARTIAL)
    assert os.path.exists(evidence_package.snapshot_path)
    assert os.path.exists(evidence_package.annotated_snapshot_path)
    assert os.path.exists(evidence_package.manifest_path)

    # Verify SHA-256 seal integrity
    is_valid, errors = packager.verify_package(evidence_package.manifest_path)
    assert is_valid is True
    assert len(errors) == 0
