import pytest
from datetime import datetime, timezone, timedelta
import numpy as np

from worker.spatial import (
    SpatialEngine,
    CameraSpatialConfig,
    ZonePolygon,
    VirtualFence,
    ZoneType,
    MovementDirection,
    SpatialTransitionType,
    draw_spatial_overlay,
    point_in_polygon,
    segments_intersect,
    calculate_movement_direction,
    InvalidGeometryError,
    ConfigurationError,
)
from worker.tracking.schemas import TrackState, TrajectoryPoint, TargetClass, BoundingBox, TrackStatus


def _make_track(
    track_id: int,
    positions: list,  # [(x, y), ...]
    camera_id: str = "cam_01",
    base_time: datetime = None,
) -> TrackState:
    t0 = base_time or datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    traj = [
        TrajectoryPoint(x=p[0], y=p[1], timestamp_utc=t0 + timedelta(milliseconds=i * 33), frame_id=i)
        for i, p in enumerate(positions)
    ]
    curr_pos = positions[-1]
    return TrackState(
        track_id=track_id,
        camera_id=camera_id,
        class_id=TargetClass.PERSON,
        bbox=BoundingBox(x_min=curr_pos[0] - 10, y_min=curr_pos[1] - 20, x_max=curr_pos[0] + 10, y_max=curr_pos[1] + 20),
        center_xy=curr_pos,
        status=TrackStatus.TRACKED,
        first_seen=t0,
        last_seen=traj[-1].timestamp_utc,
        trajectory=traj,
    )


def test_geometry_point_in_polygon():
    square = [(100.0, 100.0), (200.0, 100.0), (200.0, 200.0), (100.0, 200.0)]

    # Strictly inside
    assert point_in_polygon((150.0, 150.0), square) is True
    # Strictly outside
    assert point_in_polygon((50.0, 50.0), square) is False
    assert point_in_polygon((250.0, 150.0), square) is False
    # Boundary vertex and edge inclusion
    assert point_in_polygon((100.0, 100.0), square) is True
    assert point_in_polygon((150.0, 100.0), square) is True


def test_geometry_segments_intersect():
    # Perpendicular crossing
    p1 = (100.0, 150.0)
    p2 = (300.0, 150.0)
    q1 = (200.0, 50.0)
    q2 = (200.0, 250.0)

    crossed, pt = segments_intersect(p1, p2, q1, q2)
    assert crossed is True
    assert pt is not None
    assert abs(pt[0] - 200.0) < 1e-3
    assert abs(pt[1] - 150.0) < 1e-3

    # Parallel non-intersecting (both vertical at x=100 and x=200)
    p_par1 = (100.0, 50.0)
    p_par2 = (100.0, 250.0)
    crossed2, _ = segments_intersect(p_par1, p_par2, q1, q2)
    assert crossed2 is False

    # Disjoint non-intersecting (horizontal at y=100 from x=50 to x=150, does not reach vertical fence at x=200)
    p_dis1 = (50.0, 100.0)
    p_dis2 = (150.0, 100.0)
    crossed3, _ = segments_intersect(p_dis1, p_dis2, q1, q2)
    assert crossed3 is False

    # Touching without crossing (negative test)
    touch_p1 = (100.0, 100.0)
    touch_p2 = (200.0, 150.0)
    crossed_touch, _ = segments_intersect(touch_p1, touch_p2, q1, q2)
    assert crossed_touch is False


def test_movement_direction_calculation():
    threat_vec = (1.0, 0.0)  # Toward the right

    # Moving right (+50px) -> TOWARD
    d_toward = calculate_movement_direction((100.0, 100.0), (150.0, 100.0), threat_vec)
    assert d_toward == MovementDirection.TOWARD

    # Moving left (-50px) -> AWAY
    d_away = calculate_movement_direction((150.0, 100.0), (100.0, 100.0), threat_vec)
    assert d_away == MovementDirection.AWAY

    # Moving vertically (+50px Y) -> PARALLEL
    d_parallel = calculate_movement_direction((100.0, 100.0), (100.0, 150.0), threat_vec)
    assert d_parallel == MovementDirection.PARALLEL

    # Insufficient motion (1px) -> UNCERTAIN
    d_uncertain = calculate_movement_direction((100.0, 100.0), (101.0, 100.0), threat_vec, min_movement_dist=3.0)
    assert d_uncertain == MovementDirection.UNCERTAIN


