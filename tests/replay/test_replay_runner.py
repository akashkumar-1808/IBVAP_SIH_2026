import os
import time
import pytest
import cv2
import numpy as np
from worker.ingestion import FileVideoSource, BoundedFrameQueue, FramePacket


@pytest.fixture
def replay_video_clip(tmp_path):
    """Creates a 30-frame synthetic MP4 clip for replay pipeline validation."""
    clip_path = str(tmp_path / "replay_clip_30frames.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(clip_path, fourcc, 30.0, (320, 240))

    for i in range(30):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(frame, f"Seq {i}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        out.write(frame)

    out.release()
    yield clip_path

    if os.path.exists(clip_path):
        try:
            os.remove(clip_path)
        except Exception:
            pass


def test_replay_pipeline_end_to_end(replay_video_clip):
    """
    End-to-end replay pipeline test:
    FileVideoSource -> BoundedFrameQueue -> Consumer -> Verify sequence & metrics.
    """
    source = FileVideoSource(
        camera_id="cam_replay_01",
        file_path=replay_video_clip,
        loop=False,
    )
    queue = BoundedFrameQueue(max_size=50)

    assert source.connect() is True

    # Ingestion producer loop
    ingested_count = 0
    while True:
        pkt = source.read()
        if pkt is None:
            break
        queue.put(pkt)
        ingested_count += 1

    assert ingested_count == 30
    assert queue.size() == 30

    # Analytics consumer simulation loop
    consumed_frames = []
    while not queue.is_empty():
        pkt = queue.get(timeout=0.1)
        if pkt is not None:
            consumed_frames.append(pkt)

    assert len(consumed_frames) == 30
    for seq_idx, frame in enumerate(consumed_frames):
        assert frame.frame_id == seq_idx
        assert frame.camera_id == "cam_replay_01"
        assert frame.width == 320
        assert frame.height == 240

    source.close()
    queue.close()
