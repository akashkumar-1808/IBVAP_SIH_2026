"""
IBVAP — Manual Inspection & Verification Script for Phase 9 Evidence Package.

Generates a real forensic evidence package on disk:
- Raw Keyframe Snapshot (`snapshot_raw.jpg`)
- Forensic HUD Annotated Snapshot with border/event overlays (`snapshot_annotated.jpg`)
- Pre-Event MP4 Video Clip (`pre_event_clip.mp4`)
- Complete Incident MP4 Video Clip (`incident_clip.mp4`)
- Immutable Audit Manifest (`manifest.json`)
- SHA-256 Cryptographic Integrity Check

Architecture Decision: DEC-0008
"""

import os
import sys
import cv2
import json
import numpy as np
from pathlib import Path
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from worker.evidence import (
    EvidencePackager,
    EvidencePackageConfig,
    EvidencePackage,
    EvidenceManifest,
    EvidenceStatus,
    EvidenceHasher,
)
from worker.fusion.schemas import EventRecord, EventType, EventStatus as FusionEventStatus, FusionReasonCode
from worker.tracking.schemas import TrackState, TrajectoryPoint, TargetClass, BoundingBox, TrackStatus
from worker.spatial.schemas import (
    SpatialState,
    MovementDirection,
    BorderSide,
    CrossingStatus,
    SpatialConfidence,
    CameraSpatialConfig,
    ZonePolygon,
    Point2D,
    VirtualFence,
)
from backend.app.schemas.common import EventPriority, ZoneType


