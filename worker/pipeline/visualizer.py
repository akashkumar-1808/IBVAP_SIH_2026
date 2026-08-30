"""
High-Grade Forensic OpenCV Visualizer for Live IBVAP Stream.

Renders real-time HUD overlays:
- Calibrated projected world borders & warning buffers
- Ground contact points & track trajectories
- Object classifications & ByteTrack IDs
- Behavioral primitives & spatial boundary relationships
- Operational risk score badges & event priority banners
- Environmental condition telemetry

Architecture Decision: DEC-0010
"""

import cv2
import numpy as np
from typing import List, Optional, Dict, Tuple
from datetime import datetime

from worker.tracking.schemas import TrackState, TargetClass
from worker.spatial.schemas import SpatialState, BorderSide, CrossingStatus, SpatialConfidence
from worker.spatial.world_schemas import ProjectedBorder
from worker.behavior.schemas import BehaviorPrimitive
from worker.environment.schemas import EnvironmentState
from worker.fusion.schemas import EventRecord, EventPriority


# Color Palette (BGR)
COLOR_SAFE = (50, 205, 50)         # Lime Green
COLOR_WARNING = (0, 165, 255)       # Orange
COLOR_DANGER = (0, 0, 255)         # Red
COLOR_CYAN = (255, 255, 0)         # Cyan
COLOR_YELLOW = (0, 255, 255)       # Yellow
COLOR_WHITE = (255, 255, 255)
COLOR_DARK_BG = (20, 20, 20)
COLOR_TEXT_DIM = (180, 180, 180)


