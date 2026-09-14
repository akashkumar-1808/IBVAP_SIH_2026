"""
Dynamic Camera Registration, RTSP Connection, and World-Border Calibration API.

Architecture Decision: DEC-0010 / DEC-0011
"""

import os
import re
import threading
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel, Field

from worker.pipeline.schemas import PipelineConfig, RunMode
from worker.pipeline.orchestrator import LivePipelineOrchestrator
from worker.ingestion import mask_rtsp_url
from worker.spatial.schemas import ZoneType, CrossingStatus, MovementDirection
from .streams import update_latest_frame
from .ws import broadcast_telemetry_sync
from ...db.repositories import EventRepository, EvidenceRepository, CameraRepository

logger = logging.getLogger("ibvap.cameras")
router = APIRouter(prefix="/cameras", tags=["Cameras"])

event_repo = EventRepository()
evidence_repo = EvidenceRepository()
camera_repo = CameraRepository()

# Dynamic in-memory camera registry pre-populated with primary demo camera
_CAMERAS_REGISTRY: List[Dict[str, Any]] = [
    {
        "camera_id": "DEMO-CAM-01",
        "name": "SIH Sector Alpha Border Camera",
        "rtsp_url": "storage/samples/test_video.mp4",
        "video_file_path": "storage/samples/test_video.mp4",
        "sector_id": "SECTOR-B07",
        "sector_name": "Northern Border Sector",
        "status": "ONLINE",
        "resolution": "1280x720",
        "fps_target": 25.0,
        "is_calibrated": True,
        "location": {"lat": 28.6139, "lng": 77.2090, "elevation_m": 12.5},
        "visible_border_sections": ["SEC-ALPHA"],
        "connected_at_utc": datetime.now(timezone.utc).isoformat(),
    }
]

# Active background orchestrators & worker threads
_RUNNING_ORCHESTRATORS: Dict[str, LivePipelineOrchestrator] = {}
_RUNNING_THREADS: Dict[str, threading.Thread] = {}
_ANALYSIS_STATUS: Dict[str, Dict[str, Any]] = {}
_LAST_TELEMETRY: Dict[str, Dict[str, Any]] = {}
_ANALYSIS_LOCK = threading.Lock()


class UploadVideoResponse(BaseModel):
    status: str = Field(..., description="Source status: READY TO ANALYZE or READY")
    file_name: str
    video_path: str
    file_size_bytes: int
    camera_id: str
    message: str


class RunAnalysisRequest(BaseModel):
    camera_id: str = Field(default="DEMO-CAM-01", description="Target camera identifier")
    video_file_path: str = Field(..., description="Path to MP4 video file on server")
    device: Optional[str] = Field(default="cpu", description="Compute device: cpu or cuda")


class StopAnalysisRequest(BaseModel):
    camera_id: str = Field(default="DEMO-CAM-01")


class ConnectCameraRequest(BaseModel):
    camera_id: str = Field(..., description="Unique Camera ID (e.g. LIVE-01)")
    name: str = Field(..., description="Camera label / location name")
    rtsp_url: Optional[str] = Field(None, description="Full RTSP Stream URL")
    video_file_path: Optional[str] = Field(None, description="Local path to MP4 video file for replay")
    sector_id: Optional[str] = Field("SECTOR-B07", description="Sector identifier")
    sector_name: Optional[str] = Field("Northern Border", description="Human-readable sector name")
    device: Optional[str] = Field("cpu", description="Compute device ('cpu' or 'cuda')")


@router.get("", response_model=List[Dict[str, Any]])
def list_cameras():
    """Returns all dynamically registered cameras and operational statuses."""
    return _CAMERAS_REGISTRY


@router.get("/{camera_id}", response_model=Dict[str, Any])
def get_camera(camera_id: str):
    """Returns camera metadata by ID."""
    cam = next((c for c in _CAMERAS_REGISTRY if c["camera_id"] == camera_id), None)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found.")
    return cam


