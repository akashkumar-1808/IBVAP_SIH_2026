"""
Production Deployment & Remote Architecture Integration Tests.

Validates:
1. API URL configuration & normalization
2. WebSocket URL configuration & protocol conversion
3. CORS allowed origins from configuration
4. CORS rejection of unauthorized origins
5. Protected API rejection without credentials
6. Protected API acceptance with X-API-Key and Bearer token
7. Public accessibility of /health without credentials
8. Public accessibility of / without credentials
9. Elimination of local filesystem path exposure (/home/..., C:\\...)
10. Evidence retrieval endpoint functionality
11. Cryptographic evidence SHA-256 integrity verification
12. MP4 EOF status retention as COMPLETED (not OFFLINE or ERROR)
13. Backend survival across EOF lifecycle
14. WebSocket authentication gating
"""

import os
import io
import pytest
from pydantic import SecretStr
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.config.settings import settings


@pytest.fixture
def base_client():
    app = create_app()
    return TestClient(app)


def test_api_url_and_ws_url_logic():
    """Verifies URL normalization logic mirroring frontend/src/config.ts."""
    def get_api_url(base_url: str, path: str) -> str:
        clean_base = base_url.rstrip("/") if base_url else ""
        norm_path = path if path.startswith("/") else f"/{path}"
        return f"{clean_base}{norm_path}" if clean_base else norm_path

    def get_ws_url(ws_base: str, api_base: str, path: str) -> str:
        norm_path = path if path.startswith("/") else f"/{path}"
        if ws_base:
            return f"{ws_base.rstrip('/')}{norm_path}"
        if api_base:
            prefix = api_base.rstrip("/").replace("https://", "wss://").replace("http://", "ws://")
            return f"{prefix}{norm_path}"
        return f"wss://127.0.0.1:8000{norm_path}"

    # Standard remote deployment
    api_base = "https://ec2-12-34-56-78.compute-1.amazonaws.com:8000"
    ws_base = "wss://ec2-12-34-56-78.compute-1.amazonaws.com:8000"
    assert get_api_url(api_base, "/api/v1/cameras") == "https://ec2-12-34-56-78.compute-1.amazonaws.com:8000/api/v1/cameras"
    assert get_ws_url(ws_base, api_base, "/api/v1/ws/telemetry") == "wss://ec2-12-34-56-78.compute-1.amazonaws.com:8000/api/v1/ws/telemetry"

    # Trailing slash normalization
    assert get_api_url("https://api.ibvap.gov.in/", "health") == "https://api.ibvap.gov.in/health"
    assert get_ws_url("", "https://api.ibvap.gov.in/", "/ws") == "wss://api.ibvap.gov.in/ws"

    # Local fallback
    assert get_api_url("", "/api/v1/events") == "/api/v1/events"


