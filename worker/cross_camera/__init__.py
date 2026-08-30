"""
IBVAP Cross-Camera Association & Persistent Border Tracking Module.

Architecture Decision: DEC-0009
"""

from .exceptions import CrossCameraError, InvalidTopologyError, AssociationError
from .schemas import (
    AssociationState,
    AssociationSignal,
    CameraTransitionRule,
    CameraTopology,
    BorderTrack,
)
from .associator import CrossCameraAssociator

__all__ = [
    "CrossCameraError",
    "InvalidTopologyError",
    "AssociationError",
    "AssociationState",
    "AssociationSignal",
    "CameraTransitionRule",
    "CameraTopology",
    "BorderTrack",
    "CrossCameraAssociator",
]
