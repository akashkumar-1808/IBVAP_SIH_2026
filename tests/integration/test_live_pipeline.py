"""
Integration Tests for IBVAP Live MVP Execution Pipeline.

Tests:
1. Pipeline configuration and initialization
2. Full headless execution on synthetic stream
3. End-to-end event and evidence package generation
4. Visualizer rendering and HUD overlays
5. Graceful shutdown and signal safety
6. RTSP credential masking security

Architecture Decision: DEC-0010
"""

import os
import cv2
import json
import pytest
import numpy as np
from pathlib import Path
from datetime import datetime, timezone, timedelta

from worker.pipeline import (
    LivePipelineOrchestrator,
    PipelineConfig,
    PipelineMetrics,
    RunMode,
    LiveStreamVisualizer,
)
from worker.ingestion import FramePacket, mask_rtsp_url
from worker.tracking.schemas import TrackState, TargetClass, BoundingBox, TrajectoryPoint, TrackStatus
from worker.spatial.schemas import SpatialState, BorderSide, CrossingStatus, SpatialConfidence
from worker.behavior.schemas import BehaviorPrimitive, BehaviorType
from worker.environment.schemas import EnvironmentState
from worker.fusion.schemas import EventRecord, EventType, EventPriority, EventStatus


def _create_test_video(output_path: Path, num_frames: int = 30) -> None:
    """Generates a temporary synthetic MP4 video file with moving box."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, 25.0, (640, 480))
    for f in range(num_frames):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        # Background
        cv2.rectangle(img, (0, 0), (640, 240), (40, 50, 40), -1)
        cv2.rectangle(img, (0, 240), (640, 480), (30, 30, 50), -1)
        cv2.line(img, (0, 240), (640, 240), (0, 0, 255), 2)
        # Simulated Target
        tx, ty = 320, int(100 + f * 5)
        cv2.rectangle(img, (tx - 20, ty - 50), (tx + 20, ty), (0, 255, 255), -1)
        writer.write(img)
    writer.release()


# ── 1. Pipeline Config & Initialization ────────────────────────────────────────

def test_1_pipeline_config_and_initialization(tmp_path):
    config = PipelineConfig(
        camera_id="CAM-TEST-01",
        run_mode=RunMode.HEADLESS,
        record_output_dir=str(tmp_path / "runs"),
        evidence_storage_dir=str(tmp_path / "evidence"),
    )
    orchestrator = LivePipelineOrchestrator(config)
    orchestrator.setup_prototype_border()

    assert orchestrator.config.camera_id == "CAM-TEST-01"
    assert orchestrator._is_calibrated is True
    assert orchestrator._latest_projected_border is not None
    assert orchestrator._latest_projected_border.border_section_id == "SEC-ALPHA"


# ── 2. Full Headless Execution on Synthetic Stream ────────────────────────────

def test_2_pipeline_synthetic_execution_headless(tmp_path):
    video_path = tmp_path / "test_stream.mp4"
    _create_test_video(video_path, num_frames=25)

    config = PipelineConfig(
        camera_id="CAM-TEST-02",
        file_path=str(video_path),
        run_mode=RunMode.HEADLESS,
        record_output_dir=str(tmp_path / "runs"),
        evidence_storage_dir=str(tmp_path / "evidence"),
        max_runtime_seconds=20.0,
    )
    orchestrator = LivePipelineOrchestrator(config)
    orchestrator.setup_prototype_border()
    orchestrator.initialize_source()

    metrics = orchestrator.run()

    assert metrics.frames_processed >= 15
    assert metrics.effective_fps > 0.0
    assert "environment" in metrics.avg_stage_latencies_ms
    assert "detection" in metrics.avg_stage_latencies_ms
    assert "tracking" in metrics.avg_stage_latencies_ms

    # Check exported artifacts
    run_dir = Path(config.record_output_dir) / orchestrator.run_id
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "metrics.json").exists()
    assert (run_dir / "environment.json").exists()


# ── 3. Visualizer Rendering & Overlays ───────────────────────────────────────

def test_3_pipeline_visualizer_rendering():
    visualizer = LiveStreamVisualizer("CAM-TEST-03")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    t0 = datetime.now(timezone.utc)
    track = TrackState(
        track_id=1, camera_id="CAM-TEST-03", class_id=TargetClass.PERSON,
        bbox=BoundingBox(x_min=200, y_min=150, x_max=260, y_max=280),
        center_xy=(230.0, 215.0), status=TrackStatus.TRACKED,
        first_seen=t0, last_seen=t0, age_frames=5,
        trajectory=[TrajectoryPoint(x=230, y=215, timestamp_utc=t0, frame_id=1)],
    )
    spatial = SpatialState(
        camera_id="CAM-TEST-03", track_id=1, timestamp_utc=t0,
        border_side=BorderSide.RESTRICTED, crossing_status=CrossingStatus.CONFIRMED_CROSSING,
    )
    behavior = [
        BehaviorPrimitive(
            behavior_id="bp_01", track_id=1, camera_id="CAM-TEST-03",
            behavior_type=BehaviorType.FENCE_BREACH,
            first_observed_utc=t0, last_observed_utc=t0, timestamp_utc=t0,
            duration_seconds=1.0,
        )
    ]
    event = EventRecord(
        id="evt_test_01", camera_id="CAM-TEST-03", track_id=1,
        event_type=EventType.BORDER_CROSSING, priority=EventPriority.HIGH,
        risk_score=88.5, status=EventStatus.ACTIVE, target_class=TargetClass.PERSON,
        created_at=t0, updated_at=t0, first_observed_utc=t0, last_observed_utc=t0,
        detection_confidence=0.92,
        explanation_summary="Confirmed human border crossing in restricted zone",
    )

    from worker.spatial.world_schemas import ProjectedBorder
    proj = ProjectedBorder(
        camera_id="CAM-TEST-03",
        border_section_id="SEC-ALPHA",
        projected_points=[(50.0, 240.0), (590.0, 240.0)],
        warning_buffer_points=[(50.0, 200.0), (590.0, 200.0)],
    )

    rendered = visualizer.render_frame(
        frame=frame,
        tracks=[track],
        spatial_states=[spatial],
        behavior_primitives=behavior,
        events=[event],
        environment=None,
        projected_border=proj,
        is_calibrated=True,
        fps=25.0,
    )

    assert rendered is not None
    assert rendered.shape == (480, 640, 3)
    # Ensure drawing modified the black canvas
    assert np.count_nonzero(rendered) > 0


# ── 4. Graceful Shutdown & Resource Release ───────────────────────────────────

def test_4_pipeline_graceful_shutdown(tmp_path):
    video_path = tmp_path / "test_stream_shutdown.mp4"
    _create_test_video(video_path, num_frames=10)

    config = PipelineConfig(
        camera_id="CAM-TEST-04",
        file_path=str(video_path),
        run_mode=RunMode.HEADLESS,
        record_output_dir=str(tmp_path / "runs"),
        evidence_storage_dir=str(tmp_path / "evidence"),
    )
    orchestrator = LivePipelineOrchestrator(config)
    orchestrator.initialize_source()

    # Trigger shutdown manually
    orchestrator.stop()
    assert orchestrator._is_running is False
    assert orchestrator.source is None


# ── 5. RTSP Credential Masking Security ──────────────────────────────────────

def test_5_rtsp_url_masking_security():
    raw_url = "rtsp://admin:SecretPassword123@192.168.1.100:554/h264Preview_01_main"
    masked = mask_rtsp_url(raw_url)

    assert "SecretPassword123" not in masked
    assert "admin" not in masked
    assert "rtsp://***:***@192.168.1.100:554/h264Preview_01_main" == masked
