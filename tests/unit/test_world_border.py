"""
Unit tests for the IBVAP world-owned border model.

Covers: world border schema, camera registration, calibration validation,
planar homography, inverse transform, border projection, ground-contact point,
side determination, warning buffer, crossing candidate, crossing confirmation,
jitter resistance, camera isolation, multi-camera consistency, calibration
versioning, invalid calibration, TERRAIN_3D rejection, legacy fallback,
Phase 7 behavior compatibility.

Architecture Decision: DEC-0006
"""

import pytest
import math
import numpy as np
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from worker.spatial import (
    SpatialEngine,
    CameraSpatialConfig,
    ZonePolygon,
    VirtualFence,
    ZoneType,
    MovementDirection,
    SpatialTransitionType,
    SpatialState,
    # World-border types
    BorderSection,
    CameraRegistration,
    CameraCalibration,
    CalibrationCorrespondence,
    WorldPoint,
    CalibrationStatus,
    CalibrationModel,
    CoordinateReference,
    TerrainMode,
    BorderSide,
    CrossingStatus,
    SpatialConfidence,
    GroundReferenceMethod,
    ProjectedBorder,
    CrossingEvent,
    # Functions
    compute_homography,
    project_world_to_image,
    project_image_to_world,
    validate_calibration,
    project_border_to_camera,
    estimate_ground_contact,
    image_to_world_ground,
    determine_side,
    check_crossing,
    CrossingConfirmation,
    CalibrationError,
    TerrainModeNotImplementedError,
    # Legacy
    point_in_polygon,
    segments_intersect,
    calculate_movement_direction,
    draw_spatial_overlay,
    InvalidGeometryError,
    ConfigurationError,
)
from worker.tracking.schemas import TrackState, TrajectoryPoint, TargetClass, BoundingBox, TrackStatus


# ── Test Helpers ──────────────────────────────────────────────────────────────

def _make_track(
    track_id: int,
    positions: list,
    camera_id: str = "cam_01",
    base_time: datetime = None,
    class_id: TargetClass = TargetClass.PERSON,
) -> TrackState:
    t0 = base_time or datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    traj = [
        TrajectoryPoint(x=p[0], y=p[1], timestamp_utc=t0 + timedelta(milliseconds=i * 33), frame_id=i)
        for i, p in enumerate(positions)
    ]
    curr_pos = positions[-1]
    return TrackState(
        track_id=track_id,
        camera_id=camera_id,
        class_id=class_id,
        bbox=BoundingBox(x_min=curr_pos[0] - 15, y_min=curr_pos[1] - 40, x_max=curr_pos[0] + 15, y_max=curr_pos[1] + 10),
        center_xy=curr_pos,
        status=TrackStatus.TRACKED,
        first_seen=t0,
        last_seen=traj[-1].timestamp_utc,
        trajectory=traj,
    )


def _make_simple_calibration(camera_id: str, img_w: int = 640, img_h: int = 480, version: str = "1.0"):
    """Creates a simple calibration with 4 correspondences mapping a 100x100 world square to image."""
    return CameraCalibration(
        camera_id=camera_id,
        image_width=img_w,
        image_height=img_h,
        correspondences=[
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=0), image_point=(50, 430)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100, y=0), image_point=(590, 430)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100, y=100), image_point=(590, 50)),
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=100), image_point=(50, 50)),
        ],
        calibration_version=version,
    )


def _make_border_section():
    """Creates a border section along y=50 with permitted side toward +y."""
    return BorderSection(
        id="section_test",
        name="Test Border",
        points=[WorldPoint(x=0, y=50), WorldPoint(x=100, y=50)],
        permitted_side_normal=(0.0, 1.0),
        warning_buffer_distance=5.0,
    )


# ── 1. World Border Schema Validation ────────────────────────────────────────

def test_border_section_schema():
    section = _make_border_section()
    assert section.id == "section_test"
    assert len(section.points) == 2
    assert section.terrain_mode == TerrainMode.PLANAR_GROUND
    assert section.coordinate_reference == CoordinateReference.LOCAL_CARTESIAN
    assert section.warning_buffer_distance == 5.0


