import os
import pytest
import cv2
import numpy as np
from datetime import datetime, timezone, timedelta
from worker.ingestion import FileVideoSource, VideoFileNotFoundError


@pytest.fixture
def sample_video_file(tmp_path):
    """Generates a small 10-frame 640x480 test MP4 video using OpenCV."""
    video_path = str(tmp_path / "test_sample.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(video_path, fourcc, 10.0, (640, 480))

    for i in range(10):
        # Create solid color frame with frame index text
        frame = np.full((480, 640, 3), (i * 20, 100, 150), dtype=np.uint8)
        cv2.putText(frame, f"Frame {i}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        out.write(frame)

    out.release()
    yield video_path

    if os.path.exists(video_path):
        try:
            os.remove(video_path)
        except Exception:
            pass


def test_file_video_source_missing_file():
    source = FileVideoSource(camera_id="cam_test", file_path="non_existent_file.mp4")
    with pytest.raises(VideoFileNotFoundError):
        source.connect()


def test_file_video_source_reading_in_order(sample_video_file):
    start_time = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    source = FileVideoSource(
        camera_id="cam_01",
        file_path=sample_video_file,
        loop=False,
        start_time_utc=start_time,
    )

    assert source.connect() is True
    assert source.is_alive() is True

    frames = []
    while True:
        pkt = source.read()
        if pkt is None:
            break
        frames.append(pkt)

    assert len(frames) == 10

    # Verify monotonic frame IDs and proper metadata
    for idx, pkt in enumerate(frames):
        assert pkt.frame_id == idx
        assert pkt.camera_id == "cam_01"
        assert pkt.width == 640
        assert pkt.height == 480
        assert pkt.source_type == "file"
        # Deterministic timestamp progression: 10 FPS -> 0.1s per frame
        expected_time = start_time + timedelta(seconds=idx * 0.1)
        assert pkt.timestamp_utc == expected_time

    assert source.is_alive() is False
    source.close()


def test_file_video_source_looping(sample_video_file):
    source = FileVideoSource(
        camera_id="cam_loop",
        file_path=sample_video_file,
        loop=True,
    )
    source.connect()

    # Read 25 frames from a 10-frame video -> should loop and assign monotonic frame_id
    frames = []
    for _ in range(25):
        pkt = source.read()
        assert pkt is not None
        frames.append(pkt)

    assert len(frames) == 25
    assert frames[0].frame_id == 0
    assert frames[24].frame_id == 24
    source.close()
