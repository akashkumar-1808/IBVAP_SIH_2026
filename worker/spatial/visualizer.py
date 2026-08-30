"""
Spatial overlay visualization for IBVAP.

Renders spatial zones, virtual fences, projected world borders,
warning buffer zones, ground-contact points, border side annotations,
and crossing status badges onto camera frames.

Architecture Decision: DEC-0006
"""

from typing import List, Tuple, Dict, Optional
import cv2
import numpy as np
from .schemas import (
    SpatialState,
    CameraSpatialConfig,
    ZoneType,
    MovementDirection,
    BorderSide,
    CrossingStatus,
    SpatialConfidence,
)
from .world_schemas import ProjectedBorder

ZONE_COLORS: Dict[ZoneType, Tuple[int, int, int]] = {
    ZoneType.CRITICAL: (0, 0, 220),       # Red
    ZoneType.RESTRICTED: (0, 120, 255),   # Orange
    ZoneType.BUFFER: (0, 220, 255),       # Yellow
    ZoneType.SAFE: (0, 200, 0),           # Green
}

SIDE_COLORS: Dict[BorderSide, Tuple[int, int, int]] = {
    BorderSide.PERMITTED: (0, 200, 0),        # Green
    BorderSide.WARNING_BUFFER: (0, 220, 255), # Yellow
    BorderSide.BORDER_LINE: (255, 0, 255),    # Magenta
    BorderSide.RESTRICTED: (0, 0, 255),       # Red
    BorderSide.UNKNOWN: (180, 180, 180),      # Gray
}


def draw_spatial_overlay(
    image: np.ndarray,
    config: CameraSpatialConfig,
    spatial_states: Optional[List[SpatialState]] = None,
    projected_borders: Optional[List[ProjectedBorder]] = None,
    alpha: float = 0.20,
) -> np.ndarray:
    """
    Renders semi-transparent spatial zones, virtual fences, projected world borders,
    ground-contact points, and spatial state badges onto an image.
    Returns a newly annotated BGR image without mutating the input array.
    """
    if image is None or image.size == 0:
        return image

    annotated = image.copy()
    overlay = image.copy()

    # 1. Draw Zone Polygons (Legacy)
    for zone in config.zones:
        if not zone.is_active or len(zone.polygon) < 3:
            continue

        color = ZONE_COLORS.get(zone.type, (180, 180, 180))
        pts = np.array(zone.polygon, dtype=np.int32).reshape((-1, 1, 2))

        cv2.fillPoly(overlay, [pts], color)
        cv2.polylines(annotated, [pts], True, color, 2, cv2.LINE_AA)

        if len(zone.polygon) > 0:
            lx, ly = int(zone.polygon[0][0]), int(zone.polygon[0][1])
            label_text = f"ZONE: {zone.name} ({zone.type.value.upper()})"
            cv2.putText(annotated, label_text, (lx + 5, ly + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    cv2.addWeighted(overlay, alpha, annotated, 1.0 - alpha, 0, annotated)

    # 2. Draw Virtual Fences (Legacy)
    for fence in config.fences:
        if not fence.is_active:
            continue

        p1 = (int(round(fence.start_point[0])), int(round(fence.start_point[1])))
        p2 = (int(round(fence.end_point[0])), int(round(fence.end_point[1])))

        cv2.line(annotated, p1, p2, (255, 0, 255), 3, cv2.LINE_AA)
        cv2.circle(annotated, p1, 4, (255, 0, 255), -1)
        cv2.circle(annotated, p2, 4, (255, 0, 255), -1)

        mid_x = int((p1[0] + p2[0]) / 2)
        mid_y = int((p1[1] + p2[1]) / 2)
        cv2.putText(annotated, f"FENCE: {fence.name}", (mid_x, mid_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 1, cv2.LINE_AA)

    # 3. Draw Projected World Borders
    if projected_borders:
        for proj in projected_borders:
            if len(proj.projected_points) >= 2:
                pts = [(int(round(p[0])), int(round(p[1]))) for p in proj.projected_points]
                for i in range(len(pts) - 1):
                    cv2.line(annotated, pts[i], pts[i + 1], (0, 255, 255), 3, cv2.LINE_AA)

                # Label
                mid_idx = len(pts) // 2
                cv2.putText(
                    annotated,
                    f"WORLD BORDER: {proj.border_section_id} (v{proj.calibration_version})",
                    (pts[mid_idx][0], pts[mid_idx][1] - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 255), 2, cv2.LINE_AA,
                )

                # Draw endpoints
                for pt in pts:
                    cv2.circle(annotated, pt, 5, (0, 255, 255), -1)

            # Draw warning buffer boundary
            if proj.warning_buffer_points and len(proj.warning_buffer_points) >= 2:
                buf_pts = [(int(round(p[0])), int(round(p[1]))) for p in proj.warning_buffer_points]
                for i in range(len(buf_pts) - 1):
                    cv2.line(annotated, buf_pts[i], buf_pts[i + 1], (0, 200, 255), 2, cv2.LINE_AA)

    # 4. Draw Spatial Badges and Ground-Contact Points
    if spatial_states:
        for st in spatial_states:
            # Legacy fence crossing markers
            if st.crossing_events:
                for ev in st.crossing_events:
                    if ev.crossing_point:
                        ix, iy = int(ev.crossing_point[0]), int(ev.crossing_point[1])
                        cv2.drawMarker(annotated, (ix, iy), (0, 0, 255), cv2.MARKER_CROSS, 20, 3)
                        cv2.putText(annotated, f"CROSSING ID #{ev.track_id}", (ix + 10, iy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            # Ground-contact point marker
            if st.ground_contact is not None:
                gx, gy = int(round(st.ground_contact.pixel_xy[0])), int(round(st.ground_contact.pixel_xy[1]))
                gc_color = SIDE_COLORS.get(st.border_side, (180, 180, 180)) if st.border_side else (0, 255, 0)
                cv2.circle(annotated, (gx, gy), 4, gc_color, -1)
                cv2.circle(annotated, (gx, gy), 6, gc_color, 1)

            # Border side annotation
            if st.border_side is not None and st.border_side != BorderSide.UNKNOWN:
                side_label = st.border_side.value.upper()
                side_color = SIDE_COLORS.get(st.border_side, (180, 180, 180))
                if st.ground_contact:
                    gx, gy = int(round(st.ground_contact.pixel_xy[0])), int(round(st.ground_contact.pixel_xy[1]))
                    cv2.putText(annotated, side_label, (gx + 8, gy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.40, side_color, 1, cv2.LINE_AA)

            # Crossing status badge
            if st.crossing_status == CrossingStatus.CONFIRMED_CROSSING:
                if st.ground_contact:
                    gx, gy = int(round(st.ground_contact.pixel_xy[0])), int(round(st.ground_contact.pixel_xy[1]))
                    cv2.putText(annotated, "CONFIRMED CROSSING", (gx - 60, gy - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2, cv2.LINE_AA)
                    cv2.drawMarker(annotated, (gx, gy), (0, 0, 255), cv2.MARKER_STAR, 20, 2)

    return annotated