def test_world_point_optional_z():
    pt_2d = WorldPoint(x=10.0, y=20.0)
    assert pt_2d.z is None

    pt_3d = WorldPoint(x=10.0, y=20.0, z=5.0)
    assert pt_3d.z == 5.0


# ── 2. Camera Registration Schema ────────────────────────────────────────────

def test_camera_registration_schema():
    reg = CameraRegistration(
        camera_id="cam_test",
        visible_border_sections=["section_test"],
        calibration_status=CalibrationStatus.UNCALIBRATED,
    )
    assert reg.camera_id == "cam_test"
    assert reg.calibration_status == CalibrationStatus.UNCALIBRATED
    assert reg.height_meters is None


# ── 3. Calibration Validation ─────────────────────────────────────────────────

def test_calibration_validation_valid():
    cal = _make_simple_calibration("cam_val")
    status = validate_calibration(cal)
    assert status == CalibrationStatus.CALIBRATED


def test_calibration_validation_insufficient_points():
    # Only 3 points — should fail pydantic validation (min_length=4)
    with pytest.raises(ValidationError):
        CameraCalibration(
            camera_id="cam_bad",
            image_width=640,
            image_height=480,
            correspondences=[
                CalibrationCorrespondence(world_point=WorldPoint(x=0, y=0), image_point=(50, 430)),
                CalibrationCorrespondence(world_point=WorldPoint(x=100, y=0), image_point=(590, 430)),
                CalibrationCorrespondence(world_point=WorldPoint(x=100, y=100), image_point=(590, 50)),
            ],
        )

    # Test validate_calibration with enough points but collinear
    cal2 = CameraCalibration(
        camera_id="cam_collinear",
        image_width=640,
        image_height=480,
        correspondences=[
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=0), image_point=(0, 0)),
            CalibrationCorrespondence(world_point=WorldPoint(x=1, y=0), image_point=(1, 0)),
            CalibrationCorrespondence(world_point=WorldPoint(x=2, y=0), image_point=(2, 0)),
            CalibrationCorrespondence(world_point=WorldPoint(x=3, y=0), image_point=(3, 0)),
        ],
    )
    status = validate_calibration(cal2)
    assert status == CalibrationStatus.INVALID


def test_calibration_validation_invalid_dimensions():
    # image_width=0 should fail pydantic (gt=0)
    with pytest.raises(ValidationError):
        CameraCalibration(
            camera_id="cam_dim",
            image_width=0,
            image_height=480,
            correspondences=[
                CalibrationCorrespondence(world_point=WorldPoint(x=0, y=0), image_point=(50, 430)),
                CalibrationCorrespondence(world_point=WorldPoint(x=100, y=0), image_point=(590, 430)),
                CalibrationCorrespondence(world_point=WorldPoint(x=100, y=100), image_point=(590, 50)),
                CalibrationCorrespondence(world_point=WorldPoint(x=0, y=100), image_point=(50, 50)),
            ],
        )

    # Test with non-finite coordinate
    cal2 = CameraCalibration(
        camera_id="cam_inf",
        image_width=640,
        image_height=480,
        correspondences=[
            CalibrationCorrespondence(world_point=WorldPoint(x=float('inf'), y=0), image_point=(50, 430)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100, y=0), image_point=(590, 430)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100, y=100), image_point=(590, 50)),
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=100), image_point=(50, 50)),
        ],
    )
    status = validate_calibration(cal2)
    assert status == CalibrationStatus.INVALID


# ── 4. Planar Homography Computation ─────────────────────────────────────────

def test_homography_computation():
    cal = _make_simple_calibration("cam_homo")
    H, reproj = compute_homography(cal.correspondences)
    assert H.shape == (3, 3)
    assert reproj < 1.0  # Should be very low for exact correspondences
    assert np.all(np.isfinite(H))


def test_homography_requires_four_points():
    with pytest.raises(CalibrationError):
        compute_homography([
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=0), image_point=(0, 0)),
            CalibrationCorrespondence(world_point=WorldPoint(x=1, y=0), image_point=(1, 0)),
        ])


