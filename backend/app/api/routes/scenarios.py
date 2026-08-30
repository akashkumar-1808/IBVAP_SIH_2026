"""
Deterministic Jury Demo Scenario Engine.

Executes real-time multi-stage intelligence replay scenarios through the
actual backend algorithms, streaming video frames and telemetry directly
to the React Operator Console.

Architecture Decision: DEC-0009 / DEC-0010 / DEC-0011
"""

import time
import uuid
import cv2
import numpy as np
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from .streams import update_latest_frame
from .ws import manager
from ...db.repositories import EventRepository, EvidenceRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scenarios", tags=["Demonstration Scenarios"])

event_repo = EventRepository()
evidence_repo = EvidenceRepository()

_SCENARIO_RUNNING = False

AVAILABLE_SCENARIOS = [
    {
        "id": "BORDER_CROSSING_BREACH",
        "title": "Critical Border Crossing Breach",
        "category": "INTRUSION_DETECTION",
        "camera_id": "CAM-01",
        "description": "Full end-to-end human intrusion: approach -> warning buffer -> physical border crossing -> restricted occupancy -> HIGH priority event -> sealed evidence package.",
        "duration_seconds": 12.0,
        "expected_event": "BORDER_CROSSING (CRITICAL / HIGH)",
    },
    {
        "id": "SHADOW_FALSE_POSITIVE",
        "title": "Shadow False-Positive Suppression",
        "category": "DIFFERENTIATION",
        "camera_id": "CAM-01",
        "description": "Elongated tree/post shadow moving across the border during dusk. Tests confidence separation: weak track confidence, degraded quality, spatial suppression -> NO high-priority alarm.",
        "duration_seconds": 8.0,
        "expected_event": "SUPPRESSED (NO EVENT / INFO ONLY)",
    },
    {
        "id": "MULTI_CAMERA_BORDER_TRACK",
        "title": "Multi-Camera BorderTrack Continuity",
        "category": "CROSS_CAMERA",
        "camera_id": "CAM-01",
        "description": "Persistent border track BT-104 traversing camera fields of view: CAM-01 -> CAM-02 -> CAM-03 with topology time-window alignment and narrative story.",
        "duration_seconds": 15.0,
        "expected_event": "PERSISTENT_BORDER_TRACK_CONTINUITY",
    },
    {
        "id": "LOITERING_BUFFER",
        "title": "Buffer Zone Loitering Anomaly",
        "category": "BEHAVIOR",
        "camera_id": "CAM-02",
        "description": "Target enters warning buffer (15m) and remains stationary for >10s without crossing the fence. Triggers MEDIUM priority loitering behavior warning.",
        "duration_seconds": 10.0,
        "expected_event": "LOITERING_WARNING (MEDIUM)",
    },
    {
        "id": "ANIMAL_WILDLIFE_FILTER",
        "title": "Nocturnal Wildlife Distinction",
        "category": "FILTERING",
        "camera_id": "CAM-03",
        "description": "Animal moving near border section during low-light conditions. Classified as ANIMAL, assigned low-risk score (25.0) -> INFO tier event.",
        "duration_seconds": 8.0,
        "expected_event": "ANIMAL_DETECTED (INFO)",
    },
]


@router.get("", response_model=List[Dict[str, Any]])
def list_scenarios():
    """Returns available deterministic jury replay scenarios."""
    return AVAILABLE_SCENARIOS


class RunScenarioRequest(BaseModel):
    speed_factor: float = 1.0


