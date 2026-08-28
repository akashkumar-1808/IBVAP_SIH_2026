import pytest
from unittest.mock import MagicMock, patch
from backend.app.db.storage import SupabaseEvidenceStorage
from backend.app.db.repositories.base import BaseRepository
from backend.app.db.repositories.cameras import CameraRepository
from backend.app.db.repositories.events import EventRepository


def test_storage_availability_when_unconfigured():
    storage = SupabaseEvidenceStorage()
    with patch("backend.app.db.storage.get_supabase_client", return_value=None):
        assert storage.is_available() is False
        assert storage.ensure_bucket_exists() is False
        assert storage.upload_file("test.jpg", b"fake_bytes") is None
        assert storage.get_signed_url("test.jpg") is None
        assert storage.delete_file("test.jpg") is False


def test_storage_upload_and_signed_url():
    storage = SupabaseEvidenceStorage(bucket_name="test-evidence")
    mock_client = MagicMock()
    mock_storage_bucket = MagicMock()
    mock_client.storage.from_.return_value = mock_storage_bucket
    mock_storage_bucket.upload.return_value = {"path": "2026/08/28/evt_1/snapshot.jpg"}
    mock_storage_bucket.create_signed_url.return_value = {"signedURL": "https://storage.supabase.co/signed/test.jpg"}

    with patch("backend.app.db.storage.get_supabase_client", return_value=mock_client):
        assert storage.is_available() is True
        uploaded_path = storage.upload_file("2026/08/28/evt_1/snapshot.jpg", b"jpeg_bytes", "image/jpeg")
        assert uploaded_path == "2026/08/28/evt_1/snapshot.jpg"

        url = storage.get_signed_url("2026/08/28/evt_1/snapshot.jpg")
        assert url == "https://storage.supabase.co/signed/test.jpg"


def test_camera_repository_queries():
    repo = CameraRepository()
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "cam_01", "name": "North Gate"}])

    with patch("backend.app.db.repositories.base.get_supabase_client", return_value=mock_client):
        cams = repo.get_active_cameras()
        assert len(cams) == 1
        assert cams[0]["id"] == "cam_01"


def test_event_repository_queries():
    repo = EventRepository()
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_query = MagicMock()
    mock_table.select.return_value.order.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.range.return_value.execute.return_value = MagicMock(data=[{"id": "evt_01", "priority": "HIGH"}])

    with patch("backend.app.db.repositories.base.get_supabase_client", return_value=mock_client):
        evts = repo.query_events(camera_id="cam_01", priority="HIGH")
        assert len(evts) == 1
        assert evts[0]["priority"] == "HIGH"
