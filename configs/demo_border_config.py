"""
IBVAP — Deterministic SIH Demo Virtual Border Configuration.

Provides clearly isolated, easily modifiable virtual border, warning buffer,
and restricted zone coordinates for prototype recorded MP4 video testing.

Uses LOCAL_CARTESIAN / 2D pixel space — NO GPS / world coordinates required.
To adjust for any phone/laptop recorded video, simply adjust BORDER_LINE_START,
BORDER_LINE_END, and the THREAT_DIRECTION below.
"""

from typing import Tuple, List, Dict, Any, Optional
from worker.spatial.schemas import (
    CameraSpatialConfig,
    ZonePolygon,
    VirtualFence,
    ZoneType,
    MovementDirection,
)
from worker.spatial.world_schemas import (
    BorderSection,
    WorldPoint,
    CoordinateReference,
    TerrainMode,
    CameraRegistration,
    CameraCalibration,
    CalibrationModel,
    CalibrationStatus,
    CalibrationCorrespondence,
)

# ==============================================================================
# 🎯 EASY CONFIGURATION FOR YOUR RECORDED VIDEO
# ==============================================================================

# Expected video resolution
IMAGE_WIDTH = 1280
IMAGE_HEIGHT = 720

# Virtual Border (Fence) Line across camera view
# In 1280x720 video, person walks from upper area to lower area (or left to right)
BORDER_LINE_START: Tuple[float, float] = (150.0, 360.0)
BORDER_LINE_END: Tuple[float, float] = (1150.0, 360.0)

# Expected threat movement vector: (dx, dy)
# (0.0, 1.0) = Moving downward in frame (approaching the bottom / restricted area)
# (1.0, 0.0) = Moving left to right
EXPECTED_THREAT_VECTOR: Tuple[float, float] = (0.0, 1.0)

# Safe Zone Polygon (Upper region before buffer)
SAFE_ZONE_VERTICES: List[Tuple[float, float]] = [
    (50.0, 10.0),
    (1230.0, 10.0),
    (1230.0, 200.0),
    (50.0, 200.0),
]

# Warning Buffer Zone Polygon (Transition zone approaching border line)
WARNING_BUFFER_VERTICES: List[Tuple[float, float]] = [
    (50.0, 200.0),
    (1230.0, 200.0),
    (1230.0, 360.0),
    (50.0, 360.0),
]

# Restricted Zone Polygon (Violated area past the border line)
RESTRICTED_ZONE_VERTICES: List[Tuple[float, float]] = [
    (50.0, 360.0),
    (1230.0, 360.0),
    (1230.0, 710.0),
    (50.0, 710.0),
]


def build_camera_spatial_config(camera_id: str = "LIVE-01") -> CameraSpatialConfig:
    """Builds pixel-space zones and virtual fence for the demo camera."""
    return CameraSpatialConfig(
        camera_id=camera_id,
        zones=[
            ZonePolygon(
                id=f"{camera_id}_safe",
                name="Safe Perimeter",
                type=ZoneType.SAFE,
                polygon=SAFE_ZONE_VERTICES,
            ),
            ZonePolygon(
                id=f"{camera_id}_buffer",
                name="Warning Buffer (15m)",
                type=ZoneType.BUFFER,
                polygon=WARNING_BUFFER_VERTICES,
            ),
            ZonePolygon(
                id=f"{camera_id}_restricted",
                name="Restricted Zone",
                type=ZoneType.RESTRICTED,
                polygon=RESTRICTED_ZONE_VERTICES,
            ),
        ],
        fences=[
            VirtualFence(
                id=f"{camera_id}_border_fence",
                name="Virtual Border Line",
                start_point=BORDER_LINE_START,
                end_point=BORDER_LINE_END,
            ),
        ],
        expected_threat_vector=EXPECTED_THREAT_VECTOR,
    )


def build_world_border_components(
    camera_id: str = "LIVE-01",
    border_section_id: str = "SEC-ALPHA",
) -> Tuple[BorderSection, CameraRegistration, CameraCalibration]:
    """
    Builds calibrated Local-Cartesian plane homography and border section.
    Requires NO GPS / Satellite coordinates.
    """
    # World points on a local planar metric grid (metres)
    # Border placed at Y = 0; Warning buffer Y in [-10, 0]; Restricted Y > 0
    section = BorderSection(
        id=border_section_id,
        name="SIH Prototype Local Cartesian Border",
        coordinate_reference=CoordinateReference.LOCAL_CARTESIAN,
        points=[
            WorldPoint(x=-25.0, y=0.0),
            WorldPoint(x=0.0, y=0.0),
            WorldPoint(x=25.0, y=0.0),
        ],
        permitted_side_normal=(0.0, -1.0),
        warning_buffer_distance=6.0,
        terrain_mode=TerrainMode.PLANAR_GROUND,
    )

    # 4 image-to-world correspondences for planar homography
    # Maps top of buffer (Y=200px) to world Y=-6m; border (Y=360px) to Y=0m; restricted (Y=600px) to Y=+8m
    corr_tuples = [
        (-20.0, -6.0, 150.0, 200.0),
        (20.0, -6.0, 1130.0, 200.0),
        (20.0, 8.0, 1050.0, 600.0),
        (-20.0, 8.0, 230.0, 600.0),
    ]

    calibration = CameraCalibration(
        camera_id=camera_id,
        image_width=IMAGE_WIDTH,
        image_height=IMAGE_HEIGHT,
        calibration_version="sih_demo_v1.0",
        calibration_model=CalibrationModel.PLANAR_HOMOGRAPHY,
        correspondences=[
            CalibrationCorrespondence(world_point=WorldPoint(x=wx, y=wy), image_point=(ix, iy))
            for wx, wy, ix, iy in corr_tuples
        ],
    )

    registration = CameraRegistration(
        camera_id=camera_id,
        visible_border_sections=[border_section_id],
        calibration_status=CalibrationStatus.CALIBRATED,
    )

    return section, registration, calibration
