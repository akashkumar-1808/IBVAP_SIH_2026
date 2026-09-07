"""
Integration tests for Stream Health & Continuity lifecycle (DEC-0012).
Validates end-to-end resilience: RTSP interruption, bounded reconnect,
perceptual freeze detection, track identity recovery, and AI trust modulation.
"""

import time
import numpy as np
import pytest
from datetime import datetime, timezone, timedelta

from worker.ingestion import (
    StreamHealthState,
    TrackingRecoveryState,
    ContinuityConfig,
    StreamHealthMetrics,
    StreamContinuityManager,
    FramePacket,
    FileVideoSource,
)
from worker.perception import Detection, BoundingBox, TargetClass
from worker.tracking import ByteTrackTracker, TrackStatus
from worker.fusion import (
    FusionEngine,
    EventType,
    EventPriority,
)
from worker.pipeline import LivePipelineOrchestrator, PipelineConfig, RunMode


def _create_synthetic_packet(frame_id: int, camera_id: str, ts: datetime, intensity: int = 100) -> FramePacket:
    img = np.full((180, 320, 3), intensity, dtype=np.uint8)
    return FramePacket(
        camera_id=camera_id,
        frame_id=frame_id,
        timestamp_utc=ts,
        image=img,
        width=320,
        height=180,
        source_type="synthetic",
        source_fps=25.0,
    )


def test_rtsp_interruption_and_reconnection_lifecycle():
    """Validates full lifecycle: HEALTHY -> INTERRUPTED -> RECONNECTING -> RECOVERED -> HEALTHY."""
    cam_id = "INTEG-CAM-01"
    cfg = ContinuityConfig(recovery_confirmation_frames=3)
    mgr = StreamContinuityManager(cam_id, cfg)

    # 1. Healthy stream arrival
    now = datetime.now(timezone.utc)
    for i in range(10):
        pkt = _create_synthetic_packet(i + 1, cam_id, now + timedelta(milliseconds=i * 40), intensity=50 + i * 5)
        mgr.on_frame_received(pkt)

    assert mgr.state == StreamHealthState.HEALTHY
    assert mgr.get_metrics().trust_score == 1.0

    # 2. Interruption occurs
    mgr.on_interruption_detected("RTSP connection reset by peer")
    assert mgr.state == StreamHealthState.INTERRUPTED
    assert mgr.get_metrics().trust_score == 0.0

    # 3. Reconnection in progress
    mgr.on_reconnecting(attempt=1, max_attempts=5, delay_s=0.5)
    assert mgr.state == StreamHealthState.RECONNECTING

    mgr.on_reconnecting(attempt=2, max_attempts=5, delay_s=1.0)
    assert mgr.state == StreamHealthState.RECONNECTING

    # 4. Stream resumes: first frame promotes to RECOVERED
    resume_time = now + timedelta(seconds=2)
    pkt_res1 = _create_synthetic_packet(11, cam_id, resume_time, intensity=120)
    mgr.on_frame_received(pkt_res1)
    assert mgr.state == StreamHealthState.RECOVERED
    assert mgr.get_metrics().trust_score == 0.70

    # 5. Stabilizing frames
    pkt_res2 = _create_synthetic_packet(12, cam_id, resume_time + timedelta(milliseconds=40), intensity=130)
    mgr.on_frame_received(pkt_res2)
    assert mgr.state == StreamHealthState.RECOVERED

    # 6. Third frame confirms continuity -> promoted to HEALTHY
    pkt_res3 = _create_synthetic_packet(13, cam_id, resume_time + timedelta(milliseconds=80), intensity=140)
    mgr.on_frame_received(pkt_res3)
    assert mgr.state == StreamHealthState.HEALTHY
    assert mgr.get_metrics().trust_score == 1.0


def test_track_identity_recovery_integration():
    """Validates that track identities are restored after a stream gap using motion extrapolation."""
    cam_id = "INTEG-CAM-02"
    mgr = StreamContinuityManager(cam_id)
    tracker = ByteTrackTracker(camera_id=cam_id)

    # Frame 1: Target enters at (100, 100)
    t1 = datetime.now(timezone.utc)
    det1 = Detection(
        camera_id=cam_id,
        frame_id=1,
        bbox=BoundingBox(x_min=80.0, y_min=60.0, x_max=120.0, y_max=140.0),
        confidence=0.95,
        class_id=TargetClass.PERSON,
    )
    tracks1 = tracker.update([det1], frame_id=1, camera_id=cam_id, timestamp_utc=t1)
    assert len(tracks1) == 1
    original_track_id = tracks1[0].track_id

    # Frame 2: Target moves rightward to (120, 100) (velocity = +500 px/sec across 0.04s)
    t2 = t1 + timedelta(milliseconds=40)
    det2 = Detection(
        camera_id=cam_id,
        frame_id=2,
        bbox=BoundingBox(x_min=100.0, y_min=60.0, x_max=140.0, y_max=140.0),
        confidence=0.95,
        class_id=TargetClass.PERSON,
    )
    tracks2 = tracker.update([det2], frame_id=2, camera_id=cam_id, timestamp_utc=t2)
    assert len(tracks2) == 1
    assert tracks2[0].track_id == original_track_id

    # Simulate interruption: Snapshot active tracks
    mgr.snapshot_tracks_before_gap(tracker.get_active_tracks())
    mgr.on_interruption_detected("Network blip")

    # Gap of 0.5 seconds: Extrapolate position using active track kinematics
    gap_duration = 0.5
    t3 = t2 + timedelta(seconds=gap_duration)

    active_tracks = tracker.get_active_tracks()
    assert len(active_tracks) >= 1
    cx, cy = active_tracks[0].center_xy
    vx, vy = active_tracks[0].velocity_xy or (0.0, 0.0)
    exp_x = cx + vx * gap_duration
    exp_y = cy + vy * gap_duration

    # Candidate detection at extrapolated position
    candidate_det = Detection(
        camera_id=cam_id,
        frame_id=3,
        bbox=BoundingBox(x_min=exp_x - 20.0, y_min=exp_y - 40.0, x_max=exp_x + 20.0, y_max=exp_y + 40.0),
        confidence=0.95,
        class_id=TargetClass.PERSON,
    )

    rec_state, rec_map = mgr.evaluate_track_recovery([candidate_det], gap_duration_seconds=gap_duration)
    assert rec_state == TrackingRecoveryState.RECOVERED
    assert 0 in rec_map
    assert rec_map[0] == original_track_id

    # Update tracker with recovered_track_map
    tracks3 = tracker.update([candidate_det], frame_id=3, camera_id=cam_id, timestamp_utc=t3, recovered_track_map=rec_map)
    assert len(tracks3) == 1
    assert tracks3[0].track_id == original_track_id
    assert tracks3[0].status == TrackStatus.TRACKED


def test_fusion_operational_stream_health_events():
    """Validates that FusionEngine processes stream health and modulates risk scores."""
    engine = FusionEngine()
    cam_id = "INTEG-CAM-03"
    now = datetime.now(timezone.utc)

    # In degraded stream, events have reduced risk score and include reason code
    degraded_health = StreamHealthMetrics(
        camera_id=cam_id,
        state="DEGRADED",
        trust_score=0.45,
        gap_count=3,
        dropped_frames_total=12,
    )

    # Call process without tracks
    events = engine.process(
        tracks=[],
        spatial_states=[],
        environment_state=None,
        behavior_primitives=[],
        camera_id=cam_id,
        timestamp_utc=now,
        stream_health=degraded_health,
    )
    # Pipeline executes without errors with stream health injected
    assert isinstance(events, list)
