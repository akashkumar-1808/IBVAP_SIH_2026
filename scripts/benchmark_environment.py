import time
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone
import numpy as np
from worker.environment import EnvironmentAnalyzer, EnvironmentConfig
from worker.ingestion import FramePacket


def benchmark_environment(num_frames: int = 500, resolution: tuple = (640, 480)):
    print("=" * 60)
    print("IBVAP Phase 5 — Environment Engine Analysis Benchmark")
    print("=" * 60)

    analyzer = EnvironmentAnalyzer(config=EnvironmentConfig())

    # Create synthetic frames with varied lighting, contrast, and noise
    frames = []
    for i in range(num_frames):
        # Varying brightness and noise across frames
        base_lum = int(50 + 150 * (i / num_frames))
        img = np.full((resolution[1], resolution[0], 3), base_lum, dtype=np.uint8)
        # Add random noise
        noise = np.random.randint(-15, 15, img.shape, dtype=np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        pkt = FramePacket(
            camera_id="cam_env_bench_01",
            frame_id=i,
            timestamp_utc=datetime.now(timezone.utc),
            image=img,
            width=resolution[0],
            height=resolution[1],
            source_type="benchmark",
        )
        frames.append(pkt)

    print(f"Running Environment Engine benchmark over {num_frames} frames ({resolution[0]}x{resolution[1]})...")

    latencies = []
    for pkt in frames:
        t_start = time.perf_counter()
        state = analyzer.analyze(pkt)
        t_end = time.perf_counter()
        latencies.append((t_end - t_start) * 1000.0)

    avg_latency_ms = float(np.mean(latencies))
    min_latency_ms = float(np.min(latencies))
    max_latency_ms = float(np.max(latencies))
    p95_latency_ms = float(np.percentile(latencies, 95))
    fps = 1000.0 / avg_latency_ms if avg_latency_ms > 0 else 0.0

    latest_state = analyzer.get_state("cam_env_bench_01")

    print("-" * 60)
    print(f"Frames Analyzed:            {num_frames}")
    print(f"Mean Latency per Frame:     {avg_latency_ms:.4f} ms")
    print(f"Min / Max Latency:          {min_latency_ms:.4f} ms / {max_latency_ms:.4f} ms")
    print(f"P95 Latency:                {p95_latency_ms:.4f} ms")
    print(f"Effective Analysis Throughput: {fps:.2f} FPS")
    print("-" * 60)
    if latest_state:
        print(f"Sample Lighting Condition:  {latest_state.lighting.value}")
        print(f"Sample Visibility Quality:  {latest_state.visibility.value}")
        print(f"Sample Quality Score:       {latest_state.quality_score:.4f}")
        print(f"Sample Sharpness (Laplacian): {latest_state.blur_score:.2f}")
        print(f"Sample RMS Contrast:        {latest_state.contrast:.4f}")
        print(f"Sample Noise Estimate:      {latest_state.noise_estimate:.4f}")
    print("=" * 60)

    analyzer.close()
    return {
        "frames": num_frames,
        "mean_latency_ms": avg_latency_ms,
        "fps": fps,
    }


if __name__ == "__main__":
    benchmark_environment()
