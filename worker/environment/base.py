from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from ..ingestion.frame import FramePacket
from .schemas import EnvironmentState


class EnvironmentAnalyzerInterface(ABC):
    """
    Abstract Base Class for video environment and visual quality analyzers in IBVAP.
    Enforces clean separation between environment observation and perception/tracking layers.
    """

    @abstractmethod
    def analyze(self, frame_packet: FramePacket) -> EnvironmentState:
        """
        Analyzes the incoming FramePacket and returns a structured EnvironmentState.
        """
        pass

    @abstractmethod
    def get_state(self, camera_id: str) -> Optional[EnvironmentState]:
        """
        Returns the latest recorded environment state for the specified camera.
        """
        pass

    @abstractmethod
    def reset(self, camera_id: Optional[str] = None) -> None:
        """
        Resets temporal filter state and smoothed metrics for a camera (or all cameras).
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Releases analyzer resources cleanly.
        """
        pass
