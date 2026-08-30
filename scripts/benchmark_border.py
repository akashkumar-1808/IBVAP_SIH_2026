"""
IBVAP Spatial Intelligence Benchmark — World-Owned Border Model.

Measures:
1. Homography matrix computation latency
2. Border section projection latency (World -> Image)
3. Ground-contact point extraction latency
4. Ground-contact pixel-to-world mapping latency
5. World-space side determination latency
6. Crossing check & confirmation latency
7. End-to-end SpatialEngine throughput per frame with multiple tracks

Architecture Decision: DEC-0006
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from worker.spatial import (
    SpatialEngine,
    BorderSection,
    CameraRegistration,
    CameraCalibration,
    CalibrationCorrespondence,
    WorldPoint,
    compute_homography,
    project_border_to_camera,
    estimate_ground_contact,
    image_to_world_ground,
    determine_side,
    CrossingConfirmation,
    BorderSide,
)
from worker.tracking.schemas import TrackState, TrajectoryPoint, TargetClass, BoundingBox, TrackStatus


def run_border_benchmark(num_frames: int = 1000, num_tracks: int = 20):
    print("=" * 65)
    print("   IBVAP — World-Owned Border Model Performance Benchmark")
    print("=" * 65)

    # 1. Benchmark Homography Computation
    correspondences = [
        CalibrationCorrespondence(world_point=WorldPoint(x=0, y=0), image_point=(50, 430)),
        CalibrationCorrespondence(world_point=WorldPoint(x=100, y=0), image_point=(590, 430)),
        CalibrationCorrespondence(world_point=WorldPoint(x=100, y=100), image_point=(590, 50)),
        CalibrationCorrespondence(world_point=WorldPoint(x=0, y=100), image_point=(50, 50)),
        CalibrationCorrespondence(world_point=WorldPoint(x=50, y=50), image_point=(320, 240)),
    ]

    n_homo = 500
    t0 = time.perf_counter()
    for _ in range(n_homo):
        H, reproj = compute_homography(correspondences)
    homo_time = (time.perf_counter() - t0) / n_homo * 1000.0
    print(f"1. Homography Computation (5 points): {homo_time:.4f} ms (reproj={reproj:.4f}px)")

    # 2. Benchmark Border Section Projection
    section = BorderSection(
        id="section_bench",
        name="Benchmark Border",
        points=[WorldPoint(x=i * 10, y=50) for i in range(11)],  # 11-point polyline
        permitted_side_normal=(0.0, 1.0),
        warning_buffer_distance=5.0,
    )
    calibration = CameraCalibration(
        camera_id="cam_bench",
        image_width=1920,
        image_height=1080,
        correspondences=correspondences,
        calibration_version="1.0",
    )

    n_proj = 500
    t0 = time.perf_counter()
    for _ in range(n_proj):
        proj = project_border_to_camera(section, calibration, H)
    proj_time = (time.perf_counter() - t0) / n_proj * 1000.0
    print(f"2. Border Polyline Projection (11 pts): {proj_time:.4f} ms")

    # 3. Benchmark Ground-Contact Estimation
    H_inv = np.linalg.inv(H)
    t_dummy = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    sample_track = TrackState(
        track_id=1,
        camera_id="cam_bench",
        class_id=TargetClass.PERSON,
        bbox=BoundingBox(x_min=100, y_min=200, x_max=140, y_max=300),
        center_xy=(120.0, 250.0),
        status=TrackStatus.TRACKED,
        first_seen=t_dummy,
        last_seen=t_dummy,
        trajectory=[TrajectoryPoint(x=120, y=250, timestamp_utc=t_dummy, frame_id=0)],
    )

    n_gc = 5000
    t0 = time.perf_counter()
    for _ in range(n_gc):
        gc = estimate_ground_contact(sample_track)
    gc_time = (time.perf_counter() - t0) / n_gc * 1000.0
    print(f"3. Ground-Contact Point Extraction:   {gc_time:.5f} ms")

    # 4. Benchmark Pixel-to-World Ground Mapping
    t0 = time.perf_counter()
    for _ in range(n_gc):
        wp = image_to_world_ground(gc.pixel_xy, H_inv)
    map_time = (time.perf_counter() - t0) / n_gc * 1000.0
    print(f"4. Ground Pixel -> World Mapping:     {map_time:.5f} ms")

    # 5. Benchmark World-Space Side Determination
    world_xy = (wp.x, wp.y)
    t0 = time.perf_counter()
    for _ in range(n_gc):
        side = determine_side(world_xy, section)
    side_time = (time.perf_counter() - t0) / n_gc * 1000.0
    print(f"5. Side Determination (Signed Dist):  {side_time:.5f} ms (result={side.value})")

    # 6. Benchmark Crossing Confirmation
    cc = CrossingConfirmation(confirmation_frames=3)
    t0 = time.perf_counter()
    for i in range(n_gc):
        ev = cc.update(i % 50, "section_bench", BorderSide.RESTRICTED, "cam_bench", t_dummy)
    cross_time = (time.perf_counter() - t0) / n_gc * 1000.0
    print(f"6. Crossing Check & Confirmation:     {cross_time:.5f} ms")

    # 7. End-to-End Multi-Track SpatialEngine Benchmark
    print("-" * 65)
    print(f"Running End-to-End Benchmark over {num_frames} frames ({num_tracks} active tracks)...")

    engine = SpatialEngine(crossing_confirmation_frames=3)
    engine.register_border_section(section)
    engine.register_camera(CameraRegistration(
        camera_id="cam_bench", visible_border_sections=["section_bench"],
    ))
    engine.register_calibration(calibration)

    # Generate synthetic tracks moving across the image
    tracks_pool = []
    for tid in range(num_tracks):
        traj = []
        for f in range(5):
            traj.append(TrajectoryPoint(
                x=100.0 + tid * 20.0,
                y=150.0 + f * 5.0,
                timestamp_utc=t_dummy + timedelta(milliseconds=f * 33),
                frame_id=f,
            ))
        tracks_pool.append(TrackState(
            track_id=tid,
            camera_id="cam_bench",
            class_id=TargetClass.PERSON,
            bbox=BoundingBox(x_min=90 + tid * 20, y_min=130, x_max=110 + tid * 20, y_max=170),
            center_xy=(100.0 + tid * 20.0, 150.0),
            status=TrackStatus.TRACKED,
            first_seen=t_dummy,
            last_seen=t_dummy,
            trajectory=traj,
        ))

    latencies = []
    t_start = time.perf_counter()

    for f_idx in range(num_frames):
        ts = t_dummy + timedelta(milliseconds=f_idx * 33)
        # Update track positions slightly
        for tr in tracks_pool:
            ny = tr.center_xy[1] + (0.5 if f_idx % 2 == 0 else -0.5)
            tr.center_xy = (tr.center_xy[0], ny)
            tr.trajectory.append(TrajectoryPoint(x=tr.center_xy[0], y=ny, timestamp_utc=ts, frame_id=f_idx))
            if len(tr.trajectory) > 30:
                tr.trajectory.pop(0)

        t_f0 = time.perf_counter()
        states = engine.process_tracks(tracks_pool, "cam_bench", ts)
        t_f1 = time.perf_counter()
        latencies.append((t_f1 - t_f0) * 1000.0)

    total_time = time.perf_counter() - t_start
    mean_lat = np.mean(latencies)
    p95_lat = np.percentile(latencies, 95)
    fps = num_frames / total_time

    print("-" * 65)
    print(f"Frames Processed:           {num_frames}")
    print(f"Tracks Evaluated:           {num_frames * num_tracks}")
    print(f"Mean Latency per Frame:     {mean_lat:.4f} ms")
    print(f"P95 Latency per Frame:      {p95_lat:.4f} ms")
    print(f"Effective Spatial Engine:   {fps:.2f} FPS ({num_tracks} tracks/frame)")
    print("=" * 65)


if __name__ == "__main__":
    run_border_benchmark()
