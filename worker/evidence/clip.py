"""
Video Clip Packaging and MP4 Encoding Engine.

Compiles cached pre-event, event-duration, and post-event frames into
compact, standard MP4 video clips for forensic playback.

Architecture Decision: DEC-0008
"""

import os
import cv2
import logging
from typing import List, Optional
from datetime import datetime

from .buffer import BufferedFrame
from .exceptions import EncodingError, BufferUnderflowError

logger = logging.getLogger(__name__)


class ClipPackager:
    """Encodes a sequence of video frames into an MP4 video file."""

    @staticmethod
    def encode_clip(
        frames: List[BufferedFrame],
        destination_path: str,
        fps: float = 25.0,
    ) -> str:
        """
        Encodes a list of BufferedFrames into an MP4 file.

        Args:
            frames: Chronologically ordered list of BufferedFrame objects.
            destination_path: Absolute or relative output .mp4 file path.
            fps: Playback and encoding frame rate.

        Returns:
            The output destination file path.
        """
        if not frames:
            raise BufferUnderflowError("Cannot encode empty frame sequence into video clip.")

        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        h, w = frames[0].image.shape[:2]

        # Try standard mp4v fourcc first, with fallback to avc1
        codecs = ["mp4v", "avc1", "XVID"]
        writer = None
        used_codec = None

        for codec_str in codecs:
            fourcc = cv2.VideoWriter_fourcc(*codec_str)
            writer = cv2.VideoWriter(destination_path, fourcc, fps, (w, h))
            if writer.isOpened():
                used_codec = codec_str
                break

        if writer is None or not writer.isOpened():
            raise EncodingError(f"Failed to initialize VideoWriter for destination '{destination_path}'")

        try:
            for bf in frames:
                # Ensure frame matches dimensions
                frame_img = bf.image
                if frame_img.shape[:2] != (h, w):
                    frame_img = cv2.resize(frame_img, (w, h))
                writer.write(frame_img)
        finally:
            writer.release()

        # Check that file was created and is non-empty
        if not os.path.exists(destination_path) or os.path.getsize(destination_path) == 0:
            raise EncodingError(f"Encoded video clip file at '{destination_path}' is missing or empty.")

        logger.info(f"Encoded evidence clip ({len(frames)} frames, {len(frames)/fps:.2f}s) to '{destination_path}' using codec '{used_codec}'")
        return destination_path
