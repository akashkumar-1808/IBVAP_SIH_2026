import time
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from datetime import datetime, timezone
from worker.perception import ObjectDetector
from worker.ingestion import FramePacket


def benchmark_detector(num_frames: int = 50, resolution: tuple = (640, 480)):
    print("=" * 60)
    print("IBVAP Phase 3 — Baseline Detector Benchmark")
    print("=" * 60)

    t0 = time.perf_counter()
    detector = ObjectDetector(model_name="yolov8n", confidence_threshold=0.25)
    detector.load()
    load_time = time.perf_counter() - t0
    print(f"1. Model Load Time: {load_time:.4f}s")

    t1 = time.perf_counter()
    detector.warmup(input_size=resolution)
    warmup_time = time.perf_counter() - t1
    print(f"2. Warmup Time:     {warmup_time:.4f}s")

    # Generate synthetic frames with simulated content
    frames = []
    for i in range(num_frames):
        img = np.zeros((resolution[1], resolution[0], 3), dtype=np.uint8)
        # Draw a synthetic rectangle
        img[100:300, 150:350] = (100, 150, 200)
        pkt = FramePacket(
            camera_id="bench_cam",
            frame_id=i,
            timestamp_utc=datetime.now(timezone.utc),
            image=img,
            width=resolution[0],
            height=resolution[1],
            source_type="benchmark",
        )
        frames.append(pkt)

    print(f"3. Running inference over {num_frames} frames ({resolution[0]}x{resolution[1]})...")
    latencies = []
    all_detections_count = 0

    for pkt in frames:
        t_start = time.perf_counter()
        dets = detector.infer(pkt)
        t_end = time.perf_counter()
        latencies.append((t_end - t_start) * 1000.0)
        all_detections_count += len(dets)

    avg_latency_ms = float(np.mean(latencies))
    min_latency_ms = float(np.min(latencies))
    max_latency_ms = float(np.max(latencies))
    p95_latency_ms = float(np.percentile(latencies, 95))
    inference_fps = 1000.0 / avg_latency_ms if avg_latency_ms > 0 else 0.0

    meta = detector.get_metadata()
    print("-" * 60)
    print(f"Device:                 {meta['device']}")
    print(f"Model:                  {meta['model_name']}")
    print(f"Frames Processed:       {num_frames}")
    print(f"Mean Latency:           {avg_latency_ms:.2f} ms")
    print(f"Min / Max Latency:      {min_latency_ms:.2f} ms / {max_latency_ms:.2f} ms")
    print(f"P95 Latency:            {p95_latency_ms:.2f} ms")
    print(f"Effective Inference FPS:{inference_fps:.2f} FPS")
    print("=" * 60)

    detector.close()
    return {
        "load_time_sec": load_time,
        "warmup_time_sec": warmup_time,
        "mean_latency_ms": avg_latency_ms,
        "inference_fps": inference_fps,
        "device": meta["device"],
    }


if __name__ == "__main__":
    benchmark_detector()
