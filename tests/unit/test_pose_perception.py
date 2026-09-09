"""
Unit Tests for YOLO26 Pose Optional Perception Capability.

Verifies:
1. Human pose schemas with all 17 COCO keypoints:
   nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles.
2. Model-agnostic parse_human_pose adapter function.
3. Central registry resolution for yolo26-pose and yolov8-pose.
4. Graceful error handling on missing weights (ModelNotFoundError).
5. Seamless propagation of HumanPose through ByteTrack (STrack -> TrackState).
6. Non-breaking compatibility for existing object detection pipeline.
7. Forensic visualization of skeletons without corrupting frames.
"""

import numpy as np
import pytest
from datetime import datetime, timezone

from backend.app.schemas.common import TargetClass, TrackStatus
from backend.app.schemas.events import (
    BoundingBox,
    Detection,
    TrackState,
    PoseKeypoint,
    HumanPose,
    COCO_POSE_KEYPOINTS,
    SKELETON_CONNECTIONS,
)
from worker.perception.detector import (
    parse_human_pose,
    YOLO26PoseDetector,
    YOLOv8PoseDetector,
    MockDetector,
)
from worker.perception.registry import get_detector, list_available_detectors
from worker.perception.config import resolve_model_config
from worker.perception.exceptions import ModelNotFoundError
from worker.perception.visualizer import draw_human_pose, draw_detections
from worker.tracking.tracker import ByteTrackTracker
from worker.ingestion.frame import FramePacket


def test_human_pose_schema_and_named_joints():
    """Verifies that all 17 COCO joints are accessible as typed properties."""
    kps = {}
    for idx, name in enumerate(COCO_POSE_KEYPOINTS):
        kps[name] = PoseKeypoint(
            name=name,
            x=100.0 + idx * 5.0,
            y=150.0 + idx * 8.0,
            confidence=0.85 + (idx * 0.005),
            visible=True,
        )

    pose = HumanPose(
        keypoints=kps,
        confidence=0.90,
        num_keypoints=len(kps),
    )

    # 1. Head
    assert pose.nose is not None
    assert pose.nose.name == "nose"
    assert pose.nose.x == 100.0
    assert pose.left_eye is not None and pose.right_eye is not None
    assert pose.left_ear is not None and pose.right_ear is not None

    # 2. Upper body
    assert pose.left_shoulder is not None and pose.right_shoulder is not None
    assert pose.left_elbow is not None and pose.right_elbow is not None
    assert pose.left_wrist is not None and pose.right_wrist is not None

    # 3. Lower body
    assert pose.left_hip is not None and pose.right_hip is not None
    assert pose.left_knee is not None and pose.right_knee is not None
    assert pose.left_ankle is not None and pose.right_ankle is not None

    assert pose.num_keypoints == 17
    assert len(SKELETON_CONNECTIONS) == 16


def test_parse_human_pose_from_raw_arrays():
    """Verifies that parse_human_pose converts raw (17, 3) arrays into HumanPose."""
    # (17, 3) where each row is [x, y, confidence]
    raw_array = np.zeros((17, 3), dtype=np.float32)
    for i in range(17):
        raw_array[i] = [50.0 + i, 100.0 + i, 0.80]

    parsed = parse_human_pose(raw_array)
    assert parsed is not None
    assert isinstance(parsed, HumanPose)
    assert parsed.num_keypoints == 17
    assert parsed.left_shoulder.x == 55.0
    assert parsed.left_shoulder.confidence == 0.80
    assert parsed.left_shoulder.visible is True

    # Test None / empty input
    assert parse_human_pose(None) is None
    assert parse_human_pose([]) is None


def test_yolo26_pose_registry_and_instantiation():
    """Verifies registry resolves and instantiates YOLO26PoseDetector."""
    det = get_detector("yolo26-pose")
    assert isinstance(det, YOLO26PoseDetector)
    assert det.model_type == "yolo26-pose"

    det8 = get_detector("yolov8-pose")
    assert isinstance(det8, YOLOv8PoseDetector)
    assert det8.model_type == "yolov8-pose"

    available = list_available_detectors()
    assert "yolo26-pose" in available
    assert "yolov8-pose" in available


def test_yolo26_pose_missing_weights_graceful_error():
    """Verifies that missing weights file raises ModelNotFoundError clearly."""
    det = YOLO26PoseDetector(model_path="nonexistent_custom_yolo26_pose.pt")
    with pytest.raises(ModelNotFoundError) as exc_info:
        det.load()
    assert "not found" in str(exc_info.value).lower()