# ── 5. Inverse Transform ─────────────────────────────────────────────────────

def test_inverse_transform_roundtrip():
    cal = _make_simple_calibration("cam_inv")
    H, _ = compute_homography(cal.correspondences)
    H_inv = np.linalg.inv(H)

    # Project world point to image, then back to world
    wp = WorldPoint(x=50, y=50)
    ix, iy = project_world_to_image(wp, H)
    wp_back = project_image_to_world((ix, iy), H_inv)

    assert abs(wp_back.x - 50.0) < 1.0
    assert abs(wp_back.y - 50.0) < 1.0


# ── 6. Border Projection (World → Image) ─────────────────────────────────────

def test_border_projection():
    section = _make_border_section()
    cal = _make_simple_calibration("cam_proj")
    proj = project_border_to_camera(section, cal)

    assert proj.camera_id == "cam_proj"
    assert proj.border_section_id == "section_test"
    assert len(proj.projected_points) == 2
    assert proj.validity in (SpatialConfidence.VALID, SpatialConfidence.LOW_CONFIDENCE)
    assert proj.calibration_version == "1.0"


def test_border_projection_with_warning_buffer():
    section = _make_border_section()
    cal = _make_simple_calibration("cam_buf")
    proj = project_border_to_camera(section, cal)

    assert proj.warning_buffer_points is not None
    assert len(proj.warning_buffer_points) == 2


# ── 7. Ground-Contact Point ──────────────────────────────────────────────────

def test_ground_contact_person_bottom_center():
    track = _make_track(1, [(100.0, 200.0)], class_id=TargetClass.PERSON)
    gc = estimate_ground_contact(track)

    assert gc.method == GroundReferenceMethod.BOTTOM_CENTER
    assert gc.pixel_xy[0] == 100.0  # center x
    assert gc.pixel_xy[1] == 210.0  # y_max (bottom of bbox)
    assert gc.confidence == SpatialConfidence.VALID


def test_ground_contact_unknown_uses_center():
    track = _make_track(2, [(100.0, 200.0)], class_id=TargetClass.UNKNOWN)
    gc = estimate_ground_contact(track)

    assert gc.method == GroundReferenceMethod.CENTER
    # Center of bbox
    assert gc.pixel_xy[1] == pytest.approx((200.0 - 40 + 200.0 + 10) / 2.0, abs=1.0)


# ── 8. Side Determination ────────────────────────────────────────────────────

def test_side_permitted():
    section = _make_border_section()
    side = determine_side((50.0, 70.0), section)  # y=70, border at y=50, normal +y
    assert side == BorderSide.PERMITTED


def test_side_restricted():
    section = _make_border_section()
    side = determine_side((50.0, 30.0), section)  # y=30, border at y=50, normal +y → restricted
    assert side == BorderSide.RESTRICTED


def test_side_border_line():
    section = _make_border_section()
    side = determine_side((50.0, 50.0), section)  # On the border
    assert side == BorderSide.BORDER_LINE


# ── 9. Warning Buffer ────────────────────────────────────────────────────────

def test_warning_buffer():
    section = _make_border_section()  # buffer=5.0, border at y=50, normal +y
    # Point at y=53 → within 5m buffer on permitted side
    side = determine_side((50.0, 53.0), section)
    assert side == BorderSide.WARNING_BUFFER


def test_outside_warning_buffer():
    section = _make_border_section()
    # Point at y=60 → 10m into permitted side, beyond 5m buffer
    side = determine_side((50.0, 60.0), section)
    assert side == BorderSide.PERMITTED


# ── 10. Crossing Candidate Detection ─────────────────────────────────────────

def test_crossing_candidate_permitted_to_restricted():
    status = check_crossing(BorderSide.PERMITTED, BorderSide.RESTRICTED)
    assert status == CrossingStatus.CROSSING_CANDIDATE


