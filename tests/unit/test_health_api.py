import pytest
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


def test_health_endpoint_unconfigured():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database_status" in data
    assert "supabase_configured" in data
    if not settings.is_supabase_configured:
        assert data["database_status"] == "not_configured"


def test_health_endpoint_v1_route():
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == settings.APP_NAME