def _build_on_frame_callback(cam_id: str, rtsp_url: Optional[str], sector_id: str, session_id: str):
    """Builds unified telemetry and MJPEG stream broadcast callback for a running pipeline."""
    _inserted_event_ids: set = set()
    _last_update_ts: Dict[str, float] = {}

    def on_frame_callback(packet, env_state, detections, tracks, spatial_states, behaviors, events, fps, vis_image=None, stream_health=None):
        orch = _RUNNING_ORCHESTRATORS.get(cam_id)
        if not orch:
            return

        # Update MJPEG stream frame buffer for browser display with real rendered HUD
        stream_image = vis_image if vis_image is not None else packet.image
        update_latest_frame(cam_id, stream_image)

        # Build lookup maps
        spatial_map = {sp.track_id: sp for sp in spatial_states}

        # Format tracks from domain TrackState
        formatted_tracks = []
        for tr in tracks:
            sp = spatial_map.get(tr.track_id)
            gp = None
            if sp and sp.ground_contact:
                try:
                    if hasattr(sp.ground_contact, "pixel_xy"):
                        gp = [float(sp.ground_contact.pixel_xy[0]), float(sp.ground_contact.pixel_xy[1])]
                    elif hasattr(sp.ground_contact, "x") and hasattr(sp.ground_contact, "y"):
                        gp = [float(sp.ground_contact.x), float(sp.ground_contact.y)]
                except Exception:
                    pass

            conf_val = round(tr.confidence_history[-1], 2) if tr.confidence_history else 0.90

            formatted_tracks.append({
                "track_id": tr.track_id,
                "camera_id": tr.camera_id,
                "class": tr.class_id.value.upper(),
                "class_id": tr.class_id.value.upper(),
                "confidence": conf_val,
                "bbox": {
                    "x_min": float(tr.bbox.x_min),
                    "y_min": float(tr.bbox.y_min),
                    "x_max": float(tr.bbox.x_max),
                    "y_max": float(tr.bbox.y_max),
                },
                "center_xy": [float(tr.center_xy[0]), float(tr.center_xy[1])],
                "velocity_xy": [float(tr.velocity_xy[0]), float(tr.velocity_xy[1])],
                "velocity": [float(tr.velocity_xy[0]), float(tr.velocity_xy[1])],
                "speed_pixels_per_sec": float(tr.speed_pixels_per_sec),
                "age_frames": tr.age_frames,
                "persistence": tr.age_frames,
                "status": tr.status.value.upper(),
                "ground_point": {"x": gp[0], "y": gp[1]} if gp else None,
                "trajectory": [{"x": float(p.x), "y": float(p.y)} for p in tr.trajectory[-15:]],
            })

        # Format raw / operational detections
        formatted_detections = []
        for d in detections:
            d_bbox = {
                "x_min": float(d.bbox.x_min),
                "y_min": float(d.bbox.y_min),
                "x_max": float(d.bbox.x_max),
                "y_max": float(d.bbox.y_max),
            } if hasattr(d, "bbox") else {}
            formatted_detections.append({
                "class": d.class_id.value.upper() if hasattr(d, "class_id") and hasattr(d.class_id, "value") else str(getattr(d, "class_name", "PERSON")).upper(),
                "confidence": round(float(getattr(d, "confidence", 0.90)), 2),
                "bbox": d_bbox,
                "frame_id": packet.frame_id,
            })

        # Format spatial states from domain SpatialState
        formatted_spatial = []
        spatial_contract = []
        for sp in spatial_states:
            if sp.border_side:
                side_str = sp.border_side.value.upper()
            elif sp.current_zone_type:
                if sp.current_zone_type == ZoneType.RESTRICTED:
                    side_str = "RESTRICTED"
                elif sp.current_zone_type == ZoneType.BUFFER:
                    side_str = "WARNING_BUFFER"
                else:
                    side_str = "PERMITTED"
            else:
                side_str = "PERMITTED"

            if (sp.crossing_status and sp.crossing_status.value in ("confirmed", "confirmed_crossing")) or len(sp.fences_crossed) > 0:
                crossing_str = "CONFIRMED_CROSSING"
            elif sp.crossing_status and sp.crossing_status.value in ("candidate", "crossing_candidate"):
                crossing_str = "CROSSING_WARNING_BUFFER"
            else:
                crossing_str = "NO_CROSSING"

            dist_val = getattr(sp, "distance_to_border_meters", None)
            if dist_val is None:
                dist_val = 2.5 if side_str == "RESTRICTED" else (8.0 if side_str == "WARNING_BUFFER" else 18.0)

            gcp = None
            if sp.ground_contact:
                try:
                    if hasattr(sp.ground_contact, "pixel_xy"):
                        gcp = {"x": float(sp.ground_contact.pixel_xy[0]), "y": float(sp.ground_contact.pixel_xy[1])}
                    elif hasattr(sp.ground_contact, "x") and hasattr(sp.ground_contact, "y"):
                        gcp = {"x": float(sp.ground_contact.x), "y": float(sp.ground_contact.y)}
                except Exception:
                    pass

            formatted_spatial.append({
                "track_id": sp.track_id,
                "camera_id": sp.camera_id,
                "timestamp_utc": sp.timestamp_utc.isoformat(),
                "border_side": side_str,
                "crossing_status": crossing_str,
                "distance_to_border_meters": round(float(dist_val), 1),
                "movement_direction": sp.direction.value.upper() if hasattr(sp.direction, "value") else str(sp.direction).upper(),
                "confidence": sp.spatial_confidence.value.upper() if hasattr(sp, "spatial_confidence") else "VALID",
                "ground_contact_point": gcp,
            })

            spatial_contract.append({
                "track_id": sp.track_id,
                "border_id": getattr(sp, "border_section_id", "SEC-ALPHA"),
                "zone": sp.current_zone_id or side_str,
                "border_side": side_str,
                "distance_to_border": round(float(dist_val), 1),
                "movement_direction": sp.direction.value.upper() if hasattr(sp.direction, "value") else str(sp.direction).upper(),
                "crossing_status": crossing_str,
            })

        # Format behavior primitives from domain BehaviorPrimitive
        formatted_behaviors = []
        behavior_contract = []
        for bp in behaviors:
            b_type = bp.behavior_type.value.upper() if hasattr(bp.behavior_type, "value") else str(bp.behavior_type).upper()
            b_conf = float(getattr(bp, "confidence", 0.88))
            b_active = (bp.status.value == "active") if hasattr(bp, "status") and hasattr(bp.status, "value") else getattr(bp, "is_active", True)
            formatted_behaviors.append({
                "behavior_id": getattr(bp, "behavior_id", getattr(bp, "id", f"bp_{bp.track_id}_{b_type}")),
                "track_id": bp.track_id,
                "camera_id": bp.camera_id,
                "behavior_type": b_type,
                "confidence": round(b_conf, 2),
                "duration_seconds": round(float(bp.duration_seconds), 1),
                "is_active": b_active,
            })
            behavior_contract.append({
                "track_id": bp.track_id,
                "behavior_type": b_type,
                "confidence": round(b_conf, 2),
                "duration": round(float(bp.duration_seconds), 1),
            })

        # Format active events from domain EventRecord and persist
        formatted_events = []
        events_contract = []
        for ev in events:
            ev_dict = {
                "id": ev.id,
                "camera_id": ev.camera_id,
                "track_id": ev.track_id,
                "border_track_id": ev.border_track_id or f"BT-{ev.track_id}",
                "event_type": ev.event_type.value.upper(),
                "priority": ev.priority.value.upper(),
                "risk_score": round(float(ev.risk_score), 1),
                "status": ev.status.value.upper(),
                "target_class": ev.target_class.value.upper(),
                "created_at": ev.created_at.isoformat() if hasattr(ev.created_at, "isoformat") else str(ev.created_at),
                "updated_at": ev.updated_at.isoformat() if hasattr(ev.updated_at, "isoformat") else str(ev.updated_at),
                "duration_seconds": round(float(ev.duration_seconds), 1),
                "detection_confidence": round(float(ev.detection_confidence), 2),
                "reason_codes": [rc.value.upper() if hasattr(rc, "value") else str(rc).upper() for rc in ev.reason_codes],
                "explanation_summary": ev.explanation_summary,
            }
            formatted_events.append(ev_dict)
            if ev.id not in _inserted_event_ids:
                try:
                    event_repo.insert(ev_dict)
                    _inserted_event_ids.add(ev.id)
                    _last_update_ts[ev.id] = time.time()
                except Exception as e_err:
                    logger.debug(f"Notice inserting event to repo: {e_err}")
            else:
                from ...db.repositories.base import _MEMORY_TABLES
                if "events" in _MEMORY_TABLES and ev.id in _MEMORY_TABLES["events"]:
                    _MEMORY_TABLES["events"][ev.id].update({
                        "updated_at": ev_dict["updated_at"],
                        "duration_seconds": ev_dict["duration_seconds"],
                        "risk_score": ev_dict["risk_score"],
                        "status": ev_dict["status"],
                    })
                now_s = time.time()
                if now_s - _last_update_ts.get(ev.id, 0.0) >= 3.0:
                    _last_update_ts[ev.id] = now_s
                    def _async_patch(e_id: str, up_data: dict):
                        try:
                            event_repo.update(e_id, up_data)
                        except Exception as p_err:
                            logger.debug(f"Notice async updating event in repo: {p_err}")
                    threading.Thread(
                        target=_async_patch,
                        args=(ev.id, {
                            "updated_at": ev_dict["updated_at"],
                            "duration_seconds": ev_dict["duration_seconds"],
                            "risk_score": ev_dict["risk_score"],
                            "status": ev_dict["status"],
                        }),
                        daemon=True,
                    ).start()

            events_contract.append({
                "event_id": ev.id,
                "event_type": ev.event_type.value.upper(),
                "priority": ev.priority.value.upper(),
                "risk_score": round(float(ev.risk_score), 1),
                "confidence": round(float(ev.detection_confidence), 2),
                "track_id": ev.track_id,
                "reason_codes": [rc.value.upper() if hasattr(rc, "value") else str(rc).upper() for rc in ev.reason_codes],
                "explanation_summary": ev.explanation_summary,
            })

        # State machine transition: update analysis status if an actionable security event occurs
        has_critical_event = any(e["priority"] in ("HIGH", "CRITICAL") for e in formatted_events)
        if has_critical_event:
            _ANALYSIS_STATUS.setdefault(cam_id, {})["status"] = "EVENT_DETECTED"
            if formatted_events:
                _ANALYSIS_STATUS[cam_id]["last_event_id"] = formatted_events[0]["id"]
        elif _ANALYSIS_STATUS.get(cam_id, {}).get("status") == "EVENT_DETECTED":
            _ANALYSIS_STATUS[cam_id]["status"] = "ANALYZING"

        # Primary track context for border track pillar
        primary_track = tracks[0] if tracks else None
        border_track_payload = None
        if primary_track:
            primary_sp = spatial_map.get(primary_track.track_id)
            dir_val = primary_sp.direction.value.upper() if primary_sp else "TOWARD"
            border_track_payload = {
                "border_track_id": f"BT-{primary_track.track_id}",
                "target_class": primary_track.class_id.value.upper(),
                "camera_sequence": [cam_id],
                "active_camera_id": cam_id,
                "current_local_track_id": primary_track.track_id,
                "association_state": "CONFIRMED" if primary_track.age_frames > 5 else "ACTIVE",
                "association_confidence": 0.94,
                "direction": dir_val,
                "duration_seconds": round(primary_track.age_frames * 0.04, 1),
            }

        # Sector normality context
        sector_context_payload = {
            "sector_id": sector_id,
            "normality_state": "UNUSUAL_ACTIVITY" if any(e["risk_score"] > 60 for e in formatted_events) else "NORMAL",
            "expected_density": 0.05,
            "observed_count": len(tracks),
            "anomaly_score": max([e["risk_score"] / 100.0 for e in formatted_events], default=0.05),
            "reasons": ["Human movement toward border"] if formatted_events else [],
        }

        # Stream health contract (DEC-0012)
        sh_dict = None
        if stream_health is not None:
            sh_dict = stream_health.to_dict() if hasattr(stream_health, "to_dict") else dict(stream_health)
        elif orch and hasattr(orch, "continuity_manager"):
            sh_dict = orch.continuity_manager.get_metrics().to_dict()

        # Camera contract metrics
        now_dt = datetime.now(timezone.utc)
        frame_age_ms = round((now_dt - packet.timestamp_utc).total_seconds() * 1000.0, 1)

        if sh_dict:
            conn_status = sh_dict.get("state", "HEALTHY")
            capture_fps = sh_dict.get("capture_fps", 25.0)
            processing_fps = sh_dict.get("processing_fps", round(fps, 1))
            avg_lat = sh_dict.get("latency_ms", 40.0)
            frame_age_ms = sh_dict.get("frame_age_ms", max(0.0, frame_age_ms))
        else:
            src_health = orch.source.get_health() if (orch and orch.source) else None
            conn_status = src_health.state.value.upper() if src_health else "ONLINE"
            capture_fps = src_health.fps_measured if src_health and src_health.fps_measured > 0 else (packet.source_fps or 25.0)
            processing_fps = round(fps, 1)
            avg_lat = orch._stage_latencies_history["total"][-1] if (orch and orch._stage_latencies_history.get("total")) else 40.0

        camera_contract = {
            "camera_id": cam_id,
            "source_type": packet.source_type.upper() if hasattr(packet, "source_type") else ("RTSP" if rtsp_url else "FILE"),
            "connection_status": conn_status,
            "resolution": f"{packet.width}x{packet.height}" if packet.width and packet.height else "1280x720",
            "capture_fps": round(float(capture_fps), 1),
            "processing_fps": round(float(processing_fps), 1),
            "output_fps": round(fps, 1),
            "processing_latency_ms": round(float(avg_lat), 1),
            "frame_timestamp": packet.timestamp_utc.isoformat(),
            "frame_age_ms": max(0.0, frame_age_ms),
        }

        # Environment contract
        env_contract = {
            "lighting": env_state.lighting.value.upper() if env_state else "DAYLIGHT",
            "brightness": round(float(env_state.brightness), 2) if env_state else 128.0,
            "blur_score": round(float(env_state.blur_score), 1) if env_state else 250.0,
            "visibility": env_state.visibility.value.upper() if env_state else "HIGH_VISIBILITY",
            "weather_hint": env_state.weather.value.upper() if (env_state and hasattr(env_state, "weather")) else "CLEAR",
            "quality_score": round(float(env_state.quality_score), 2) if env_state else 1.0,
            "uncertainty_flags": [f.value.upper() if hasattr(f, "value") else str(f).upper() for f in getattr(env_state, "flags", [])] if env_state else [],
        }

        # Build unified real-time telemetry packet
        telemetry_payload = {
            "session_id": session_id,
            "analysis_status": _ANALYSIS_STATUS.get(cam_id, {}).get("status", "ANALYZING"),
            "camera": camera_contract,
            "stream_health": sh_dict,
            "environment": env_contract,
            "detections": formatted_detections,
            "tracks": formatted_tracks,
            "spatial": spatial_contract,
            "behavior": behavior_contract,
            "events": events_contract,
            # Top-level backward-compatible keys
            "camera_id": cam_id,
            "timestamp_utc": packet.timestamp_utc.isoformat(),
            "fps": round(fps, 1),
            "is_calibrated": True,
            "spatial_states": formatted_spatial,
            "behavior_primitives": formatted_behaviors,
            "active_events": formatted_events,
            "border_track": border_track_payload,
            "sector_context": sector_context_payload,
        }
        _LAST_TELEMETRY[cam_id] = telemetry_payload.copy()
        broadcast_telemetry_sync(telemetry_payload)

    return on_frame_callback


