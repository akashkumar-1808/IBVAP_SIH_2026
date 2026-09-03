import re
import time
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import cv2
from .base import VideoSource
from .frame import FramePacket
from .health import StreamHealthState
from .exceptions import RTSPConnectionError, RTSPTimeoutError

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def mask_rtsp_url(url: str) -> str:
    """Masks credentials in RTSP URLs for safe logging: rtsp://user:pass@ip -> rtsp://***:***@ip"""
    if not url:
        return ""
    return re.sub(r"://([^:]+):([^@]+)@", r"://***:***@", url)


class RTSPVideoSource(VideoSource):
    """
    Production-grade RTSP stream ingestion source with background capture,
    controlled reconnect with exponential backoff, and active health monitoring.
    """

    def __init__(
        self,
        camera_id: str,
        rtsp_url: str,
        connection_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 3.0,
        max_reconnect_delay_seconds: float = 30.0,
        base_reconnect_delay_seconds: float = 1.0,
        max_reconnect_attempts: int = 10,
    ):
        super().__init__(camera_id)
        self.rtsp_url = rtsp_url
        self.connection_timeout_seconds = connection_timeout_seconds
        self.read_timeout_seconds = read_timeout_seconds
        self.max_reconnect_delay_seconds = max_reconnect_delay_seconds
        self.base_reconnect_delay_seconds = base_reconnect_delay_seconds
        self.max_reconnect_attempts = max_reconnect_attempts

        self._masked_url = mask_rtsp_url(rtsp_url)
        self._cap: Optional[cv2.VideoCapture] = None
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Shared frame state between capture thread and consumer
        self._latest_frame: Optional[FramePacket] = None
        self._frame_id = 0
        self._last_frame_received_time = 0.0
        self._width = 0
        self._height = 0
        self._fps = 25.0

    def connect(self) -> bool:
        """Initializes connection and starts the continuous capture background thread."""
        logger.info(f"Connecting to RTSP stream for camera '{self.camera_id}' ({self._masked_url})...")
        success = self._open_capture()
        if success:
            self._is_running = True
            self._thread = threading.Thread(target=self._capture_loop, name=f"RTSP-{self.camera_id}", daemon=True)
            self._thread.start()
            return True
        else:
            self._health_metrics.state = StreamHealthState.DISCONNECTED
            return False

    def _open_capture(self) -> bool:
        """Internal helper to instantiate and open cv2.VideoCapture."""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

        try:
            # Set transport protocols and buffer size where supported by backend
            self._cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            if not self._cap.isOpened():
                logger.warning(f"RTSP stream '{self._masked_url}' failed to open.")
                return False

            # Probe stream properties
            fps_val = self._cap.get(cv2.CAP_PROP_FPS)
            self._fps = fps_val if fps_val and fps_val > 0 else 25.0
            self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self._last_frame_received_time = time.time()
            self._health_metrics.state = StreamHealthState.ONLINE
            self._health_metrics.fps_measured = self._fps
            return True
        except Exception as exc:
            logger.error(f"Error opening RTSP stream '{self._masked_url}': {exc}")
            return False

    def _capture_loop(self) -> None:
        """
        Background capture loop continuously pulling latest frames to prevent buffer latency.
        Handles timeout detection and exponential backoff reconnection.
        """
        consecutive_errors = 0
        reconnect_attempts = 0

        while self._is_running:
            if self._cap is None or not self._cap.isOpened():
                # Stream is down; attempt reconnect with backoff
                reconnect_attempts += 1
                self._health_metrics.reconnect_attempts = reconnect_attempts
                self._health_metrics.state = StreamHealthState.DEGRADED

                delay = min(
                    self.max_reconnect_delay_seconds,
                    self.base_reconnect_delay_seconds * (2 ** min(reconnect_attempts - 1, 6)),
                )
                logger.warning(
                    f"RTSP stream '{self._masked_url}' disconnected. Reconnect attempt {reconnect_attempts} in {delay:.1f}s..."
                )
                time.sleep(delay)

                if not self._is_running:
                    break

                if self._open_capture():
                    logger.info(f"RTSP stream '{self._masked_url}' reconnected successfully.")
                    consecutive_errors = 0
                    reconnect_attempts = 0
                else:
                    if reconnect_attempts >= self.max_reconnect_attempts:
                        self._health_metrics.state = StreamHealthState.ERROR
                        self._health_metrics.last_error_message = "Max reconnect attempts reached"
                    continue

            # Read frame from stream
            ret, frame = self._cap.read()
            now = time.time()

            if ret and frame is not None:
                consecutive_errors = 0
                self._last_frame_received_time = now
                self._health_metrics.state = StreamHealthState.ONLINE
                self._health_metrics.total_frames_read += 1
                self._health_metrics.last_frame_timestamp = _utc_now()

                packet = FramePacket(
                    camera_id=self.camera_id,
                    frame_id=self._frame_id,
                    timestamp_utc=_utc_now(),
                    image=frame,
                    width=frame.shape[1],
                    height=frame.shape[0],
                    source_type="rtsp",
                    source_fps=self._fps,
                    sequence_number=self._frame_id,
                    metadata={"masked_url": self._masked_url},
                )
                self._frame_id += 1

                with self._lock:
                    if self._latest_frame is not None:
                        self._health_metrics.frames_dropped += 1
                    self._latest_frame = packet
            else:
                consecutive_errors += 1
                time_since_last_frame = now - self._last_frame_received_time

                if time_since_last_frame > self.read_timeout_seconds:
                    self._health_metrics.state = StreamHealthState.STALE
                    logger.warning(
                        f"RTSP stream '{self._masked_url}' frame read timeout ({time_since_last_frame:.1f}s without frame)."
                    )
                    # Trigger reconnect on next iteration
                    if self._cap:
                        try:
                            self._cap.release()
                        except Exception:
                            pass
                        self._cap = None

                time.sleep(0.01)

        self._health_metrics.state = StreamHealthState.DISCONNECTED

    def read(self) -> Optional[FramePacket]:
        """Returns the latest frame captured from the stream."""
        with self._lock:
            frame = self._latest_frame
            self._latest_frame = None  # Consume frame once
            return frame

    def is_alive(self) -> bool:
        if not self._is_running:
            return False
        # Consider alive if frame was received within read_timeout_seconds * 2
        return (time.time() - self._last_frame_received_time) < (self.read_timeout_seconds * 2)

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "source_type": "rtsp",
            "masked_url": self._masked_url,
            "width": self._width,
            "height": self._height,
            "fps": self._fps,
            "current_frame_id": self._frame_id,
            "health_state": self._health_metrics.state.value,
        }

    def stop(self) -> None:
        self._is_running = False
        self._health_metrics.state = StreamHealthState.DISCONNECTED

    def close(self) -> None:
        self.stop()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None

        if self._cap is not None:
            try:
                self._cap.release()
            except Exception as exc:
                logger.warning(f"Error releasing RTSP video capture: {exc}")
            self._cap = None

        logger.info(f"RTSPVideoSource closed: camera={self.camera_id}")
