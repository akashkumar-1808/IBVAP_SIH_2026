class EnvironmentAnalysisError(Exception):
    """Base exception for all environment analysis errors."""
    pass


class InvalidFrameError(EnvironmentAnalysisError):
    """Raised when an empty, None, or invalid shape frame is passed to analyzer."""
    pass
