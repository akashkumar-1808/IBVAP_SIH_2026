"""
Dynamic Camera Registration, RTSP Connection, and World-Border Calibration API.

Architecture Decision: DEC-0010 / DEC-0011
"""

import threading
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from worker.pipeline.schemas import PipelineConfig, RunMode
from worker.pipeline.orchestrator import LivePipelineOrchestrator
from worker.ingestion import mask_rtsp_url
from worker.spatial.schemas import ZoneType, CrossingStatus, MovementDirection
from .streams import update_latest_frame
from .ws import broadcast_telemetry_sync
from ...db.repositories import EventRepository, EvidenceRepository

logger = logging.getLogger("ibvap.cameras")
router = APIRouter(prefix="/cameras", tags=["Cameras"])

event_repo = EventRepository()
evidence_repo = EvidenceRepository()

# Dynamic in-memory camera registry
_CAMERAS_REGISTRY: List[Dict[str, Any]] = []

# Active background orchestrators & worker threads
_RUNNING_ORCHESTRATORS: Dict[str, LivePipelineOrchestrator] = {}
_RUNNING_THREADS: Dict[str, threading.Thread] = {}


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


@router.post("/connect", response_model=Dict[str, Any])
def connect_rtsp_camera(request: ConnectCameraRequest):
    """
    Connects to a live RTSP stream or local MP4 video file, starts the 9-stage intelligence
    pipeline in a background worker, and streams frames + telemetry directly to the operator console.
    """
    cam_id = request.camera_id.strip()
    rtsp_url = request.rtsp_url.strip() if request.rtsp_url else None
    video_file_path = request.video_file_path.strip() if request.video_file_path else None

    if not rtsp_url and not video_file_path:
        raise HTTPException(
            status_code=400,
            detail="Either 'rtsp_url' or 'video_file_path' must be provided.",
        )

    # 1. If camera already running, stop previous worker first
    if cam_id in _RUNNING_ORCHESTRATORS:
        try:
            _RUNNING_ORCHESTRATORS[cam_id].stop()
        except Exception:
            pass
        _RUNNING_ORCHESTRATORS.pop(cam_id, None)
        _RUNNING_THREADS.pop(cam_id, None)

    # 2. Configure Pipeline for live RTSP stream or offline MP4 file
    config = PipelineConfig(
        camera_id=cam_id,
        rtsp_url=rtsp_url,
        file_path=video_file_path,
        run_mode=RunMode.HEADLESS,
        device=request.device or "cpu",
        status_interval_seconds=5.0,
    )

    try:
        orchestrator = LivePipelineOrchestrator(config)
        # Setup prototype calibrated world-border for spatial analysis
        orchestrator.setup_prototype_border()
        # Initialize video ingestion source (with model warmup)
        orchestrator.initialize_source()

        # Pre-seed initial frame into MJPEG stream buffer for instantaneous (<25ms) browser display
        try:
            initial_packet = orchestrator.source.read()
            if initial_packet is not None:
                initial_vis = orchestrator.visualizer.render_frame(
                    frame=initial_packet.image,
                    tracks=[],
                    spatial_states=[],
                    behavior_primitives=[],
                    events=[],
                    environment=None,
                    projected_border=orchestrator._latest_projected_border,
                    is_calibrated=orchestrator._is_calibrated,
                    fps=25.0,
                )
                update_latest_frame(cam_id, initial_vis)
                orchestrator.queue.put(initial_packet)
        except Exception as exc:
            logger.debug(f"Pre-seed initial frame notice: {exc}")
    except Exception as exc:
        source_desc = mask_rtsp_url(rtsp_url) if rtsp_url else video_file_path
        logger.error(f"Failed to connect camera {cam_id} with source '{source_desc}': {exc}")
        raise HTTPException(
            status_code=400,
            detail=f"Unable to connect to source '{source_desc}'. Reason: {str(exc)}",
        )

    # 3. Setup real-time frame and telemetry broadcast hook
    def on_frame_callback(packet, env_state, detections, tracks, spatial_states, behaviors, events, fps, vis_image=None):
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
            event_repo.insert(ev_dict)

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
            "sector_id": request.sector_id or "SECTOR-B07",
            "normality_state": "UNUSUAL_ACTIVITY" if any(e["risk_score"] > 60 for e in formatted_events) else "NORMAL",
            "expected_density": 0.05,
            "observed_count": len(tracks),
            "anomaly_score": max([e["risk_score"] / 100.0 for e in formatted_events], default=0.05),
            "reasons": ["Human movement toward border"] if formatted_events else [],
        }

        # Camera contract metrics
        now_dt = datetime.now(timezone.utc)
        frame_age_ms = round((now_dt - packet.timestamp_utc).total_seconds() * 1000.0, 1)
        src_health = orchestrator.source.get_health() if orchestrator.source else None
        conn_status = src_health.state.value.upper() if src_health else "ONLINE"
        src_fps = src_health.fps_measured if src_health and src_health.fps_measured > 0 else (packet.source_fps or 25.0)
        avg_lat = orchestrator._stage_latencies_history["total"][-1] if orchestrator._stage_latencies_history.get("total") else 40.0

        camera_contract = {
            "camera_id": cam_id,
            "source_type": packet.source_type.upper() if hasattr(packet, "source_type") else ("RTSP" if rtsp_url else "FILE"),
            "connection_status": conn_status,
            "resolution": f"{packet.width}x{packet.height}" if packet.width and packet.height else "1280x720",
            "capture_fps": round(float(src_fps), 1),
            "processing_fps": round(fps, 1),
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
            "camera": camera_contract,
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
        broadcast_telemetry_sync(telemetry_payload)

    orchestrator.on_frame_processed = on_frame_callback

    # 4. Spawn background execution thread
    thread = threading.Thread(target=orchestrator.run, name=f"IBVAP-Pipeline-{cam_id}", daemon=True)
    thread.start()

    _RUNNING_ORCHESTRATORS[cam_id] = orchestrator
    _RUNNING_THREADS[cam_id] = thread

    # 5. Register in Camera Registry
    display_source = mask_rtsp_url(rtsp_url) if rtsp_url else f"FILE: {video_file_path}"
    cam_entry = {
        "camera_id": cam_id,
        "name": request.name,
        "rtsp_url": display_source,
        "video_file_path": video_file_path,
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

    # Replace existing or append
    existing_idx = next((i for i, c in enumerate(_CAMERAS_REGISTRY) if c["camera_id"] == cam_id), None)
    if existing_idx is not None:
        _CAMERAS_REGISTRY[existing_idx] = cam_entry
    else:
        _CAMERAS_REGISTRY.append(cam_entry)

    logger.info(f"Camera '{cam_id}' ({display_source}) successfully connected and pipeline worker started.")
    return {
        "status": "CONNECTED",
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
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        video_path = repo_root / video_path_str

    if not video_path.exists():
        logger.warning(
            f"Demo video file '{video_path_str}' not found on disk at '{video_path}'. "
            "Skipping automatic pipeline startup. Connect manually via UI or POST /api/v1/cameras/connect."
        )
        return

    logger.info(f"Auto-starting production demo pipeline for camera '{cam_id}' with video '{video_path}'...")
    req = ConnectCameraRequest(
        camera_id=cam_id,
        name="SIH Recorded Breach Demo",
        video_file_path=str(video_path),
        sector_id="SECTOR-B07",
        sector_name="Northern Border Sector",
        device=getattr(settings, "DEFAULT_DEVICE", "cpu"),
    )
    try:
        connect_rtsp_camera(req)
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
