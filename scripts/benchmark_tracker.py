import time
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone, timedelta
import numpy as np
from worker.tracking import ByteTrackTracker, Detection, BoundingBox, TargetClass


def benchmark_tracker(num_frames: int = 200, num_objects: int = 10):
    print("=" * 60)
    print("IBVAP Phase 4 — ByteTrack Multi-Object Tracking Benchmark")
    print("=" * 60)

    tracker = ByteTrackTracker(camera_id="cam_bench_01", min_hits=2, max_lost_frames=30)

    # Simulate object trajectories across frames
    base_time = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    object_positions = [
        {"x": np.random.uniform(50, 500), "y": np.random.uniform(50, 400), "vx": np.random.uniform(-2, 2), "vy": np.random.uniform(-1, 1)}
        for _ in range(num_objects)
    ]

    total_detections = 0
    latencies = []

    print(f"Running tracker benchmark over {num_frames} frames ({num_objects} simultaneous objects)...")

    for frame_id in range(num_frames):
        ts = base_time + timedelta(milliseconds=frame_id * 33.33)
        frame_detections = []

        for obj_idx, obj in enumerate(object_positions):
            # Update object position with simulated motion
            obj["x"] += obj["vx"]
            obj["y"] += obj["vy"]

            # Drop detection randomly 5% of time to test missed frame robustness
            if np.random.rand() < 0.05:
                continue

            x1 = float(obj["x"])
            y1 = float(obj["y"])
            x2 = float(x1 + 40.0)
            y2 = float(y1 + 100.0)

            det = Detection(
                camera_id="cam_bench_01",
                frame_id=frame_id,
                timestamp_utc=ts,
                class_id=TargetClass.PERSON if obj_idx % 2 == 0 else TargetClass.VEHICLE,
                confidence=float(np.random.uniform(0.60, 0.95)),
                bbox=BoundingBox(x_min=x1, y_min=y1, x_max=x2, y_max=y2),
            )
            frame_detections.append(det)

        total_detections += len(frame_detections)

        t_start = time.perf_counter()
        tracks = tracker.update(
            detections=frame_detections,
            frame_id=frame_id,
            timestamp_utc=ts,
            camera_id="cam_bench_01",
        )
        t_end = time.perf_counter()
        latencies.append((t_end - t_start) * 1000.0)

    avg_latency_ms = float(np.mean(latencies))
    min_latency_ms = float(np.min(latencies))
    max_latency_ms = float(np.max(latencies))
    p95_latency_ms = float(np.percentile(latencies, 95))
    effective_tracking_fps = 1000.0 / avg_latency_ms if avg_latency_ms > 0 else 0.0

    final_tracks = tracker.get_tracks()
    active_count = len([t for t in final_tracks if t.status.value == "tracked"])
    total_tracks_created = tracker._next_track_id - 1

    print("-" * 60)
    print(f"Frames Processed:           {num_frames}")
    print(f"Total Detections Processed: {total_detections}")
    print(f"Total Tracks Created:       {total_tracks_created}")
    print(f"Final Active Tracks:        {active_count}")
    print(f"Mean Update Latency:        {avg_latency_ms:.4f} ms")
    print(f"Min / Max Latency:          {min_latency_ms:.4f} ms / {max_latency_ms:.4f} ms")
    print(f"P95 Latency:                {p95_latency_ms:.4f} ms")
    print(f"Effective Tracking FPS:     {effective_tracking_fps:.2f} FPS")
    print("=" * 60)

    tracker.close()
    return {
        "frames": num_frames,
        "mean_latency_ms": avg_latency_ms,
        "tracking_fps": effective_tracking_fps,
        "active_tracks": active_count,
    }


if __name__ == "__main__":
    benchmark_tracker()