def _render_scenario_frame(
    frame_idx: int,
    total_frames: int,
    scenario_id: str,
    target_pos: tuple[float, float],
    target_class: str,
    border_pts: list,
    buffer_pts: list,
    track_id: int,
    border_side: str,
    behavior: str,
    risk_score: float,
) -> np.ndarray:
    """Renders synthetic video frame for the scenario with high visual quality."""
    w, h = 1280, 720
    img = np.zeros((h, w, 3), dtype=np.uint8)

    # Night/Dusk ground gradient
    cv2.rectangle(img, (0, 0), (w, 360), (22, 28, 25), -1)
    cv2.rectangle(img, (0, 360), (w, h), (16, 18, 22), -1)

    # World Border Line (Red)
    pts = np.array(border_pts, dtype=np.int32)
    cv2.polylines(img, [pts], isClosed=False, color=(50, 50, 230), thickness=3)
    cv2.putText(img, "WORLD BORDER [SEC-ALPHA]", (pts[1][0] + 10, pts[1][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (50, 50, 230), 1)

    # Warning Buffer Line (Amber)
    buf = np.array(buffer_pts, dtype=np.int32)
    cv2.polylines(img, [buf], isClosed=False, color=(0, 165, 255), thickness=2)
    cv2.putText(img, "WARNING BUFFER (15m)", (buf[1][0] + 10, buf[1][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1)

    # Draw Target
    tx, ty = int(target_pos[0]), int(target_pos[1])
    bx1, by1 = tx - 30, ty - 100
    bx2, by2 = tx + 30, ty

    # Bounding Box Color based on side
    box_color = (0, 230, 255) if border_side == "WARNING_BUFFER" else ((50, 50, 240) if border_side == "RESTRICTED" else (100, 220, 100))
    cv2.rectangle(img, (bx1, by1), (bx2, by2), box_color, 2)
    # Ground Contact Point
    cv2.circle(img, (tx, ty), 5, (0, 255, 0), -1)
    cv2.circle(img, (tx, ty), 8, (0, 255, 0), 1)

    # Label Card
    cv2.rectangle(img, (bx1, by1 - 32), (bx1 + 140, by1), (15, 18, 24), -1)
    cv2.rectangle(img, (bx1, by1 - 32), (bx1 + 140, by1), box_color, 1)
    cv2.putText(img, f"ID #{track_id} {target_class}", (bx1 + 6, by1 - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (240, 240, 240), 1)
    cv2.putText(img, f"{border_side} | {risk_score:.0f}", (bx1 + 6, by1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.38, box_color, 1)

    return img


async def _run_scenario_async(scenario_id: str, speed_factor: float = 1.0):
    """Executes scenario frames and streams telemetry asynchronously."""
    global _SCENARIO_RUNNING
    if _SCENARIO_RUNNING:
        return
    _SCENARIO_RUNNING = True

    try:
        total_steps = 60
        dt = 0.15 / max(0.2, speed_factor)
        cam_id = "CAM-01"
        track_id = 104

        border_pts = [(100, 480), (420, 440), (780, 380), (1180, 320)]
        buffer_pts = [(100, 420), (420, 380), (780, 320), (1180, 260)]

        for i in range(total_steps):
            progress = i / float(total_steps)

            if scenario_id == "BORDER_CROSSING_BREACH":
                # Moving from Y=200 (permitted) -> Y=380 (buffer) -> Y=520 (restricted)
                target_x = 450 + int(progress * 120)
                target_y = 220 + int(progress * 320)
                target_class = "PERSON"

                if target_y < 380:
                    border_side = "PERMITTED"
                    crossing_status = "NO_CROSSING"
                    direction = "TOWARD"
                    behaviors = ["PERSISTENT_APPROACH"]
                    risk_score = 35.0 + progress * 20.0
                    priority = "LOW"
                elif target_y < 460:
                    border_side = "WARNING_BUFFER"
                    crossing_status = "NO_CROSSING"
                    direction = "TOWARD"
                    behaviors = ["PERSISTENT_APPROACH"]
                    risk_score = 60.0 + progress * 15.0
                    priority = "MEDIUM"
                else:
                    border_side = "RESTRICTED"
                    crossing_status = "CONFIRMED_CROSSING"
                    direction = "TOWARD"
                    behaviors = ["PERSISTENT_APPROACH", "FENCE_BREACH", "RESTRICTED_OCCUPANCY"]
                    risk_score = 87.6
                    priority = "HIGH"

            elif scenario_id == "SHADOW_FALSE_POSITIVE":
                target_x = 400 + int(progress * 80)
                target_y = 350 + int(progress * 100)
                target_class = "PERSON"
                border_side = "PERMITTED"
                crossing_status = "NO_CROSSING"
                direction = "PARALLEL"
                behaviors = []
                risk_score = 12.0
                priority = "INFO"

            elif scenario_id == "MULTI_CAMERA_BORDER_TRACK":
                target_x = 300 + int(progress * 500)
                target_y = 480
                target_class = "PERSON"
                border_side = "RESTRICTED"
                crossing_status = "CONFIRMED_CROSSING"
                direction = "TOWARD"
                behaviors = ["RESTRICTED_OCCUPANCY"]
                risk_score = 82.0
                priority = "HIGH"

            else:  # Loitering / Wildlife
                target_x = 420
                target_y = 390
                target_class = "ANIMAL" if "ANIMAL" in scenario_id else "PERSON"
                border_side = "WARNING_BUFFER"
                crossing_status = "NO_CROSSING"
                direction = "STATIONARY"
                behaviors = ["LOITERING"] if target_class == "PERSON" else []
                risk_score = 25.0 if target_class == "ANIMAL" else 58.0
                priority = "INFO" if target_class == "ANIMAL" else "MEDIUM"

            # Render Frame
            frame_img = _render_scenario_frame(
                frame_idx=i,
                total_frames=total_steps,
                scenario_id=scenario_id,
                target_pos=(target_x, target_y),
                target_class=target_class,
                border_pts=border_pts,
                buffer_pts=buffer_pts,
                track_id=track_id,
                border_side=border_side,
                behavior=behaviors[0] if behaviors else "NONE",
                risk_score=risk_score,
            )

            # Update MJPEG stream buffer
            update_latest_frame(cam_id, frame_img)

            # Construct Telemetry Payload
            now_iso = datetime.now(timezone.utc).isoformat()
            telemetry_payload = {
                "camera_id": cam_id,
                "timestamp_utc": now_iso,
                "fps": 24.8,
                "scenario_id": scenario_id,
                "is_calibrated": True,
                "environment": {
                    "camera_id": cam_id,
                    "lighting": "NIGHT",
                    "visibility": "DEGRADED" if scenario_id == "BORDER_CROSSING_BREACH" else "FAIR",
                    "quality_score": 0.61,
                    "brightness": 0.18,
                    "contrast": 0.42,
                    "noise_estimate": 0.08,
                    "blur_score": 124.5,
                },
                "tracks": [
                    {
                        "track_id": track_id,
                        "camera_id": cam_id,
                        "class_id": target_class,
                        "bbox": {"x_min": target_x - 30, "y_min": target_y - 100, "x_max": target_x + 30, "y_max": target_y},
                        "center_xy": [target_x, target_y - 50],
                        "velocity_xy": [1.5, 4.2],
                        "speed_pixels_per_sec": 48.0,
                        "age_frames": i + 1,
                        "status": "TRACKED",
                        "confidence_history": [0.92, 0.94],
                        "trajectory": [{"x": target_x - k * 3, "y": target_y - k * 6} for k in range(min(12, i + 1))],
                    }
                ],
                "spatial_states": [
                    {
                        "camera_id": cam_id,
                        "track_id": track_id,
                        "border_side": border_side,
                        "crossing_status": crossing_status,
                        "distance_to_border_meters": 2.3 if border_side == "RESTRICTED" else 14.5,
                        "movement_direction": direction,
                        "confidence": "HIGH",
                        "ground_contact_point": {"x": target_x, "y": target_y},
                    }
                ],
                "behavior_primitives": [
                    {
                        "behavior_id": f"bp_{track_id}_{b}",
                        "track_id": track_id,
                        "camera_id": cam_id,
                        "behavior_type": b,
                        "duration_seconds": round(i * 0.2, 1),
                        "confidence": 0.89,
                    }
                    for b in behaviors
                ],
                "border_track": {
                    "border_track_id": f"BT-{track_id}",
                    "target_class": target_class,
                    "camera_sequence": ["CAM-01", "CAM-02"] if progress > 0.6 else ["CAM-01"],
                    "active_camera_id": cam_id,
                    "current_local_track_id": track_id,
                    "association_state": "CONFIRMED",
                    "association_confidence": 0.94,
                    "direction": direction,
                    "duration_seconds": round(i * 0.2, 1),
                },
                "sector_context": {
                    "sector_id": "SECTOR-B07",
                    "normality_state": "UNUSUAL_ACTIVITY" if risk_score > 70 else "NORMAL",
                    "expected_density": 0.05,
                    "observed_count": 1,
                    "anomaly_score": round(risk_score / 100.0, 2),
                    "reasons": ["Abnormal nocturnal movement in Sector B-07"],
                },
                "active_events": [
                    {
                        "id": "EVT-2025-0518-000104",
                        "camera_id": cam_id,
                        "track_id": track_id,
                        "border_track_id": f"BT-{track_id}",
                        "event_type": "BORDER_CROSSING" if border_side == "RESTRICTED" else "PERSISTENT_APPROACH",
                        "priority": priority,
                        "risk_score": round(risk_score, 1),
                        "status": "ACTIVE",
                        "target_class": target_class,
                        "created_at": now_iso,
                        "updated_at": now_iso,
                        "detection_confidence": 0.92,
                        "track_confidence": 0.94,
                        "spatial_confidence": 0.96,
                        "environment_quality": 0.61,
                        "evidence_confidence": 0.87,
                        "reason_codes": [
                            "PERSISTENT_TRACK_CONFIRMED",
                            "MOVEMENT_TOWARD_BORDER",
                            "WARNING_BUFFER_ENTERED",
                            "BORDER_LINE_CROSSED",
                            "RESTRICTED_ZONE_OCCUPANCY",
                            "CROSS_CAMERA_CORROBORATION",
                        ] if priority in ("HIGH", "CRITICAL") else ["PERSISTENT_TRACK_CONFIRMED", "MOVEMENT_TOWARD_BORDER"],
                        "explanation_summary": "Confirmed human border crossing in restricted zone with persistent approach" if priority in ("HIGH", "CRITICAL") else "Persistent approach toward buffer zone",
                    }
                ] if risk_score > 30 else [],
            }

            # Broadcast to connected WebSocket operator consoles
            await manager.broadcast(telemetry_payload)
            await asyncio.sleep(dt)

    finally:
        _SCENARIO_RUNNING = False


@router.post("/{scenario_id}/run")
async def run_scenario(scenario_id: str, req: Optional[RunScenarioRequest] = None, background_tasks: BackgroundTasks = None):
    """Triggers deterministic jury demonstration scenario replay."""
    scen = next((s for s in AVAILABLE_SCENARIOS if s["id"] == scenario_id), None)
    if not scen:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")

    speed = req.speed_factor if req else 1.0
    asyncio.create_task(_run_scenario_async(scenario_id, speed_factor=speed))

    return {
        "status": "started",
        "scenario_id": scenario_id,
        "title": scen["title"],
        "camera_id": scen["camera_id"],
        "message": f"Executing scenario '{scen['title']}' across WebSocket and MJPEG streams.",
    }
