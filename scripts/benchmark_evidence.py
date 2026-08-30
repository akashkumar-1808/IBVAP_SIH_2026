"""
IBVAP — Structured Evidence Storage & Packaging Subsystem Performance Benchmark.

Measures:
1. Ring buffer frame push latency
2. Time-window frame slice retrieval latency
3. Raw & Annotated JPEG Snapshot encoding latency
4. MP4 video clip encoding latency (50 frames / 2.0s clip)
5. Cryptographic SHA-256 artifact hashing and manifest sealing latency
6. End-to-end EvidencePackage creation throughput and latency on CPU.

Architecture Decision: DEC-0008
"""

import sys
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np
import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from worker.evidence import (
    RollingFrameBuffer,
    BufferedFrame,
    SnapshotExtractor,
    ClipPackager,
    EvidenceHasher,
    EvidencePackager,
    EvidencePackageConfig,
    EvidenceManifest,
)
from worker.fusion.schemas import EventRecord, EventType, EventStatus, FusionReasonCode
from backend.app.schemas.common import TargetClass, EventPriority


def run_evidence_benchmark():
    print("=" * 70)
    print("   IBVAP — Structured Evidence Storage & Packaging Performance Benchmark")
    print("=" * 70)

    temp_dir = tempfile.mkdtemp(prefix="ibvap_evidence_bench_")
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    # Synthetic 640x480 frame
    sample_frame = np.full((480, 640, 3), 50, dtype=np.uint8)
    cv2.putText(sample_frame, "BENCHMARK FRAME", (100, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

    sample_event = EventRecord(
        id="evt_bench_001",
        camera_id="cam_bench_01",
        track_id=1,
        event_type=EventType.BORDER_CROSSING,
        priority=EventPriority.CRITICAL,
        risk_score=92.5,
        status=EventStatus.ACTIVE,
        target_class=TargetClass.PERSON,
        created_at=t0,
        updated_at=t0,
        first_observed_utc=t0,
        last_observed_utc=t0 + timedelta(seconds=2.0),
        duration_seconds=2.0,
        detection_confidence=0.95,
        track_persistence_frames=20,
        reason_codes=[FusionReasonCode.PERSON_DETECTED, FusionReasonCode.BORDER_CROSSED],
        explanation_summary="[CRITICAL PRIORITY — Score 92.5/100] Confirmed border crossing.",
    )

    try:
        # 1. Ring Buffer Insertion Latency
        buf = RollingFrameBuffer(max_seconds=15.0, fps=25.0)  # capacity = 375 frames
        n_pushes = 5000
        t_start = time.perf_counter()
        for i in range(n_pushes):
            buf.add_frame(i, t0 + timedelta(milliseconds=i * 40), sample_frame, "cam_bench_01")
        push_latency = (time.perf_counter() - t_start) / n_pushes * 1000.0
        print(f"1. Ring Buffer Frame Push Latency:        {push_latency:.5f} ms (per frame, including copy)")

        # 2. Window Retrieval Latency
        n_queries = 2000
        t_start = time.perf_counter()
        for _ in range(n_queries):
            window = buf.get_window(t0 + timedelta(seconds=1.0), t0 + timedelta(seconds=6.0))
        query_latency = (time.perf_counter() - t_start) / n_queries * 1000.0
        print(f"2. Time-Window Slice Retrieval Latency:   {query_latency:.5f} ms ({len(window)} frames retrieved)")

        # 3. Snapshot Encoding Latency
        raw_snap_path = f"{temp_dir}/snap_raw.jpg"
        n_snaps = 200
        t_start = time.perf_counter()
        for _ in range(n_snaps):
            SnapshotExtractor.save_raw_snapshot(sample_frame, raw_snap_path, quality=95)
        raw_snap_latency = (time.perf_counter() - t_start) / n_snaps * 1000.0
        print(f"3a. Raw Snapshot JPEG Encoding Latency:   {raw_snap_latency:.3f} ms (640x480 @ Q=95)")

        ann_snap_path = f"{temp_dir}/snap_ann.jpg"
        t_start = time.perf_counter()
        for _ in range(n_snaps):
            SnapshotExtractor.save_annotated_snapshot(sample_frame, sample_event, ann_snap_path, quality=95)
        ann_snap_latency = (time.perf_counter() - t_start) / n_snaps * 1000.0
        print(f"3b. Forensic HUD Annotated JPEG Latency:  {ann_snap_latency:.3f} ms (with banner & border overlays)")

        # 4. MP4 Video Clip Encoding Latency (50 frames / 2.0s)
        buffered_frames = [
            BufferedFrame(i, t0 + timedelta(milliseconds=i * 40), sample_frame, "cam_bench_01")
            for i in range(50)
        ]
        clip_path = f"{temp_dir}/bench_clip.mp4"
        n_clips = 50
        t_start = time.perf_counter()
        for _ in range(n_clips):
            ClipPackager.encode_clip(buffered_frames, clip_path, fps=25.0)
        clip_latency = (time.perf_counter() - t_start) / n_clips * 1000.0
        print(f"4. MP4 Clip Encoding Latency (50 frames): {clip_latency:.3f} ms ({50 / (clip_latency / 1000.0):.1f} FPS encoding speed)")

        # 5. Cryptographic SHA-256 Sealing Latency
        n_hashes = 1000
        t_start = time.perf_counter()
        for _ in range(n_hashes):
            h_snap = EvidenceHasher.hash_file(raw_snap_path)
            h_clip = EvidenceHasher.hash_file(clip_path)
        hash_latency = (time.perf_counter() - t_start) / n_hashes * 1000.0
        print(f"5. Cryptographic SHA-256 Sealing Latency: {hash_latency:.4f} ms (per artifact pair)")

        # 6. End-to-End Evidence Package Creation Throughput
        print("-" * 70)
        print("Running End-to-End Evidence Packaging Engine Benchmark...")
        config = EvidencePackageConfig(
            pre_event_seconds=2.0,
            post_event_seconds=1.0,
            fps=25.0,
            storage_root=f"{temp_dir}/packages",
        )
        packager = EvidencePackager(config=config)

        # Preload buffer with 75 frames (3.0s)
        for i in range(75):
            packager.add_raw_frame("cam_bench_01", i, t0 + timedelta(milliseconds=i * 40), sample_frame)

        n_packages = 100
        t_start = time.perf_counter()
        for p_idx in range(n_packages):
            ev = EventRecord(
                id=f"evt_bench_p{p_idx}",
                camera_id="cam_bench_01",
                track_id=p_idx,
                event_type=EventType.BORDER_CROSSING,
                priority=EventPriority.HIGH,
                risk_score=85.0,
                status=EventStatus.ACTIVE,
                target_class=TargetClass.PERSON,
                created_at=t0,
                updated_at=t0,
                first_observed_utc=t0 + timedelta(seconds=1.0),
                last_observed_utc=t0 + timedelta(seconds=2.0),
                duration_seconds=1.0,
                detection_confidence=0.90,
                track_persistence_frames=10,
                reason_codes=[FusionReasonCode.BORDER_CROSSED],
                explanation_summary="Benchmark event",
            )
            pkg = packager.create_package(event=ev, current_frame=sample_frame)
        total_pkg_time = time.perf_counter() - t_start
        mean_pkg_lat = (total_pkg_time / n_packages) * 1000.0
        pkg_throughput = n_packages / total_pkg_time

        print(f"Total Packages Generated & Sealed:       {n_packages}")
        print(f"Mean Full Package Assembly Latency:       {mean_pkg_lat:.2f} ms")
        print(f"Full Packaging Throughput (CPU):          {pkg_throughput:.2f} packages/sec")
        print("=" * 70)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_evidence_benchmark()