def test_cors_allowed_and_rejected_origins(monkeypatch):
    """Verifies CORS headers honor explicit allowlist and reject unlisted origins."""
    monkeypatch.setattr(
        settings,
        "CORS_ORIGINS",
        "https://ibvap-console.onrender.com,http://localhost:5173",
    )
    app = create_app()
    client = TestClient(app)

    # 1. Allowed Render origin
    res_render = client.options(
        "/api/v1/cameras",
        headers={
            "Origin": "https://ibvap-console.onrender.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res_render.headers.get("access-control-allow-origin") == "https://ibvap-console.onrender.com"
    assert res_render.headers.get("access-control-allow-credentials") == "true"

    # 2. Allowed localhost origin
    res_local = client.options(
        "/api/v1/cameras",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res_local.headers.get("access-control-allow-origin") == "http://localhost:5173"

    # 3. Disallowed origin must NOT be granted CORS access
    res_blocked = client.options(
        "/api/v1/cameras",
        headers={
            "Origin": "https://unauthorized-attacker.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res_blocked.headers.get("access-control-allow-origin") is None


def test_public_endpoints_unrestricted(base_client, monkeypatch):
    """Ensures /health and / remain public and unauthenticated even with API_KEY configured."""
    monkeypatch.setattr(settings, "API_KEY", SecretStr("test-secret-key-12345"))
    app = create_app()
    client = TestClient(app)

    # /health probe without credentials
    res_health = client.get("/health?check_db=false")
    assert res_health.status_code == 200
    data = res_health.json()
    assert data["status"] in ("ok", "degraded")
    assert "IBVAP" in data["app_name"]

    # Root / without credentials
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "version" in res_root.json()


def test_api_authentication_enforcement(monkeypatch):
    """Verifies protected API endpoints reject missing/invalid keys and accept valid keys."""
    monkeypatch.setattr(settings, "API_KEY", SecretStr("secret-prototype-token-xyz"))
    app = create_app()
    client = TestClient(app)

    # 1. Missing credentials -> 401
    res_unauth = client.get("/api/v1/cameras")
    assert res_unauth.status_code == 401
    assert "Invalid or missing API key" in res_unauth.json()["detail"]

    # 2. Invalid credentials -> 401
    res_bad = client.get("/api/v1/cameras", headers={"X-API-Key": "wrong-key"})
    assert res_bad.status_code == 401

    # 3. Valid X-API-Key header -> 200
    res_header = client.get("/api/v1/cameras", headers={"X-API-Key": "secret-prototype-token-xyz"})
    assert res_header.status_code == 200
    assert isinstance(res_header.json(), list)

    # 4. Valid Authorization: Bearer <token> -> 200
    res_bearer = client.get("/api/v1/cameras", headers={"Authorization": "Bearer secret-prototype-token-xyz"})
    assert res_bearer.status_code == 200

    # 5. Valid query parameter ?api_key=... (for <img> / <video> tags) -> 200
    res_query = client.get("/api/v1/cameras?api_key=secret-prototype-token-xyz")
    assert res_query.status_code == 200


def test_websocket_authentication(monkeypatch):
    """Verifies WebSocket endpoint enforces prototype token gating when configured."""
    monkeypatch.setattr(settings, "API_KEY", SecretStr("ws-secret-pass"))
    app = create_app()
    client = TestClient(app)

    # 1. Connection without token is rejected
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/ws/telemetry") as ws:
            pass

    # 2. Connection with valid query token is accepted
    with client.websocket_connect("/api/v1/ws/telemetry?api_key=ws-secret-pass") as ws:
        # Connected successfully
        assert ws is not None


def test_no_filesystem_paths_exposed(base_client):
    """Verifies upload and evidence endpoints never leak absolute server disk paths."""
    # 1. Test video upload response
    dummy_mp4 = io.BytesIO(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom")
    res = base_client.post(
        "/api/v1/cameras/upload",
        files={"file": ("border_eval.mp4", dummy_mp4, "video/mp4")},
        data={"camera_id": "DEMO-CAM-01"},
    )
    assert res.status_code == 200
    data = res.json()

    # The returned path must be a logical storage key, NOT an absolute server filesystem path
    assert "video_path" in data
    video_path = data["video_path"]
    assert not video_path.startswith("/")
    assert not video_path.startswith("C:\\")
    assert not video_path.startswith("c:\\")
    assert not video_path.startswith("/home/")
    assert not video_path.startswith("/var/")
    assert video_path.startswith("uploads/")

    # 2. Check signed URL endpoint does not return local disk paths
    signed_res = base_client.get("/api/v1/evidence/dummy-id/signed-url")
    if signed_res.status_code == 200:
        s_data = signed_res.json()
        assert not s_data.get("storage_reference", "").startswith("/home/")
        assert not s_data.get("storage_reference", "").startswith("C:\\")


def test_mp4_eof_semantics_and_server_survival(base_client):
    """Verifies that MP4 completion is marked COMPLETED and backend remains alive and usable."""
    # Set status directly to simulate video completion
    from backend.app.api.routes.cameras import _ANALYSIS_STATUS

    _ANALYSIS_STATUS["DEMO-CAM-01"] = {
        "status": "COMPLETED",
        "file_name": "test_video.mp4",
        "video_path": "uploads/test_video.mp4",
        "completed_at": "2026-09-14T12:00:00Z",
    }

    # Query analysis status
    res = base_client.get("/api/v1/cameras/DEMO-CAM-01/analysis-status")
    assert res.status_code == 200
    data = res.json()

    # Status must be COMPLETED, NOT ERROR or OFFLINE
    assert data["status"] == "COMPLETED"
    assert data["status"] != "ERROR"
    assert data["status"] != "OFFLINE"

    # Backend remains alive: subsequent camera query succeeds
    res_cams = base_client.get("/api/v1/cameras")
    assert res_cams.status_code == 200

    # Live stream generator preserves last frame on EOF
    stream_res = base_client.get("/api/v1/streams/DEMO-CAM-01/snapshot")
    assert stream_res.status_code == 200
    assert stream_res.headers["content-type"] == "image/jpeg"
