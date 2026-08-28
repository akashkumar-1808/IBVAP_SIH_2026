import time
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import List
from datetime import datetime, timezone, timedelta
import numpy as np

from worker.behavior import BehaviorEngine, BehaviorConfig, BehaviorType
from worker.spatial.schemas import SpatialState, MovementDirection, ZoneType, SpatialTransitionType
from worker.tracking.schemas import TrackState, TrajectoryPoint, TargetClass, BoundingBox, TrackStatus


def benchmark_behavior(num_frames: int = 1000, num_tracks: int = 20):
    print("=" * 60)
    print("IBVAP Phase 7 — Behavioral Analytics Engine Benchmark")
    print("=" * 60)

    config = BehaviorConfig(
        loitering_seconds=3.0,
        loitering_max_displacement_px=50.0,
        persistent_approach_seconds=2.0,
        persistent_approach_min_distance_px=20.0,
        repeated_approach_window_sec=15.0,
    )
    engine = BehaviorEngine(default_config=config)
    engine.configure("cam_bench_behavior", config)

    base_time = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Initialize track simulated positions
    track_states = [
        {"x": 100.0 + i * 20.0, "y": 100.0 + i * 10.0, "vx": np.random.uniform(0.5, 2.5), "vy": 0.0}
        for i in range(num_tracks)
    ]

    latencies = []
    total_primitives_generated = 0

    print(f"Running Behavior benchmark over {num_frames} frames ({num_tracks} active tracks)...")

    for frame_id in range(num_frames):
        ts = base_time + timedelta(milliseconds=frame_id * 33.33)
        current_tracks: List[TrackState] = []
        spatial_states: List[SpatialState] = []

        for idx, pos in enumerate(track_states):
            pos["x"] += pos["vx"]
            if pos["x"] > 600:
                pos["x"] = 100.0

            traj = [
                TrajectoryPoint(x=pos["x"] - pos["vx"], y=pos["y"], timestamp_utc=ts - timedelta(milliseconds=33), frame_id=frame_id - 1),
                TrajectoryPoint(x=pos["x"], y=pos["y"], timestamp_utc=ts, frame_id=frame_id),
            ]

            t_state = TrackState(
                track_id=idx + 1,
                camera_id="cam_bench_behavior",
                class_id=TargetClass.PERSON,
                bbox=BoundingBox(x_min=pos["x"] - 15, y_min=pos["y"] - 30, x_max=pos["x"] + 15, y_max=pos["y"] + 30),
                center_xy=(pos["x"], pos["y"]),
                status=TrackStatus.TRACKED,
                first_seen=base_time,
                last_seen=ts,
                trajectory=traj,
            )
            current_tracks.append(t_state)

            # Alternate between RESTRICTED and BUFFER zones
            z_id = "zone_restricted_01" if pos["x"] > 300 else "zone_safe_01"
            z_type = ZoneType.RESTRICTED if pos["x"] > 300 else ZoneType.SAFE
            dir_state = MovementDirection.TOWARD if pos["vx"] > 0 else MovementDirection.AWAY

            s_state = SpatialState(
                camera_id="cam_bench_behavior",
                track_id=idx + 1,
                timestamp_utc=ts,
                current_zone_id=z_id,
                current_zone_type=z_type,
                transition=SpatialTransitionType.NONE,
                direction=dir_state,
            )
            spatial_states.append(s_state)

        t_start = time.perf_counter()
        primitives = engine.process(current_tracks, spatial_states, ts)
        t_end = time.perf_counter()

        latencies.append((t_end - t_start) * 1000.0)
        total_primitives_generated += len(primitives)

    avg_latency_ms = float(np.mean(latencies))
    min_latency_ms = float(np.min(latencies))
    max_latency_ms = float(np.max(latencies))
    p95_latency_ms = float(np.percentile(latencies, 95))
    fps = 1000.0 / avg_latency_ms if avg_latency_ms > 0 else 0.0

    print("-" * 60)
    print(f"Frames Processed:           {num_frames}")
    print(f"Total Tracks Evaluated:     {num_frames * num_tracks}")
    print(f"Total Behaviors Generated:  {total_primitives_generated}")
    print(f"Mean Latency per Frame:     {avg_latency_ms:.4f} ms")
    print(f"Min / Max Latency:          {min_latency_ms:.4f} ms / {max_latency_ms:.4f} ms")
    print(f"P95 Latency:                {p95_latency_ms:.4f} ms")
    print(f"Effective Behavior FPS:     {fps:.2f} FPS")
    print("=" * 60)

    engine.close()


if __name__ == "__main__":
    benchmark_behavior()
