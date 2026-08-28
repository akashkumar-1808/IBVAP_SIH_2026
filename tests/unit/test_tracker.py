import pytest
from datetime import datetime, timezone, timedelta
import numpy as np

from worker.tracking import (
    ByteTrackTracker,
    TrackStatus,
    TargetClass,
    BoundingBox,
    Detection,
    draw_tracks,
    InvalidDetectionError,
)


def _make_det(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    conf: float = 0.85,
    cls: TargetClass = TargetClass.PERSON,
    frame_id: int = 0,
    camera_id: str = "cam_01",
    ts: datetime = None,
) -> Detection:
    return Detection(
        camera_id=camera_id,
        frame_id=frame_id,
        timestamp_utc=ts or datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc),
        class_id=cls,
        confidence=conf,
        bbox=BoundingBox(x_min=x1, y_min=y1, x_max=x2, y_max=y2),
    )


def test_tracker_initialization():
    tracker = ByteTrackTracker(camera_id="cam_01", min_hits=2, max_lost_frames=10)
    assert tracker.camera_id == "cam_01"
    assert len(tracker.get_tracks()) == 0


def test_new_track_creation_and_confirmation():
    tracker = ByteTrackTracker(camera_id="cam_01", min_hits=2)
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Frame 0: New detection -> Candidate track
    d0 = _make_det(100, 100, 150, 200, conf=0.90, frame_id=0, ts=t0)
    tracks_f0 = tracker.update([d0], frame_id=0, timestamp_utc=t0)
    assert len(tracks_f0) == 1
    assert tracks_f0[0].status == TrackStatus.CANDIDATE
    track_id = tracks_f0[0].track_id

    # Frame 1: Associated detection -> Promoted to Tracked
    t1 = t0 + timedelta(milliseconds=33)
    d1 = _make_det(102, 101, 152, 201, conf=0.92, frame_id=1, ts=t1)
    tracks_f1 = tracker.update([d1], frame_id=1, timestamp_utc=t1)
    assert len(tracks_f1) == 1
    assert tracks_f1[0].track_id == track_id
    assert tracks_f1[0].status == TrackStatus.TRACKED
    assert tracks_f1[0].age_frames == 2


def test_multi_object_tracking_persistence():
    tracker = ByteTrackTracker(camera_id="cam_01", min_hits=1)
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Frame 0: Person A, Person B, Vehicle C
    dA0 = _make_det(50, 50, 90, 150, cls=TargetClass.PERSON, frame_id=0, ts=t0)
    dB0 = _make_det(200, 200, 240, 300, cls=TargetClass.PERSON, frame_id=0, ts=t0)
    dC0 = _make_det(400, 100, 550, 250, cls=TargetClass.VEHICLE, frame_id=0, ts=t0)

    tracks0 = tracker.update([dA0, dB0, dC0], frame_id=0, timestamp_utc=t0)
    assert len(tracks0) == 3
    id_map = {t.bbox.x_min: t.track_id for t in tracks0}

    # Frame 1: Slightly moved objects
    t1 = t0 + timedelta(milliseconds=33)
    dA1 = _make_det(52, 51, 92, 151, cls=TargetClass.PERSON, frame_id=1, ts=t1)
    dB1 = _make_det(202, 201, 242, 301, cls=TargetClass.PERSON, frame_id=1, ts=t1)
    dC1 = _make_det(405, 102, 555, 252, cls=TargetClass.VEHICLE, frame_id=1, ts=t1)

    tracks1 = tracker.update([dA1, dB1, dC1], frame_id=1, timestamp_utc=t1)
    assert len(tracks1) == 3
    # Check ID persistence
    for t in tracks1:
        if t.class_id == TargetClass.VEHICLE:
            assert t.bbox.x_min > 390
        assert t.status == TrackStatus.TRACKED