class LiveStreamVisualizer:
    """Renders factual live telemetry overlays on video frames."""

    def __init__(self, camera_id: str):
        self.camera_id = camera_id

    def render_frame(
        self,
        frame: np.ndarray,
        tracks: List[TrackState],
        spatial_states: List[SpatialState],
        behavior_primitives: List[BehaviorPrimitive],
        events: List[EventRecord],
        environment: Optional[EnvironmentState],
        projected_border: Optional[ProjectedBorder] = None,
        is_calibrated: bool = True,
        fps: float = 0.0,
    ) -> np.ndarray:
        """Draws all analytical overlays on a copy of the input frame."""
        vis = frame.copy()
        h, w = vis.shape[:2]

        # 1. Top Telemetry HUD Banner
        self._draw_hud_banner(vis, environment, fps)

        # 2. Draw Calibrated World Border
        self._draw_border_overlay(vis, projected_border, is_calibrated)

        # 3. Index states by track_id
        spatial_map = {s.track_id: s for s in spatial_states}
        behavior_map: Dict[int, List[BehaviorPrimitive]] = {}
        for b in behavior_primitives:
            behavior_map.setdefault(b.track_id, []).append(b)
        event_map = {e.track_id: e for e in events}

        # 4. Draw Tracks & Target Overlays
        for track in tracks:
            t_id = track.track_id
            spatial = spatial_map.get(t_id)
            behaviors = behavior_map.get(t_id, [])
            event = event_map.get(t_id)

            self._draw_single_track(vis, track, spatial, behaviors, event)

        # 5. Draw Active Event Notification Badge
        if events:
            top_event = max(events, key=lambda e: e.risk_score)
            self._draw_event_alert_badge(vis, top_event)

        return vis

    def _draw_hud_banner(self, img: np.ndarray, env: Optional[EnvironmentState], fps: float) -> None:
        """Renders top dark telemetry strip."""
        w = img.shape[1]
        cv2.rectangle(img, (0, 0), (w, 36), COLOR_DARK_BG, -1)
        cv2.line(img, (0, 36), (w, 36), (60, 60, 60), 1)

        # Left: Camera & FPS
        fps_text = f"{fps:.1f} FPS" if fps > 0 else "-- FPS"
        left_text = f"IBVAP LIVE | {self.camera_id} | {fps_text}"
        cv2.putText(img, left_text, (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.60, COLOR_WHITE, 2)

        # Right: Environmental telemetry
        if env:
            light_str = env.lighting.value.upper()
            vis_str = env.visibility.value.upper()
            qual_str = f"Q:{env.quality_score:.2f}"
            env_text = f"LIGHT: {light_str} | VIS: {vis_str} | {qual_str}"
            (tw, _), _ = cv2.getTextSize(env_text, cv2.FONT_HERSHEY_SIMPLEX, 0.50, 1)
            cv2.putText(img, env_text, (w - tw - 12, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (200, 220, 200), 1)

    def _draw_border_overlay(self, img: np.ndarray, proj: Optional[ProjectedBorder], is_calibrated: bool) -> None:
        """Draws projected world border line and buffer zones."""
        if not is_calibrated or proj is None or not proj.image_polygon:
            # Uncalibrated Indicator
            cv2.putText(img, "SPATIAL: UNCALIBRATED", (14, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 140, 255), 1)
            return

        pts = np.array(proj.image_polygon, dtype=np.int32)
        if len(pts) >= 2:
            # Draw Main Border Line
            cv2.polylines(img, [pts], isClosed=False, color=COLOR_DANGER, thickness=3)
            # Label
            mid_pt = pts[len(pts) // 2]
            cv2.putText(img, f"WORLD BORDER [{proj.border_section_id}]", (mid_pt[0] + 8, mid_pt[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLOR_DANGER, 1)

        # Draw Warning Buffer if present
        if proj.warning_buffer_polygon and len(proj.warning_buffer_polygon) >= 3:
            buf_pts = np.array(proj.warning_buffer_polygon, dtype=np.int32)
            cv2.polylines(img, [buf_pts], isClosed=True, color=COLOR_WARNING, thickness=1)

    def _draw_single_track(
        self,
        img: np.ndarray,
        track: TrackState,
        spatial: Optional[SpatialState],
        behaviors: List[BehaviorPrimitive],
        event: Optional[EventRecord],
    ) -> None:
        """Draws bounding box, ground point, trajectory, and annotations for one track."""
        bb = track.bbox
        x1, y1, x2, y2 = int(bb.x_min), int(bb.y_min), int(bb.x_max), int(bb.y_max)

        # Determine color based on spatial/event state
        color = COLOR_SAFE
        if event and event.priority in (EventPriority.HIGH, EventPriority.CRITICAL):
            color = COLOR_DANGER
        elif spatial and spatial.border_side == BorderSide.RESTRICTED:
            color = COLOR_DANGER
        elif spatial and spatial.border_side == BorderSide.WARNING_BUFFER:
            color = COLOR_WARNING
        elif event and event.priority == EventPriority.MEDIUM:
            color = COLOR_WARNING

        # 1. Bounding Box
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

        # 2. Trajectory Trail
        if len(track.trajectory) > 1:
            traj_pts = np.array([[int(p.x), int(p.y)] for p in track.trajectory[-30:]], dtype=np.int32)
            cv2.polylines(img, [traj_pts], isClosed=False, color=color, thickness=2)

        # 3. Ground Contact Point
        gc_x, gc_y = int((x1 + x2) / 2), y2
        cv2.circle(img, (gc_x, gc_y), 4, (0, 255, 0), -1)
        cv2.circle(img, (gc_x, gc_y), 6, COLOR_WHITE, 1)

        # 4. Multi-Line Annotation Card
        lines = [
            f"ID #{track.track_id} | {track.class_id.value.upper()}",
        ]
        if spatial:
            side_str = spatial.border_side.value.upper()
            dir_str = spatial.direction.value.upper()
            lines.append(f"SIDE: {side_str} ({dir_str})")
            if spatial.crossing_status == CrossingStatus.CONFIRMED_CROSSING:
                lines.append("!! BORDER BREACH !!")

        for b in behaviors:
            lines.append(f"BEH: {b.behavior_type.value.upper()}")

        if event:
            lines.append(f"RISK: {event.risk_score:.1f} [{event.priority.value.upper()}]")

        # Draw card background
        card_y = max(40, y1 - 8 - (len(lines) * 16))
        card_w = max(140, max(len(l) for l in lines) * 8 + 12)
        cv2.rectangle(img, (x1, card_y), (x1 + card_w, card_y + len(lines) * 16 + 6), COLOR_DARK_BG, -1)
        cv2.rectangle(img, (x1, card_y), (x1 + card_w, card_y + len(lines) * 16 + 6), color, 1)

        for i, line in enumerate(lines):
            t_color = COLOR_DANGER if "BREACH" in line or "CRITICAL" in line else COLOR_WHITE
            cv2.putText(img, line, (x1 + 6, card_y + 14 + (i * 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.40, t_color, 1)

    def _draw_event_alert_badge(self, img: np.ndarray, event: EventRecord) -> None:
        """Draws high-visibility event banner at bottom right."""
        h, w = img.shape[:2]
        badge_w, badge_h = 320, 60
        bx1 = w - badge_w - 12
        by1 = h - badge_h - 12

        color = COLOR_DANGER if event.priority in (EventPriority.HIGH, EventPriority.CRITICAL) else COLOR_WARNING
        cv2.rectangle(img, (bx1, by1), (bx1 + badge_w, by1 + badge_h), COLOR_DARK_BG, -1)
        cv2.rectangle(img, (bx1, by1), (bx1 + badge_w, by1 + badge_h), color, 2)

        title = f"ACTIVE EVENT: {event.event_type.value.upper()}"
        detail = f"Priority: {event.priority.value.upper()} | Score: {event.risk_score:.1f}"
        summary = event.explanation_summary[:42] + ("..." if len(event.explanation_summary) > 42 else "")

        cv2.putText(img, title, (bx1 + 8, by1 + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 2)
        cv2.putText(img, detail, (bx1 + 8, by1 + 36), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_WHITE, 1)
        cv2.putText(img, summary, (bx1 + 8, by1 + 52), cv2.FONT_HERSHEY_SIMPLEX, 0.36, COLOR_TEXT_DIM, 1)
