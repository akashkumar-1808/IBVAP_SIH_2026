"""
Abstract Base Class for Structured Evidence Packaging Subsystem.

Defines the contract for creating cryptographically sealed, verifiable
Evidence Packages from qualified EventRecord instances and frame buffers.

Architecture Decision: DEC-0008
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from datetime import datetime
import numpy as np

from .schemas import EvidencePackage, EvidencePackageConfig
from ..fusion.schemas import EventRecord
from ..tracking.schemas import TrackState
from ..spatial.schemas import SpatialState, CameraSpatialConfig
from ..spatial.world_schemas import ProjectedBorder
from ..ingestion import FramePacket


class EvidencePackagerInterface(ABC):
    """Abstract interface for evidence packaging."""

    @abstractmethod
    def add_frame(self, frame_packet: FramePacket) -> None:
        """Buffers an incoming camera frame in the rolling ring buffer."""
        pass

    @abstractmethod
    def create_package(
        self,
        event: EventRecord,
        track: Optional[TrackState] = None,
        spatial_state: Optional[SpatialState] = None,
        projected_borders: Optional[List[ProjectedBorder]] = None,
        spatial_config: Optional[CameraSpatialConfig] = None,
        current_frame: Optional[np.ndarray] = None,
        force_repackage: bool = False,
    ) -> EvidencePackage:
        """
        Extracts snapshots, compiles pre/post/incident video clips, generates
        audit manifest, seals with SHA-256 hashes, and returns a verified EvidencePackage.
        """
        pass

    @abstractmethod
    def verify_package(self, manifest_path: str) -> Tuple[bool, List[str]]:
        """Verifies the cryptographic integrity and chain of custody of a package."""
        pass

    @abstractmethod
    def reset(self, camera_id: Optional[str] = None) -> None:
        """Resets frame buffers and packaging state."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Cleans up resources."""
        pass