def test_pose_propagation_through_bytetrack():
    """
    Verifies that optional pose keypoints flow seamlessly from Detection
    into ByteTrack STrack and are preserved in TrackState.
    """
    tracker = ByteTrackTracker(camera_id="cam-01", min_hits=1)

    # Build a detection with pose
    raw_kps = np.ones((17, 3), dtype=np.float32) * 120.0
    pose = parse_human_pose(raw_kps)

    det = Detection(
        camera_id="cam-01",
        frame_id=1,
        timestamp_utc=datetime.now(timezone.utc),
        class_id=TargetClass.PERSON,
        class_name="person",
        confidence=0.92,
        bbox=BoundingBox(x_min=100.0, y_min=100.0, x_max=200.0, y_max=300.0),
        keypoints=pose,
    )

    # First update: creates active track since min_hits=1
    tracks_1 = tracker.update([det], frame_id=1, timestamp_utc=det.timestamp_utc, camera_id="cam-01")
    assert len(tracks_1) == 1
    assert tracks_1[0].keypoints is not None
    assert tracks_1[0].keypoints.num_keypoints == 17
    assert tracks_1[0].keypoints.nose.x == 120.0

    # Second update: confirmed active track updated with new keypoints
    raw_kps_2 = np.ones((17, 3), dtype=np.float32) * 135.0
    pose_2 = parse_human_pose(raw_kps_2)
    det2 = det.model_copy(update={"frame_id": 2, "keypoints": pose_2})
    tracks_2 = tracker.update([det2], frame_id=2, timestamp_utc=det2.timestamp_utc, camera_id="cam-01")
    assert len(tracks_2) == 1
    track_state = tracks_2[0]
    assert isinstance(track_state, TrackState)
    assert track_state.keypoints is not None
    assert track_state.keypoints.num_keypoints == 17
    assert track_state.keypoints.nose.x == 135.0


def test_normal_detection_pipeline_unaffected():
    """
    Verifies that normal object detection without pose continues operating
    with identical behavior and keypoints = None.
    """
    tracker = ByteTrackTracker(camera_id="cam-01", min_hits=1)

    det_no_pose = Detection(
        camera_id="cam-01",
        frame_id=1,
        timestamp_utc=datetime.now(timezone.utc),
        class_id=TargetClass.PERSON,
        class_name="person",
        confidence=0.88,
        bbox=BoundingBox(x_min=50.0, y_min=50.0, x_max=150.0, y_max=250.0),
        keypoints=None,
    )

    tracks = tracker.update([det_no_pose], frame_id=1, timestamp_utc=det_no_pose.timestamp_utc, camera_id="cam-01")
    assert len(tracks) == 1
    assert tracks[0].keypoints is None


def test_pose_visualization_rendering():
    """Verifies that draw_human_pose and draw_detections render skeleton overlays cleanly."""
    canvas = np.zeros((480, 640, 3), dtype=np.uint8)

    raw_kps = np.zeros((17, 3), dtype=np.float32)
    # Head
    raw_kps[0] = [320.0, 100.0, 0.9]  # nose
    raw_kps[1] = [315.0, 95.0, 0.9]   # left_eye
    raw_kps[2] = [325.0, 95.0, 0.9]   # right_eye
    # Shoulders
    raw_kps[5] = [280.0, 150.0, 0.9]  # left_shoulder
    raw_kps[6] = [360.0, 150.0, 0.9]  # right_shoulder
    # Elbows
    raw_kps[7] = [260.0, 200.0, 0.9]  # left_elbow
    raw_kps[8] = [380.0, 200.0, 0.9]  # right_elbow
    # Wrists
    raw_kps[9] = [250.0, 250.0, 0.9]  # left_wrist
    raw_kps[10] = [390.0, 250.0, 0.9] # right_wrist
    # Hips
    raw_kps[11] = [300.0, 280.0, 0.9] # left_hip
    raw_kps[12] = [340.0, 280.0, 0.9] # right_hip
    # Knees
    raw_kps[13] = [295.0, 350.0, 0.9] # left_knee
    raw_kps[14] = [345.0, 350.0, 0.9] # right_knee
    # Ankles
    raw_kps[15] = [290.0, 420.0, 0.9] # left_ankle
    raw_kps[16] = [350.0, 420.0, 0.9] # right_ankle

    pose = parse_human_pose(raw_kps)
    annotated = draw_human_pose(canvas.copy(), pose)

    # Ensure pixels were modified (skeleton drawn)
    assert np.any(annotated > 0)

    # Test draw_detections with pose
    det = Detection(
        camera_id="cam-01",
        frame_id=1,
        timestamp_utc=datetime.now(timezone.utc),
        class_id=TargetClass.PERSON,
        class_name="person",
        confidence=0.95,
        bbox=BoundingBox(x_min=240.0, y_min=80.0, x_max=400.0, y_max=440.0),
        keypoints=pose,
    )
    det_annotated = draw_detections(canvas.copy(), [det])
    assert np.any(det_annotated > 0)
