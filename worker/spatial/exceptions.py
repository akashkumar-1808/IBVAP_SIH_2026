class SpatialError(Exception):
    """Base exception for all spatial engine and geometry errors."""
    pass


class InvalidGeometryError(SpatialError):
    """Raised when a polygon, fence, or point configuration is invalid, degenerate, or has fewer than required vertices."""
    pass


class ConfigurationError(SpatialError):
    """Raised when camera spatial configuration is invalid or missing required parameters."""
    pass
