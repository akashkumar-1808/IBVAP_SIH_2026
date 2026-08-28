import os
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import cv2
from .base import VideoSource
from .frame import FramePacket
from .health import StreamHealthState
from .exceptions import VideoFileNotFoundError, VideoDecodeError

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FileVideoSource(VideoSource):
    """
    Deterministic video source for MP4/AVI replay and automated benchmark testing.
    Produces identical monotonic frame sequences and timestamps across test runs.
    """

    def __init__(
        self,
        camera_id: str,
        file_path: str,
        loop: bool = False,
        realtime_pacing: bool = False,
        start_time_utc: Optional[datetime] = None,
    ):
        super().__init__(camera_id)
        self.file_path = file_path
        self.loop = loop
        self.realtime_pacing = realtime_pacing
        self.start_time_utc = start_time_utc or _utc_now()

        self._cap: Optional[cv2.VideoCapture] = None
        self._is_running = False
        self._frame_id = 0
        self._fps = 25.0
        self._width = 0
        self._height = 0
        self._total_frames = 0
        self._last_read_perf_time = 0.0

    def connect(self) -> bool:
        """Opens the video file via OpenCV VideoCapture."""
        if not os.path.exists(self.file_path):
            self._health_metrics.state = StreamHealthState.ERROR
            self._health_metrics.last_error_message = f"File not found: {self.file_path}"
            logger.error(f"Cannot open video source: file '{self.file_path}' does not exist.")
            raise VideoFileNotFoundError(f"Video file not found: {self.file_path}")

        self._cap = cv2.VideoCapture(self.file_path)
        if not self._cap.isOpened():
            self._health_metrics.state = StreamHealthState.ERROR
            self._health_metrics.last_error_message = f"Failed to open video file: {self.file_path}"
            logger.error(f"OpenCV failed to open video file: {self.file_path}")
            raise VideoDecodeError(f"Cannot decode video file: {self.file_path}")

        # Read video metadata
        fps_val = self._cap.get(cv2.CAP_PROP_FPS)
        self._fps = fps_val if fps_val and fps_val > 0 else 25.0
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self._is_running = True
        self._health_metrics.state = StreamHealthState.ONLINE
        self._health_metrics.fps_measured = self._fps
        self._last_read_perf_time = time.perf_counter()

        logger.info(
            f"FileVideoSource connected: camera={self.camera_id}, file={self.file_path}, "
            f"resolution={self._width}x{self._height}, fps={self._fps:.2f}, total_frames={self._total_frames}"
        )
        return True

    def read(self) -> Optional[FramePacket]:
        """
        Decodes the next frame from the file.
        Returns FramePacket with deterministic monotonic frame_id and timestamp.
        """
        if not self._is_running or self._cap is None:
            return None

        # Real-time pacing if requested
        if self.realtime_pacing and self._fps > 0:
            target_interval = 1.0 / self._fps
            elapsed = time.perf_counter() - self._last_read_perf_time
            if elapsed < target_interval:
                time.sleep(target_interval - elapsed)
            self._last_read_perf_time = time.perf_counter()

        ret, frame = self._cap.read()
        if not ret or frame is None:
            if self.loop:
                logger.debug(f"Looping video: {self.file_path}")
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._cap.read()
                if not ret or frame is None:
                    self._is_running = False
                    self._health_metrics.state = StreamHealthState.DISCONNECTED
                    return None
            else:
                logger.info(f"End of video file reached: {self.file_path}")
                self._is_running = False
                self._health_metrics.state = StreamHealthState.DISCONNECTED
                return None

        # Deterministic timestamp calculation
        frame_offset_seconds = self._frame_id / self._fps
        frame_timestamp = self.start_time_utc + timedelta(seconds=frame_offset_seconds)

        packet = FramePacket(
            camera_id=self.camera_id,
            frame_id=self._frame_id,
            timestamp_utc=frame_timestamp,
            image=frame,
            width=self._width if self._width > 0 else frame.shape[1],
            height=self._height if self._height > 0 else frame.shape[0],
            source_type="file",
            source_fps=self._fps,
            sequence_number=self._frame_id,
            metadata={"file_path": self.file_path, "total_frames": self._total_frames},
        )

        self._frame_id += 1
        self._health_metrics.total_frames_read += 1
        self._health_metrics.last_frame_timestamp = frame_timestamp
        return packet

    def is_alive(self) -> bool:
        return self._is_running and self._cap is not None and self._cap.isOpened()

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "source_type": "file",
            "file_path": self.file_path,
            "width": self._width,
            "height": self._height,
            "fps": self._fps,
            "total_frames": self._total_frames,
            "current_frame_id": self._frame_id,
            "is_looping": self.loop,
        }

    def stop(self) -> None:
        self._is_running = False
        self._health_metrics.state = StreamHealthState.DISCONNECTED

    def close(self) -> None:
        self.stop()
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception as exc:
                logger.warning(f"Error releasing video capture handle: {exc}")
            self._cap = None
        logger.info(f"FileVideoSource closed: {self.file_path}")
