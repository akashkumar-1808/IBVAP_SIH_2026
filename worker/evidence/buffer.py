"""
Rolling Frame Ring Buffer for continuous pre-event video caching.

Maintains a bounded time-indexed memory ring buffer of recent camera frames
to allow instant extraction of pre-event, active-event, and post-event video clips.

Architecture Decision: DEC-0008
"""

import threading
from collections import deque
from typing import List, Tuple, Optional
from datetime import datetime, timezone, timedelta
import numpy as np

import cv2
from ..ingestion import FramePacket


class BufferedFrame:
    """Lightweight in-memory container for a cached camera frame with compact JPEG compression."""
    __slots__ = ("frame_id", "timestamp_utc", "_jpeg_bytes", "camera_id", "_shape")

    def __init__(self, frame_id: int, timestamp_utc: datetime, image: np.ndarray, camera_id: str):
        self.frame_id = frame_id
        self.timestamp_utc = timestamp_utc
        self.camera_id = camera_id
        self._shape = image.shape if image is not None else (720, 1280, 3)
        if image is not None and isinstance(image, np.ndarray) and image.size > 0:
            ok, enc = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80])
            self._jpeg_bytes = enc.tobytes() if ok else None
        else:
            self._jpeg_bytes = None

    @property
    def image(self) -> np.ndarray:
        if self._jpeg_bytes is not None:
            decoded = cv2.imdecode(np.frombuffer(self._jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
            if decoded is not None:
                return decoded
        h, w = self._shape[:2]
        return np.zeros((h, w, 3), dtype=np.uint8)


class RollingFrameBuffer:
    """
    Thread-safe continuous ring buffer storing recent video frames.
    Bounded by maximum duration (seconds) and estimated FPS.
    """

    def __init__(self, max_seconds: float = 10.0, fps: float = 20.0):
        self.max_seconds = max(1.0, float(max_seconds))
        self.fps = max(1.0, float(fps))
        self.capacity = int(self.max_seconds * self.fps)
        self._buffer: deque[BufferedFrame] = deque(maxlen=self.capacity)
        self._lock = threading.Lock()

    def add_packet(self, packet: FramePacket) -> None:
        """Adds a FramePacket to the rolling buffer with compact compression."""
        with self._lock:
            self._buffer.append(BufferedFrame(
                frame_id=packet.frame_id,
                timestamp_utc=packet.timestamp_utc,
                image=packet.image,
                camera_id=packet.camera_id,
            ))

    def add_frame(self, frame_id: int, timestamp_utc: datetime, image: np.ndarray, camera_id: str) -> None:
        """Adds a raw frame image to the rolling buffer with compact compression."""
        with self._lock:
            self._buffer.append(BufferedFrame(
                frame_id=frame_id,
                timestamp_utc=timestamp_utc,
                image=image,
                camera_id=camera_id,
            ))

    def get_window(self, start_utc: datetime, end_utc: datetime) -> List[BufferedFrame]:
        """
        Retrieves all buffered frames within the [start_utc, end_utc] timestamp window.
        """
        with self._lock:
            matching = [
                f for f in self._buffer
                if start_utc <= f.timestamp_utc <= end_utc
            ]
            return matching

    def get_pre_event_frames(self, event_start_utc: datetime, pre_seconds: float = 5.0) -> List[BufferedFrame]:
        """
        Retrieves frames captured in the pre_seconds window preceding the event.
        """
        start_utc = event_start_utc - timedelta(seconds=pre_seconds)
        return self.get_window(start_utc, event_start_utc)

    def get_latest_frame(self) -> Optional[BufferedFrame]:
        """Returns the most recent frame in the buffer, if any."""
        with self._lock:
            return self._buffer[-1] if self._buffer else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)

    def clear(self) -> None:
        """Clears all cached frames."""
        with self._lock:
            self._buffer.clear()
