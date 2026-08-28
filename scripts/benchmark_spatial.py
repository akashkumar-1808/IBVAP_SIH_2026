import time
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import List, Tuple
from datetime import datetime, timezone, timedelta
import numpy as np
from worker.spatial import (
    SpatialEngine,
    CameraSpatialConfig,
    ZonePolygon,
    VirtualFence,
    ZoneType,
)
from worker.tracking.schemas import TrackState, TrajectoryPoint, TargetClass, BoundingBox, TrackStatus


def benchmark_spatial(num_frames: int = 1000, num_tracks: int = 20):
    print("=" * 60)
    print("IBVAP Phase 6 — Spatial Intelligence Engine Benchmark")
    print("=" * 60)

    engine = SpatialEngine()

    # Configure Camera with 4 zones and 2 virtual fences
    config = CameraSpatialConfig(
        camera_id="cam_bench_spatial",
        zones=[
            ZonePolygon(id="z_safe", name="Safe Zone", type=ZoneType.SAFE, polygon=[(0, 0), (300, 0), (300, 400), (0, 400)]),
            ZonePolygon(id="z_buffer", name="Buffer Zone", type=ZoneType.BUFFER, polygon=[(300, 0), (500, 0), (500, 400), (300, 400)]),
            ZonePolygon(id="z_restricted", name="Restricted Zone", type=ZoneType.RESTRICTED, polygon=[(500, 0), (700, 0), (700, 400), (500, 400)]),
            ZonePolygon(id="z_critical", name="Critical Border", type=ZoneType.CRITICAL, polygon=[(700, 0), (800, 0), (800, 400), (700, 400)]),
        ],
        fences=[
            VirtualFence(id="fence_outer", name="Outer Perimeter Fence", start_point=(400, 0), end_point=(400, 400)),
            VirtualFence(id="fence_inner", name="Inner Security Fence", start_point=(600, 0), end_point=(600, 400)),
        ],
        expected_threat_vector=(1.0, 0.0),  # Rightwards movement (towards border)
    )
    engine.configure_camera(config)

    # Generate synthetic track state sequence
    base_time = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    track_positions = [
        {"x": 100.0 + i * 25.0, "y": 50.0 + i * 15.0, "vx": np.random.uniform(1.5, 4.0), "vy": np.random.uniform(-0.5, 0.5)}
        for i in range(num_tracks)
    ]

    total_zone_evaluations = 0
    total_fence_evaluations = 0
    latencies = []

    print(f"Running Spatial benchmark over {num_frames} frames ({num_tracks} active tracks)...")

    for frame_id in range(num_frames):
        ts = base_time + timedelta(milliseconds=frame_id * 33.33)
        current_tracks: List[TrackState] = []

        for idx, pos in enumerate(track_positions):
            pos["x"] += pos["vx"]
            pos["y"] += pos["vy"]

            # Wrap around if beyond boundary
            if pos["x"] > 800:
                pos["x"] = 50.0

            traj = [
                TrajectoryPoint(x=pos["x"] - pos["vx"], y=pos["y"] - pos["vy"], timestamp_utc=ts - timedelta(milliseconds=33), frame_id=frame_id - 1),
                TrajectoryPoint(x=pos["x"], y=pos["y"], timestamp_utc=ts, frame_id=frame_id),
            ]

            t_state = TrackState(
                track_id=idx + 1,
                camera_id="cam_bench_spatial",
                class_id=TargetClass.PERSON,
                bbox=BoundingBox(x_min=pos["x"] - 20, y_min=pos["y"] - 50, x_max=pos["x"] + 20, y_max=pos["y"] + 50),
                center_xy=(pos["x"], pos["y"]),
                velocity_xy=(pos["vx"] * 30.0, pos["vy"] * 30.0),
                speed_pixels_per_sec=float(np.hypot(pos["vx"] * 30.0, pos["vy"] * 30.0)),
                age_frames=frame_id + 1,
                consecutive_invisible_frames=0,
                status=TrackStatus.TRACKED,
                first_seen=base_time,
                last_seen=ts,
                trajectory=traj,
            )
            current_tracks.append(t_state)

        t_start = time.perf_counter()
        spatial_states = engine.process_tracks(current_tracks, "cam_bench_spatial", ts)
        t_end = time.perf_counter()

        latencies.append((t_end - t_start) * 1000.0)
        total_zone_evaluations += len(current_tracks) * len(config.zones)
        total_fence_evaluations += len(current_tracks) * len(config.fences)

    avg_latency_ms = float(np.mean(latencies))
    min_latency_ms = float(np.min(latencies))
    max_latency_ms = float(np.max(latencies))
    p95_latency_ms = float(np.percentile(latencies, 95))
    fps = 1000.0 / avg_latency_ms if avg_latency_ms > 0 else 0.0

    print("-" * 60)
    print(f"Frames Processed:           {num_frames}")
    print(f"Total Tracks Processed:     {num_frames * num_tracks}")
    print(f"Total Zone Checks:          {total_zone_evaluations}")
    print(f"Total Fence Checks:         {total_fence_evaluations}")
    print(f"Mean Latency per Frame:     {avg_latency_ms:.4f} ms")
    print(f"Min / Max Latency:          {min_latency_ms:.4f} ms / {max_latency_ms:.4f} ms")
    print(f"P95 Latency:                {p95_latency_ms:.4f} ms")
    print(f"Effective Spatial FPS:      {fps:.2f} FPS")
    print("=" * 60)

    engine.close()
    return {
        "frames": num_frames,
        "mean_latency_ms": avg_latency_ms,
        "spatial_fps": fps,
    }


if __name__ == "__main__":
    benchmark_spatial()
