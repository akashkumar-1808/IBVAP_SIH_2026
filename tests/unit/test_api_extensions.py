"""
Unit tests for new Phase 10 API extensions:
- Cameras and Calibration endpoints
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
    assert len(data) >= 3
    assert any(c["camera_id"] == "CAM-01" for c in data)

    resp_single = client.get("/api/v1/cameras/CAM-01")
    assert resp_single.status_code == 200
    assert resp_single.json()["camera_id"] == "CAM-01"


def test_camera_calibration():
    resp = client.get("/api/v1/cameras/CAM-01/calibration")
    assert resp.status_code == 200
    data = resp.json()
    assert data["camera_id"] == "CAM-01"
    assert data["calibration_status"] == "CALIBRATED"
    assert "projected_points" in data
    assert len(data["projected_points"]) >= 2


def test_stream_snapshot():
    resp = client.get("/api/v1/streams/CAM-01/snapshot")
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
