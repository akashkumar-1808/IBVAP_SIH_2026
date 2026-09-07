"""
Unit tests for IBVAP Stream Health & Continuity Subsystem (DEC-0012).
Tests deterministic state machine transitions, gap detection without frame fabrication,
perceptual freshness / frozen imagery detection, motion recovery, and AI trust modulation.
"""

import time
import numpy as np
import pytest
from datetime import datetime, timezone, timedelta

from worker.ingestion import (
    StreamHealthState,
    TrackingRecoveryState,
    ContinuityConfig,
    StreamGapRecord,
    StreamHealthMetrics,
    StreamContinuityManager,
    FramePacket,
)
from worker.perception import Detection, BoundingBox, TargetClass
from worker.tracking import TrackState, TrackStatus
from worker.fusion import (
    calculate_risk_score,
    EvidenceType,
    EvidenceExtractor,
    EventRecord,
    EventPriority,
    EventStatus,
    EventType,
    FusionReasonCode,
)


def _make_packet(frame_id: int, image: np.ndarray, timestamp: datetime) -> FramePacket:
    return FramePacket(
        camera_id="TEST-CAM-01",
        frame_id=frame_id,
        timestamp_utc=timestamp,
        image=image,
        width=image.shape[1],
        height=image.shape[0],
        source_type="test",
        source_fps=25.0,
    )


def test_continuity_config_defaults():
    cfg = ContinuityConfig()
    assert cfg.expected_fps == 25.0
    assert cfg.interruption_timeout_s == 1.5
    assert cfg.stale_timeout_s == 2.0
    assert cfg.max_track_recovery_gap_s == 5.0
    assert cfg.duplicate_mse_threshold == 0.35
    assert cfg.recovery_confirmation_frames == 5


def test_stream_gap_record_serialization():
    now = datetime.now(timezone.utc)
    rec = StreamGapRecord(
        gap_id="gap_1001_TEST-CAM-01",
        camera_id="TEST-CAM-01",
        start_utc=now,
        end_utc=now + timedelta(seconds=2),
        duration_seconds=2.0,
        estimated_missed_frames=50,
        start_sequence_number=10,
        end_sequence_number=61,
        tracking_state_before={"1": {"class_id": "PERSON", "center_xy": (100.0, 200.0)}},
    )
    d = rec.model_dump()
    assert d["gap_id"] == "gap_1001_TEST-CAM-01"
    assert d["estimated_missed_frames"] == 50
    assert d["duration_seconds"] == 2.0
    assert "1" in d["tracking_state_before"]


def test_nominal_healthy_stream():
    cfg = ContinuityConfig(expected_fps=25.0, recovery_confirmation_frames=3)
    mgr = StreamContinuityManager("TEST-CAM-01", cfg)

    base_time = datetime.now(timezone.utc)
    for i in range(15):
        # Varying image to avoid frozen detection
        img = np.full((180, 320, 3), (i * 10) % 255, dtype=np.uint8)
        pkt = _make_packet(i + 1, img, base_time + timedelta(milliseconds=i * 40))
        metrics = mgr.on_frame_received(pkt)

    assert mgr.state == StreamHealthState.HEALTHY
    assert metrics.state == "HEALTHY"
    assert metrics.trust_score == 1.0
    assert metrics.dropped_frames_total == 0
    assert metrics.gap_count == 0


def test_rate_degradation_transition():
    cfg = ContinuityConfig(expected_fps=25.0, degraded_fps_ratio=0.60)
    mgr = StreamContinuityManager("TEST-CAM-01", cfg)

    base_time = datetime.now(timezone.utc)
    # Feed frames at only 5 FPS (200ms gap) when 25 FPS is expected
    for i in range(10):
        img = np.full((180, 320, 3), (i * 15) % 255, dtype=np.uint8)
        pkt = _make_packet(i + 1, img, base_time + timedelta(milliseconds=i * 200))
        metrics = mgr.on_frame_received(pkt)

    assert mgr.state == StreamHealthState.DEGRADED
    assert metrics.trust_score < 1.0
    assert "Low FPS" in metrics.status_reason or "gap" in metrics.status_reason.lower()


