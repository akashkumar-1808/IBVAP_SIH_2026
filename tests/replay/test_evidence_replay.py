"""
Deterministic Replay Pipeline Test for Phase 9 Structured Evidence Storage & Packaging.

Runs complete 9-layer end-to-end video pipeline:
Video -> Ingestion -> Perception (YOLOv8) -> Tracking (ByteTrack) -> Environment (Analyzer)
      -> Spatial (World-Border Homography) -> Behavior (Detectors) -> Fusion (Engine)
      -> EvidencePackager -> Cryptographically Sealed EvidencePackage
"""

import os
import cv2
import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import List

from worker.ingestion import FileVideoSource, BoundedFrameQueue
from worker.perception import ObjectDetector
from worker.tracking import ByteTrackTracker
from worker.environment import EnvironmentAnalyzer
from backend.app.schemas.common import TargetClass
from worker.spatial import (
    SpatialEngine,
    BorderSection,
    CameraRegistration,
    CameraCalibration,
    CalibrationCorrespondence,
    WorldPoint,
    BorderSide,
)
from worker.behavior import BehaviorEngine, BehaviorConfig
from worker.fusion import FusionEngine, EventRecord, EventType
from worker.evidence import (
    EvidencePackager,
    EvidencePackageConfig,
    EvidencePackage,
    EvidenceStatus,
)


@pytest.fixture
def evidence_test_clip(tmp_path):
    """Generates a 30-frame synthetic test video where a target moves across the border."""
    clip_path = str(tmp_path / "evidence_replay_30frames.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(clip_path, fourcc, 25.0, (640, 480))

    # Target moves from top to bottom
    for i in range(30):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cx = 320
        cy = int(100 + i * (280 / 29))
        cv2.circle(frame, (cx, cy), 20, (255, 255, 255), -1)
        out.write(frame)

    out.release()
    yield clip_path

    if os.path.exists(clip_path):
        try:
            os.remove(clip_path)
        except Exception:
            pass


def test_full_evidence_replay_pipeline(evidence_test_clip, tmp_path):
    """
    End-to-end deterministic 9-layer pipeline test:
    Ingestion -> Perception -> Tracking -> Environment -> Spatial -> Behavior -> Fusion -> EvidencePackager
    """
    camera_id = "cam_evidence_replay"
    source = FileVideoSource(camera_id=camera_id, file_path=evidence_test_clip, loop=False)
    queue = BoundedFrameQueue(max_size=30)
    detector = ObjectDetector(model_name="yolov8n", confidence_threshold=0.15)
    tracker = ByteTrackTracker(camera_id=camera_id, min_hits=1, max_lost_frames=10)
    env_analyzer = EnvironmentAnalyzer()

    # 1. Spatial Engine with World-Border Model
    spatial_engine = SpatialEngine(crossing_confirmation_frames=2)
    border_section = BorderSection(
        id="section_ev_replay",
        name="Evidence Replay Sector Border",
        points=[WorldPoint(x=0, y=50), WorldPoint(x=100, y=50)],
        permitted_side_normal=(0.0, 1.0),
        warning_buffer_distance=5.0,
    )
    spatial_engine.register_border_section(border_section)
    spatial_engine.register_camera(CameraRegistration(
        camera_id=camera_id,
        visible_border_sections=["section_ev_replay"],
    ))
    calibration = CameraCalibration(
        camera_id=camera_id,
        image_width=640,
        image_height=480,
        correspondences=[
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=0), image_point=(50, 430)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100, y=0), image_point=(590, 430)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100, y=100), image_point=(590, 50)),
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=100), image_point=(50, 50)),
        ],
        calibration_version="1.0",
    )
    spatial_engine.register_calibration(calibration)

    # 2. Behavior Engine
    behavior_engine = BehaviorEngine(default_config=BehaviorConfig(loitering_seconds=1.0, persistent_approach_seconds=0.5))

    # 3. Fusion Engine
    fusion_engine = FusionEngine()

    # 4. Evidence Packager Subsystem
    evidence_config = EvidencePackageConfig(
        pre_event_seconds=2.0,
        post_event_seconds=1.0,
        fps=25.0,
        storage_root=str(tmp_path / "evidence_output"),
    )
    evidence_packager = EvidencePackager(config=evidence_config)

    assert source.connect() is True
    assert detector.load() is True

    # Ingest frames into queue
    while True:
        pkt = source.read()
        if pkt is None:
            break
        queue.put(pkt)

    processed_frames = 0
    created_packages: List[EvidencePackage] = []

    while not queue.is_empty():
        pkt = queue.get(timeout=0.1)
        if pkt is None:
            break

        # Layer 1: Frame Buffering in Evidence Ring Buffer
        evidence_packager.add_frame(pkt)

        # Layer 2: Environment
        env_state = env_analyzer.analyze(pkt)

        # Layer 3: Perception
        detections = detector.infer(pkt)

        # Layer 4: Tracking
        tracks = tracker.update(
            detections=detections,
            frame_id=pkt.frame_id,
            timestamp_utc=pkt.timestamp_utc,
            camera_id=pkt.camera_id,
        )

        # Layer 5: Spatial Intelligence
        spatial_states = spatial_engine.process_tracks(
            tracks=tracks,
            camera_id=pkt.camera_id,
            timestamp_utc=pkt.timestamp_utc,
        )

        # Layer 6: Behavioral Analytics
        behaviors = behavior_engine.process(
            tracks=tracks,
            spatial_states=spatial_states,
            timestamp_utc=pkt.timestamp_utc,
            environment_state=env_state,
        )

        # Layer 7: Multi-Modal Evidence Fusion
        events = fusion_engine.process(
            tracks=tracks,
            spatial_states=spatial_states,
            environment_state=env_state,
            behavior_primitives=behaviors,
            camera_id=pkt.camera_id,
            timestamp_utc=pkt.timestamp_utc,
        )

        # Layer 8: Evidence Packaging for qualified actionable events
        if events:
            for ev in events:
                # Package event
                pkg = evidence_packager.create_package(
                    event=ev,
                    track=tracks[0] if tracks else None,
                    spatial_state=spatial_states[0] if spatial_states else None,
                    projected_borders=spatial_engine.get_projected_borders(pkt.camera_id),
                    current_frame=pkt.image,
                )
                created_packages.append(pkg)

        processed_frames += 1

    assert processed_frames == 30
    assert len(created_packages) > 0

    # Verify latest package structure and cryptographic integrity
    latest_pkg = created_packages[-1]
    assert latest_pkg.status == EvidenceStatus.SEALED
    assert latest_pkg.is_sealed is True
    assert latest_pkg.sha256_seal is not None
    assert len(latest_pkg.sha256_seal) == 64

    # Verify physical file existence
    assert os.path.exists(latest_pkg.snapshot_path)
    assert os.path.exists(latest_pkg.annotated_snapshot_path)
    assert os.path.exists(latest_pkg.incident_clip_path)
    assert os.path.exists(latest_pkg.manifest_path)

    # Verify manifest details
    assert latest_pkg.manifest.event_id == latest_pkg.event_id
    assert latest_pkg.manifest.camera_id == camera_id
    assert len(latest_pkg.manifest.artifacts) >= 3

    # Cryptographic non-repudiation verification
    is_valid, errors = evidence_packager.verify_package(latest_pkg.manifest_path)
    assert is_valid is True
    assert len(errors) == 0

    # Clean shutdown
    source.close()
    queue.close()
    detector.close()
    tracker.close()
    env_analyzer.close()
    spatial_engine.close()
    behavior_engine.close()
    fusion_engine.close()
    evidence_packager.close()