def test_crossing_candidate_restricted_to_permitted():
    status = check_crossing(BorderSide.RESTRICTED, BorderSide.PERMITTED)
    assert status == CrossingStatus.CROSSING_CANDIDATE


def test_no_crossing_same_side():
    status = check_crossing(BorderSide.PERMITTED, BorderSide.PERMITTED)
    assert status == CrossingStatus.NONE


def test_no_crossing_unknown():
    status = check_crossing(BorderSide.UNKNOWN, BorderSide.RESTRICTED)
    assert status == CrossingStatus.NONE


# ── 11. Crossing Confirmation (Sustained Frames) ─────────────────────────────

def test_crossing_confirmation_sustained():
    cc = CrossingConfirmation(confirmation_frames=3)
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    # Frame 0: Permitted
    ev = cc.update(1, "sec_a", BorderSide.PERMITTED, "cam_01", t0)
    assert ev is None

    # Frame 1: Cross to restricted (candidate frame 1)
    ev = cc.update(1, "sec_a", BorderSide.RESTRICTED, "cam_01", t0 + timedelta(milliseconds=33))
    assert ev is None

    # Frame 2: Still restricted (candidate frame 2)
    ev = cc.update(1, "sec_a", BorderSide.RESTRICTED, "cam_01", t0 + timedelta(milliseconds=66))
    assert ev is None

    # Frame 3: Still restricted (candidate frame 3 → CONFIRMED)
    ev = cc.update(1, "sec_a", BorderSide.RESTRICTED, "cam_01", t0 + timedelta(milliseconds=99))
    assert ev is not None
    assert ev.crossing_status == CrossingStatus.CONFIRMED_CROSSING
    assert ev.previous_side == BorderSide.PERMITTED
    assert ev.current_side == BorderSide.RESTRICTED


# ── 12. Jitter/Noise Resistance ──────────────────────────────────────────────

def test_jitter_no_false_crossing():
    cc = CrossingConfirmation(confirmation_frames=3)
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    cc.update(1, "sec_a", BorderSide.PERMITTED, "cam_01", t0)

    # Frame 1: Jitter to restricted
    ev = cc.update(1, "sec_a", BorderSide.RESTRICTED, "cam_01", t0 + timedelta(milliseconds=33))
    assert ev is None

    # Frame 2: Jitter back to permitted → cancels candidate
    ev = cc.update(1, "sec_a", BorderSide.PERMITTED, "cam_01", t0 + timedelta(milliseconds=66))
    assert ev is None

    # Frame 3: Jitter to restricted again (new candidate, count=1)
    ev = cc.update(1, "sec_a", BorderSide.RESTRICTED, "cam_01", t0 + timedelta(milliseconds=99))
    assert ev is None

    # Frame 4: Back to permitted → no confirmed crossing
    ev = cc.update(1, "sec_a", BorderSide.PERMITTED, "cam_01", t0 + timedelta(milliseconds=132))
    assert ev is None


def test_object_touches_border_but_returns():
    """Object enters border line but returns — no confirmed crossing."""
    cc = CrossingConfirmation(confirmation_frames=3)
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    cc.update(1, "sec_a", BorderSide.PERMITTED, "cam_01", t0)
    cc.update(1, "sec_a", BorderSide.BORDER_LINE, "cam_01", t0 + timedelta(milliseconds=33))
    cc.update(1, "sec_a", BorderSide.BORDER_LINE, "cam_01", t0 + timedelta(milliseconds=66))
    ev = cc.update(1, "sec_a", BorderSide.PERMITTED, "cam_01", t0 + timedelta(milliseconds=99))
    assert ev is None  # Returned without fully crossing


# ── 13. Camera Isolation ──────────────────────────────────────────────────────

