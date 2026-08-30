"""
Exceptions for IBVAP Multi-Modal Evidence Fusion Engine.
"""

class FusionError(Exception):
    """Base exception for all fusion engine errors."""
    pass


class InvalidFusionConfigError(FusionError):
    """Raised when fusion weights or thresholds are invalid or non-normalized."""
    pass


class EvidenceExtractionError(FusionError):
    """Raised when structured evidence extraction encounters malformed inputs."""
    pass
