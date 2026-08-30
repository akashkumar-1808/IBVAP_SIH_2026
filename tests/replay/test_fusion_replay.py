"""
Deterministic Replay Pipeline Test for Phase 8 Multi-Modal Evidence Fusion Engine.

Runs complete end-to-end video pipeline:
Video -> Ingestion -> Perception (YOLOv8) -> Tracking (ByteTrack) -> Environment (Analyzer)
      -> Spatial (World-Border Homography) -> Behavior (Detectors) -> FusionEngine -> EventRecord[]
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
from worker.fusion import FusionEngine, FusionConfig, EventRecord, EventType, EventPriority, FusionReasonCode


@pytest.fixture
def fusion_test_clip(tmp_path):
    """Generates a 30-frame synthetic test video where a target moves from permitted across a calibrated border into restricted."""
    clip_path = str(tmp_path / "fusion_replay_30frames.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(clip_path, fourcc, 25.0, (640, 480))

    # Target moves from upper image (world y ~ 85, permitted) to lower image (world y ~ 15, restricted)
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


def test_full_fusion_replay_pipeline(fusion_test_clip):
    """
    End-to-end deterministic multi-layer pipeline test:
    Ingestion -> Perception -> Tracking -> Environment -> Spatial (World-Border) -> Behavior -> Fusion
    """
    camera_id = "cam_fusion_replay"
    source = FileVideoSource(camera_id=camera_id, file_path=fusion_test_clip, loop=False)
    queue = BoundedFrameQueue(max_size=30)
    detector = ObjectDetector(model_name="yolov8n", confidence_threshold=0.15)
    tracker = ByteTrackTracker(camera_id=camera_id, min_hits=1, max_lost_frames=10)
    env_analyzer = EnvironmentAnalyzer()

    # 1. Spatial Engine with World-Border Model (Y=50 is the border line)
    spatial_engine = SpatialEngine(crossing_confirmation_frames=2)
    border_section = BorderSection(
        id="section_replay",
        name="Replay Sector Border",
        points=[WorldPoint(x=0, y=50), WorldPoint(x=100, y=50)],
        permitted_side_normal=(0.0, 1.0),
        warning_buffer_distance=5.0,
    )
    spatial_engine.register_border_section(border_section)
    spatial_engine.register_camera(CameraRegistration(
        camera_id=camera_id,
        visible_border_sections=["section_replay"],
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

    assert source.connect() is True
    assert detector.load() is True

    # Ingest frames
    while True:
        pkt = source.read()
        if pkt is None:
            break
        queue.put(pkt)

    processed_frames = 0
    generated_events: List[EventRecord] = []

    while not queue.is_empty():
        pkt = queue.get(timeout=0.1)
        if pkt is None:
            break

        # Layer 1: Environment
        env_state = env_analyzer.analyze(pkt)

        # Layer 2: Perception
        detections = detector.infer(pkt)

        # Layer 3: Tracking
        tracks = tracker.update(
            detections=detections,
            frame_id=pkt.frame_id,
            timestamp_utc=pkt.timestamp_utc,
            camera_id=pkt.camera_id,
        )

        # Layer 4: Spatial Intelligence
        spatial_states = spatial_engine.process_tracks(
            tracks=tracks,
            camera_id=pkt.camera_id,
            timestamp_utc=pkt.timestamp_utc,
        )

        # Layer 5: Behavioral Analytics
        behaviors = behavior_engine.process(
            tracks=tracks,
            spatial_states=spatial_states,
            timestamp_utc=pkt.timestamp_utc,
            environment_state=env_state,
        )

        # Layer 6: Multi-Modal Evidence Fusion
        events = fusion_engine.process(
            tracks=tracks,
            spatial_states=spatial_states,
            environment_state=env_state,
            behavior_primitives=behaviors,
            camera_id=pkt.camera_id,
            timestamp_utc=pkt.timestamp_utc,
        )

        if events:
            generated_events.extend(events)
        processed_frames += 1

    assert processed_frames == 30
    assert len(generated_events) > 0

    # Verify that an actionable EventRecord was produced
    latest_event = generated_events[-1]
    assert latest_event.camera_id == camera_id
    assert latest_event.target_class in (TargetClass.PERSON, TargetClass.UNKNOWN)
    assert latest_event.risk_score > 30.0
    assert len(latest_event.reason_codes) > 0
    assert len(latest_event.explanation_summary) > 10

    # Clean shutdown
    source.close()
    queue.close()
    detector.close()
    tracker.close()
    env_analyzer.close()
    spatial_engine.close()
    behavior_engine.close()
    fusion_engine.close()
