import os
import cv2
import pytest
import numpy as np
from typing import List
from datetime import datetime, timezone, timedelta

from worker.ingestion import FileVideoSource, BoundedFrameQueue
from worker.perception import ObjectDetector
from worker.tracking import ByteTrackTracker
from worker.environment import EnvironmentAnalyzer
from worker.spatial import SpatialEngine, CameraSpatialConfig, ZonePolygon, VirtualFence, ZoneType
from worker.behavior import BehaviorEngine, BehaviorConfig, BehaviorPrimitive


@pytest.fixture
def behavior_test_clip(tmp_path):
    """Generates a 30-frame synthetic test video moving into a restricted zone."""
    clip_path = str(tmp_path / "behavior_replay_30frames.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(clip_path, fourcc, 25.0, (320, 240))

    for i in range(30):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        # Stationary target inside restricted zone (x=200, y=120)
        cx = 200
        cy = 120
        cv2.circle(frame, (cx, cy), 18, (255, 255, 255), -1)
        out.write(frame)

    out.release()
    yield clip_path

    if os.path.exists(clip_path):
        try:
            os.remove(clip_path)
        except Exception:
            pass


def test_full_pipeline_to_behavior_engine(behavior_test_clip):
    """
    End-to-end multi-layer pipeline:
    Phase 2 (Ingestion) -> Phase 3 (Detector) -> Phase 4 (Tracker) -> Phase 5 (Environment) -> Phase 6 (Spatial) -> Phase 7 (Behavior)
    """
    source = FileVideoSource(camera_id="cam_beh_replay", file_path=behavior_test_clip, loop=False)
    queue = BoundedFrameQueue(max_size=30)
    detector = ObjectDetector(model_name="yolov8n", confidence_threshold=0.15)
    tracker = ByteTrackTracker(camera_id="cam_beh_replay", min_hits=1, max_lost_frames=10)
    env_analyzer = EnvironmentAnalyzer()
    spatial_engine = SpatialEngine()
    behavior_engine = BehaviorEngine(default_config=BehaviorConfig(loitering_seconds=0.5, persistent_approach_seconds=0.5))

    # Spatial configuration
    spatial_config = CameraSpatialConfig(
        camera_id="cam_beh_replay",
        zones=[
            ZonePolygon(id="zone_restricted", name="Target Zone", type=ZoneType.RESTRICTED, polygon=[(100, 50), (300, 50), (300, 200), (100, 200)]),
        ],
        expected_threat_vector=(1.0, 0.0),
    )
    spatial_engine.configure_camera(spatial_config)

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
    all_behaviors: List[BehaviorPrimitive] = []

    while not queue.is_empty():
        pkt = queue.get(timeout=0.1)
        if pkt is None:
            break

        # 1. Environment
        env_state = env_analyzer.analyze(pkt)

        # 2. Perception
        detections = detector.infer(pkt)

        # 3. Tracking
        tracks = tracker.update(
            detections=detections,
            frame_id=pkt.frame_id,
            timestamp_utc=pkt.timestamp_utc,
            camera_id=pkt.camera_id,
        )

        # 4. Spatial Intelligence
        spatial_states = spatial_engine.process_tracks(
            tracks=tracks,
            camera_id=pkt.camera_id,
            timestamp_utc=pkt.timestamp_utc,
        )

        # 5. Behavioral Analytics
        primitives = behavior_engine.process(
            tracks=tracks,
            spatial_states=spatial_states,
            timestamp_utc=pkt.timestamp_utc,
            environment_state=env_state,
        )

        all_behaviors.extend(primitives)
        processed_frames += 1

    assert processed_frames == 30
    # Must have generated restricted occupancy primitives
    assert len(all_behaviors) > 0
    assert any(b.behavior_type.value == "restricted_occupancy" for b in all_behaviors)

    source.close()
    queue.close()
    detector.close()
    tracker.close()
    env_analyzer.close()
    spatial_engine.close()
    behavior_engine.close()