def generate_and_inspect_evidence_package():
    print("=" * 75)
    print("   IBVAP — PHASE 9 EVIDENCE PACKAGE INSPECTION & VERIFICATION DEMO")
    print("=" * 75)

    output_root = "storage/evidence"
    config = EvidencePackageConfig(
        pre_event_seconds=2.0,
        post_event_seconds=1.5,
        fps=25.0,
        snapshot_quality=95,
        storage_root=output_root,
    )
    packager = EvidencePackager(config=config)

    camera_id = "cam_sector_north_01"
    event_id = "evt_demo_border_breach_001"
    t0 = datetime(2026, 8, 30, 14, 0, 0, tzinfo=timezone.utc)

    # 1. Simulate 60 frames (2.4s) of a person approaching and crossing the border
    print(f"1. Buffering 60 frames (25 FPS) for camera '{camera_id}'...")
    for i in range(60):
        ts = t0 + timedelta(milliseconds=i * 40)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Draw realistic background environment
        cv2.rectangle(frame, (0, 0), (640, 240), (45, 55, 45), -1)  # Permitted upper field
        cv2.rectangle(frame, (0, 240), (640, 480), (35, 35, 60), -1) # Restricted lower field
        cv2.line(frame, (0, 240), (640, 240), (0, 0, 255), 2)       # Border Line

        # Person target moving from y=120 down to y=360
        target_y = int(120 + i * 4.0)
        target_x = 320
        cv2.rectangle(frame, (target_x - 15, target_y - 45), (target_x + 15, target_y), (0, 255, 255), 2)
        cv2.circle(frame, (target_x, target_y), 4, (0, 255, 0), -1) # Ground contact point

        packager.add_raw_frame(camera_id, i, ts, frame)

    # 2. Build EventRecord for Confirmed Border Crossing
    event = EventRecord(
        id=event_id,
        camera_id=camera_id,
        track_id=1,
        event_type=EventType.BORDER_CROSSING,
        priority=EventPriority.CRITICAL,
        risk_score=94.5,
        status=FusionEventStatus.ACTIVE,
        target_class=TargetClass.PERSON,
        created_at=t0,
        updated_at=t0,
        first_observed_utc=t0 + timedelta(milliseconds=500),
        last_observed_utc=t0 + timedelta(milliseconds=2000),
        duration_seconds=1.5,
        detection_confidence=0.96,
        track_persistence_frames=38,
        reason_codes=[
            FusionReasonCode.PERSON_DETECTED,
            FusionReasonCode.BORDER_CROSSED,
            FusionReasonCode.RESTRICTED_ZONE_ENTRY,
        ],
        explanation_summary="[CRITICAL PRIORITY — Score 94.5/100] BORDER CROSSING: PERSON confirmed across boundary into RESTRICTED zone.",
    )

    track = TrackState(
        track_id=1,
        camera_id=camera_id,
        class_id=TargetClass.PERSON,
        bbox=BoundingBox(x_min=305, y_min=240, x_max=335, y_max=285),
        center_xy=(320.0, 262.5),
        status=TrackStatus.TRACKED,
        first_seen=t0,
        last_seen=t0 + timedelta(seconds=2.0),
        trajectory=[TrajectoryPoint(x=320, y=int(120 + j * 4.0), timestamp_utc=t0 + timedelta(milliseconds=j*40), frame_id=j) for j in range(50)],
    )

    spatial_state = SpatialState(
        camera_id=camera_id,
        track_id=1,
        timestamp_utc=t0 + timedelta(seconds=1.5),
        border_side=BorderSide.RESTRICTED,
        crossing_status=CrossingStatus.CONFIRMED_CROSSING,
        direction=MovementDirection.TOWARD,
        spatial_confidence=SpatialConfidence.VALID,
        calibration_version="1.0-planar",
    )

    spatial_cfg = CameraSpatialConfig(
        camera_id=camera_id,
        zones=[
            ZonePolygon(id="z_perm", name="Safe Sector", zone_type=ZoneType.SAFE, polygon=[(0.0, 0.0), (640.0, 0.0), (640.0, 240.0), (0.0, 240.0)]),
            ZonePolygon(id="z_rest", name="Restricted Perimeter", zone_type=ZoneType.RESTRICTED, polygon=[(0.0, 240.0), (640.0, 240.0), (640.0, 480.0), (0.0, 480.0)]),
        ],
        fences=[VirtualFence(id="f_border", name="Border Line Alpha", start_point=(0.0, 240.0), end_point=(640.0, 240.0))],
    )

    # 3. Create, Seal, and Persist Evidence Package
    print("2. Assembling, sealing, and persisting EvidencePackage...")
    package = packager.create_package(
        event=event,
        track=track,
        spatial_state=spatial_state,
        spatial_config=spatial_cfg,
    )

    print("-" * 75)
    print("3. Manual Inspection Findings:")
    print(f"   - Package ID:              {package.id}")
    print(f"   - Status:                  {package.status.value.upper()}")
    print(f"   - Package Directory:       {os.path.abspath(package.package_dir)}")
    print(f"   - Raw Snapshot:            {package.snapshot_path} ({os.path.getsize(package.snapshot_path)} bytes)")
    print(f"   - Annotated Snapshot:      {package.annotated_snapshot_path} ({os.path.getsize(package.annotated_snapshot_path)} bytes)")
    print(f"   - Pre-Event Clip:          {package.pre_event_clip_path} ({os.path.getsize(package.pre_event_clip_path)} bytes)")
    print(f"   - Incident Clip:           {package.incident_clip_path} ({os.path.getsize(package.incident_clip_path)} bytes)")
    print(f"   - Audit Manifest:          {package.manifest_path} ({os.path.getsize(package.manifest_path)} bytes)")
    print(f"   - Cryptographic Seal:      {package.sha256_seal}")
    print(f"   - Sealed Artifact Count:   {len(package.manifest.artifacts)}")

    # 4. Perform Verification
    is_valid, errors = packager.verify_package(package.manifest_path)
    print("-" * 75)
    print(f"4. SHA-256 Non-Repudiation Verification: {'[PASS] VALID' if is_valid else '[FAIL] TAMPERED'}")
    assert is_valid is True

    print("=" * 75)
    print(f"[OK] Real Evidence Package successfully generated and verified at:\n     {os.path.abspath(package.package_dir)}")
    print("=" * 75)


if __name__ == "__main__":
    generate_and_inspect_evidence_package()