def test_missed_detection_and_expiration():
    tracker = ByteTrackTracker(camera_id="cam_01", min_hits=1, max_lost_frames=3)
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Frame 0: Detection exists -> Tracked
    d0 = _make_det(100, 100, 150, 200, conf=0.90, frame_id=0, ts=t0)
    tracks0 = tracker.update([d0], frame_id=0, timestamp_utc=t0)
    assert tracks0[0].status == TrackStatus.TRACKED

    # Frame 1: Missed -> Transitions to Lost
    t1 = t0 + timedelta(milliseconds=33)
    tracks1 = tracker.update([], frame_id=1, timestamp_utc=t1)
    assert len(tracks1) == 1
    assert tracks1[0].status == TrackStatus.LOST
    assert tracks1[0].consecutive_invisible_frames == 1

    # Frame 2 & 3: Still missed
    tracker.update([], frame_id=2, timestamp_utc=t0 + timedelta(milliseconds=66))
    tracker.update([], frame_id=3, timestamp_utc=t0 + timedelta(milliseconds=99))

    # Frame 4: Exceeds max_lost_frames (3) -> Expired and pruned
    tracks4 = tracker.update([], frame_id=4, timestamp_utc=t0 + timedelta(milliseconds=132))
    assert len(tracks4) == 0


def test_trajectory_and_velocity_calculation():
    tracker = ByteTrackTracker(camera_id="cam_01", min_hits=1, max_trajectory_length=10)
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Initial frame
    d0 = _make_det(100, 100, 200, 200, frame_id=0, ts=t0)  # center = (150, 150)
    tracker.update([d0], frame_id=0, timestamp_utc=t0)

    # 1 second later: moved +50px X, +0px Y
    t1 = t0 + timedelta(seconds=1.0)
    d1 = _make_det(150, 100, 250, 200, frame_id=1, ts=t1)  # center = (200, 150)
    tracks = tracker.update([d1], frame_id=1, timestamp_utc=t1)

    assert len(tracks) == 1
    tr = tracks[0]
    assert len(tr.trajectory) == 2
    assert tr.center_xy[0] > 180.0
    assert tr.velocity_xy[0] > 0.0
    assert tr.speed_pixels_per_sec > 0.0


def test_camera_isolation():
    tracker_a = ByteTrackTracker(camera_id="cam_east_01", min_hits=1)
    tracker_b = ByteTrackTracker(camera_id="cam_west_02", min_hits=1)
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    d_a = _make_det(100, 100, 150, 200, camera_id="cam_east_01", ts=t0)
    d_b = _make_det(300, 300, 350, 400, camera_id="cam_west_02", ts=t0)

    tracks_a = tracker_a.update([d_a], frame_id=0, timestamp_utc=t0)
    tracks_b = tracker_b.update([d_b], frame_id=0, timestamp_utc=t0)

    assert tracks_a[0].camera_id == "cam_east_01"
    assert tracks_b[0].camera_id == "cam_west_02"
    assert tracks_a[0].bbox.x_min == 100
    assert tracks_b[0].bbox.x_min == 300


def test_tracker_reset():
    tracker = ByteTrackTracker(camera_id="cam_01", min_hits=1)
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    d0 = _make_det(100, 100, 150, 200, ts=t0)
    tracker.update([d0], frame_id=0, timestamp_utc=t0)
    assert len(tracker.get_tracks()) == 1

    tracker.reset()
    assert len(tracker.get_tracks()) == 0
    assert tracker._next_track_id == 1


def test_invalid_detections_input():
    tracker = ByteTrackTracker()
    with pytest.raises(InvalidDetectionError):
        tracker.update(None, frame_id=0)


def test_visualizer_draw_tracks():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    tracker = ByteTrackTracker(camera_id="cam_01", min_hits=1)
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    d0 = _make_det(100, 100, 180, 250, ts=t0)
    tracks = tracker.update([d0], frame_id=0, timestamp_utc=t0)

    annotated = draw_tracks(img, tracks)
    assert annotated.shape == img.shape
    assert np.max(annotated) > 0
    assert np.max(img) == 0
