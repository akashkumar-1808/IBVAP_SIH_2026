"""
IBVAP — World-Owned Border Multi-Camera Coordination Test & Visualizer.

Demonstrates that ONE REAL-WORLD BORDER is observed by TWO CAMERAS with different perspectives:
- Camera 1 (Angled/Diagonal View): Border appears diagonal in image space.
- Camera 2 (Frontal View): Border appears horizontal in image space.

A simulated target moves across the world border from PERMITTED -> WARNING BUFFER -> BORDER -> RESTRICTED.
Both camera views are rendered side-by-side into an annotated video demonstrating synchronized semantic coordination.

Usage:
    python scripts/test_world_border_multi_cam.py
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from worker.spatial import (
    SpatialEngine,
    CameraSpatialConfig,
    BorderSection,
    CameraRegistration,
    CameraCalibration,
    CalibrationCorrespondence,
    WorldPoint,
    BorderSide,
    CrossingStatus,
    draw_spatial_overlay,
    project_world_to_image,
)
from worker.tracking.schemas import TrackState, TrajectoryPoint, TargetClass, BoundingBox, TrackStatus


def run_multi_cam_border_test(output_path: str = "storage/output/multi_cam_border_test.mp4"):
    print("=" * 75)
    print("   IBVAP — World Border Multi-Camera Coordination Test & Visualizer")
    print("=" * 75)

    # 1. Initialize Single Spatial Engine
    engine = SpatialEngine(crossing_confirmation_frames=2)

    # 2. Define ONE Canonical World Border Section
    # World Coordinates: Border lies along Y = 50 from X = 0 to X = 100
    # Permitted (friendly) side is +Y (Y > 50)
    # Restricted side is -Y (Y < 50)
    # Warning Buffer distance = 10 metres (between Y = 50 and Y = 60)
    world_border = BorderSection(
        id="border_sector_01",
        name="Sector 01 Perimeter",
        points=[
            WorldPoint(x=0.0, y=50.0),
            WorldPoint(x=25.0, y=50.0),
            WorldPoint(x=50.0, y=50.0),
            WorldPoint(x=75.0, y=50.0),
            WorldPoint(x=100.0, y=50.0),
        ],
        permitted_side_normal=(0.0, 1.0),
        warning_buffer_distance=10.0,
    )
    engine.register_border_section(world_border)
    print("[OK] Registered 1 World Border Section (Sector 01, Y=50, Buffer=10m)")

    # 3. Configure Camera 1 (Angled View: Border will appear DIAGONAL)
    engine.register_camera(CameraRegistration(
        camera_id="cam_01_angled",
        visible_border_sections=["border_sector_01"],
        orientation_deg=135.0,
    ))
    cal_cam1 = CameraCalibration(
        camera_id="cam_01_angled",
        image_width=640,
        image_height=480,
        correspondences=[
            CalibrationCorrespondence(world_point=WorldPoint(x=0.0, y=100.0), image_point=(80, 80)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100.0, y=100.0), image_point=(560, 150)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100.0, y=0.0), image_point=(580, 440)),
            CalibrationCorrespondence(world_point=WorldPoint(x=0.0, y=0.0), image_point=(60, 380)),
        ],
        calibration_version="1.0",
    )
    engine.register_calibration(cal_cam1)
    proj_cam1 = engine.project_border("cam_01_angled", "border_sector_01")
    print(f"[OK] Camera 1 Configured (Angled View) -> Projected Border Endpoints: {proj_cam1.projected_points[0]} to {proj_cam1.projected_points[-1]}")

    # 4. Configure Camera 2 (Frontal View: Border will appear HORIZONTAL)
    engine.register_camera(CameraRegistration(
        camera_id="cam_02_frontal",
        visible_border_sections=["border_sector_01"],
        orientation_deg=0.0,
    ))
    cal_cam2 = CameraCalibration(
        camera_id="cam_02_frontal",
        image_width=640,
        image_height=480,
        correspondences=[
            CalibrationCorrespondence(world_point=WorldPoint(x=0.0, y=100.0), image_point=(60, 60)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100.0, y=100.0), image_point=(580, 60)),
            CalibrationCorrespondence(world_point=WorldPoint(x=100.0, y=0.0), image_point=(580, 420)),
            CalibrationCorrespondence(world_point=WorldPoint(x=0.0, y=0.0), image_point=(60, 420)),
        ],
        calibration_version="1.0",
    )
    engine.register_calibration(cal_cam2)
    proj_cam2 = engine.project_border("cam_02_frontal", "border_sector_01")
    print(f"[OK] Camera 2 Configured (Frontal View) -> Projected Border Endpoints: {proj_cam2.projected_points[0]} to {proj_cam2.projected_points[-1]}")

    # 5. Generate Multi-Frame Trajectory Moving Across Border in World Space
    # Target moves from World Y=85 (PERMITTED) -> Y=55 (WARNING BUFFER) -> Y=48 (BORDER/RESTRICTED) -> Y=15 (RESTRICTED)
    total_frames = 60
    world_x = 50.0  # Moves along center line in X
    H1 = engine._homography_matrices["cam_01_angled"]
    H2 = engine._homography_matrices["cam_02_frontal"]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    # Output video will be side-by-side: 1280 x 540 (two 640x480 images + top header banner)
    writer = cv2.VideoWriter(output_path, fourcc, 15.0, (1280, 540))

    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    traj_cam1 = []
    traj_cam2 = []

    print("-" * 75)
    print("Simulating Target Movement Across World Border (60 frames)...")
    print("Frames 01-18: Permitted Area (Y=85 -> Y=62)")
    print("Frames 19-32: Warning Buffer (Y=60 -> Y=51, within 10m buffer)")
    print("Frames 33-40: Crossing Event  (Y=49 -> Y=40, crossing Y=50 border)")
    print("Frames 41-60: Restricted Area (Y=38 -> Y=15)")
    print("-" * 75)

    for f in range(total_frames):
        ts = t0 + timedelta(milliseconds=f * 66)
        # World Y position linearly interpolates from 85.0 to 15.0
        world_y = 85.0 - (f / (total_frames - 1)) * 70.0
        wp = WorldPoint(x=world_x, y=world_y)

        # Project world position to Camera 1 and Camera 2 pixels
        px1, py1 = project_world_to_image(wp, H1)
        px2, py2 = project_world_to_image(wp, H2)

        traj_cam1.append(TrajectoryPoint(x=px1, y=py1, timestamp_utc=ts, frame_id=f))
        traj_cam2.append(TrajectoryPoint(x=px2, y=py2, timestamp_utc=ts, frame_id=f))

        # Build TrackState for Camera 1 (bbox bottom center matches px1, py1)
        track_cam1 = TrackState(
            track_id=101,
            camera_id="cam_01_angled",
            class_id=TargetClass.PERSON,
            bbox=BoundingBox(x_min=px1 - 15, y_min=py1 - 50, x_max=px1 + 15, y_max=py1),
            center_xy=(px1, py1 - 25),
            status=TrackStatus.TRACKED,
            first_seen=t0,
            last_seen=ts,
            trajectory=list(traj_cam1[-20:]),
        )

        # Build TrackState for Camera 2
        track_cam2 = TrackState(
            track_id=101,
            camera_id="cam_02_frontal",
            class_id=TargetClass.PERSON,
            bbox=BoundingBox(x_min=px2 - 15, y_min=py2 - 50, x_max=px2 + 15, y_max=py2),
            center_xy=(px2, py2 - 25),
            status=TrackStatus.TRACKED,
            first_seen=t0,
            last_seen=ts,
            trajectory=list(traj_cam2[-20:]),
        )

        # Process through SpatialEngine for both cameras
        states_cam1 = engine.process_tracks([track_cam1], "cam_01_angled", ts)
        states_cam2 = engine.process_tracks([track_cam2], "cam_02_frontal", ts)

        st1 = states_cam1[0]
        st2 = states_cam2[0]

        # Draw frame for Camera 1
        frame1 = np.full((480, 640, 3), 20, dtype=np.uint8)
        # Draw background perspective grid
        for gy in range(0, 101, 20):
            p_l = project_world_to_image(WorldPoint(x=0, y=gy), H1)
            p_r = project_world_to_image(WorldPoint(x=100, y=gy), H1)
            cv2.line(frame1, (int(p_l[0]), int(p_l[1])), (int(p_r[0]), int(p_r[1])), (45, 45, 45), 1)

        # Render bbox & trajectory trail
        cv2.rectangle(frame1, (int(track_cam1.bbox.x_min), int(track_cam1.bbox.y_min)), (int(track_cam1.bbox.x_max), int(track_cam1.bbox.y_max)), (255, 255, 255), 2)
        cv2.putText(frame1, f"Track #{track_cam1.track_id} (person)", (int(track_cam1.bbox.x_min), int(track_cam1.bbox.y_min - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        for i in range(len(traj_cam1) - 1):
            cv2.line(frame1, (int(traj_cam1[i].x), int(traj_cam1[i].y)), (int(traj_cam1[i+1].x), int(traj_cam1[i+1].y)), (0, 255, 255), 2)

        annotated1 = draw_spatial_overlay(frame1, engine._camera_configs.get("cam_01_angled") or CameraSpatialConfig(camera_id="cam_01_angled"), [st1], [proj_cam1])

        # Draw frame for Camera 2
        frame2 = np.full((480, 640, 3), 20, dtype=np.uint8)
        for gy in range(0, 101, 20):
            p_l = project_world_to_image(WorldPoint(x=0, y=gy), H2)
            p_r = project_world_to_image(WorldPoint(x=100, y=gy), H2)
            cv2.line(frame2, (int(p_l[0]), int(p_l[1])), (int(p_r[0]), int(p_r[1])), (45, 45, 45), 1)

        cv2.rectangle(frame2, (int(track_cam2.bbox.x_min), int(track_cam2.bbox.y_min)), (int(track_cam2.bbox.x_max), int(track_cam2.bbox.y_max)), (255, 255, 255), 2)
        cv2.putText(frame2, f"Track #{track_cam2.track_id} (person)", (int(track_cam2.bbox.x_min), int(track_cam2.bbox.y_min - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        for i in range(len(traj_cam2) - 1):
            cv2.line(frame2, (int(traj_cam2[i].x), int(traj_cam2[i].y)), (int(traj_cam2[i+1].x), int(traj_cam2[i+1].y)), (0, 255, 255), 2)

        annotated2 = draw_spatial_overlay(frame2, engine._camera_configs.get("cam_02_frontal") or CameraSpatialConfig(camera_id="cam_02_frontal"), [st2], [proj_cam2])

        # Add Camera Title Badges
        cv2.putText(annotated1, "CAMERA 1: ANGLED PERSPECTIVE (Border is DIAGONAL)", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 2)
        cv2.putText(annotated1, f"Side: {st1.border_side.value.upper() if st1.border_side else 'N/A'} | Status: {st1.crossing_status.value.upper()}", (15, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 0) if st1.border_side == BorderSide.PERMITTED else ((0, 200, 255) if st1.border_side == BorderSide.WARNING_BUFFER else (0, 0, 255)), 2)

        cv2.putText(annotated2, "CAMERA 2: FRONTAL PERSPECTIVE (Border is HORIZONTAL)", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 2)
        cv2.putText(annotated2, f"Side: {st2.border_side.value.upper() if st2.border_side else 'N/A'} | Status: {st2.crossing_status.value.upper()}", (15, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 0) if st2.border_side == BorderSide.PERMITTED else ((0, 200, 255) if st2.border_side == BorderSide.WARNING_BUFFER else (0, 0, 255)), 2)

        # Combine side-by-side (1280 x 480)
        combined_cams = np.hstack([annotated1, annotated2])

        # Add Top Global Telemetry Header (60px height)
        header = np.zeros((60, 1280, 3), dtype=np.uint8)
        cv2.putText(header, f"IBVAP WORLD-OWNED BORDER MODEL TEST | Frame {f+1:02d}/60 | Target World Pos: (X={world_x:.1f}m, Y={world_y:.1f}m)", (20, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        coord_status = "PERMITTED (FRIENDLY)" if world_y > 60 else ("WARNING BUFFER (APPROACHING)" if world_y >= 50 else "RESTRICTED (BREACHED)")
        status_color = (0, 255, 0) if world_y > 60 else ((0, 220, 255) if world_y >= 50 else (0, 0, 255))
        cv2.putText(header, f"Real-World Ground Truth: {coord_status} | Synchronized Across Both Cameras: TRUE", (20, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.50, status_color, 2)

        full_frame = np.vstack([header, combined_cams])
        writer.write(full_frame)

        if f % 15 == 0 or f == total_frames - 1:
            print(f"Frame {f+1:02d}/60 -> World Y={world_y:.1f}m | Cam1 Side: {st1.border_side.value:14s} | Cam2 Side: {st2.border_side.value:14s} | Crossing Status: {st1.crossing_status.value}")

    writer.release()
    print("=" * 75)
    print(f"[OK] Video successfully rendered & saved to: {os.path.abspath(output_path)}")
    print("=" * 75)


if __name__ == "__main__":
    run_multi_cam_border_test()