def test_engine_camera_isolation():
    """Same border, different cameras, independent spatial states."""
    engine = SpatialEngine()
    section = _make_border_section()
    engine.register_border_section(section)

    # Camera A
    cal_a = _make_simple_calibration("cam_A")
    engine.register_camera(CameraRegistration(
        camera_id="cam_A", visible_border_sections=["section_test"],
    ))
    engine.register_calibration(cal_a)

    # Camera B — different image coordinates but same world border
    cal_b = CameraCalibration(
        camera_id="cam_B",
        image_width=1280,
        image_height=720,
        correspondences=[
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=0), image_point=(100, 650)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100, y=0), image_point=(1180, 650)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100, y=100), image_point=(1180, 70)),
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=100), image_point=(100, 70)),
        ],
        calibration_version="1.0",
    )
    engine.register_camera(CameraRegistration(
        camera_id="cam_B", visible_border_sections=["section_test"],
    ))
    engine.register_calibration(cal_b)

    # Project border — should produce DIFFERENT image projections
    proj_a = engine.project_border("cam_A", "section_test")
    proj_b = engine.project_border("cam_B", "section_test")

    assert proj_a is not None
    assert proj_b is not None
    # Different cameras → different projected pixel coordinates
    assert proj_a.projected_points != proj_b.projected_points


# ── 14. Same Border, Different Camera Projections ─────────────────────────────

def test_same_border_different_projections():
    """Verifies the same world border produces visually different projections in different cameras."""
    section = _make_border_section()

    cal1 = _make_simple_calibration("cam_diag", img_w=800, img_h=600)
    cal2 = CameraCalibration(
        camera_id="cam_horiz",
        image_width=800,
        image_height=600,
        correspondences=[
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=0), image_point=(100, 500)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100, y=0), image_point=(700, 500)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100, y=100), image_point=(700, 100)),
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=100), image_point=(100, 100)),
        ],
        calibration_version="1.0",
    )

    proj1 = project_border_to_camera(section, cal1)
    proj2 = project_border_to_camera(section, cal2)

    # Both project the same world section but pixels differ
    assert proj1.projected_points[0] != proj2.projected_points[0]
    assert proj1.projected_points[1] != proj2.projected_points[1]


# ── 15. Calibration Versioning ────────────────────────────────────────────────

def test_calibration_versioning():
    engine = SpatialEngine()
    section = _make_border_section()
    engine.register_border_section(section)

    engine.register_camera(CameraRegistration(
        camera_id="cam_ver", visible_border_sections=["section_test"],
    ))

    # Version 1
    cal_v1 = _make_simple_calibration("cam_ver", version="1.0")
    engine.register_calibration(cal_v1)
    proj_v1 = engine.project_border("cam_ver", "section_test")
    assert proj_v1.calibration_version == "1.0"

    # Version 2 — different correspondences
    cal_v2 = CameraCalibration(
        camera_id="cam_ver",
        image_width=640,
        image_height=480,
        correspondences=[
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=0), image_point=(60, 420)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100, y=0), image_point=(580, 420)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100, y=100), image_point=(580, 60)),
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=100), image_point=(60, 60)),
        ],
        calibration_version="2.0",
    )
    engine.register_calibration(cal_v2)
    proj_v2 = engine.project_border("cam_ver", "section_test")
    assert proj_v2.calibration_version == "2.0"
    # Different calibration → different projection
    assert proj_v1.projected_points != proj_v2.projected_points


# ── 16. Invalid Calibration Rejection ─────────────────────────────────────────

def test_invalid_calibration_does_not_project():
    engine = SpatialEngine()
    section = _make_border_section()
    engine.register_border_section(section)

    engine.register_camera(CameraRegistration(
        camera_id="cam_bad", visible_border_sections=["section_test"],
    ))

    # Collinear points → invalid
    cal_bad = CameraCalibration(
        camera_id="cam_bad",
        image_width=640,
        image_height=480,
        correspondences=[
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=0), image_point=(0, 0)),
            CalibrationCorrespondence(world_point=WorldPoint(x=1, y=0), image_point=(1, 0)),
            CalibrationCorrespondence(world_point=WorldPoint(x=2, y=0), image_point=(2, 0)),
            CalibrationCorrespondence(world_point=WorldPoint(x=3, y=0), image_point=(3, 0)),
        ],
    )
    engine.register_calibration(cal_bad)

    proj = engine.project_border("cam_bad", "section_test")
    assert proj is None  # Cannot project with invalid calibration


