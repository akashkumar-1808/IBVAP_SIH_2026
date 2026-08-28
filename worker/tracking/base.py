from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from .schemas import Detection, TrackState


class TrackerInterface(ABC):
    """
    Abstract Base Class for multi-object tracking engines in IBVAP.
    Enforces clean separation between frame-level detections and temporal track persistence.
    """

    @abstractmethod
    def update(
        self,
        detections: List[Detection],
        frame_id: int,
        timestamp_utc: datetime,
        camera_id: Optional[str] = None,
    ) -> List[TrackState]:
        """
        Updates tracking state with detections from the current video frame.
        Returns a list of active TrackState objects.
        """
        pass

    @abstractmethod
    def get_tracks(self) -> List[TrackState]:
        """
        Returns all current tracks (candidate, tracked, lost) maintained by the tracker.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """
        Resets all active tracks, trajectory buffers, and ID sequences.
        Called on video replay restarts, camera disconnections, or manual resets.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Releases internal memory and resources cleanly.
        """
        pass
