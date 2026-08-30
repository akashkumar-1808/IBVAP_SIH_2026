"""
Abstract Base Class for Multi-Modal Evidence Fusion Engine.

Defines the contract for combining Tracking, Spatial, Environment, and Behavior
observations into explainable, prioritized EventRecord instances.

Architecture Decision: DEC-0007
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..tracking.schemas import TrackState
from ..spatial.schemas import SpatialState
from ..environment.schemas import EnvironmentState
from ..behavior.schemas import BehaviorPrimitive
from .schemas import EventRecord, FusionConfig


class FusionEngineInterface(ABC):
    """
    Abstract Base Class for Multi-Modal Evidence Fusion.
    Enforces strict architectural boundaries and testability.
    """

    @abstractmethod
    def configure(self, camera_id: str, config: FusionConfig) -> None:
        """Configures weights and operational parameters for a specific camera."""
        pass

    @abstractmethod
    def process(
        self,
        tracks: List[TrackState],
        spatial_states: List[SpatialState],
        environment_state: Optional[EnvironmentState],
        behavior_primitives: List[BehaviorPrimitive],
        camera_id: str,
        timestamp_utc: datetime,
    ) -> List[EventRecord]:
        """
        Fuses multi-modal observations and produces or updates canonical EventRecords.
        """
        pass

    @abstractmethod
    def get_active_events(self, camera_id: Optional[str] = None) -> List[EventRecord]:
        """Returns all currently active EventRecords for a camera (or all cameras)."""
        pass

    @abstractmethod
    def acknowledge_event(self, event_id: str, acknowledged_by: str, timestamp_utc: datetime) -> bool:
        """Marks an active or historical event as acknowledged by an operator."""
        pass

    @abstractmethod
    def reset(self, camera_id: Optional[str] = None) -> None:
        """Resets active events, cooldowns, and track history for a camera (or all cameras)."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Cleans up engine resources."""
        pass
