import os
import cv2
import pytest
import numpy as np
from worker.ingestion import FileVideoSource, BoundedFrameQueue
from worker.perception import ObjectDetector
from worker.tracking import ByteTrackTracker, draw_tracks, TrackState


@pytest.fixture
def tracking_test_clip(tmp_path):
    """Generates a 20-frame 320x240 video clip with a moving synthetic circle."""
    clip_path = str(tmp_path / "track_replay_20frames.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(clip_path, fourcc, 20.0, (320, 240))

    for i in range(20):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        # Moving circle from x=40 to x=220
        cx = int(40 + i * 9)
        cy = 120
        cv2.circle(frame, (cx, cy), 25, (255, 255, 255), -1)
        out.write(frame)

    out.release()
    yield clip_path

    if os.path.exists(clip_path):
        try:
            os.remove(clip_path)
        except Exception:
            pass


def test_full_pipeline_replay_to_tracker(tracking_test_clip):
    """
    End-to-end multi-phase integration:
    Phase 2 (FileVideoSource + BoundedFrameQueue)
      ↓
    Phase 3 (ObjectDetector -> Detection[])
      ↓
    Phase 4 (ByteTrackTracker -> TrackState[])
      ↓
    Debug Visualization (draw_tracks)
    """
    source = FileVideoSource(camera_id="cam_track_test", file_path=tracking_test_clip, loop=False)
    queue = BoundedFrameQueue(max_size=30)
    detector = ObjectDetector(model_name="yolov8n", confidence_threshold=0.15)
    tracker = ByteTrackTracker(camera_id="cam_track_test", min_hits=1, max_lost_frames=10)

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

    assert ingest_count == 20
    assert queue.size() == 20

    # Process all frames through detector + tracker
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

        assert isinstance(tracks, list)

        # 3. Visualization
        annotated = draw_tracks(pkt.image, tracks)
        assert annotated.shape == (240, 320, 3)

        processed_count += 1

    assert processed_count == 20

    source.close()
    queue.close()
    detector.close()
    tracker.close()
