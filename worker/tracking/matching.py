from typing import Tuple, List
import numpy as np
from scipy.optimize import linear_sum_assignment


def compute_iou_matrix(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """
    Computes Intersection over Union (IoU) matrix between two sets of bounding boxes.
    boxes_a: (N, 4) [x1, y1, x2, y2]
    boxes_b: (M, 4) [x1, y1, x2, y2]
    Returns: (N, M) IoU matrix with values in [0.0, 1.0]
    """
    if len(boxes_a) == 0 or len(boxes_b) == 0:
        return np.zeros((len(boxes_a), len(boxes_b)), dtype=np.float32)

    boxes_a = np.ascontiguousarray(boxes_a, dtype=np.float32)
    boxes_b = np.ascontiguousarray(boxes_b, dtype=np.float32)

    area_a = (boxes_a[:, 2] - boxes_a[:, 0]) * (boxes_a[:, 3] - boxes_a[:, 1])
    area_b = (boxes_b[:, 2] - boxes_b[:, 0]) * (boxes_b[:, 3] - boxes_b[:, 1])

    # Intersections
    lt = np.maximum(boxes_a[:, None, :2], boxes_b[None, :, :2])  # (N, M, 2)
    rb = np.minimum(boxes_a[:, None, 2:], boxes_b[None, :, 2:])  # (N, M, 2)

    wh = np.clip(rb - lt, a_min=0, a_max=None)  # (N, M, 2)
    inter = wh[:, :, 0] * wh[:, :, 1]  # (N, M)

    union = area_a[:, None] + area_b[None, :] - inter
    iou = inter / np.maximum(union, 1e-6)
    return np.clip(iou, 0.0, 1.0)


def linear_assignment(
    cost_matrix: np.ndarray,
    thresh: float,
) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """
    Solves linear sum assignment (Hungarian algorithm) on cost matrix with a rejection threshold.
    Returns:
    - matches: List of (row_idx, col_idx) pairs where cost <= thresh
    - unmatched_a: List of unmatched row indices
    - unmatched_b: List of unmatched column indices
    """
    if cost_matrix.size == 0:
        return [], list(range(cost_matrix.shape[0])), list(range(cost_matrix.shape[1]))

    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    matches = []
    unmatched_a = list(range(cost_matrix.shape[0]))
    unmatched_b = list(range(cost_matrix.shape[1]))

    for r, c in zip(row_ind, col_ind):
        if cost_matrix[r, c] <= thresh:
            matches.append((int(r), int(c)))
            if r in unmatched_a:
                unmatched_a.remove(r)
            if c in unmatched_b:
                unmatched_b.remove(c)

    return matches, unmatched_a, unmatched_b
