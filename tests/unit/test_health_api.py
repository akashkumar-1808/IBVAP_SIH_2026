import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings
from backend.app.db.client import reset_supabase_client


@pytest.fixture(autouse=True)
def cleanup():
    reset_supabase_client()
    yield
    reset_supabase_client()


def test_root_endpoint():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == settings.APP_NAME
    assert data["version"] == "0.1.0"


def test_health_endpoint_healthy_state():
    with patch("backend.app.api.routes.health.check_database_health", return_value=("healthy", None)):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database_status"] == "healthy"


def test_health_endpoint_degraded_state():
    with patch("backend.app.api.routes.health.check_database_health", return_value=("degraded", "Schema not applied")):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database_status"] == "degraded"


def test_health_endpoint_v1_route():
    with patch("backend.app.api.routes.health.check_database_health", return_value=("healthy", None)):
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["app_name"] == settings.APP_NAME