def _resolve_model_path(model_type: Optional[str] = None, explicit_weights: Optional[str] = None) -> str:
    """Resolves model weights to an absolute filesystem path across families (YOLOv8, YOLO11, YOLO26)."""
    from ...config import settings
    from worker.perception.config import resolve_model_weights
    m_type = model_type or getattr(settings, "MODEL_TYPE", "yolov8") or "yolov8"
    weights = explicit_weights or getattr(settings, "MODEL_WEIGHTS", None) or settings.YOLO_MODEL_PATH
    return resolve_model_weights(m_type, weights)



def _resolve_video_path(raw_path: str) -> Optional[Path]:
    """Resolves a video file path across server root and storage directories."""
    from ...config import settings
    clean_raw = raw_path.replace("\\", "/")
    candidates = [
        Path(raw_path),
        Path(clean_raw),
        settings.repo_root / clean_raw,
        settings.storage_path / "uploads" / clean_raw,
        settings.storage_path / "uploads" / Path(clean_raw).name,
        settings.samples_path / clean_raw,
        settings.samples_path / Path(clean_raw).name,
        settings.storage_path / clean_raw,
    ]
    for cand in candidates:
        if cand.exists() and cand.is_file():
            return cand.resolve()
    return None


def _get_rss_mb() -> float:
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def _run_analysis_background(
    cam_id: str,
    video_file_path: Optional[str],
    rtsp_url: Optional[str],
    device: str,
    session_id: str,
    sector_id: str = "SECTOR-B07",
    sector_name: str = "Northern Border Sector",
):
    """
    Executes real 9-stage intelligence analysis asynchronously in the background.
    Safely opens video source, loads and warms up YOLOv8n, primes the MJPEG stream,
    broadcasts initial WebSocket telemetry, and runs the main processing loop until completion.
    Catches all background exceptions, updates status to ERROR or COMPLETED, and cleans up resources.
    """
    from ...config import settings

    t_bg_start = time.perf_counter()
    rss_init = _get_rss_mb()
    logger.info(f"[RUN_ANALYSIS] background_worker_invoked: session='{session_id}', rss={rss_init:.1f}MB")

    source_name = Path(video_file_path).name if video_file_path else mask_rtsp_url(rtsp_url or "")
    orchestrator: Optional[LivePipelineOrchestrator] = None

    try:
        # A. Register camera in database if not present
        try:
            existing_db_cam = camera_repo.get(cam_id)
            if not existing_db_cam:
                camera_repo.insert({
                    "id": cam_id,
                    "name": f"Camera {cam_id}",
                    "stream_url": str(video_file_path or rtsp_url or "storage/samples/test_video.mp4"),
                    "location": f"{sector_name} ({sector_id})",
                    "status": "online",
                    "is_active": True,
                })
        except Exception as exc:
            logger.debug(f"Database camera sync notice: {exc}")

        # B. Resolve model path and runtime storage directories
        logger.info(f"[RUN_ANALYSIS] pipeline_init_start +{(time.perf_counter() - t_bg_start)*1000.0:.1f}ms")
        resolved_model_path = _resolve_model_path()
        evidence_dir = str(settings.evidence_path)
        runs_dir = str(settings.repo_root / "results" / "live_runs")

        config = PipelineConfig(
            camera_id=cam_id,
            run_id=f"run_{int(time.time())}_{cam_id}",
            rtsp_url=rtsp_url,
            file_path=video_file_path,
            run_mode=RunMode.HEADLESS,
            device=device,
            detector_type=getattr(settings, "MODEL_TYPE", "yolov8") or "yolov8",
            model_path=resolved_model_path,
            detection_confidence=getattr(settings, "CONFIDENCE_THRESHOLD", 0.35),
            evidence_storage_dir=evidence_dir,
            record_output_dir=runs_dir,
            status_interval_seconds=5.0,
            loop_video=False,  # Video finishes at EOF so COMPLETED status triggers
        )

        orchestrator = LivePipelineOrchestrator(config)
        orchestrator.setup_prototype_border()

        # C. Open Video Source
        logger.info(f"[RUN_ANALYSIS] video_open_start +{(time.perf_counter() - t_bg_start)*1000.0:.1f}ms")
        orchestrator.initialize_source()
        src_health = orchestrator.source.get_health()
        logger.info(
            f"[RUN_ANALYSIS] video_opened +{(time.perf_counter() - t_bg_start)*1000.0:.1f}ms: "
            f"'{source_name}' (health={src_health.state.value.upper()}, FPS={src_health.fps_measured:.1f})"
        )

        # D. Read first frame from source
        logger.info(f"[RUN_ANALYSIS] first_frame_start +{(time.perf_counter() - t_bg_start)*1000.0:.1f}ms")
        first_packet = orchestrator.source.read()
        if first_packet is None:
            raise RuntimeError(f"Unable to read initial frame from video source '{source_name}'")
        logger.info(
            f"[RUN_ANALYSIS] first_frame_received +{(time.perf_counter() - t_bg_start)*1000.0:.1f}ms: "
            f"{first_packet.width}x{first_packet.height}"
        )

        # E. Ensure YOLO is ready & warmed up
        if not getattr(orchestrator.detector, "_warmup_done", False):
            logger.info(f"[RUN_ANALYSIS] model_load_start +{(time.perf_counter() - t_bg_start)*1000.0:.1f}ms")
            orchestrator.detector.load()
            logger.info(f"[RUN_ANALYSIS] model_loaded +{(time.perf_counter() - t_bg_start)*1000.0:.1f}ms")
            logger.info(f"[RUN_ANALYSIS] warmup_start +{(time.perf_counter() - t_bg_start)*1000.0:.1f}ms")
            orchestrator.detector.warmup()
            logger.info(f"[RUN_ANALYSIS] warmup_complete +{(time.perf_counter() - t_bg_start)*1000.0:.1f}ms")
        det_name = getattr(orchestrator.detector, "model_name", "Detector")
        logger.info(f"[DETECTOR_READY] {det_name} detector loaded from '{resolved_model_path}' and warmed up on device '{device}'")

        # F. First inference & initial visualization frame
        logger.info(f"[RUN_ANALYSIS] inference_start +{(time.perf_counter() - t_bg_start)*1000.0:.1f}ms")
        raw_dets = orchestrator.detector.infer(first_packet)
        logger.info(f"[RUN_ANALYSIS] inference_complete +{(time.perf_counter() - t_bg_start)*1000.0:.1f}ms: dets={len(raw_dets)}")

        camera_motion = orchestrator.camera_motion_estimator.update(first_packet.image)
        filt = orchestrator.detection_filter.filter_detections(
            raw_detections=raw_dets,
            image_shape=first_packet.image.shape,
            camera_motion=camera_motion,
        )
        initial_vis = orchestrator.visualizer.render_frame(
            frame=first_packet.image,
            tracks=[],
            spatial_states=[],
            behavior_primitives=[],
            events=[],
            environment=None,
            projected_border=orchestrator._latest_projected_border,
            is_calibrated=orchestrator._is_calibrated,
            fps=25.0,
            raw_detections_count=len(raw_dets),
            operational_detections_count=len(filt.operational_detections),
            camera_motion=camera_motion,
        )
        logger.info(f"[FIRST_FRAME_PROCESSED] First frame processed: {first_packet.width}x{first_packet.height} (frame_id={first_packet.frame_id}, detections={len(raw_dets)})")

        # G. Prime MJPEG stream buffer immediately with the rendered frame
        update_latest_frame(cam_id, initial_vis)
        logger.info(f"[RUN_ANALYSIS] mjpeg_primed +{(time.perf_counter() - t_bg_start)*1000.0:.1f}ms")

        # H. Put first packet into queue so orchestrator processes it through the pipeline
        orchestrator.queue.put(first_packet)

        # I. Register on-frame callback for ongoing telemetry & MJPEG stream updates
        orchestrator.on_frame_processed = _build_on_frame_callback(cam_id, rtsp_url, sector_id, session_id)

        # J. Broadcast initial telemetry packet immediately over WebSocket
        initial_telemetry = {
            "camera_id": cam_id,
            "session_id": session_id,
            "analysis_status": "ANALYZING",
            "camera": {
                "camera_id": cam_id,
                "source_type": "FILE" if video_file_path else "RTSP",
                "connection_status": "HEALTHY",
                "resolution": f"{first_packet.width}x{first_packet.height}",
                "capture_fps": 25.0,
                "processing_fps": 25.0,
                "output_fps": 25.0,
                "processing_latency_ms": 30.0,
                "frame_timestamp": first_packet.timestamp_utc.isoformat(),
                "frame_age_ms": 0.0,
            },
            "stream_health": orchestrator.continuity_manager.get_metrics().to_dict(),
            "environment": {
                "lighting": "DAYLIGHT",
                "brightness": 128.0,
                "blur_score": 250.0,
                "visibility": "HIGH_VISIBILITY",
                "weather_hint": "CLEAR",
                "quality_score": 1.0,
                "uncertainty_flags": [],
            },
            "detections": [],
            "tracks": [],
            "spatial": [],
            "behavior": [],
            "events": [],
            "timestamp_utc": first_packet.timestamp_utc.isoformat(),
            "fps": 25.0,
            "is_calibrated": True,
        }
        broadcast_telemetry_sync(initial_telemetry)
        logger.info(f"[RUN_ANALYSIS] telemetry_active +{(time.perf_counter() - t_bg_start)*1000.0:.1f}ms")
        rss_running = _get_rss_mb()
        logger.info(f"[RESOURCE] background pipeline active: rss={rss_running:.1f}MB, delta={rss_running - rss_init:+.1f}MB")

        # K. Register in active orchestrator table
        _RUNNING_ORCHESTRATORS[cam_id] = orchestrator
        logger.info(f"[ANALYSIS_RUNNING] Real analysis pipeline active and processing frames for camera '{cam_id}' on '{source_name}'")

        # L. Run main frame processing loop
        orchestrator.run()

        logger.info(f"[ANALYSIS_COMPLETED] Video analysis completed successfully for camera '{cam_id}' (session '{session_id}')")
        completed_at_iso = datetime.now(timezone.utc).isoformat()
        _ANALYSIS_STATUS[cam_id] = {
            "session_id": session_id,
            "status": "COMPLETED",
            "camera_id": cam_id,
            "video_path": video_file_path or rtsp_url,
            "file_name": source_name,
            "completed_at": completed_at_iso,
        }

        # Build comprehensive COMPLETED telemetry packet preserving last state
        completed_telem = _LAST_TELEMETRY.get(cam_id, {}).copy()
        if not completed_telem:
            completed_telem = initial_telemetry.copy()

        completed_telem["analysis_status"] = "COMPLETED"
        completed_telem["status"] = "COMPLETED"
        completed_telem["session_id"] = session_id
        completed_telem["camera_id"] = cam_id
        completed_telem["timestamp_utc"] = completed_at_iso
        completed_telem["fps"] = 0.0

        if "camera" in completed_telem and isinstance(completed_telem["camera"], dict):
            completed_telem["camera"]["processing_fps"] = 0.0
            completed_telem["camera"]["capture_fps"] = 0.0
            completed_telem["camera"]["output_fps"] = 0.0
            completed_telem["camera"]["connection_status"] = "ONLINE"

        if "stream_health" in completed_telem and isinstance(completed_telem["stream_health"], dict):
            completed_telem["stream_health"]["state"] = "COMPLETED"
            completed_telem["stream_health"]["status_reason"] = "Video analysis completed successfully (EOF)"
            completed_telem["stream_health"]["capture_fps"] = 0.0
            completed_telem["stream_health"]["processing_fps"] = 0.0

        _LAST_TELEMETRY[cam_id] = completed_telem.copy()
        broadcast_telemetry_sync(completed_telem)

        # Start post-completion WebSocket heartbeat so browser connection stays active indefinitely
        def _post_complete_heartbeat():
            while (
                _ANALYSIS_STATUS.get(cam_id, {}).get("session_id") == session_id
                and _ANALYSIS_STATUS.get(cam_id, {}).get("status") == "COMPLETED"
            ):
                time.sleep(2.5)
                if (
                    _ANALYSIS_STATUS.get(cam_id, {}).get("session_id") != session_id
                    or _ANALYSIS_STATUS.get(cam_id, {}).get("status") != "COMPLETED"
                ):
                    break
                heartbeat = _LAST_TELEMETRY.get(cam_id, {}).copy()
                if heartbeat:
                    heartbeat["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
                    broadcast_telemetry_sync(heartbeat)

        threading.Thread(
            target=_post_complete_heartbeat,
            daemon=True,
            name=f"Heartbeat-{cam_id}-{session_id}",
        ).start()

    except Exception as exc:
        logger.error(f"[ANALYSIS_ERROR] Background pipeline failed on camera '{cam_id}' (session '{session_id}'): {exc}", exc_info=True)
        _ANALYSIS_STATUS[cam_id] = {
            "session_id": session_id,
            "status": "ERROR",
            "camera_id": cam_id,
            "video_path": video_file_path or rtsp_url,
            "file_name": source_name,
            "error": str(exc),
        }
        broadcast_telemetry_sync({
            "camera_id": cam_id,
            "session_id": session_id,
            "analysis_status": "ERROR",
            "status": "ERROR",
            "error": str(exc),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        _RUNNING_ORCHESTRATORS.pop(cam_id, None)
        _RUNNING_THREADS.pop(cam_id, None)
        if orchestrator is not None:
            try:
                orchestrator.stop()
            except Exception:
                pass
        import gc
        gc.collect()
        logger.info(f"[PIPELINE_CLEANUP] Resources released and gc.collect() executed for camera '{cam_id}'")


def _initialize_and_start_pipeline(
    cam_id: str,
    video_file_path: Optional[str],
    rtsp_url: Optional[str],
    device: str,
    session_id: str,
    sector_id: str = "SECTOR-B07",
    sector_name: str = "Northern Border Sector",
):
    """Spawns background analysis thread for backward-compatibility."""
    worker_thread = threading.Thread(
        target=_run_analysis_background,
        args=(cam_id, video_file_path, rtsp_url, device, session_id, sector_id, sector_name),
        name=f"IBVAP-Analysis-{cam_id}-{session_id}",
        daemon=True,
    )
    worker_thread.start()
    _RUNNING_THREADS[cam_id] = worker_thread


@router.post("/connect", response_model=Dict[str, Any])
def connect_rtsp_camera(request: ConnectCameraRequest):
    """
    Connects to a live RTSP stream or local MP4 video file, starts the 9-stage intelligence
    pipeline in a background worker, and streams frames + telemetry directly to the operator console.
    """
    cam_id = request.camera_id.strip()
    rtsp_url = request.rtsp_url.strip() if request.rtsp_url else None
    raw_video_path = request.video_file_path.strip() if request.video_file_path else None

    if not rtsp_url and not raw_video_path:
        raise HTTPException(
            status_code=400,
            detail="Either 'rtsp_url' or 'video_file_path' must be provided.",
        )

    # 1. Stop previous worker cleanly
    if cam_id in _RUNNING_ORCHESTRATORS:
        try:
            _RUNNING_ORCHESTRATORS[cam_id].stop()
        except Exception:
            pass
        _RUNNING_ORCHESTRATORS.pop(cam_id, None)
        if cam_id in _RUNNING_THREADS:
            _RUNNING_THREADS[cam_id].join(timeout=1.0)
            _RUNNING_THREADS.pop(cam_id, None)

    # 2. If RTSP stream, verify connectivity first
    if rtsp_url:
        from worker.ingestion.rtsp_source import RTSPVideoSource
        test_source = RTSPVideoSource(camera_id=cam_id, rtsp_url=rtsp_url, max_reconnect_attempts=1)
        if not test_source.connect():
            raise HTTPException(
                status_code=400,
                detail=f"Unable to connect to RTSP source '{mask_rtsp_url(rtsp_url)}'",
            )
        test_source.close()

    # Resolve video path if file provided
    resolved_video_str: Optional[str] = None
    if raw_video_path:
        resolved_p = _resolve_video_path(raw_video_path)
        if not resolved_p or not resolved_p.exists():
            raise HTTPException(status_code=404, detail=f"Video file not found at '{raw_video_path}'")
        resolved_video_str = str(resolved_p)

    session_id = f"ses_{int(time.time() * 1000)}_{cam_id}"

    # 3. Register in Camera Registry
    display_source = mask_rtsp_url(rtsp_url) if rtsp_url else f"FILE: {resolved_video_str}"
    cam_entry = {
        "camera_id": cam_id,
        "name": request.name,
        "rtsp_url": display_source,
        "video_file_path": resolved_video_str,
        "sector_id": request.sector_id or "SECTOR-B07",
        "sector_name": request.sector_name or "Northern Border",
        "status": "ONLINE",
        "resolution": "1280x720",
        "fps_target": 25.0,
        "is_calibrated": True,
        "location": {"lat": 28.6139, "lng": 77.2090, "elevation_m": 12.5},
        "visible_border_sections": ["SEC-ALPHA"],
        "connected_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    existing_idx = next((i for i, c in enumerate(_CAMERAS_REGISTRY) if c["camera_id"] == cam_id), None)
    if existing_idx is not None:
        _CAMERAS_REGISTRY[existing_idx] = cam_entry
    else:
        _CAMERAS_REGISTRY.append(cam_entry)

    try:
        existing_db_cam = camera_repo.get(cam_id)
        if not existing_db_cam:
            camera_repo.insert({
                "id": cam_id,
                "name": request.name or f"Camera {cam_id}",
                "stream_url": resolved_video_str or rtsp_url or "storage/samples/test_video.mp4",
                "location": "Northern Border Sector",
                "status": "online",
                "is_active": True,
            })
    except Exception as exc:
        logger.debug(f"Database camera sync notice: {exc}")

    # 4. Asynchronously initialize and start background execution
    _ANALYSIS_STATUS[cam_id] = {
        "session_id": session_id,
        "status": "ANALYZING",
        "camera_id": cam_id,
        "video_path": resolved_video_str or rtsp_url,
        "file_name": display_source,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "error": None,
    }
    try:
        _initialize_and_start_pipeline(
            cam_id=cam_id,
            video_file_path=resolved_video_str,
            rtsp_url=rtsp_url,
            device=request.device or "cpu",
            session_id=session_id,
            sector_id=request.sector_id or "SECTOR-B07",
            sector_name=request.sector_name or "Northern Border",
        )
    except Exception as exc:
        logger.error(f"Failed to connect camera '{cam_id}': {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Camera pipeline startup failed: {str(exc)}")

    logger.info(f"Camera '{cam_id}' ({display_source}) connected, session '{session_id}' started.")
    return {
        "status": "CONNECTED",
        "session_id": session_id,
        "message": f"Pipeline active for camera '{cam_id}' on {display_source}",
        "camera": cam_entry,
    }


@router.post("/{camera_id}/disconnect", response_model=Dict[str, Any])
def disconnect_camera(camera_id: str):
    """Stops the live pipeline and marks the camera as disconnected."""
    if camera_id in _RUNNING_ORCHESTRATORS:
        try:
            _RUNNING_ORCHESTRATORS[camera_id].stop()
        except Exception:
            pass
        _RUNNING_ORCHESTRATORS.pop(camera_id, None)
        if camera_id in _RUNNING_THREADS:
            _RUNNING_THREADS[camera_id].join(timeout=1.0)
            _RUNNING_THREADS.pop(camera_id, None)

    for cam in _CAMERAS_REGISTRY:
        if cam["camera_id"] == camera_id:
            cam["status"] = "OFFLINE"

    return {"status": "DISCONNECTED", "camera_id": camera_id}


@router.delete("/{camera_id}", response_model=Dict[str, Any])
def delete_camera(camera_id: str):
    """Stops the pipeline and removes the camera from the registry."""
    disconnect_camera(camera_id)
    global _CAMERAS_REGISTRY
    _CAMERAS_REGISTRY = [c for c in _CAMERAS_REGISTRY if c["camera_id"] != camera_id]
    return {"status": "REMOVED", "camera_id": camera_id}


@router.get("/{camera_id}/calibration", response_model=Dict[str, Any])
def get_camera_calibration(camera_id: str):
    """Returns projected world-border geometry for the requested camera."""
    try:
        from configs.demo_border_config import BORDER_LINE_START, BORDER_LINE_END, WARNING_BUFFER_VERTICES
        proj_pts = [
            {"x": float(BORDER_LINE_START[0]), "y": float(BORDER_LINE_START[1])},
            {"x": float(BORDER_LINE_END[0]), "y": float(BORDER_LINE_END[1])},
        ]
        warn_pts = [
            {"x": float(WARNING_BUFFER_VERTICES[0][0]), "y": float(WARNING_BUFFER_VERTICES[0][1])},
            {"x": float(WARNING_BUFFER_VERTICES[1][0]), "y": float(WARNING_BUFFER_VERTICES[1][1])},
        ]
    except Exception:
        proj_pts = [{"x": 150.0, "y": 360.0}, {"x": 1150.0, "y": 360.0}]
        warn_pts = [{"x": 150.0, "y": 200.0}, {"x": 1150.0, "y": 200.0}]

    return {
        "camera_id": camera_id,
        "calibration_status": "CALIBRATED",
        "border_section_id": "SEC-ALPHA",
        "projected_points": proj_pts,
        "warning_buffer_points": warn_pts,
        "reprojection_error_px": 0.42,
        "last_calibrated_utc": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{camera_id}/health", response_model=Dict[str, Any])
def get_camera_health(camera_id: str):
    """Returns real-time stream health & continuity metrics for the requested camera."""
    orch = _RUNNING_ORCHESTRATORS.get(camera_id)
    if orch and hasattr(orch, "continuity_manager"):
        return orch.continuity_manager.get_metrics().to_dict()

    last_telem = _LAST_TELEMETRY.get(camera_id, {})
    if "stream_health" in last_telem and last_telem["stream_health"]:
        return last_telem["stream_health"]

    return {
        "camera_id": camera_id,
        "state": "OFFLINE",
        "status_reason": "No active pipeline running for this camera",
        "capture_fps": 0.0,
        "processing_fps": 0.0,
        "latency_ms": 0.0,
        "jitter_ms": 0.0,
        "frame_age_ms": 0.0,
        "dropped_frames_total": 0,
        "trust_score": 0.0,
        "is_frozen": False,
        "consecutive_healthy_frames": 0,
        "last_interruption_duration": 0.0,
        "gap_count": 0,
    }


@router.post("/upload", response_model=UploadVideoResponse)
async def upload_video(
    file: UploadFile = File(...),
    camera_id: str = Form("DEMO-CAM-01"),
):
    """
    Uploads an MP4 video file from the Operator Console to server-side storage.
    Stages it as ready for real pipeline analysis without Windows-specific paths.
    """
    if not file.filename.lower().endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Only MP4 video files (.mp4) are supported.")

    from ...config import settings
    upload_dir = settings.storage_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename and create unique timestamped destination
    clean_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", file.filename)
    dest_filename = f"{int(time.time())}_{clean_name}"
    dest_path = upload_dir / dest_filename

    total_bytes = 0
    try:
        with open(dest_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)
                total_bytes += len(chunk)
    except Exception as exc:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        logger.error(f"Failed to save uploaded video: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to write uploaded file: {str(exc)}")

    storage_ref = f"uploads/{dest_filename}"
    _ANALYSIS_STATUS[camera_id] = {
        "status": "READY TO ANALYZE",
        "file_name": file.filename,
        "video_path": storage_ref,
        "file_size": total_bytes,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(f"Uploaded video '{file.filename}' ({total_bytes} bytes) staged at '{dest_path}' for camera '{camera_id}'")
    return UploadVideoResponse(
        status="READY TO ANALYZE",
        file_name=file.filename,
        video_path=storage_ref,
        file_size_bytes=total_bytes,
        camera_id=camera_id,
        message=f"Video '{file.filename}' uploaded successfully ({total_bytes / (1024*1024):.1f} MB). Ready to analyze.",
    )



@router.post("/run-analysis", response_model=Dict[str, Any])
def run_analysis(request: RunAnalysisRequest):
    """
    Starts real 9-stage intelligence analysis on an uploaded or specified MP4 video file.
    Non-blocking async starter: validates request, creates session, launches background worker,
    and returns HTTP 200 with status ANALYZING immediately (< 100ms) while analysis continues.
    Enforces single-session concurrency: cleanly rejects concurrent runs if another analysis is active.
    """
    t_req_start = time.perf_counter()
    rss_before = _get_rss_mb()
    cam_id = request.camera_id.strip()
    raw_path = request.video_file_path.strip()

    logger.info(f"[RUN_ANALYSIS] request_received: camera='{cam_id}', path='{raw_path}', rss={rss_before:.1f}MB")

    # 1. Path Resolution across server locations
    resolved_path = _resolve_video_path(raw_path)
    if not resolved_path or not resolved_path.exists():
        logger.error(f"Run Analysis failed: Video file not found at '{raw_path}'")
        raise HTTPException(status_code=404, detail=f"Video file not found at '{raw_path}'")

    if not os.access(resolved_path, os.R_OK):
        logger.error(f"Run Analysis failed: Video file not readable at '{resolved_path}'")
        raise HTTPException(status_code=400, detail=f"Video file not readable at '{resolved_path}'")

    logger.info(
        f"[RUN_ANALYSIS] upload_resolved +{(time.perf_counter() - t_req_start)*1000.0:.1f}ms: "
        f"'{resolved_path}' ({resolved_path.stat().st_size} bytes)"
    )

    # 2. Concurrency Protection (Only ONE analysis session may run at a time)
    with _ANALYSIS_LOCK:
        # Clean up any stale threads or stopped orchestrators
        for cid, th in list(_RUNNING_THREADS.items()):
            if not th.is_alive():
                _RUNNING_THREADS.pop(cid, None)
        for cid, orch in list(_RUNNING_ORCHESTRATORS.items()):
            if not getattr(orch, "_is_running", False):
                _RUNNING_ORCHESTRATORS.pop(cid, None)

        is_any_running = False
        active_cam_id = None
        for cid, orch in list(_RUNNING_ORCHESTRATORS.items()):
            if getattr(orch, "_is_running", False):
                is_any_running = True
                active_cam_id = cid
                break
        if not is_any_running:
            for cid, th in list(_RUNNING_THREADS.items()):
                if th.is_alive() and _ANALYSIS_STATUS.get(cid, {}).get("status") in ("STARTING", "ANALYZING", "EVENT_DETECTED"):
                    is_any_running = True
                    active_cam_id = cid
                    break

        if is_any_running:
            logger.warning(f"[RUN_ANALYSIS_REJECTED] Analysis session already running on camera '{active_cam_id}'. Concurrent requests cleanly rejected.")
            raise HTTPException(
                status_code=409,
                detail=f"An analysis session is already running on camera '{active_cam_id}'. Please wait for completion or click Stop before starting a new analysis.",
            )

        # 3. Create Unique Session Identifier
        session_id = f"ses_{int(time.time() * 1000)}_{cam_id}"
        logger.info(f"[RUN_ANALYSIS] session_created +{(time.perf_counter() - t_req_start)*1000.0:.1f}ms: session_id='{session_id}'")

        # Ensure camera registered in local memory registry
        cam_entry = {
            "camera_id": cam_id,
            "name": "Operator Video Analysis",
            "rtsp_url": f"FILE: {resolved_path.name}",
            "video_file_path": str(resolved_path),
            "sector_id": "SECTOR-B07",
            "sector_name": "Northern Border Sector",
            "status": "ONLINE",
            "resolution": "1280x720",
            "fps_target": 25.0,
            "is_calibrated": True,
            "location": {"lat": 28.6139, "lng": 77.2090, "elevation_m": 12.5},
            "visible_border_sections": ["SEC-ALPHA"],
            "connected_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        existing_idx = next((i for i, c in enumerate(_CAMERAS_REGISTRY) if c["camera_id"] == cam_id), None)
        if existing_idx is not None:
            _CAMERAS_REGISTRY[existing_idx] = cam_entry
        else:
            _CAMERAS_REGISTRY.append(cam_entry)
        logger.info(f"[RUN_ANALYSIS] camera_ready +{(time.perf_counter() - t_req_start)*1000.0:.1f}ms")

        # 4. Mark status as ANALYZING immediately
        _ANALYSIS_STATUS[cam_id] = {
            "session_id": session_id,
            "status": "ANALYZING",
            "camera_id": cam_id,
            "video_path": str(resolved_path),
            "file_name": resolved_path.name,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }

        # 5. Launch background execution thread for complete real pipeline
        worker_thread = threading.Thread(
            target=_run_analysis_background,
            args=(cam_id, str(resolved_path), None, request.device or "cpu", session_id, "SECTOR-B07", "Northern Border Sector"),
            name=f"IBVAP-Analysis-{cam_id}-{session_id}",
            daemon=True,
        )
        worker_thread.start()
        _RUNNING_THREADS[cam_id] = worker_thread
        logger.info(
            f"[RUN_ANALYSIS] background_started +{(time.perf_counter() - t_req_start)*1000.0:.1f}ms: "
            f"thread='{worker_thread.name}'"
        )

    rss_after = _get_rss_mb()
    elapsed_ms = (time.perf_counter() - t_req_start) * 1000.0
    logger.info(
        f"[RESOURCE] rss_before={rss_before:.1f}MB, rss_after={rss_after:.1f}MB, "
        f"delta={rss_after - rss_before:+.1f}MB, elapsed={elapsed_ms:.1f}ms"
    )
    logger.info(f"[RUN_ANALYSIS] response_returning +{elapsed_ms:.1f}ms")

    # 6. Return immediate HTTP response (< 100ms)
    return {
        "session_id": session_id,
        "status": "ANALYZING",
        "camera_id": cam_id,
        "source": str(resolved_path),
        "video_file_path": str(resolved_path),
        "file_name": resolved_path.name,
        "message": f"Real analysis pipeline active on {resolved_path.name}",
        "camera": cam_entry,
    }


@router.post("/stop-analysis", response_model=Dict[str, Any])
def stop_analysis(request: StopAnalysisRequest):
    """Stops active analysis on the specified camera and transitions state to COMPLETED."""
    cam_id = request.camera_id.strip()
    if cam_id in _RUNNING_ORCHESTRATORS:
        try:
            _RUNNING_ORCHESTRATORS[cam_id].stop()
        except Exception:
            pass
        _RUNNING_ORCHESTRATORS.pop(cam_id, None)
    if cam_id in _RUNNING_THREADS:
        _RUNNING_THREADS[cam_id].join(timeout=2.0)
        _RUNNING_THREADS.pop(cam_id, None)

    _ANALYSIS_STATUS[cam_id] = {
        "status": "COMPLETED",
        "stopped_at": datetime.now(timezone.utc).isoformat(),
    }
    from .streams import _LATEST_FRAMES
    _LATEST_FRAMES.pop(cam_id, None)
    logger.info(f"[ANALYSIS_STOPPED] Operator stopped analysis on camera '{cam_id}'")
    import gc
    gc.collect()
    return {"status": "COMPLETED", "camera_id": cam_id, "message": "Analysis stopped successfully"}


@router.get("/{camera_id}/analysis-status", response_model=Dict[str, Any])
def get_analysis_status(camera_id: str):
    """Returns the real-time operational status of the video analysis session."""
    st = _ANALYSIS_STATUS.get(camera_id, {})
    current_orch = _RUNNING_ORCHESTRATORS.get(camera_id)
    thread = _RUNNING_THREADS.get(camera_id)
    is_running = (current_orch is not None and getattr(current_orch, "_is_running", False)) or (
        thread is not None and thread.is_alive() and st.get("status") in ("STARTING", "ANALYZING", "EVENT_DETECTED")
    )

    current_status = st.get("status")
    if not current_status:
        current_status = "ANALYZING" if is_running else "READY"
    elif is_running and current_status not in ("EVENT_DETECTED",):
        current_status = "ANALYZING"

    return {
        "camera_id": camera_id,
        "status": current_status,
        "session_id": st.get("session_id"),
        "file_name": st.get("file_name"),
        "video_path": st.get("video_path"),
        "is_running": is_running,
        "started_at": st.get("started_at"),
        "completed_at": st.get("completed_at"),
        "error": st.get("error"),
    }


def start_demo_pipeline_if_configured():
    """
    Called on FastAPI startup (lifespan) to start the single demo pipeline if configured.
    Guarantees exactly ONE pipeline runs without duplicates.
    """
    from ...config import settings
    from pathlib import Path

    if not getattr(settings, "AUTO_START_DEMO_PIPELINE", False):
        return

    cam_id = getattr(settings, "DEFAULT_CAMERA_ID", "DEMO-CAM-01")
    if cam_id in _RUNNING_ORCHESTRATORS:
        logger.info(f"Demo camera '{cam_id}' pipeline is already running.")
        return

    video_path_str = getattr(settings, "DEMO_VIDEO_PATH", "storage/samples/test_video.mp4")
    video_path = Path(video_path_str)
    if not video_path.is_absolute():
        repo_root = settings.repo_root
        video_path = repo_root / video_path_str

    if not video_path.exists():
        logger.warning(
            f"Demo video file '{video_path_str}' not found on disk at '{video_path}'. "
            "Skipping automatic pipeline startup. Connect manually via UI or POST /api/v1/cameras/run-analysis."
        )
        return

    logger.info(f"Auto-starting production demo pipeline for camera '{cam_id}' with video '{video_path}'...")
    req = RunAnalysisRequest(
        camera_id=cam_id,
        video_file_path=str(video_path),
        device=getattr(settings, "DEFAULT_DEVICE", "cpu"),
    )
    try:
        run_analysis(req)
        logger.info(f"Production demo pipeline for camera '{cam_id}' started successfully.")
    except Exception as exc:
        logger.error(f"Failed to auto-start demo camera pipeline: {exc}")


def stop_all_pipelines():
    """Stops all active camera orchestrators and worker threads on server shutdown."""
    for cam_id, orch in list(_RUNNING_ORCHESTRATORS.items()):
        try:
            logger.info(f"Stopping orchestrator for camera '{cam_id}'...")
            orch.stop()
        except Exception as exc:
            logger.debug(f"Error stopping camera '{cam_id}': {exc}")
    _RUNNING_ORCHESTRATORS.clear()
    _RUNNING_THREADS.clear()
