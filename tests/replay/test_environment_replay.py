import os
import cv2
import pytest
import numpy as np
from worker.ingestion import FileVideoSource, BoundedFrameQueue
from worker.environment import EnvironmentAnalyzer, EnvironmentState


@pytest.fixture
def env_test_clip(tmp_path):
    """Generates a 15-frame 320x240 video clip transitioning from dark to bright."""
    clip_path = str(tmp_path / "env_replay_15frames.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(clip_path, fourcc, 15.0, (320, 240))

    for i in range(15):
        lum = int(20 + i * 14)  # 20 up to 216
        frame = np.full((240, 320, 3), lum, dtype=np.uint8)
        # Add some edges
        cv2.putText(frame, f"Frame {i}", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        out.write(frame)

    out.release()
    yield clip_path

    if os.path.exists(clip_path):
        try:
            os.remove(clip_path)
        except Exception:
            pass


def test_environment_replay_pipeline(env_test_clip):
    """
    End-to-end replay pipeline test:
    FileVideoSource -> BoundedFrameQueue -> EnvironmentAnalyzer -> EnvironmentState verification.
    """
    source = FileVideoSource(camera_id="cam_env_test", file_path=env_test_clip, loop=False)
    queue = BoundedFrameQueue(max_size=30)
    analyzer = EnvironmentAnalyzer()

    assert source.connect() is True

    # Ingest frames
    ingest_count = 0
    while True:
        pkt = source.read()
        if pkt is None:
            break
        queue.put(pkt)
        ingest_count += 1

    assert ingest_count == 15
    assert queue.size() == 15

    # Process all frames through EnvironmentAnalyzer
    processed_count = 0
    states = []
    while not queue.is_empty():
        pkt = queue.get(timeout=0.1)
        if pkt is None:
            break

        state = analyzer.analyze(pkt)
        assert isinstance(state, EnvironmentState)
        assert state.camera_id == "cam_env_test"
        assert 0.0 <= state.brightness <= 1.0
        assert 0.0 <= state.contrast <= 1.0
        assert state.blur_score >= 0.0
        assert 0.0 <= state.quality_score <= 1.0

        states.append(state)
        processed_count += 1

    assert processed_count == 15
    # First frame should be darker than last frame due to synthetic brightness ramp
    assert states[0].brightness < states[-1].brightness

    source.close()
    queue.close()
    analyzer.close()
