import pytest
import numpy as np
from datetime import datetime, timezone
from worker.perception import (
    ObjectDetector,
    DetectorInterface,
    Detection,
    BoundingBox,
    TargetClass,
    draw_detections,
    map_raw_class_to_target,
    InvalidInputError,
    ModelLoadError,
)
from worker.ingestion import FramePacket


def _create_frame(image: np.ndarray, frame_id: int = 0, camera_id: str = "cam_01") -> FramePacket:
    h, w = image.shape[:2]
    return FramePacket(
        camera_id=camera_id,
        frame_id=frame_id,
        timestamp_utc=datetime.now(timezone.utc),
        image=image,
        width=w,
        height=h,
        source_type="test",
    )


def test_class_mapping():
    assert map_raw_class_to_target("person") == TargetClass.PERSON
    assert map_raw_class_to_target("car") == TargetClass.VEHICLE
    assert map_raw_class_to_target("truck") == TargetClass.VEHICLE
    assert map_raw_class_to_target("motorcycle") == TargetClass.VEHICLE
    assert map_raw_class_to_target("dog") == TargetClass.ANIMAL
    assert map_raw_class_to_target("horse") == TargetClass.ANIMAL
    assert map_raw_class_to_target("toaster") == TargetClass.UNKNOWN


def test_detector_initialization():
    detector = ObjectDetector(model_name="yolov8n", confidence_threshold=0.40)
    meta = detector.get_metadata()
    assert meta["model_name"] == "yolov8n"
    assert meta["confidence_threshold"] == 0.40
    assert meta["is_loaded"] is False
    assert meta["device"] in ("cpu", "cuda:0")


def test_detector_load_and_warmup():
    detector = ObjectDetector(model_name="yolov8n")
    assert detector.load() is True
    assert detector.warmup(input_size=(320, 240)) is True

    meta = detector.get_metadata()
    assert meta["is_loaded"] is True
    assert meta["warmup_done"] is True
    detector.close()


def test_detector_infer_valid_frame():
    detector = ObjectDetector(model_name="yolov8n", confidence_threshold=0.25)
    detector.load()

    # Create synthetic test frame
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[100:300, 200:400] = (200, 200, 200)  # white patch
    pkt = _create_frame(img, frame_id=42, camera_id="cam_border_01")

    detections = detector.infer(pkt)
    assert isinstance(detections, list)

    meta = detector.get_metadata()
    assert meta["total_inferences"] == 1
    assert meta["average_latency_ms"] >= 0.0
    detector.close()


def test_detector_invalid_inputs():
    detector = ObjectDetector(model_name="yolov8n")
    detector.load()

    # None packet
    with pytest.raises(InvalidInputError):
        detector.infer(None)

    # Empty frame
    empty_pkt = FramePacket(
        camera_id="cam_01",
        frame_id=0,
        timestamp_utc=datetime.now(timezone.utc),
        image=np.array([], dtype=np.uint8),
        width=0,
        height=0,
    )
    with pytest.raises(InvalidInputError):
        detector.infer(empty_pkt)

    detector.close()


def test_detector_invalid_model_path():
    detector = ObjectDetector(model_name="invalid_model", model_path="non_existent_weights_xyz.pt")
    with pytest.raises(ModelLoadError):
        detector.load()


def test_visualizer_drawing():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    det = Detection(
        camera_id="cam_01",
        frame_id=1,
        class_id=TargetClass.PERSON,
        confidence=0.92,
        bbox=BoundingBox(x_min=50.0, y_min=50.0, x_max=150.0, y_max=250.0),
        metadata={"raw_class_name": "person"},
    )

    annotated = draw_detections(img, [det])
    assert annotated.shape == img.shape
    # Check that image was annotated without mutating original zero array
    assert np.max(annotated) > 0
    assert np.max(img) == 0
