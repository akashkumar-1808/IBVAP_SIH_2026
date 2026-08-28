import time
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
from worker.ingestion import FileVideoSource, BoundedFrameQueue


def benchmark_ingestion(num_frames: int = 300, max_queue_size: int = 30):
    temp_video = "storage/temp_bench.mp4"
    os.makedirs("storage", exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(temp_video, fourcc, 30.0, (640, 480))

    for i in range(num_frames):
        frame = np.full((480, 640, 3), (i % 255, 100, 150), dtype=np.uint8)
        out.write(frame)
    out.release()

    source = FileVideoSource(camera_id="bench_cam", file_path=temp_video, loop=False, realtime_pacing=False)
    queue = BoundedFrameQueue(max_size=max_queue_size)
    source.connect()

    start = time.perf_counter()
    read_count = 0
    while True:
        pkt = source.read()
        if pkt is None:
            break
        queue.put(pkt)
        read_count += 1
    duration = time.perf_counter() - start

    source.close()
    if os.path.exists(temp_video):
        try:
            os.remove(temp_video)
        except Exception:
            pass

    fps = read_count / duration if duration > 0 else 0
    stats = queue.stats()
    print(f"Ingestion Benchmark: {read_count} frames in {duration:.4f}s -> {fps:.2f} decode FPS | Dropped: {stats['total_dropped']}")
    return fps


if __name__ == "__main__":
    benchmark_ingestion()
