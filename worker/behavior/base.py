from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..tracking.schemas import TrackState
from ..spatial.schemas import SpatialState
from ..environment.schemas import EnvironmentState
from .schemas import BehaviorPrimitive, BehaviorConfig


class BehaviorEngineInterface(ABC):
    """
    Abstract Base Class for behavioral analytics and temporal pattern reasoning.
    Enforces clean separation between behavioral observation and threat/risk assessment.
    """

    @abstractmethod
    def configure(self, camera_id: str, config: BehaviorConfig) -> None:
        """Configures temporal thresholds and parameters for a specific camera."""
        pass

    @abstractmethod
    def process(
        self,
        tracks: List[TrackState],
        spatial_states: List[SpatialState],
        timestamp_utc: datetime,
        environment_state: Optional[EnvironmentState] = None,
    ) -> List[BehaviorPrimitive]:
        """
        Evaluates temporal and spatial trajectories of active tracks to produce BehaviorPrimitive instances.
        """
        pass

    @abstractmethod
    def get_active_behaviors(self, camera_id: str) -> List[BehaviorPrimitive]:
        """Returns all currently active behaviors for a specific camera."""
        pass

    @abstractmethod
    def reset(self, camera_id: Optional[str] = None) -> None:
        """Resets temporal tracking history and active behaviors for one or all cameras."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Releases resources cleanly."""
        pass
