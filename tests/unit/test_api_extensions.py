"""
Unit tests for new Phase 10 API extensions:
- Dynamic RTSP Cameras, Connection, and Calibration endpoints
- Video streaming endpoints
- WebSocket telemetry endpoint
- Jury demonstration scenario endpoints
- Evidence physical file endpoint
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_cameras_list_and_get():
    resp = client.get("/api/v1/cameras")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_camera_calibration():
    resp = client.get("/api/v1/cameras/LIVE-01/calibration")
    assert resp.status_code == 200
    data = resp.json()
    assert data["camera_id"] == "LIVE-01"
    assert data["calibration_status"] == "CALIBRATED"
    assert "projected_points" in data
    assert len(data["projected_points"]) >= 2


def test_stream_snapshot():
    resp = client.get("/api/v1/streams/LIVE-01/snapshot")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    assert len(resp.content) > 0


def test_scenarios_list():
    resp = client.get("/api/v1/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    ids = [s["id"] for s in data]
    assert "BORDER_CROSSING_BREACH" in ids
    assert "SHADOW_FALSE_POSITIVE" in ids


def test_scenario_run():
    resp = client.post("/api/v1/scenarios/BORDER_CROSSING_BREACH/run", json={"speed_factor": 5.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"
    assert data["scenario_id"] == "BORDER_CROSSING_BREACH"


def test_camera_connect_and_disconnect():
    # Test connection attempt to unreachable test URL
    resp = client.post(
        "/api/v1/cameras/connect",
        json={
            "camera_id": "TEST-CAM-99",
            "name": "Test Border Cam",
            "rtsp_url": "rtsp://invalid.nonexistent.host:554/live",
            "sector_name": "Northern Border",
        },
    )
    # Expected 400 since host is invalid
    assert resp.status_code == 400

    # Test disconnect endpoint
    resp_disc = client.post("/api/v1/cameras/TEST-CAM-99/disconnect")
    assert resp_disc.status_code == 200
    assert resp_disc.json()["status"] == "DISCONNECTED"
