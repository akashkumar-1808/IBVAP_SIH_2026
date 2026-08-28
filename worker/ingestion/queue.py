import collections
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from .frame import FramePacket
from .exceptions import QueueClosedError

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BoundedFrameQueue:
    """
    Thread-safe bounded frame queue designed for real-time video analytics.

    Primary Policy:
    REAL-TIME FRESHNESS > PROCESSING EVERY STALE FRAME

    When the queue reaches max_size, the OLDEST waiting frame is dropped to make room
    for the newest frame. This prevents queue growth and latency accumulation.
    """

    def __init__(self, max_size: int = 30):
        if max_size <= 0:
            raise ValueError("max_size must be greater than 0")

        self.max_size = max_size
        self._deque = collections.deque()
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._closed = False

        # Telemetry metrics
        self._total_inserted = 0
        self._total_dropped = 0

    def put(self, frame: FramePacket) -> bool:
        """
        Inserts a frame into the queue.
        If full, drops the oldest frame and increments total_dropped counter.
        Returns True if inserted without drop, or False if a drop occurred.
        """
        with self._lock:
            if self._closed:
                raise QueueClosedError("Cannot put frame into a closed BoundedFrameQueue")

            dropped = False
            if len(self._deque) >= self.max_size:
                dropped_frame = self._deque.popleft()
                self._total_dropped += 1
                dropped = True
                logger.debug(
                    f"Queue full (max={self.max_size}). Dropped oldest frame: "
                    f"id={dropped_frame.frame_id}, camera={dropped_frame.camera_id}"
                )

            self._deque.append(frame)
            self._total_inserted += 1
            self._not_empty.notify()
            return not dropped

    def get(self, timeout: Optional[float] = None) -> Optional[FramePacket]:
        """
        Pulls the next oldest frame from the queue.
        Blocks up to `timeout` seconds if empty.
        Returns FramePacket, or None if timed out or closed while empty.
        """
        with self._not_empty:
            while not self._deque:
                if self._closed:
                    return None
                if timeout is not None and timeout <= 0:
                    return None
                not_empty_event = self._not_empty.wait(timeout=timeout)
                if not not_empty_event and not self._deque:
                    return None

            if not self._deque:
                return None

            return self._deque.popleft()

    def size(self) -> int:
        """Returns current number of buffered frames."""
        with self._lock:
            return len(self._deque)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._deque) == 0

    def clear(self) -> int:
        """Clears all buffered frames. Returns count of cleared frames."""
        with self._lock:
            cleared_count = len(self._deque)
            self._deque.clear()
            return cleared_count

    def close(self) -> None:
        """Closes the queue and unblocks all waiting consumers."""
        with self._lock:
            self._closed = True
            self._not_empty.notify_all()

    @property
    def is_closed(self) -> bool:
        with self._lock:
            return self._closed

    def stats(self) -> Dict[str, Any]:
        """Returns a snapshot of queue statistics and oldest frame age."""
        with self._lock:
            oldest_age_sec: Optional[float] = None
            if self._deque:
                oldest_frame = self._deque[0]
                now = _utc_now()
                # Handle tz-aware vs tz-naive gracefully
                if oldest_frame.timestamp_utc.tzinfo is None:
                    oldest_age_sec = (datetime.utcnow() - oldest_frame.timestamp_utc).total_seconds()
                else:
                    oldest_age_sec = (now - oldest_frame.timestamp_utc).total_seconds()

            return {
                "max_size": self.max_size,
                "current_size": len(self._deque),
                "total_inserted": self._total_inserted,
                "total_dropped": self._total_dropped,
                "is_closed": self._closed,
                "oldest_frame_age_seconds": oldest_age_sec,
            }
