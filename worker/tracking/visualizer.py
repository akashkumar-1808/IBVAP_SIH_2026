from typing import List, Tuple, Dict
import cv2
import numpy as np
from .schemas import TrackState, TrackStatus

STATUS_COLORS: Dict[TrackStatus, Tuple[int, int, int]] = {
    TrackStatus.TRACKED: (0, 255, 0),     # Bright Green
    TrackStatus.CANDIDATE: (0, 255, 255), # Yellow
    TrackStatus.LOST: (0, 140, 255),      # Orange
    TrackStatus.EXPIRED: (128, 128, 128), # Gray
}


def draw_tracks(
    image: np.ndarray,
    tracks: List[TrackState],
    draw_trajectory: bool = True,
    line_thickness: int = 2,
    font_scale: float = 0.5,
) -> np.ndarray:
    """
    Renders bounding boxes, persistent Track IDs, status badges, and trajectory trails onto an image.
    Returns a newly annotated BGR image without mutating the original input.
    """
    if image is None or image.size == 0:
        return image

    annotated = image.copy()

    for track in tracks:
        color = STATUS_COLORS.get(track.status, (0, 255, 0))
        bbox = track.bbox

        x1 = int(round(bbox.x_min))
        y1 = int(round(bbox.y_min))
        x2 = int(round(bbox.x_max))
        y2 = int(round(bbox.y_max))

        # Clamp to image bounds
        x1 = max(0, min(x1, annotated.shape[1] - 1))
        y1 = max(0, min(y1, annotated.shape[0] - 1))
        x2 = max(0, min(x2, annotated.shape[1] - 1))
        y2 = max(0, min(y2, annotated.shape[0] - 1))

        # Draw bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, line_thickness)

        # Draw Track ID header: e.g. "ID #17 | person"
        label_text = f"ID #{track.track_id} | {track.class_id.value} ({track.status.value})"
        (text_w, text_h), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)

        label_y1 = max(0, y1 - text_h - 4)
        cv2.rectangle(
            annotated,
            (x1, label_y1),
            (x1 + text_w + 4, label_y1 + text_h + baseline + 2),
            color,
            -1,
        )
        cv2.putText(
            annotated,
            label_text,
            (x1 + 2, label_y1 + text_h + 1),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )

        # Draw trajectory trailing line
        if draw_trajectory and len(track.trajectory) > 1:
            pts = [(int(round(p.x)), int(round(p.y))) for p in track.trajectory]
            for i in range(1, len(pts)):
                cv2.line(annotated, pts[i - 1], pts[i], color, 2, cv2.LINE_AA)

    return annotated
