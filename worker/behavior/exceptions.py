class BehaviorError(Exception):
    """Base domain exception for behavioral analytics engine."""
    pass


class InvalidBehaviorConfigError(BehaviorError):
    """Raised when behavioral parameters, windows, or thresholds are invalid."""
    pass
