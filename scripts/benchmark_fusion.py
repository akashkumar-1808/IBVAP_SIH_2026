"""
IBVAP — Multi-Modal Evidence Fusion Engine Performance Benchmark.

Measures:
1. Evidence extraction latency per track
2. Risk priority score calculation latency
3. Factual explanation summary generation latency
4. Full FusionEngine multi-track throughput (1,000 frames, 20 active tracks per frame)
5. Mean latency, P95 latency, and effective FPS throughput on CPU.

Architecture Decision: DEC-0007
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from worker.fusion import (
    FusionEngine,
    FusionConfig,
    EvidenceExtractor,
    EvidenceType,
    EvidenceItem,
    calculate_risk_score,
    generate_factual_summary,
    EventType,
    EventPriority,
    FusionReasonCode,
)
from worker.tracking.schemas import TrackState, TrajectoryPoint, TargetClass, BoundingBox, TrackStatus
from worker.spatial.schemas import SpatialState, MovementDirection, BorderSide, CrossingStatus, SpatialConfidence
from worker.environment.schemas import EnvironmentState, VisibilityQuality, LightingCondition, WeatherHint, TerrainProfile
from worker.behavior.schemas import BehaviorPrimitive, BehaviorType


def run_fusion_benchmark(num_frames: int = 1000, num_tracks: int = 20):
    print("=" * 68)
    print("   IBVAP — Multi-Modal Evidence Fusion Engine Performance Benchmark")
    print("=" * 68)

    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    config = FusionConfig()

    sample_track = TrackState(
        track_id=1,
        camera_id="cam_bench",
        class_id=TargetClass.PERSON,
        bbox=BoundingBox(x_min=100, y_min=100, x_max=130, y_max=180),
        center_xy=(115.0, 140.0),
        status=TrackStatus.TRACKED,
        first_seen=t0,
        last_seen=t0,
        trajectory=[TrajectoryPoint(x=115, y=140, timestamp_utc=t0, frame_id=0) for _ in range(5)],
    )

    sample_spatial = SpatialState(
        camera_id="cam_bench",
        track_id=1,
        timestamp_utc=t0,
        border_side=BorderSide.WARNING_BUFFER,
        direction=MovementDirection.TOWARD,
        spatial_confidence=SpatialConfidence.VALID,
    )

    sample_env = EnvironmentState(
        camera_id="cam_bench",
        timestamp_utc=t0,
        visibility=VisibilityQuality.GOOD,
        lighting=LightingCondition.DAY,
        weather=WeatherHint.CLEAR,
        terrain=TerrainProfile.OPEN_GROUND,
        luminance_mean=120.0,
        contrast_rms=45.0,
        blur_score=110.0,
        noise_variance=5.0,
        quality_score=0.85,
    )

    sample_behaviors = [
        BehaviorPrimitive(
            behavior_id="b_1",
            camera_id="cam_bench",
            track_id=1,
            behavior_type=BehaviorType.PERSISTENT_APPROACH,
            timestamp_utc=t0,
            first_observed_utc=t0,
            last_observed_utc=t0,
            duration_seconds=3.0,
        )
    ]

    # 1. Benchmark Evidence Extraction
    n_runs = 5000
    t_start = time.perf_counter()
    for _ in range(n_runs):
        evidence_items = EvidenceExtractor.extract_evidence(
            track=sample_track,
            spatial=sample_spatial,
            environment=sample_env,
            behaviors=sample_behaviors,
            camera_id="cam_bench",
            timestamp_utc=t0,
        )
    extract_time = (time.perf_counter() - t_start) / n_runs * 1000.0
    print(f"1. Evidence Extraction Latency (per track): {extract_time:.5f} ms ({len(evidence_items)} items)")

    # 2. Benchmark Score Calculation
    t_start = time.perf_counter()
    for _ in range(n_runs):
        score, reasons, flags = calculate_risk_score(evidence_items, config)
    score_time = (time.perf_counter() - t_start) / n_runs * 1000.0
    print(f"2. Risk Score Calculation Latency:          {score_time:.5f} ms (Score: {score:.1f}/100)")

    # 3. Benchmark Factual Summary Generation
    t_start = time.perf_counter()
    for _ in range(n_runs):
        summary = generate_factual_summary(
            event_type=EventType.PERSISTENT_APPROACH,
            target_class=TargetClass.PERSON,
            priority=EventPriority.HIGH,
            score=score,
            reason_codes=reasons,
            uncertainty_flags=flags,
        )
    summary_time = (time.perf_counter() - t_start) / n_runs * 1000.0
    print(f"3. Factual Explanation Summary Latency:     {summary_time:.5f} ms")

    # 4. Multi-Track End-to-End Fusion Engine Benchmark
    print("-" * 68)
    print(f"Running End-to-End Fusion Engine Benchmark over {num_frames} frames ({num_tracks} tracks/frame)...")

    engine = FusionEngine()
    engine.configure("cam_bench", config)

    # Build tracks and spatial states
    tracks_pool = []
    spatial_pool = []
    behaviors_pool = []

    for tid in range(num_tracks):
        tracks_pool.append(_make_bench_track(tid, t0))
        spatial_pool.append(SpatialState(
            camera_id="cam_bench",
            track_id=tid,
            timestamp_utc=t0,
            border_side=BorderSide.WARNING_BUFFER if tid % 2 == 0 else BorderSide.PERMITTED,
            direction=MovementDirection.TOWARD if tid % 3 == 0 else MovementDirection.UNCERTAIN,
            spatial_confidence=SpatialConfidence.VALID,
        ))
        if tid % 4 == 0:
            behaviors_pool.append(BehaviorPrimitive(
                behavior_id=f"b_{tid}",
                camera_id="cam_bench",
                track_id=tid,
                behavior_type=BehaviorType.PERSISTENT_APPROACH,
                timestamp_utc=t0,
                first_observed_utc=t0,
                last_observed_utc=t0,
                duration_seconds=2.0,
            ))

    latencies = []
    total_events_count = 0
    t_start = time.perf_counter()

    for f_idx in range(num_frames):
        ts = t0 + timedelta(milliseconds=f_idx * 33)

        t_f0 = time.perf_counter()
        events = engine.process(
            tracks=tracks_pool,
            spatial_states=spatial_pool,
            environment_state=sample_env,
            behavior_primitives=behaviors_pool,
            camera_id="cam_bench",
            timestamp_utc=ts,
        )
        t_f1 = time.perf_counter()

        latencies.append((t_f1 - t_f0) * 1000.0)
        total_events_count += len(events)

    total_time = time.perf_counter() - t_start
    mean_lat = float(np.mean(latencies))
    p95_lat = float(np.percentile(latencies, 95))
    fps = num_frames / total_time

    print("-" * 68)
    print(f"Frames Processed:           {num_frames}")
    print(f"Tracks Evaluated:           {num_frames * num_tracks}")
    print(f"Total Events Processed:     {total_events_count}")
    print(f"Active Events:              {len(engine.get_active_events('cam_bench'))}")
    print(f"Mean Latency per Frame:     {mean_lat:.4f} ms")
    print(f"P95 Latency per Frame:      {p95_lat:.4f} ms")
    print(f"Effective Fusion Throughput:{fps:.2f} FPS ({num_tracks} tracks/frame on CPU)")
    print("=" * 68)


def _make_bench_track(track_id: int, t0: datetime) -> TrackState:
    traj = [
        TrajectoryPoint(x=100.0 + track_id * 10.0, y=100.0 + f * 5.0, timestamp_utc=t0, frame_id=f)
        for f in range(5)
    ]
    curr_pos = (traj[-1].x, traj[-1].y)
    return TrackState(
        track_id=track_id,
        camera_id="cam_bench",
        class_id=TargetClass.PERSON if track_id % 3 != 0 else TargetClass.VEHICLE,
        bbox=BoundingBox(x_min=curr_pos[0] - 15, y_min=curr_pos[1] - 40, x_max=curr_pos[0] + 15, y_max=curr_pos[1]),
        center_xy=curr_pos,
        status=TrackStatus.TRACKED,
        first_seen=t0,
        last_seen=t0,
        trajectory=traj,
    )


if __name__ == "__main__":
    run_fusion_benchmark()