# ── 17. TERRAIN_3D Raises NotImplementedError ─────────────────────────────────

def test_terrain_3d_not_implemented():
    with pytest.raises(TerrainModeNotImplementedError):
        engine = SpatialEngine()
        engine.register_border_section(BorderSection(
            id="sec_3d",
            name="3D Section",
            points=[WorldPoint(x=0, y=0), WorldPoint(x=100, y=0)],
            permitted_side_normal=(0.0, 1.0),
            terrain_mode=TerrainMode.TERRAIN_3D,
        ))


# ── 18. Legacy Image-Space Fallback ──────────────────────────────────────────

def test_legacy_fallback_uncalibrated():
    """Uncalibrated camera uses legacy image-space zones/fences."""
    engine = SpatialEngine()
    config = CameraSpatialConfig(
        camera_id="cam_legacy",
        zones=[
            ZonePolygon(id="z_legacy", name="Legacy Zone", type=ZoneType.RESTRICTED,
                       polygon=[(200, 0), (400, 0), (400, 400), (200, 400)]),
        ],
    )
    engine.configure_camera(config)
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track = _make_track(1, [(250.0, 100.0)], camera_id="cam_legacy")
    states = engine.process_tracks([track], "cam_legacy", t0)

    assert len(states) == 1
    assert states[0].current_zone_id == "z_legacy"
    assert states[0].current_zone_type == ZoneType.RESTRICTED
    assert states[0].border_side is None  # No world-border data


# ── 19. Phase 7 Behavior Compatibility ────────────────────────────────────────

def test_spatial_state_backward_compatible():
    """SpatialState must have all original fields with correct defaults."""
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    state = SpatialState(
        camera_id="cam_compat",
        track_id=1,
        timestamp_utc=t0,
    )
    # Original Phase 6 fields must exist with defaults
    assert state.current_zone_id is None
    assert state.current_zone_type is None
    assert state.previous_zone_id is None
    assert state.transition == SpatialTransitionType.NONE
    assert state.direction == MovementDirection.UNCERTAIN
    assert state.fences_crossed == []
    assert state.crossing_events == []
    assert state.metadata == {}
    # New optional fields must exist with safe defaults
    assert state.border_side is None
    assert state.crossing_status == CrossingStatus.NONE
    assert state.ground_contact is None
    assert state.calibration_version is None
    assert state.spatial_confidence == SpatialConfidence.VALID


# ── 20. Full Regression of Legacy Spatial Tests ───────────────────────────────

def test_legacy_zone_transition():
    """Regression: ensure Phase 6 zone transition logic still works."""
    engine = SpatialEngine()
    config = CameraSpatialConfig(
        camera_id="cam_reg_test",
        zones=[
            ZonePolygon(id="z_r", name="Restricted", type=ZoneType.RESTRICTED,
                       polygon=[(200, 0), (400, 0), (400, 400), (200, 400)]),
        ],
    )
    engine.configure_camera(config)
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    # Outside
    tr0 = _make_track(1, [(100.0, 100.0)], camera_id="cam_reg_test")
    st0 = engine.process_tracks([tr0], "cam_reg_test", t0)[0]
    assert st0.current_zone_id is None

    # Enter restricted
    t1 = t0 + timedelta(milliseconds=33)
    tr1 = _make_track(1, [(100.0, 100.0), (250.0, 100.0)], camera_id="cam_reg_test")
    st1 = engine.process_tracks([tr1], "cam_reg_test", t1)[0]
    assert st1.current_zone_id == "z_r"
    assert st1.transition == SpatialTransitionType.ZONE_ENTERED


def test_legacy_virtual_fence_crossing():
    """Regression: ensure Phase 6 fence crossing still works."""
    engine = SpatialEngine()
    config = CameraSpatialConfig(
        camera_id="cam_fence_reg",
        fences=[
            VirtualFence(id="f_reg", name="Fence", start_point=(200.0, 0.0), end_point=(200.0, 400.0)),
        ],
        expected_threat_vector=(1.0, 0.0),
    )
    engine.configure_camera(config)
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    track = _make_track(1, [(150.0, 100.0), (250.0, 100.0)], camera_id="cam_fence_reg")
    states = engine.process_tracks([track], "cam_fence_reg", t0)
    assert len(states) == 1
    assert "f_reg" in states[0].fences_crossed


