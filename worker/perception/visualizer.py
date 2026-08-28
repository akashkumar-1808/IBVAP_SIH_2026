from typing import List, Tuple, Dict
import cv2
import numpy as np
from .schemas import Detection, TargetClass

CLASS_COLORS: Dict[TargetClass, Tuple[int, int, int]] = {
    TargetClass.PERSON: (0, 255, 255),    # Yellow/Cyan in BGR: (0, 255, 255)
    TargetClass.VEHICLE: (0, 165, 255),   # Orange in BGR
    TargetClass.ANIMAL: (255, 0, 255),    # Magenta in BGR
    TargetClass.UNKNOWN: (180, 180, 180), # Gray in BGR
}


def draw_detections(
    image: np.ndarray,
    detections: List[Detection],
    line_thickness: int = 2,
    font_scale: float = 0.5,
) -> np.ndarray:
    """
    Renders bounding boxes, class labels, and confidence scores onto an image for debug/verification.
    Returns a newly annotated BGR image without mutating the original input.
    """
    if image is None or image.size == 0:
        return image

    annotated = image.copy()

    for det in detections:
        color = CLASS_COLORS.get(det.class_id, (0, 255, 0))
        bbox = det.bbox

        x1 = int(round(bbox.x_min))
        y1 = int(round(bbox.y_min))
        x2 = int(round(bbox.x_max))
        y2 = int(round(bbox.y_max))

        # Clamp to image boundaries
        x1 = max(0, min(x1, annotated.shape[1] - 1))
        y1 = max(0, min(y1, annotated.shape[0] - 1))
        x2 = max(0, min(x2, annotated.shape[1] - 1))
        y2 = max(0, min(y2, annotated.shape[0] - 1))

        # Draw bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, line_thickness)

        # Draw label header
        raw_name = det.metadata.get("raw_class_name", det.class_id.value)
        label_text = f"{raw_name}: {det.confidence:.2f}"
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

    return annotated
