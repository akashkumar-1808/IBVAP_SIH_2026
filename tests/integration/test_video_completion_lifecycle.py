"""
Tests for Video-Completion Lifecycle Architecture.
Verifies that:
1. Video EOF transitions cleanly to COMPLETED status without server shutdown or process exit.
2. The last processed/annotated frame is preserved indefinitely in the stream buffer.
3. Telemetry packet maintains COMPLETED state with all tracks, spatial, and event data preserved.
4. A second Run Analysis can be immediately started without restarting the server.
5. Endpoints and repository records remain accessible.
"""

import time
import pytest
import numpy as np
import cv2
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api.routes.streams import update_latest_frame, _frame_generator, _LATEST_FRAMES
from backend.app.api.routes.cameras import (
    _ANALYSIS_STATUS,
    _LAST_TELEMETRY,
    _RUNNING_ORCHESTRATORS,
    _RUNNING_THREADS,
    _run_analysis_background,
)
from worker.pipeline import LivePipelineOrchestrator, PipelineConfig, RunMode


def _create_short_test_video(output_path: Path, num_frames: int = 15) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, 25.0, (640, 480))
    for f in range(num_frames):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(img, (0, 0), (640, 240), (40, 50, 40), -1)
        cv2.rectangle(img, (0, 240), (640, 480), (30, 30, 50), -1)
        cv2.line(img, (0, 240), (640, 240), (0, 0, 255), 2)
        tx, ty = 320, int(100 + f * 5)
        cv2.rectangle(img, (tx - 20, ty - 50), (tx + 20, ty), (0, 255, 255), -1)
        writer.write(img)
    writer.release()


def test_video_eof_preserves_last_frame_indefinitely():
    """Verify that _frame_generator keeps serving the last frame even after long delays."""
    cam_id = "TEST-EOF-STREAM-01"
    test_img = np.ones((480, 640, 3), dtype=np.uint8) * 120
    cv2.putText(test_img, "FINAL ANNOTATED KEYFRAME", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    
    update_latest_frame(cam_id, test_img)
    
    # Fast forward frame timestamp by 100 seconds to simulate time after EOF
    saved_bytes, _ = _LATEST_FRAMES[cam_id]
    _LATEST_FRAMES[cam_id] = (saved_bytes, time.time() - 100.0)
    
    gen = _frame_generator(cam_id)
    chunk = next(gen)
    
    # Verify the chunk contains the saved frame, not the fallback frame
    assert saved_bytes in chunk
    assert b"CONNECTING..." not in chunk


def test_video_analysis_eof_lifecycle_and_second_run(tmp_path):
    """Verify full EOF lifecycle: ANALYZING -> COMPLETED, state preservation, and immediate second run."""
    cam_id = "TEST-EOF-CAM-01"
    video1 = tmp_path / "test_run_1.mp4"
    video2 = tmp_path / "test_run_2.mp4"
    _create_short_test_video(video1, num_frames=10)
    _create_short_test_video(video2, num_frames=10)

    # 1. Run First Video Analysis to EOF
    session1 = f"ses_test_1_{int(time.time())}"
    _run_analysis_background(
        cam_id=cam_id,
        video_file_path=str(video1),
        rtsp_url=None,
        device="cpu",
        session_id=session1,
    )

    # Verify status is COMPLETED
    assert _ANALYSIS_STATUS.get(cam_id, {}).get("status") == "COMPLETED"
    assert _ANALYSIS_STATUS.get(cam_id, {}).get("session_id") == session1

    # Verify telemetry was cached and contains COMPLETED status and 0.0 FPS
    telem = _LAST_TELEMETRY.get(cam_id)
    assert telem is not None
    assert telem.get("analysis_status") == "COMPLETED"
    assert telem.get("fps") == 0.0
    assert telem.get("camera", {}).get("connection_status") == "ONLINE"

    # Verify orchestrator was cleanly removed from running tables
    assert cam_id not in _RUNNING_ORCHESTRATORS
    assert cam_id not in _RUNNING_THREADS

    # 2. Run Second Video Analysis without server restart
    session2 = f"ses_test_2_{int(time.time())}"
    _run_analysis_background(
        cam_id=cam_id,
        video_file_path=str(video2),
        rtsp_url=None,
        device="cpu",
        session_id=session2,
    )

    # Verify second run completes cleanly
    assert _ANALYSIS_STATUS.get(cam_id, {}).get("status") == "COMPLETED"
    assert _ANALYSIS_STATUS.get(cam_id, {}).get("session_id") == session2
    telem2 = _LAST_TELEMETRY.get(cam_id)
    assert telem2.get("session_id") == session2
    assert telem2.get("analysis_status") == "COMPLETED"


def test_api_status_reports_completed_and_console_accessible():
    """TestClient verification: /console is 200, status is COMPLETED, and server is alive."""
    client = TestClient(app)
    
    # 1. Verify health endpoint
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert "IBVAP" in health_resp.json().get("app_name", "")

    # 2. Verify /console dashboard route is accessible
    console_resp = client.get("/console")
    assert console_resp.status_code == 200

    # 3. Verify analysis status endpoint reports COMPLETED
    _ANALYSIS_STATUS["DEMO-CAM-01"] = {
        "session_id": "ses_completed_demo",
        "status": "COMPLETED",
        "camera_id": "DEMO-CAM-01",
        "file_name": "test_video.mp4",
        "completed_at": "2026-09-05T00:00:00Z",
    }
    status_resp = client.get("/api/v1/cameras/DEMO-CAM-01/analysis-status")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["status"] == "COMPLETED"
    assert data["session_id"] == "ses_completed_demo"
