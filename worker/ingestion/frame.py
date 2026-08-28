from datetime import datetime, timezone
from typing import Optional, Dict, Any
import numpy as np


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FramePacket:
    """
    Canonical video frame packet passed from the ingestion subsystem
    to downstream AI analytics workers.

    Image coordinate convention:
    - Origin (0, 0) is the top-left corner of the frame.
    - X-axis increases to the right [0, width - 1].
    - Y-axis increases downwards [0, height - 1].
    - Colorspace is standard BGR uint8 NumPy ndarray (OpenCV native).
    """

    __slots__ = (
        "camera_id",
        "frame_id",
        "timestamp_utc",
        "image",
        "width",
        "height",
        "source_type",
        "source_fps",
        "sequence_number",
        "metadata",
    )

    def __init__(
        self,
        camera_id: str,
        frame_id: int,
        timestamp_utc: datetime,
        image: np.ndarray,
        width: int,
        height: int,
        source_type: str = "file",
        source_fps: Optional[float] = None,
        sequence_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.camera_id = camera_id
        self.frame_id = frame_id
        self.timestamp_utc = timestamp_utc
        self.image = image
        self.width = width
        self.height = height
        self.source_type = source_type
        self.source_fps = source_fps
        self.sequence_number = sequence_number if sequence_number is not None else frame_id
        self.metadata = metadata or {}

    @property
    def shape(self):
        return self.image.shape

    def __repr__(self) -> str:
        return (
            f"FramePacket(camera_id='{self.camera_id}', frame_id={self.frame_id}, "
            f"timestamp={self.timestamp_utc.isoformat()}, size={self.width}x{self.height}, "
            f"source={self.source_type})"
        )