def test_interruption_detection_and_reconnect():
    cfg = ContinuityConfig()
    mgr = StreamContinuityManager("TEST-CAM-01", cfg)

    mgr.on_interruption_detected("Socket timeout")
    assert mgr.state == StreamHealthState.INTERRUPTED
    assert mgr.get_metrics().trust_score == 0.0
    assert "Socket timeout" in mgr.get_metrics().status_reason

    mgr.on_reconnecting(attempt=1, max_attempts=5, delay_s=0.5)
    assert mgr.state == StreamHealthState.RECONNECTING
    assert "attempt 1/" in mgr.get_metrics().status_reason.lower()


def test_recovery_hysteresis():
    cfg = ContinuityConfig(recovery_confirmation_frames=4)
    mgr = StreamContinuityManager("TEST-CAM-01", cfg)

    mgr.on_interruption_detected("RTSP drop")
    assert mgr.state == StreamHealthState.INTERRUPTED

    base_time = datetime.now(timezone.utc)
    # Frame 1 after interruption -> RECOVERED (1/4)
    img1 = np.full((180, 320, 3), 50, dtype=np.uint8)
    pkt1 = _make_packet(1, img1, base_time)
    mgr.on_frame_received(pkt1)
    assert mgr.state == StreamHealthState.RECOVERED

    # Frame 2 -> RECOVERED (2/4)
    img2 = np.full((180, 320, 3), 70, dtype=np.uint8)
    pkt2 = _make_packet(2, img2, base_time + timedelta(milliseconds=40))
    mgr.on_frame_received(pkt2)
    assert mgr.state == StreamHealthState.RECOVERED

    # Frame 3 -> RECOVERED (3/4)
    img3 = np.full((180, 320, 3), 90, dtype=np.uint8)
    pkt3 = _make_packet(3, img3, base_time + timedelta(milliseconds=80))
    mgr.on_frame_received(pkt3)
    assert mgr.state == StreamHealthState.RECOVERED

    # Frame 4 -> Promoted to HEALTHY
    img4 = np.full((180, 320, 3), 110, dtype=np.uint8)
    pkt4 = _make_packet(4, img4, base_time + timedelta(milliseconds=120))
    mgr.on_frame_received(pkt4)
    assert mgr.state == StreamHealthState.HEALTHY


def test_perceptual_freshness_frozen_detection():
    cfg = ContinuityConfig(stale_timeout_s=0.08, duplicate_mse_threshold=1.0)
    mgr = StreamContinuityManager("TEST-CAM-01", cfg)

    # Identical image sent repeatedly
    frozen_img = np.full((180, 320, 3), 120, dtype=np.uint8)
    base_time = datetime.now(timezone.utc)

    for i in range(12):
        pkt = _make_packet(i + 1, frozen_img, base_time + timedelta(milliseconds=i * 40))
        mgr.on_frame_received(pkt)
        time.sleep(0.015)

    assert mgr.state == StreamHealthState.STALE_FROZEN
    assert mgr.is_frozen is True
    assert mgr.get_metrics().is_frozen is True
    assert mgr.get_metrics().trust_score == 0.10


def test_file_video_source_completed_eof():
    mgr = StreamContinuityManager("TEST-CAM-01")
    mgr.on_completed()
    assert mgr.state == StreamHealthState.COMPLETED
    assert mgr.get_metrics().state == "COMPLETED"
    assert mgr.get_metrics().trust_score == 1.0


