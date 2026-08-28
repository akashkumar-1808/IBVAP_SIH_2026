import pytest
from unittest.mock import MagicMock, patch
from worker.ingestion import RTSPVideoSource, mask_rtsp_url, StreamHealthState


def test_mask_rtsp_url():
    url_with_creds = "rtsp://admin:superSecret123@192.168.1.50:554/live/ch0"
    masked = mask_rtsp_url(url_with_creds)
    assert "superSecret123" not in masked
    assert "admin" not in masked
    assert masked == "rtsp://***:***@192.168.1.50:554/live/ch0"

    url_no_creds = "rtsp://192.168.1.50:554/live/ch0"
    assert mask_rtsp_url(url_no_creds) == "rtsp://192.168.1.50:554/live/ch0"


def test_rtsp_source_initialization():
    source = RTSPVideoSource(
        camera_id="cam_rtsp_01",
        rtsp_url="rtsp://admin:pass@10.0.0.1:554/stream",
        connection_timeout_seconds=2.0,
        read_timeout_seconds=1.5,
    )
    assert source.camera_id == "cam_rtsp_01"
    assert "pass" not in source._masked_url
    assert source.get_health().state == StreamHealthState.DISCONNECTED
    assert source.is_alive() is False


def test_rtsp_source_failed_connect():
    # Attempting to connect to invalid host should fail gracefully and set DISCONNECTED state
    source = RTSPVideoSource(
        camera_id="cam_fail",
        rtsp_url="rtsp://127.0.0.1:9999/non_existent_stream",
        connection_timeout_seconds=0.5,
    )
    with patch("worker.ingestion.rtsp_source.cv2.VideoCapture") as mock_cap_cls:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_cls.return_value = mock_cap

        success = source.connect()
        assert success is False
        assert source.get_health().state == StreamHealthState.DISCONNECTED
        assert source.is_alive() is False
        source.close()