# ── 21. Multi-Camera Consistency ──────────────────────────────────────────────

def test_multi_camera_consistent_side():
    """Same world point should produce same semantic side in different cameras."""
    section = _make_border_section()

    # Camera A calibration
    cal_a = _make_simple_calibration("cam_mc_a")
    H_a, _ = compute_homography(cal_a.correspondences)
    H_a_inv = np.linalg.inv(H_a)

    # Camera B calibration (different pixel mapping)
    cal_b = CameraCalibration(
        camera_id="cam_mc_b",
        image_width=1280,
        image_height=720,
        correspondences=[
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=0), image_point=(100, 650)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100, y=0), image_point=(1180, 650)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100, y=100), image_point=(1180, 70)),
            CalibrationCorrespondence(world_point=WorldPoint(x=0, y=100), image_point=(100, 70)),
        ],
        calibration_version="1.0",
    )
    H_b, _ = compute_homography(cal_b.correspondences)
    H_b_inv = np.linalg.inv(H_b)

    # World point on permitted side (y=70, border at y=50, normal +y)
    world_point = (50.0, 70.0)

    # Project to camera A image, then ground-contact back to world
    px_a = project_world_to_image(WorldPoint(x=50, y=70), H_a)
    wp_a = project_image_to_world(px_a, H_a_inv)
    side_a = determine_side((wp_a.x, wp_a.y), section)

    px_b = project_world_to_image(WorldPoint(x=50, y=70), H_b)
    wp_b = project_image_to_world(px_b, H_b_inv)
    side_b = determine_side((wp_b.x, wp_b.y), section)

    # Both cameras should agree on PERMITTED side
    assert side_a == BorderSide.PERMITTED
    assert side_b == BorderSide.PERMITTED

    # Different pixel coordinates in each camera
    assert abs(px_a[0] - px_b[0]) > 10 or abs(px_a[1] - px_b[1]) > 10


# ── 22. Visualizer with World Border ──────────────────────────────────────────

def test_visualizer_with_projected_border():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    config = CameraSpatialConfig(camera_id="cam_vis")
    proj = ProjectedBorder(
        camera_id="cam_vis",
        border_section_id="sec_vis",
        projected_points=[(100, 240), (540, 240)],
        warning_buffer_points=[(100, 220), (540, 220)],
        validity=SpatialConfidence.VALID,
        calibration_version="1.0",
    )
    annotated = draw_spatial_overlay(img, config, projected_borders=[proj])
    assert annotated.shape == img.shape
    assert np.max(annotated) > 0
    assert np.max(img) == 0


# ── 23. End-to-End World-Border Engine Pipeline ──────────────────────────────

def test_engine_world_border_pipeline():
    """Full pipeline: register border → calibrate camera → process tracks → check side/crossing."""
    engine = SpatialEngine(crossing_confirmation_frames=2)

    # Register border
    section = _make_border_section()
    engine.register_border_section(section)

    # Register and calibrate camera
    engine.register_camera(CameraRegistration(
        camera_id="cam_e2e", visible_border_sections=["section_test"],
    ))
    cal = _make_simple_calibration("cam_e2e")
    engine.register_calibration(cal)

    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    # Track on permitted side (world y > 50, should map to upper part of image)
    # In our calibration, world (50, 70) maps to image space
    H = engine._homography_matrices["cam_e2e"]
    px, py = project_world_to_image(WorldPoint(x=50, y=70), H)
    track_permitted = _make_track(1, [(px, py)], camera_id="cam_e2e")
    states = engine.process_tracks([track_permitted], "cam_e2e", t0)

    assert len(states) == 1
    assert states[0].border_side == BorderSide.PERMITTED
    assert states[0].ground_contact is not None
    assert states[0].calibration_version == "1.0"
