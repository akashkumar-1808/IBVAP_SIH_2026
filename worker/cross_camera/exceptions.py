"""
Exceptions for Cross-Camera Association and Border-Level Tracking.

Architecture Decision: DEC-0009
"""

class CrossCameraError(Exception):
    """Base exception for all cross-camera tracking operations."""
    pass


class InvalidTopologyError(CrossCameraError):
    """Raised when an invalid camera transition or topology graph is defined."""
    pass


class AssociationError(CrossCameraError):
    """Raised when an error occurs during cross-camera track association."""
    pass
