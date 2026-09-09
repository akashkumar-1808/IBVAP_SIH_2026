from typing import List, Tuple, Dict, Any, Optional
import cv2
import numpy as np
from .schemas import Detection, TargetClass, HumanPose, SKELETON_CONNECTIONS

CLASS_COLORS: Dict[TargetClass, Tuple[int, int, int]] = {
    TargetClass.PERSON: (0, 255, 255),    # Yellow/Cyan in BGR: (0, 255, 255)
    TargetClass.VEHICLE: (0, 165, 255),   # Orange in BGR
    TargetClass.ANIMAL: (255, 0, 255),    # Magenta in BGR
    TargetClass.UNKNOWN: (180, 180, 180), # Gray in BGR
}

SKELETON_COLORS: Dict[Tuple[str, str], Tuple[int, int, int]] = {
    # Torso
    ("left_shoulder", "right_shoulder"): (0, 255, 255),
    ("left_shoulder", "left_hip"): (0, 255, 255),
    ("right_shoulder", "right_hip"): (0, 255, 255),
    ("left_hip", "right_hip"): (0, 255, 255),
    # Arms (left: cyan, right: orange)
    ("left_shoulder", "left_elbow"): (255, 255, 0),
    ("left_elbow", "left_wrist"): (255, 255, 0),
    ("right_shoulder", "right_elbow"): (0, 165, 255),
    ("right_elbow", "right_wrist"): (0, 165, 255),
    # Legs (left: green, right: magenta)
    ("left_hip", "left_knee"): (0, 255, 0),
    ("left_knee", "left_ankle"): (0, 255, 0),
    ("right_hip", "right_knee"): (255, 0, 255),
    ("right_knee", "right_ankle"): (255, 0, 255),
    # Head / Face
    ("nose", "left_eye"): (0, 200, 255),
    ("nose", "right_eye"): (0, 200, 255),
    ("left_eye", "left_ear"): (0, 200, 255),
    ("right_eye", "right_ear"): (0, 200, 255),
}


def draw_human_pose(
    image: np.ndarray,
    pose: Any,
    min_confidence: float = 0.25,
) -> np.ndarray:
    """
    Renders human skeleton joints and bone connection lines onto an image.
    Supports HumanPose instance or dict representation.
    """
    if image is None or image.size == 0 or pose is None:
        return image

    kps = getattr(pose, "keypoints", None)
    if kps is None and isinstance(pose, dict):
        kps = pose.get("keypoints")

    if not kps or not isinstance(kps, dict):
        return image

    # 1. Draw Bones / Connections
    for (u_name, v_name), b_color in SKELETON_COLORS.items():
        pt_u = kps.get(u_name)
        pt_v = kps.get(v_name)
        if pt_u and pt_v:
            conf_u = getattr(pt_u, "confidence", 1.0)
            conf_v = getattr(pt_v, "confidence", 1.0)
            vis_u = getattr(pt_u, "visible", True)
            vis_v = getattr(pt_v, "visible", True)
            if vis_u and vis_v and conf_u >= min_confidence and conf_v >= min_confidence:
                ux = int(round(getattr(pt_u, "x", 0)))
                uy = int(round(getattr(pt_u, "y", 0)))
                vx = int(round(getattr(pt_v, "x", 0)))
                vy = int(round(getattr(pt_v, "y", 0)))
                cv2.line(image, (ux, uy), (vx, vy), b_color, 2, cv2.LINE_AA)

    # 2. Draw Joint Dots
    for name, pt in kps.items():
        conf = getattr(pt, "confidence", 1.0)
        vis = getattr(pt, "visible", True)
        if vis and conf >= min_confidence:
            px = int(round(getattr(pt, "x", 0)))
            py = int(round(getattr(pt, "y", 0)))
            cv2.circle(image, (px, py), 3, (0, 0, 255), -1, cv2.LINE_AA)
            cv2.circle(image, (px, py), 4, (255, 255, 255), 1, cv2.LINE_AA)

    return image


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

        # Draw optional pose skeleton
        if det.keypoints is not None:
            draw_human_pose(annotated, det.keypoints)

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
