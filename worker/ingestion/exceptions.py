class VideoSourceError(Exception):
    """Base exception for all video ingestion errors."""
    pass


class VideoFileNotFoundError(VideoSourceError):
    """Raised when the specified video file path does not exist."""
    pass


class VideoDecodeError(VideoSourceError):
    """Raised when video frames cannot be decoded or file is corrupted."""
    pass


class RTSPConnectionError(VideoSourceError):
    """Raised when connecting to an RTSP endpoint fails."""
    pass


class RTSPTimeoutError(VideoSourceError):
    """Raised when an RTSP stream read times out."""
    pass


class QueueClosedError(Exception):
    """Raised when attempting to operate on a closed BoundedFrameQueue."""
    pass