def test_spatial_engine_zone_transition():
    engine = SpatialEngine()
    config = CameraSpatialConfig(
        camera_id="cam_zone_test",
        zones=[
            ZonePolygon(id="z_restricted", name="Restricted Zone", type=ZoneType.RESTRICTED, polygon=[(200, 0), (400, 0), (400, 400), (200, 400)]),
        ],
    )
    engine.configure_camera(config)
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Frame 0: Outside restricted zone (x=100) -> None
    tr0 = _make_track(1, [(100.0, 100.0)], camera_id="cam_zone_test", base_time=t0)
    st0 = engine.process_tracks([tr0], "cam_zone_test", t0)[0]
    assert st0.current_zone_id is None
    assert st0.transition == SpatialTransitionType.NONE

    # Frame 1: Moves inside restricted zone (x=250) -> ZONE_ENTERED
    t1 = t0 + timedelta(milliseconds=33)
    tr1 = _make_track(1, [(100.0, 100.0), (250.0, 100.0)], camera_id="cam_zone_test", base_time=t0)
    st1 = engine.process_tracks([tr1], "cam_zone_test", t1)[0]
    assert st1.current_zone_id == "z_restricted"
    assert st1.transition == SpatialTransitionType.ZONE_ENTERED

    # Frame 2: Remains inside (x=260) -> Transition NONE
    t2 = t0 + timedelta(milliseconds=66)
    tr2 = _make_track(1, [(100.0, 100.0), (250.0, 100.0), (260.0, 100.0)], camera_id="cam_zone_test", base_time=t0)
    st2 = engine.process_tracks([tr2], "cam_zone_test", t2)[0]
    assert st2.current_zone_id == "z_restricted"
    assert st2.transition == SpatialTransitionType.NONE

    # Frame 3: Exits restricted zone (x=450) -> ZONE_EXITED
    t3 = t0 + timedelta(milliseconds=99)
    tr3 = _make_track(1, [(250.0, 100.0), (260.0, 100.0), (450.0, 100.0)], camera_id="cam_zone_test", base_time=t0)
    st3 = engine.process_tracks([tr3], "cam_zone_test", t3)[0]
    assert st3.current_zone_id is None
    assert st3.transition == SpatialTransitionType.ZONE_EXITED


def test_spatial_engine_virtual_fence_crossing():
    engine = SpatialEngine()
    config = CameraSpatialConfig(
        camera_id="cam_fence_test",
        fences=[
            VirtualFence(id="fence_alpha", name="Boundary Fence Alpha", start_point=(200.0, 0.0), end_point=(200.0, 400.0)),
        ],
        expected_threat_vector=(1.0, 0.0),
    )
    engine.configure_camera(config)
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Track crosses from x=150 to x=250 across x=200 vertical fence
    tr = _make_track(1, [(150.0, 100.0), (250.0, 100.0)], camera_id="cam_fence_test", base_time=t0)
    states = engine.process_tracks([tr], "cam_fence_test", t0)

    assert len(states) == 1
    st = states[0]
    assert "fence_alpha" in st.fences_crossed
    assert len(st.crossing_events) == 1
    ev = st.crossing_events[0]
    assert ev.fence_id == "fence_alpha"
    assert ev.crossing_direction == MovementDirection.TOWARD
    assert ev.crossing_point is not None


def test_spatial_engine_overlapping_zone_precedence():
    engine = SpatialEngine()
    config = CameraSpatialConfig(
        camera_id="cam_prec_test",
        zones=[
            ZonePolygon(id="z_safe", name="Safe Area", type=ZoneType.SAFE, polygon=[(0, 0), (500, 0), (500, 500), (0, 500)]),
            ZonePolygon(id="z_critical", name="Critical Target", type=ZoneType.CRITICAL, polygon=[(200, 200), (300, 200), (300, 300), (200, 300)]),
        ],
    )
    engine.configure_camera(config)
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Point at (250, 250) is inside BOTH z_safe and z_critical -> CRITICAL wins due to precedence
    tr = _make_track(1, [(250.0, 250.0)], camera_id="cam_prec_test", base_time=t0)
    st = engine.process_tracks([tr], "cam_prec_test", t0)[0]
    assert st.current_zone_id == "z_critical"
    assert st.current_zone_type == ZoneType.CRITICAL


def test_camera_isolation():
    engine = SpatialEngine()
    config_a = CameraSpatialConfig(
        camera_id="cam_A",
        zones=[ZonePolygon(id="zone_A", name="Zone A", type=ZoneType.CRITICAL, polygon=[(0, 0), (200, 0), (200, 200), (0, 200)])],
    )
    config_b = CameraSpatialConfig(
        camera_id="cam_B",
        zones=[ZonePolygon(id="zone_B", name="Zone B", type=ZoneType.SAFE, polygon=[(0, 0), (200, 0), (200, 200), (0, 200)])],
    )
    engine.configure_camera(config_a)
    engine.configure_camera(config_b)
    t0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    tr_a = _make_track(1, [(50.0, 50.0)], camera_id="cam_A", base_time=t0)
    tr_b = _make_track(1, [(50.0, 50.0)], camera_id="cam_B", base_time=t0)

    st_a = engine.process_tracks([tr_a], "cam_A", t0)[0]
    st_b = engine.process_tracks([tr_b], "cam_B", t0)[0]

    assert st_a.current_zone_id == "zone_A"
    assert st_a.current_zone_type == ZoneType.CRITICAL
    assert st_b.current_zone_id == "zone_B"
    assert st_b.current_zone_type == ZoneType.SAFE


def test_visualizer_spatial_overlay():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    config = CameraSpatialConfig(
        camera_id="cam_vis_test",
        zones=[ZonePolygon(id="z_crit", name="Critical", type=ZoneType.CRITICAL, polygon=[(50, 50), (250, 50), (250, 250), (50, 250)])],
        fences=[VirtualFence(id="f_vis", name="Fence Vis", start_point=(100, 400), end_point=(500, 400))],
    )
    annotated = draw_spatial_overlay(img, config)
    assert annotated.shape == img.shape
    assert np.max(annotated) > 0
    assert np.max(img) == 0
