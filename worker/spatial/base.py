from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..tracking.schemas import TrackState
from .schemas import SpatialState, CameraSpatialConfig


class SpatialEngineInterface(ABC):
    """
    Abstract Base Class for spatial intelligence and camera-relative geometry reasoning.
    Enforces clean separation between 2D geometry evaluation and behavior/risk reasoning.
    """

    @abstractmethod
    def configure_camera(self, config: CameraSpatialConfig) -> None:
        """
        Registers or updates the spatial zones, virtual fences, and threat vectors for a camera.
        """
        pass

    @abstractmethod
    def process_tracks(
        self,
        tracks: List[TrackState],
        camera_id: str,
        timestamp_utc: datetime,
    ) -> List[SpatialState]:
        """
        Processes active object tracks against camera spatial geometry and produces SpatialState records.
        """
        pass

    @abstractmethod
    def get_spatial_state(self, camera_id: str, track_id: int) -> Optional[SpatialState]:
        """
        Returns the latest recorded spatial state for a specific track.
        """
        pass

    @abstractmethod
    def reset(self, camera_id: Optional[str] = None) -> None:
        """
        Resets track spatial history and transition states for a camera (or all cameras).
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Releases engine resources cleanly.
        """
        pass
