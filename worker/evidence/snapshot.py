"""
High-Resolution Keyframe Snapshot Extraction and Annotation.

Extracts raw JPEG keyframes and renders forensic HUD overlays
(target bounding box, ground contact, projected border lines, event badges)
for operator review and legal chain of custody.

Architecture Decision: DEC-0008
"""

import os
import cv2
import numpy as np
from typing import Optional, List, Tuple
from datetime import datetime

from .exceptions import EncodingError
from ..fusion.schemas import EventRecord
from ..tracking.schemas import TrackState
from ..spatial.schemas import SpatialState, CameraSpatialConfig
from ..spatial.world_schemas import ProjectedBorder
from ..spatial.visualizer import draw_spatial_overlay


class SnapshotExtractor:
    """Extracts and saves raw and annotated keyframe snapshots in JPEG format."""

    @staticmethod
    def save_raw_snapshot(
        image: np.ndarray,
        destination_path: str,
        quality: int = 95,
    ) -> str:
        """Saves an unannotated raw camera keyframe."""
        if image is None or image.size == 0:
            raise EncodingError("Cannot encode empty or null frame image.")

        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), max(10, min(100, quality))]
        success = cv2.imwrite(destination_path, image, encode_params)
        if not success:
            raise EncodingError(f"OpenCV failed to write JPEG snapshot to '{destination_path}'")
        return destination_path

    @staticmethod
    def save_annotated_snapshot(
        image: np.ndarray,
        event: EventRecord,
        destination_path: str,
        track: Optional[TrackState] = None,
        spatial_state: Optional[SpatialState] = None,
        projected_borders: Optional[List[ProjectedBorder]] = None,
        spatial_config: Optional[CameraSpatialConfig] = None,
        quality: int = 95,
    ) -> str:
        """
        Renders forensic HUD overlays (bounding box, ground contact, world borders, event badge)
        and encodes the annotated evidence snapshot to JPEG.
        """
        if image is None or image.size == 0:
            raise EncodingError("Cannot encode empty or null frame image.")

        annotated = image.copy()

        # 1. Draw spatial zones & projected world borders
        cfg = spatial_config or CameraSpatialConfig(camera_id=event.camera_id)
        states = [spatial_state] if spatial_state else []
        annotated = draw_spatial_overlay(annotated, cfg, states, projected_borders)

        # 2. Draw Target Bounding Box (if track provided)
        if track:
            bx1, by1 = int(round(track.bbox.x_min)), int(round(track.bbox.y_min))
            bx2, by2 = int(round(track.bbox.x_max)), int(round(track.bbox.y_max))
            cv2.rectangle(annotated, (bx1, by1), (bx2, by2), (0, 0, 255), 2, cv2.LINE_AA)
            label = f"Target #{track.track_id} ({track.class_id.value})"
            cv2.putText(annotated, label, (bx1, max(15, by1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1, cv2.LINE_AA)

        # 3. Top Forensic Event Banner
        h, w = annotated.shape[:2]
        banner_h = 50
        banner = np.zeros((banner_h, w, 3), dtype=np.uint8)

        priority_color = (0, 0, 255) if event.priority.value in ("HIGH", "CRITICAL") else ((0, 200, 255) if event.priority.value == "MEDIUM" else (0, 255, 0))
        cv2.putText(
            banner,
            f"EVIDENCE SNAPSHOT — {event.event_type.value.upper()} [{event.priority.value}]",
            (15, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            priority_color,
            2,
            cv2.LINE_AA,
        )
        ts_str = event.last_observed_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        cv2.putText(
            banner,
            f"Event ID: {event.id} | Camera: {event.camera_id} | Score: {event.risk_score:.1f}/100 | Time: {ts_str}",
            (15, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.40,
            (220, 220, 220),
            1,
            cv2.LINE_AA,
        )

        final_image = np.vstack([banner, annotated])

        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), max(10, min(100, quality))]
        success = cv2.imwrite(destination_path, final_image, encode_params)
        if not success:
            raise EncodingError(f"OpenCV failed to write annotated JPEG snapshot to '{destination_path}'")

        return destination_path
