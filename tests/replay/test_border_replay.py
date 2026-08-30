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
from worker.spatial import (
    SpatialEngine,
    BorderSection,
    CameraRegistration,
    CameraCalibration,
    CalibrationCorrespondence,
    WorldPoint,
    BorderSide,
    CrossingStatus,
)
from worker.behavior import BehaviorEngine, BehaviorConfig, BehaviorPrimitive


@pytest.fixture
def border_test_clip(tmp_path):
    """Generates a 30-frame synthetic test video where a target moves from permitted to restricted across a calibrated world border."""
    clip_path = str(tmp_path / "border_replay_30frames.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(clip_path, fourcc, 25.0, (640, 480))

    # Move from top (permitted, world y ~ 80, image y ~ 100)
    # toward bottom (restricted, world y ~ 20, image y ~ 380)
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


def test_full_pipeline_with_world_border_model(border_test_clip):
    """
    End-to-end multi-layer pipeline test:
    Ingestion -> Perception -> Tracking -> Environment -> Spatial (World-Border Calibrated) -> Behavior
    """
    source = FileVideoSource(camera_id="cam_border_replay", file_path=border_test_clip, loop=False)
    queue = BoundedFrameQueue(max_size=30)
    detector = ObjectDetector(model_name="yolov8n", confidence_threshold=0.15)
    tracker = ByteTrackTracker(camera_id="cam_border_replay", min_hits=1, max_lost_frames=10)
    env_analyzer = EnvironmentAnalyzer()

    # Spatial Engine with World-Border Model
    spatial_engine = SpatialEngine(crossing_confirmation_frames=2)

    # 1. Register World Border Section at world y=50 (horizontal boundary)
    # Permitted side is +y (world y > 50, image y < 240)
    # Restricted side is -y (world y < 50, image y > 240)
    border_section = BorderSection(
        id="section_alpha",
        name="Border Section Alpha",
        points=[WorldPoint(x=0, y=50), WorldPoint(x=100, y=50)],
        permitted_side_normal=(0.0, 1.0),
        warning_buffer_distance=5.0,
    )
    spatial_engine.register_border_section(border_section)

    # 2. Register Camera
    camera_reg = CameraRegistration(
        camera_id="cam_border_replay",
        visible_border_sections=["section_alpha"],
    )
    spatial_engine.register_camera(camera_reg)

    # 3. Register Camera Calibration (mapping 100x100 world box to 640x480 frame)
    # Note: image y increases downward, so world y=100 -> image y=50 (top), world y=0 -> image y=430 (bottom)
    calibration = CameraCalibration(
        camera_id="cam_border_replay",
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

    # 4. Behavior Engine
    behavior_engine = BehaviorEngine(default_config=BehaviorConfig(loitering_seconds=1.0, persistent_approach_seconds=0.5))

    assert source.connect() is True
    assert detector.load() is True

    ingest_count = 0
    while True:
        pkt = source.read()
        if pkt is None:
            break
        queue.put(pkt)
        ingest_count += 1

    assert ingest_count == 30

    processed_frames = 0
    all_spatial_states = []
    all_behaviors: List[BehaviorPrimitive] = []

    while not queue.is_empty():
        pkt = queue.get(timeout=0.1)
        if pkt is None:
            break

        env_state = env_analyzer.analyze(pkt)
        detections = detector.infer(pkt)
        tracks = tracker.update(
            detections=detections,
            frame_id=pkt.frame_id,
            timestamp_utc=pkt.timestamp_utc,
            camera_id=pkt.camera_id,
        )
        spatial_states = spatial_engine.process_tracks(
            tracks=tracks,
            camera_id=pkt.camera_id,
            timestamp_utc=pkt.timestamp_utc,
        )
        primitives = behavior_engine.process(
            tracks=tracks,
            spatial_states=spatial_states,
            timestamp_utc=pkt.timestamp_utc,
            environment_state=env_state,
        )

        all_spatial_states.extend(spatial_states)
        all_behaviors.extend(primitives)
        processed_frames += 1

    assert processed_frames == 30
    assert len(all_spatial_states) > 0

    # Verify that world border side transitions were recorded
    sides_observed = {st.border_side for st in all_spatial_states if st.border_side is not None}
    assert BorderSide.PERMITTED in sides_observed or BorderSide.WARNING_BUFFER in sides_observed
    assert BorderSide.RESTRICTED in sides_observed

    # Verify crossing detection occurred
    crossing_statuses = {st.crossing_status for st in all_spatial_states}
    assert CrossingStatus.CONFIRMED_CROSSING in crossing_statuses

    source.close()
    queue.close()
    detector.close()
    tracker.close()
    env_analyzer.close()
    spatial_engine.close()
    behavior_engine.close()