def test_track_snapshot_and_motion_recovery():
    mgr = StreamContinuityManager("TEST-CAM-01", ContinuityConfig(track_recovery_max_distance_px=150.0))

    # Pre-gap track: moving at +50 px/sec in X, at (100, 200)
    class FakeTrack:
        track_id = 42
        center_xy = (100.0, 200.0)
        velocity_xy = (50.0, 0.0)
        class_id = TargetClass.PERSON

    mgr.snapshot_tracks_before_gap([FakeTrack()])

    # Post-reconnect candidate detection 1.0 second later
    # Expected location: (100 + 50*1.0, 200) = (150, 200)
    candidate_det = Detection(
        camera_id="TEST-CAM-01",
        frame_id=1,
        bbox=BoundingBox(x_min=140.0, y_min=180.0, x_max=160.0, y_max=220.0),
        confidence=0.92,
        class_id=TargetClass.PERSON,
    )

    rec_state, rec_map = mgr.evaluate_track_recovery(
        candidate_detections=[candidate_det],
        gap_duration_seconds=1.0,
    )

    assert rec_state == TrackingRecoveryState.RECOVERED
    assert 0 in rec_map
    assert rec_map[0] == 42


def test_track_snapshot_loss_after_timeout():
    mgr = StreamContinuityManager("TEST-CAM-01", ContinuityConfig(max_track_recovery_gap_s=2.0))

    class FakeTrack:
        track_id = 42
        center_xy = (100.0, 200.0)
        velocity_xy = (0.0, 0.0)
        class_id = TargetClass.PERSON

    mgr.snapshot_tracks_before_gap([FakeTrack()])

    candidate_det = Detection(
        camera_id="TEST-CAM-01",
        frame_id=1,
        bbox=BoundingBox(x_min=90.0, y_min=190.0, x_max=110.0, y_max=210.0),
        confidence=0.92,
        class_id=TargetClass.PERSON,
    )

    # 3.5 second gap exceeds 2.0 second recovery threshold
    rec_state, rec_map = mgr.evaluate_track_recovery(
        candidate_detections=[candidate_det],
        gap_duration_seconds=3.5,
    )

    assert rec_state == TrackingRecoveryState.LOST
    assert len(rec_map) == 0


def test_trust_score_fusion_dampening():
    from worker.fusion import EvidenceExtractor, calculate_risk_score, FusionConfig
    from worker.tracking.schemas import TrackState, TrajectoryPoint, BoundingBox

    now = datetime.now(timezone.utc)
    track = TrackState(
        track_id=1,
        camera_id="TEST-CAM-01",
        class_id=TargetClass.PERSON,
        bbox=BoundingBox(x_min=100.0, y_min=100.0, x_max=150.0, y_max=200.0),
        center_xy=(125.0, 150.0),
        velocity_xy=(0.0, 0.0),
        speed_pixels_per_sec=0.0,
        age_frames=10,
        consecutive_invisible_frames=0,
        status=TrackStatus.TRACKED,
        first_seen=now - timedelta(seconds=1),
        last_seen=now,
        confidence_history=[0.95],
        trajectory=[TrajectoryPoint(x=125.0, y=150.0, timestamp_utc=now, frame_id=1)],
    )

    healthy_metrics = StreamHealthMetrics(
        camera_id="TEST-CAM-01",
        state=StreamHealthState.HEALTHY,
        trust_score=1.0,
    )
    ev_healthy = EvidenceExtractor.extract_evidence(
        track=track,
        spatial=None,
        environment=None,
        behaviors=[],
        camera_id="TEST-CAM-01",
        timestamp_utc=now,
        stream_health=healthy_metrics,
    )
    score_healthy, reasons_healthy, _ = calculate_risk_score(ev_healthy, FusionConfig())

    degraded_metrics = StreamHealthMetrics(
        camera_id="TEST-CAM-01",
        state=StreamHealthState.DEGRADED,
        trust_score=0.50,
        gap_count=2,
    )
    ev_degraded = EvidenceExtractor.extract_evidence(
        track=track,
        spatial=None,
        environment=None,
        behaviors=[],
        camera_id="TEST-CAM-01",
        timestamp_utc=now,
        stream_health=degraded_metrics,
    )
    score_degraded, reasons_degraded, _ = calculate_risk_score(ev_degraded, FusionConfig())

    assert score_degraded < score_healthy
    assert FusionReasonCode.STREAM_QUALITY_DEGRADED in reasons_degraded
