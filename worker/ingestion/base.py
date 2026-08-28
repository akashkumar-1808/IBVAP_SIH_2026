from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from .frame import FramePacket
from .health import StreamHealthMetrics, StreamHealthState


class VideoSource(ABC):
    """
    Abstract Base Class for all IBVAP video ingestion sources.
    Decouples video stream transport and decoding from downstream AI inference pipelines.
    """

    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self._health_metrics = StreamHealthMetrics(camera_id=camera_id)

    @abstractmethod
    def connect(self) -> bool:
        """
        Establishes connection to the video source (file or RTSP stream).
        Returns True if connection succeeds, False otherwise.
        """
        pass

    @abstractmethod
    def read(self) -> Optional[FramePacket]:
        """
        Decodes and returns the next FramePacket.
        Returns None on EOF, disconnect, or timeout.
        """
        pass

    @abstractmethod
    def is_alive(self) -> bool:
        """Returns True if the source is actively receiving or decoding frames."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Returns source stream metadata (width, height, FPS, codec, total frames if known)."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Signals the video source to stop capturing."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Releases underlying OS decoder handles, sockets, and threads cleanly."""
        pass

    def get_health(self) -> StreamHealthMetrics:
        """Returns the current telemetry health metrics of the stream."""
        return self._health_metrics
