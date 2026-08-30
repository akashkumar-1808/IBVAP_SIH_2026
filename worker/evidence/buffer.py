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

from ..ingestion import FramePacket


class BufferedFrame:
    """Lightweight in-memory container for a cached camera frame."""
    __slots__ = ("frame_id", "timestamp_utc", "image", "camera_id")

    def __init__(self, frame_id: int, timestamp_utc: datetime, image: np.ndarray, camera_id: str):
        self.frame_id = frame_id
        self.timestamp_utc = timestamp_utc
        self.image = image
        self.camera_id = camera_id


class RollingFrameBuffer:
    """
    Thread-safe continuous ring buffer storing recent video frames.
    Bounded by maximum duration (seconds) and estimated FPS.
    """

    def __init__(self, max_seconds: float = 15.0, fps: float = 25.0):
        self.max_seconds = max(1.0, float(max_seconds))
        self.fps = max(1.0, float(fps))
        self.capacity = int(self.max_seconds * self.fps)
        self._buffer: deque[BufferedFrame] = deque(maxlen=self.capacity)
        self._lock = threading.Lock()

    def add_packet(self, packet: FramePacket) -> None:
        """Adds a FramePacket to the rolling buffer."""
        with self._lock:
            self._buffer.append(BufferedFrame(
                frame_id=packet.frame_id,
                timestamp_utc=packet.timestamp_utc,
                image=packet.image.copy(),  # Defensive copy to decouple from downstream processing
                camera_id=packet.camera_id,
            ))

    def add_frame(self, frame_id: int, timestamp_utc: datetime, image: np.ndarray, camera_id: str) -> None:
        """Adds a raw frame image to the rolling buffer."""
        with self._lock:
            self._buffer.append(BufferedFrame(
                frame_id=frame_id,
                timestamp_utc=timestamp_utc,
                image=image.copy(),
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
