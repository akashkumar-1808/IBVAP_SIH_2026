"""
Video streaming endpoints delivering MJPEG / JPEG frames to the browser console.

Architecture Decision: DEC-0010 / DEC-0011
"""

import time
import cv2
import numpy as np
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response

router = APIRouter(prefix="/streams", tags=["Video Streams"])

# Shared in-memory frame cache updated by active workers/replays: camera_id -> (jpeg_bytes, timestamp)
_LATEST_FRAMES: Dict[str, tuple[bytes, float]] = {}


def update_latest_frame(camera_id: str, frame_bgr: np.ndarray) -> None:
    """Helper called by pipeline or scenarios to update the live stream buffer."""
    _, encoded = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 75])
    _LATEST_FRAMES[camera_id] = (encoded.tobytes(), time.time())


def _generate_fallback_frame(camera_id: str) -> bytes:
    """Generates an operational command-console visual frame when stream is initializing."""
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    # Dark terrain
    cv2.rectangle(img, (0, 0), (1280, 420), (30, 35, 30), -1)
    cv2.rectangle(img, (0, 420), (1280, 720), (20, 22, 28), -1)
    # Calibrated border line
    cv2.line(img, (100, 480), (1180, 320), (0, 0, 255), 2)
    cv2.line(img, (100, 420), (1180, 260), (0, 165, 255), 1)
    cv2.putText(img, "IBVAP LIVE VIDEO STREAM", (480, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
    cv2.putText(img, f"CAMERA: {camera_id} | CONNECTING...", (470, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 1)
    _, enc = cv2.imencode(".jpg", img)
    return enc.tobytes()


def _frame_generator(camera_id: str):
    """Yields multipart/x-mixed-replace MJPEG frame stream, preserving last processed frame indefinitely."""
    while True:
        frame_data = _LATEST_FRAMES.get(camera_id)
        if frame_data:
            # Always preserve and stream the last processed/annotated frame on EOF
            jpg_bytes = frame_data[0]
        else:
            jpg_bytes = _generate_fallback_frame(camera_id)

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpg_bytes + b"\r\n"
        )
        time.sleep(0.04)  # ~25 FPS stream pacing


@router.get("/{camera_id}/live")
def stream_live_video(camera_id: str):
    """Streams live MJPEG video for the requested camera to browser <img> elements."""
    return StreamingResponse(
        _frame_generator(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/{camera_id}/snapshot")
def get_live_snapshot(camera_id: str):
    """Returns the most recent single JPEG keyframe."""
    frame_data = _LATEST_FRAMES.get(camera_id)
    if frame_data:
        return Response(content=frame_data[0], media_type="image/jpeg")
    return Response(content=_generate_fallback_frame(camera_id), media_type="image/jpeg")
