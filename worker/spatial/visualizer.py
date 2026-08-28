from typing import List, Tuple, Dict, Optional
import cv2
import numpy as np
from .schemas import (
    SpatialState,
    CameraSpatialConfig,
    ZoneType,
    MovementDirection,
)

ZONE_COLORS: Dict[ZoneType, Tuple[int, int, int]] = {
    ZoneType.CRITICAL: (0, 0, 220),       # Red
    ZoneType.RESTRICTED: (0, 120, 255),   # Orange
    ZoneType.BUFFER: (0, 220, 255),       # Yellow
    ZoneType.SAFE: (0, 200, 0),           # Green
}


def draw_spatial_overlay(
    image: np.ndarray,
    config: CameraSpatialConfig,
    spatial_states: Optional[List[SpatialState]] = None,
    alpha: float = 0.20,
) -> np.ndarray:
    """
    Renders semi-transparent spatial zones, virtual fences, and spatial direction badges onto an image.
    Returns a newly annotated BGR image without mutating the input array.
    """
    if image is None or image.size == 0:
        return image

    annotated = image.copy()
    overlay = image.copy()

    # 1. Draw Zone Polygons
    for zone in config.zones:
        if not zone.is_active or len(zone.polygon) < 3:
            continue

        color = ZONE_COLORS.get(zone.type, (180, 180, 180))
        pts = np.array(zone.polygon, dtype=np.int32).reshape((-1, 1, 2))

        # Fill transparent polygon on overlay
        cv2.fillPoly(overlay, [pts], color)
        # Draw solid contour boundary
        cv2.polylines(annotated, [pts], True, color, 2, cv2.LINE_AA)

        # Draw Zone label
        if len(zone.polygon) > 0:
            lx, ly = int(zone.polygon[0][0]), int(zone.polygon[0][1])
            label_text = f"ZONE: {zone.name} ({zone.type.value.upper()})"
            cv2.putText(annotated, label_text, (lx + 5, ly + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    # Blend polygon fills
    cv2.addWeighted(overlay, alpha, annotated, 1.0 - alpha, 0, annotated)

    # 2. Draw Virtual Fences
    for fence in config.fences:
        if not fence.is_active:
            continue

        p1 = (int(round(fence.start_point[0])), int(round(fence.start_point[1])))
        p2 = (int(round(fence.end_point[0])), int(round(fence.end_point[1])))

        # Draw thick virtual boundary line
        cv2.line(annotated, p1, p2, (255, 0, 255), 3, cv2.LINE_AA)
        cv2.circle(annotated, p1, 4, (255, 0, 255), -1)
        cv2.circle(annotated, p2, 4, (255, 0, 255), -1)

        mid_x = int((p1[0] + p2[0]) / 2)
        mid_y = int((p1[1] + p2[1]) / 2)
        cv2.putText(annotated, f"FENCE: {fence.name}", (mid_x, mid_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 1, cv2.LINE_AA)

    # 3. Draw Spatial Badges if states are provided
    if spatial_states:
        for st in spatial_states:
            if st.crossing_events:
                for ev in st.crossing_events:
                    if ev.crossing_point:
                        ix, iy = int(ev.crossing_point[0]), int(ev.crossing_point[1])
                        cv2.drawMarker(annotated, (ix, iy), (0, 0, 255), cv2.MARKER_CROSS, 20, 3)
                        cv2.putText(annotated, f"CROSSING ID #{ev.track_id}", (ix + 10, iy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    return annotated
