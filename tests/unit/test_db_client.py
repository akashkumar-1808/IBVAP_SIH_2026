import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from backend.app.db.client import get_supabase_client, check_database_health, reset_supabase_client
from backend.app.config.settings import Settings


@pytest.fixture(autouse=True)
def reset_client():
    reset_supabase_client()
    yield
    reset_supabase_client()


@pytest.mark.asyncio
async def test_check_database_health_unconfigured():
    with patch.object(Settings, "is_supabase_configured", new_callable=PropertyMock, return_value=False):
        status, msg = await check_database_health()
        assert status == "not_configured"
        assert msg is not None


@pytest.mark.asyncio
async def test_check_database_health_healthy():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

    with patch.object(Settings, "is_supabase_configured", new_callable=PropertyMock, return_value=True):
        with patch("backend.app.db.client.get_supabase_client", return_value=mock_client):
            status, msg = await check_database_health()
            assert status == "healthy"
            assert msg is None


@pytest.mark.asyncio
async def test_check_database_health_unreachable():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception("Connection timeout")

    with patch.object(Settings, "is_supabase_configured", new_callable=PropertyMock, return_value=True):
        with patch("backend.app.db.client.get_supabase_client", return_value=mock_client):
            status, msg = await check_database_health()
            assert status == "unreachable"
            assert msg is not None
            # Must not expose private tokens or connection strings
            assert "key" not in msg.lower()
