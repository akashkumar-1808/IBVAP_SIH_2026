class TrackingError(Exception):
    """Base exception for all tracking errors."""
    pass


class InvalidDetectionError(TrackingError):
    """Raised when incoming detection list or detection object is malformed or invalid."""
    pass


class TrackerNotInitializedError(TrackingError):
    """Raised when trying to perform tracking operations before initialization."""
    pass
