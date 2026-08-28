import os
import cv2
import pytest
import numpy as np
from worker.ingestion import FileVideoSource, BoundedFrameQueue
from worker.perception import ObjectDetector
from worker.tracking import ByteTrackTracker
from worker.spatial import (
    SpatialEngine,
    CameraSpatialConfig,
    ZonePolygon,
    VirtualFence,
    ZoneType,
    draw_spatial_overlay,
    SpatialState,
)


@pytest.fixture
def spatial_test_clip(tmp_path):
    """Generates a 25-frame 320x240 video clip moving across a virtual boundary."""
    clip_path = str(tmp_path / "spatial_replay_25frames.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(clip_path, fourcc, 25.0, (320, 240))

    for i in range(25):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        # Moving object across x=50 to x=250
        cx = int(50 + i * 8)
        cy = 120
        cv2.circle(frame, (cx, cy), 20, (255, 255, 255), -1)
        out.write(frame)

    out.release()
    yield clip_path

    if os.path.exists(clip_path):
        try:
            os.remove(clip_path)
        except Exception:
            pass


def test_full_pipeline_to_spatial_engine(spatial_test_clip):
    """
    End-to-end multi-layer pipeline:
    Phase 2 (FileVideoSource + BoundedFrameQueue)
      ↓
    Phase 3 (ObjectDetector -> Detection[])
      ↓
    Phase 4 (ByteTrackTracker -> TrackState[])
      ↓
    Phase 6 (SpatialEngine -> SpatialState[])
      ↓
    Debug Overlay (draw_spatial_overlay)
    """
    source = FileVideoSource(camera_id="cam_spatial_replay", file_path=spatial_test_clip, loop=False)
    queue = BoundedFrameQueue(max_size=30)
    detector = ObjectDetector(model_name="yolov8n", confidence_threshold=0.15)
    tracker = ByteTrackTracker(camera_id="cam_spatial_replay", min_hits=1, max_lost_frames=10)
    spatial_engine = SpatialEngine()

    # Configure Spatial Zones & Fences for this camera
    spatial_config = CameraSpatialConfig(
        camera_id="cam_spatial_replay",
        zones=[
            ZonePolygon(id="zone_safe", name="Safe Area", type=ZoneType.SAFE, polygon=[(0, 0), (160, 0), (160, 240), (0, 240)]),
            ZonePolygon(id="zone_restricted", name="Restricted Zone", type=ZoneType.RESTRICTED, polygon=[(160, 0), (320, 0), (320, 240), (160, 240)]),
        ],
        fences=[
            VirtualFence(id="fence_mid", name="Center Barrier", start_point=(160.0, 0.0), end_point=(160.0, 240.0)),
        ],
        expected_threat_vector=(1.0, 0.0),
    )
    spatial_engine.configure_camera(spatial_config)

    assert source.connect() is True
    assert detector.load() is True
    assert detector.warmup((320, 240)) is True

    # Ingest frames into bounded queue
    ingest_count = 0
    while True:
        pkt = source.read()
        if pkt is None:
            break
        queue.put(pkt)
        ingest_count += 1

    assert ingest_count == 25

    # Process all frames through complete stack
    processed_count = 0
    while not queue.is_empty():
        pkt = queue.get(timeout=0.1)
        if pkt is None:
            break

        # 1. Perception
        detections = detector.infer(pkt)

        # 2. Tracking
        tracks = tracker.update(
            detections=detections,
            frame_id=pkt.frame_id,
            timestamp_utc=pkt.timestamp_utc,
            camera_id=pkt.camera_id,
        )

        # 3. Spatial Intelligence
        spatial_states = spatial_engine.process_tracks(
            tracks=tracks,
            camera_id=pkt.camera_id,
            timestamp_utc=pkt.timestamp_utc,
        )

        assert isinstance(spatial_states, list)

        # 4. Visualization
        annotated = draw_spatial_overlay(pkt.image, spatial_config, spatial_states)
        assert annotated.shape == (240, 320, 3)

        processed_count += 1

    assert processed_count == 25

    source.close()
    queue.close()
    detector.close()
    tracker.close()
    spatial_engine.close()
