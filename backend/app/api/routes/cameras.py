"""
Camera configuration, status, and world-border calibration API endpoints.

Architecture Decision: DEC-0010 / DEC-0011
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone

router = APIRouter(prefix="/cameras", tags=["Cameras"])

# Configured camera registry
_CAMERAS_REGISTRY: List[Dict[str, Any]] = [
    {
        "camera_id": "CAM-01",
        "name": "Border North",
        "sector_id": "SECTOR-B07",
        "sector_name": "Northern Border",
        "status": "ONLINE",
        "resolution": "1280x720",
        "fps_target": 25.0,
        "is_calibrated": True,
        "location": {"lat": 28.6139, "lng": 77.2090, "elevation_m": 12.5},
        "visible_border_sections": ["SEC-ALPHA", "SEC-BETA"],
    },
    {
        "camera_id": "CAM-02",
        "name": "Border Central",
        "sector_id": "SECTOR-B07",
        "sector_name": "Northern Border",
        "status": "ONLINE",
        "resolution": "1280x720",
        "fps_target": 25.0,
        "is_calibrated": True,
        "location": {"lat": 28.6145, "lng": 77.2098, "elevation_m": 14.0},
        "visible_border_sections": ["SEC-BETA", "SEC-GAMMA"],
    },
    {
        "camera_id": "CAM-03",
        "name": "Border South",
        "sector_id": "SECTOR-B07",
        "sector_name": "Northern Border",
        "status": "DEGRADED",
        "resolution": "1280x720",
        "fps_target": 25.0,
        "is_calibrated": True,
        "location": {"lat": 28.6152, "lng": 77.2105, "elevation_m": 10.0},
        "visible_border_sections": ["SEC-GAMMA"],
    },
]


@router.get("", response_model=List[Dict[str, Any]])
def list_cameras():
    """Returns all registered cameras and operational status."""
    return _CAMERAS_REGISTRY


@router.get("/{camera_id}", response_model=Dict[str, Any])
def get_camera(camera_id: str):
    """Returns camera metadata by ID."""
    cam = next((c for c in _CAMERAS_REGISTRY if c["camera_id"] == camera_id), None)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found.")
    return cam


@router.get("/{camera_id}/calibration", response_model=Dict[str, Any])
def get_camera_calibration(camera_id: str):
    """
    Returns projected world-border geometry, warning buffer polygon,
    and calibration status for the requested camera view.
    """
    cam = next((c for c in _CAMERAS_REGISTRY if c["camera_id"] == camera_id), None)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found.")

    # Project standard border points relative to 1280x720 normalized view
    projected_points = [
        {"x": 100.0, "y": 480.0},
        {"x": 420.0, "y": 440.0},
        {"x": 780.0, "y": 380.0},
        {"x": 1180.0, "y": 320.0},
    ]
    warning_buffer_points = [
        {"x": 100.0, "y": 420.0},
        {"x": 420.0, "y": 380.0},
        {"x": 780.0, "y": 320.0},
        {"x": 1180.0, "y": 260.0},
    ]

    return {
        "camera_id": camera_id,
        "calibration_status": "CALIBRATED",
        "border_section_id": "SEC-ALPHA",
        "projected_points": projected_points,
        "warning_buffer_points": warning_buffer_points,
        "reprojection_error_px": 0.42,
        "last_calibrated_utc": datetime.now(timezone.utc).isoformat(),
    }
