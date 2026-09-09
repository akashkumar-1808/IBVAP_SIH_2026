"""
High-Grade Forensic OpenCV Visualizer for Live IBVAP Stream.

Renders real-time HUD overlays:
- Calibrated projected world borders & warning buffers
- Ground contact points & track trajectories
- Object classifications & ByteTrack IDs
- Behavioral primitives & spatial boundary relationships
- Operational risk score badges & event priority banners
- Environmental condition telemetry & detection stabilization stats

Architecture Decision: DEC-0010, DEC-0012
"""

import cv2
import numpy as np
from typing import List, Optional, Dict, Tuple, Any
from datetime import datetime

from worker.tracking.schemas import TrackState, TargetClass
from worker.spatial.schemas import SpatialState, BorderSide, CrossingStatus, SpatialConfidence
from worker.spatial.world_schemas import ProjectedBorder
from worker.behavior.schemas import BehaviorPrimitive
from worker.environment.schemas import EnvironmentState
from worker.fusion.schemas import EventRecord, EventPriority
from worker.perception.visualizer import draw_human_pose


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
        raw_detections_count: int = 0,
        operational_detections_count: int = 0,
        camera_motion: Optional[Any] = None,
    ) -> np.ndarray:
        """Draws all analytical overlays on a copy of the input frame."""
        vis = frame.copy()
        h, w = vis.shape[:2]

        # 1. Top Telemetry HUD Banner
        self._draw_hud_banner(
            img=vis,
            env=environment,
            fps=fps,
            raw_detections_count=raw_detections_count,
            operational_detections_count=operational_detections_count,
            active_tracks_count=len(tracks),
            camera_motion=camera_motion,
        )

        # 2. Draw Calibrated World Border
        self._draw_border_overlay(vis, projected_border, is_calibrated)

        # 3. Index states by track_id
        spatial_map = {s.track_id: s for s in spatial_states}
        behavior_map: Dict[int, List[BehaviorPrimitive]] = {}
        for b in behavior_primitives:
            behavior_map.setdefault(b.track_id, []).append(b)
        event_map = {e.track_id: e for e in events}

        # 4. Draw Tracks & Target Overlays (Operational tracked objects only)
        for track in tracks:
            t_id = track.track_id
            spatial = spatial_map.get(t_id)
            behaviors = behavior_map.get(t_id, [])
            event = event_map.get(t_id)

            self._draw_single_track(vis, track, spatial, behaviors, event, projected_border=projected_border)

        # 5. Draw Active Event Notification Badge
        if events:
            top_event = max(events, key=lambda e: e.risk_score)
            self._draw_event_alert_badge(vis, top_event)

        return vis

    def _draw_hud_banner(
        self,
        img: np.ndarray,
        env: Optional[EnvironmentState],
        fps: float,
        raw_detections_count: int = 0,
        operational_detections_count: int = 0,
        active_tracks_count: int = 0,
        camera_motion: Optional[Any] = None,
    ) -> None:
        """Renders top dark telemetry strip."""
        w = img.shape[1]
        cv2.rectangle(img, (0, 0), (w, 36), COLOR_DARK_BG, -1)
        cv2.line(img, (0, 36), (w, 36), (60, 60, 60), 1)

        # Camera & FPS
        fps_text = f"{fps:.1f} FPS" if fps > 0 else "-- FPS"
        
        # Camera motion state display
        cam_state = "STABLE"
        if camera_motion:
            if hasattr(camera_motion, "state"):
                cam_state = getattr(camera_motion.state, "value", str(camera_motion.state))
            elif isinstance(camera_motion, str):
                cam_state = camera_motion

        left_text = f"IBVAP | {self.camera_id} | {fps_text} | RAW:{raw_detections_count} OP:{operational_detections_count} TRK:{active_tracks_count} | CAM:{cam_state}"
        cv2.putText(img, left_text, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.46, COLOR_WHITE, 1)

        # Right: Environmental telemetry
        if env:
            light_str = env.lighting.value.upper()
            vis_str = env.visibility.value.upper()
            qual_str = f"Q:{env.quality_score:.2f}"
            env_text = f"LIGHT:{light_str} | VIS:{vis_str} | {qual_str}"
            (tw, _), _ = cv2.getTextSize(env_text, cv2.FONT_HERSHEY_SIMPLEX, 0.46, 1)
            cv2.putText(img, env_text, (w - tw - 10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (200, 220, 200), 1)

    def _draw_border_overlay(self, img: np.ndarray, proj: Optional[ProjectedBorder], is_calibrated: bool) -> None:
        """Draws projected world border line and buffer zones."""
        if not is_calibrated or proj is None or not proj.projected_points:
            # Uncalibrated Indicator
            cv2.putText(img, "SPATIAL: UNCALIBRATED", (14, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 140, 255), 1)
            return

        pts = np.array(proj.projected_points, dtype=np.int32)
        if len(pts) >= 2:
            # Draw Main Border Line (Red)
            cv2.polylines(img, [pts], isClosed=False, color=COLOR_DANGER, thickness=3)

            # Label
            mid_pt = pts[len(pts) // 2]
            cv2.putText(img, f"VIRTUAL BORDER [{proj.border_section_id}]", (mid_pt[0] + 8, mid_pt[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLOR_DANGER, 1)

        # Draw Warning Buffer if present (Amber)
        if proj.warning_buffer_points and len(proj.warning_buffer_points) >= 2:
            buf_pts = np.array(proj.warning_buffer_points, dtype=np.int32)
            cv2.polylines(img, [buf_pts], isClosed=False, color=COLOR_WARNING, thickness=2)
            b_mid = buf_pts[len(buf_pts) // 2]
            cv2.putText(img, "WARNING BUFFER ZONE (15m)", (b_mid[0] + 8, b_mid[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, COLOR_WARNING, 1)

    @staticmethod
    def _calculate_pixel_distance_to_border(
        point_xy: Tuple[float, float],
        proj: ProjectedBorder,
    ) -> Optional[float]:
        """Computes minimum Euclidean perpendicular distance in pixels to projected border."""
        if not proj or not proj.projected_points or len(proj.projected_points) < 2:
            return None
        px, py = point_xy
        min_dist_sq = float("inf")
        pts = proj.projected_points
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            dx = bx - ax
            dy = by - ay
            seg_len_sq = dx * dx + dy * dy
            if seg_len_sq < 1e-6:
                proj_x, proj_y = ax, ay
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len_sq))
                proj_x = ax + t * dx
                proj_y = ay + t * dy
            dist_sq = (px - proj_x) ** 2 + (py - proj_y) ** 2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
        return float(np.sqrt(min_dist_sq))

    def _draw_single_track(
        self,
        img: np.ndarray,
        track: TrackState,
        spatial: Optional[SpatialState],
        behaviors: List[BehaviorPrimitive],
        event: Optional[EventRecord],
        projected_border: Optional[ProjectedBorder] = None,
    ) -> None:
        """
        Renders bounding box, ground point, trajectory, and comprehensive situational awareness HUD.
        Displays:
        - bounding box
        - class name
        - confidence
        - Track ID
        - trajectory
        - optional pose keypoints
        - movement direction
        - estimated speed if already available
        - current GIS zone
        - distance/direction relative to configured virtual border
        """
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

        # 1b. Optional Forensic Pose Skeleton Overlay
        if getattr(track, "keypoints", None) is not None:
            draw_human_pose(img, track.keypoints)

        # 2. Trajectory Trail
        if len(track.trajectory) > 1:
            traj_pts = np.array([[int(p.x), int(p.y)] for p in track.trajectory[-30:]], dtype=np.int32)
            cv2.polylines(img, [traj_pts], isClosed=False, color=color, thickness=2)

        # 3. Ground Contact Point
        gc_x = int((x1 + x2) / 2)
        gc_y = y2
        if spatial and spatial.ground_contact:
            gc_x = int(spatial.ground_contact.x)
            gc_y = int(spatial.ground_contact.y)
        cv2.circle(img, (gc_x, gc_y), 4, (0, 255, 0), -1)
        cv2.circle(img, (gc_x, gc_y), 6, COLOR_WHITE, 1)

        # 4. Multi-Line Situational Awareness & Debug HUD Card
        lines: List[str] = []

        # (a) Class Name & Track ID
        cls_name = track.class_id.value.capitalize()
        lines.append(f"{cls_name}")
        lines.append(f"ID: {track.track_id}")

        # (b) Confidence
        if track.confidence_history:
            conf_val = track.confidence_history[-1]
            lines.append(f"Confidence: {conf_val:.2f}")

        # (c) Estimated Speed (only if available / non-zero)
        if track.speed_pixels_per_sec > 0.0:
            lines.append(f"Speed: {track.speed_pixels_per_sec:.1f} px/s")

        # (d) Movement Direction (only if calculated)
        dir_label = None
        if spatial and spatial.direction:
            raw_dir = spatial.direction.value.upper()
            if raw_dir == "TOWARD":
                dir_label = "APPROACHING"
            elif raw_dir == "AWAY":
                dir_label = "RECEDING"
            elif raw_dir == "PARALLEL":
                dir_label = "PARALLEL"
            elif raw_dir != "UNCERTAIN":
                dir_label = raw_dir
        elif track.direction_angle is not None:
            dir_label = f"{track.direction_angle:.0f}°"

        if dir_label:
            lines.append(f"Direction: {dir_label}")

        # (e) Current GIS Zone
        zone_label = None
        if spatial and spatial.border_side:
            zone_label = spatial.border_side.value.upper().replace("_", " ")
        elif spatial and spatial.current_zone_id:
            zone_label = spatial.current_zone_id.upper()
        elif track.current_zone_id:
            zone_label = track.current_zone_id.upper()

        if zone_label:
            lines.append(f"Zone: {zone_label}")

        # (f) Border Distance & Direction relative to configured virtual border
        border_dist_str = None
        if spatial and getattr(spatial, "border_distance_m", None) is not None:
            border_dist_str = f"{spatial.border_distance_m:.1f}m"
        elif projected_border and projected_border.projected_points and len(projected_border.projected_points) >= 2:
            px_dist = self._calculate_pixel_distance_to_border((gc_x, gc_y), projected_border)
            if px_dist is not None:
                border_dist_str = f"{px_dist:.0f}px"

        if border_dist_str:
            if dir_label in ("APPROACHING", "RECEDING"):
                lines.append(f"Border distance: {border_dist_str} ({dir_label})")
            else:
                lines.append(f"Border distance: {border_dist_str}")

        # (g) Optional Pose Keypoints (if detected on this target)
        if getattr(track, "keypoints", None) is not None:
            kp_cnt = getattr(track.keypoints, "num_keypoints", 17) if hasattr(track.keypoints, "num_keypoints") else 17
            lines.append(f"Pose: {kp_cnt} Keypoints")

        # (h) Breach & Alert notices
        if spatial and spatial.crossing_status == CrossingStatus.CONFIRMED_CROSSING:
            lines.append("!! BORDER BREACH !!")

        for b in behaviors:
            lines.append(f"Behavior: {b.behavior_type.value.upper()}")

        if event:
            lines.append(f"Risk: {event.risk_score:.1f} [{event.priority.value.upper()}]")

        # 5. Draw Card Background & Text
        line_height = 15
        card_h = len(lines) * line_height + 8
        max_w = max(cv2.getTextSize(l, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)[0][0] for l in lines) if lines else 120
        card_w = max(150, max_w + 16)

        # Smart positioning (avoid clipping at frame boundaries)
        card_y = y1 - 8 - card_h
        if card_y < 40:
            card_y = min(img.shape[0] - card_h - 10, y2 + 8)
        card_x = max(10, min(x1, img.shape[1] - card_w - 10))

        cv2.rectangle(img, (card_x, card_y), (card_x + card_w, card_y + card_h), COLOR_DARK_BG, -1)
        cv2.rectangle(img, (card_x, card_y), (card_x + card_w, card_y + card_h), color, 1)

        for i, line in enumerate(lines):
            t_color = COLOR_WHITE
            if "BREACH" in line or "CRITICAL" in line:
                t_color = COLOR_DANGER
            elif "APPROACHING" in line or "WARNING" in line:
                t_color = COLOR_WARNING
            elif "Pose:" in line:
                t_color = COLOR_CYAN
            elif i == 0:  # Class name header
                t_color = (0, 255, 255) if track.class_id == TargetClass.PERSON else COLOR_WHITE

            cv2.putText(
                img,
                line,
                (card_x + 8, card_y + 12 + (i * line_height)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.38,
                t_color,
                1,
                cv2.LINE_AA,
            )

    def _draw_event_alert_badge(self, img: np.ndarray, event: EventRecord) -> None:
        """Draws high-visibility event banner at bottom right."""
        h, w = img.shape[:2]
        badge_w, badge_h = 320, 60
        bx1 = w - badge_w - 12
        by1 = h - badge_h - 12
        cv2.rectangle(img, (bx1, by1), (w - 12, h - 12), COLOR_DARK_BG, -1)
        cv2.rectangle(img, (bx1, by1), (w - 12, h - 12), COLOR_DANGER, 2)

        cv2.putText(img, f"EVENT: {event.event_type.value.upper()}", (bx1 + 10, by1 + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, COLOR_DANGER, 1)
        cv2.putText(img, f"PRIORITY: {event.priority.value.upper()} | RISK: {event.risk_score:.1f}", (bx1 + 10, by1 + 44),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, COLOR_WHITE, 1)
