import os
import cv2
import pytest
import numpy as np
from worker.ingestion import FileVideoSource, BoundedFrameQueue
from worker.perception import ObjectDetector, draw_detections, Detection


@pytest.fixture
def detector_test_clip(tmp_path):
    """Generates a 15-frame 320x240 synthetic video clip for perception pipeline testing."""
    clip_path = str(tmp_path / "det_replay_15frames.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(clip_path, fourcc, 15.0, (320, 240))

    for i in range(15):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        # Draw moving circle/rectangle across frames
        center_x = 50 + i * 15
        cv2.circle(frame, (center_x, 120), 30, (255, 255, 255), -1)
        out.write(frame)

    out.release()
    yield clip_path

    if os.path.exists(clip_path):
        try:
            os.remove(clip_path)
        except Exception:
            pass


def test_detector_replay_pipeline(detector_test_clip):
    """
    Validates the end-to-end perception flow:
    Video File -> FileVideoSource -> BoundedFrameQueue -> ObjectDetector -> Detection output -> Annotation.
    """
    source = FileVideoSource(camera_id="cam_det_test", file_path=detector_test_clip, loop=False)
    queue = BoundedFrameQueue(max_size=30)
    detector = ObjectDetector(model_name="yolov8n", confidence_threshold=0.20)

    assert source.connect() is True
    assert detector.load() is True
    assert detector.warmup(input_size=(320, 240)) is True

    # Ingest all frames
    frame_count = 0
    while True:
        pkt = source.read()
        if pkt is None:
            break
        queue.put(pkt)
        frame_count += 1

    assert frame_count == 15
    assert queue.size() == 15

    # Process all frames through detector
    processed_count = 0
    while not queue.is_empty():
        pkt = queue.get(timeout=0.1)
        if pkt is None:
            break

        detections = detector.infer(pkt)
        assert isinstance(detections, list)

        # Verify each detection structure if any are found
        for det in detections:
            assert det.camera_id == "cam_det_test"
            assert det.frame_id == pkt.frame_id
            assert 0.0 <= det.confidence <= 1.0
            assert det.bbox.x_min >= 0.0
            assert det.bbox.y_min >= 0.0

        annotated = draw_detections(pkt.image, detections)
        assert annotated.shape == (240, 320, 3)

        processed_count += 1

    assert processed_count == 15
    source.close()
    queue.close()
    detector.close()
