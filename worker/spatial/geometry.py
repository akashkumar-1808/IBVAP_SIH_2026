import math
from typing import List, Tuple, Optional
import numpy as np
from .schemas import MovementDirection


def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """
    Deterministic Point-in-Polygon test using the Ray-Casting algorithm.
    Includes boundary vertices and edges within numerical tolerance (epsilon=1e-5).
    point: (x, y)
    polygon: List of (x, y) vertices
    Returns: True if point is inside or on the boundary of polygon, False otherwise.
    """
    if len(polygon) < 3:
        return False

    px, py = float(point[0]), float(point[1])
    n = len(polygon)
    inside = False

    # Check for boundary inclusion first
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]

        # Check if point is close to segment [ (x1, y1), (x2, y2) ]
        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx * dx + dy * dy

        if length_sq > 1e-9:
            # Projection factor t
            t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            dist_sq = (px - proj_x) ** 2 + (py - proj_y) ** 2
            if dist_sq < 1e-6:
                return True

    # Standard Ray-Casting algorithm (horizontal ray to +infinity)
    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if py > min(p1y, p2y):
            if py <= max(p1y, p2y):
                if px <= max(p1x, p2x):
                    if p1y != p2y:
                        x_inters = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or px <= x_inters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def _cross_product(o: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """2D cross product of vector OA and OB: (ax - ox)*(by - oy) - (ay - oy)*(bx - ox)."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def segments_intersect(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    q1: Tuple[float, float],
    q2: Tuple[float, float],
) -> Tuple[bool, Optional[Tuple[float, float]]]:
    """
    Tests whether segment P (p1 -> p2) and segment Q (q1 -> q2) strictly cross each other.
    Returns: (is_crossing, intersection_point)
    """
    d1 = _cross_product(q1, q2, p1)
    d2 = _cross_product(q1, q2, p2)
    d3 = _cross_product(p1, p2, q1)
    d4 = _cross_product(p1, p2, q2)

    # Strict crossing test (endpoints lie on strictly opposite sides)
    if ((d1 > 1e-5 and d2 < -1e-5) or (d1 < -1e-5 and d2 > 1e-5)) and \
       ((d3 > 1e-5 and d4 < -1e-5) or (d3 < -1e-5 and d4 > 1e-5)):

        # Compute exact intersection point
        denom = (p1[0] - p2[0]) * (q1[1] - q2[1]) - (p1[1] - p2[1]) * (q1[0] - q2[0])
        if abs(denom) < 1e-9:
            return False, None

        t = ((p1[0] - q1[0]) * (q1[1] - q2[1]) - (p1[1] - q1[1]) * (q1[0] - q2[0])) / denom
        ix = p1[0] + t * (p2[0] - p1[0])
        iy = p1[1] + t * (p2[1] - p1[1])
        return True, (float(ix), float(iy))

    return False, None


def calculate_movement_direction(
    prev_point: Tuple[float, float],
    curr_point: Tuple[float, float],
    expected_vector: Optional[Tuple[float, float]],
    min_movement_dist: float = 3.0,
) -> MovementDirection:
    """
    Evaluates track movement direction relative to camera's expected threat/border vector.
    prev_point: (x1, y1)
    curr_point: (x2, y2)
    expected_vector: [dx, dy] pointing toward the border/restricted direction
    """
    if expected_vector is None:
        return MovementDirection.UNCERTAIN

    dx = curr_point[0] - prev_point[0]
    dy = curr_point[1] - prev_point[1]
    dist = math.hypot(dx, dy)

    # Deadband threshold: negligible movement is classified as UNCERTAIN
    if dist < min_movement_dist:
        return MovementDirection.UNCERTAIN

    edx = expected_vector[0]
    edy = expected_vector[1]
    e_norm = math.hypot(edx, edy)
    if e_norm < 1e-6:
        return MovementDirection.UNCERTAIN

    # Cosine similarity between track displacement and expected vector
    cos_sim = (dx * edx + dy * edy) / (dist * e_norm)

    if cos_sim >= 0.50:       # Within +/- 60 degrees of expected vector
        return MovementDirection.TOWARD
    elif cos_sim <= -0.50:    # Within +/- 60 degrees of opposite vector
        return MovementDirection.AWAY
    else:                     # Flanking / parallel movement
        return MovementDirection.PARALLEL
