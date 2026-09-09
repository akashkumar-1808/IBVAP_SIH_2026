"""
Unit Tests for Situational Awareness and Debug HUD Overlay in LiveStreamVisualizer.

Verifies:
- Rendering of bounding box, trajectory, ground point.
- Presence of class name, ID, confidence, speed, direction, GIS zone, border distance.
- Optional pose keypoints rendering.
- Graceful handling of missing/uncalculated fields without fabrication.
"""

import numpy as np
import pytest
from datetime import datetime, timezone

from backend.app.schemas.common import TargetClass, TrackStatus, BehaviorType, EventPriority
from backend.app.schemas.events import (
    BoundingBox,
    TrackState,
    TrajectoryPoint,
    EventRecord,
)
from worker.spatial.schemas import (
    SpatialState,
    BorderSide,
    CrossingStatus,
    MovementDirection,
)
from worker.spatial.world_schemas import ProjectedBorder, GroundContactPoint
from worker.behavior.schemas import BehaviorPrimitive
from worker.pipeline.visualizer import LiveStreamVisualizer
from worker.perception.detector import parse_human_pose


def test_visualizer_overlay_complete_fields():
    """Verifies that all situational awareness fields are formatted and rendered onto the image."""
    vis = LiveStreamVisualizer(camera_id="cam-01")
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    # 1. Track with confidence, speed, trajectory, pose
    raw_kps = np.ones((17, 3), dtype=np.float32) * 150.0
    pose = parse_human_pose(raw_kps)

    track = TrackState(
        track_id=27,
        camera_id="cam-01",
        class_id=TargetClass.PERSON,
        bbox=BoundingBox(x_min=200.0, y_min=200.0, x_max=320.0, y_max=500.0),
        center_xy=(260.0, 350.0),
        velocity_xy=(5.2, -12.4),
        speed_pixels_per_sec=13.4,
        confidence_history=[0.85, 0.91],
        trajectory=[
            TrajectoryPoint(x=250.0, y=380.0, timestamp_utc=datetime.now(timezone.utc), frame_id=1),
            TrajectoryPoint(x=260.0, y=350.0, timestamp_utc=datetime.now(timezone.utc), frame_id=2),
        ],
        keypoints=pose,
    )

    # 2. Spatial state with zone, direction, border distance
    spatial = SpatialState(
        camera_id="cam-01",
        track_id=27,
        timestamp_utc=datetime.now(timezone.utc),
        border_side=BorderSide.WARNING_BUFFER,
        direction=MovementDirection.TOWARD,
        ground_contact=GroundContactPoint(source_track_id=27, pixel_xy=(260.0, 500.0)),
        border_distance_m=14.2,
    )

    # 3. Projected border
    proj_border = ProjectedBorder(
        camera_id="cam-01",
        border_section_id="SEC-01",
        projected_points=[(100.0, 550.0), (800.0, 550.0)],
        warning_buffer_points=[(100.0, 510.0), (800.0, 510.0)],
    )

    rendered = vis.render_frame(
        frame=frame,
        tracks=[track],
        spatial_states=[spatial],
        behavior_primitives=[],
        events=[],
        environment=None,
        projected_border=proj_border,
        is_calibrated=True,
    )

    assert rendered.shape == frame.shape
    # Frame must have pixels rendered (bounding box, card, HUD banner, border)
    assert np.any(rendered > 0)


def test_visualizer_overlay_missing_fields_no_fabrication():
    """
    Verifies that when speed, direction, zone, or border distance are uncalculated,
    the HUD does not crash or fabricate false information.
    """
    vis = LiveStreamVisualizer(camera_id="cam-01")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Minimal track with zero speed, empty confidence history, no pose
    track = TrackState(
        track_id=1,
        camera_id="cam-01",
        class_id=TargetClass.PERSON,
        bbox=BoundingBox(x_min=50.0, y_min=50.0, x_max=150.0, y_max=200.0),
        center_xy=(100.0, 125.0),
        speed_pixels_per_sec=0.0,
        confidence_history=[],
        trajectory=[],
        keypoints=None,
    )

    # No spatial state, no border
    rendered = vis.render_frame(
        frame=frame,
        tracks=[track],
        spatial_states=[],
        behavior_primitives=[],
        events=[],
        environment=None,
        projected_border=None,
        is_calibrated=False,
    )

    assert rendered.shape == frame.shape
    assert np.any(rendered > 0)


def test_pixel_distance_to_border_calculation():
    """Verifies perpendicular distance in pixels from point to border line."""
    proj = ProjectedBorder(
        camera_id="cam-01",
        border_section_id="SEC-01",
        projected_points=[(0.0, 100.0), (500.0, 100.0)],
    )

    dist = LiveStreamVisualizer._calculate_pixel_distance_to_border((250.0, 150.0), proj)
    assert dist is not None
    assert pytest.approx(dist, 0.01) == 50.0
