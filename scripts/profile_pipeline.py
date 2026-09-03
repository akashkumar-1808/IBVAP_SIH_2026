"""
Comprehensive Profiler for IBVAP Pipeline
Measures all 16 target metrics on storage/samples/test_video.mp4
"""

import sys
import time
import cv2
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
from worker.pipeline.orchestrator import LivePipelineOrchestrator, PipelineConfig, RunMode
from worker.ingestion.file_source import FileVideoSource
from backend.app.api.routes.streams import update_latest_frame, _LATEST_FRAMES
from backend.app.api.routes.ws import broadcast_telemetry_sync
from worker.spatial.schemas import ZoneType
from worker.fusion.schemas import EventPriority

def profile_pipeline(video_path: str, num_frames: int = 120, device: str = "cpu"):
    print("=" * 75)
    print(f"      IBVAP PIPELINE PERFORMANCE PROFILING (DEVICE: {device.upper()})")
    print(f"      Target Video: {video_path}")
    print(f"      Frames to Measure: {num_frames}")
    print("=" * 75)

    # 1. MP4 Open Time
    t_open_start = time.perf_counter()
    src = FileVideoSource(camera_id="PROFILE-CAM", file_path=video_path, loop=False)
    src.connect()
    t_mp4_open_ms = (time.perf_counter() - t_open_start) * 1000.0
    print(f"[1] MP4 Open Time: {t_mp4_open_ms:.2f} ms")

    # 2. Setup Orchestrator
    config = PipelineConfig(
        camera_id="PROFILE-CAM",
        file_path=video_path,
        run_mode=RunMode.HEADLESS,
        device=device,
    )
    orchestrator = LivePipelineOrchestrator(config)
    orchestrator.setup_prototype_border()
    orchestrator.initialize_source()

    metrics = {
        "frame_acquisition": [],
        "yolo_inference": [],
        "detection_filtering": [],
        "bytetrack": [],
        "spatial_reasoning": [],
        "behavior_reasoning": [],
        "fusion": [],
        "visualization": [],
        "jpeg_encoding": [],
        "websocket_broadcast": [],
        "evidence_generation": [],
        "total_latency": [],
        "frame_age": [],
    }

    evidence_times = []
    frames_processed = 0

    fps_window = []

    print("\nProcessing frames and measuring stages...")

    for i in range(num_frames):
        # Measure Frame Acquisition / Decode
        t_acq_start = time.perf_counter()
        packet = orchestrator.source.read()
        t_acq = (time.perf_counter() - t_acq_start) * 1000.0
        if packet is None:
            print(f"Reached EOF at frame {i}")
            break
        metrics["frame_acquisition"].append(t_acq)

        frame_start = time.perf_counter()
        img = packet.image
        cam_id = packet.camera_id
        ts = packet.timestamp_utc
        frame_id = packet.frame_id

        # Buffer raw frame for evidence
        orchestrator.evidence_packager.add_frame(packet)

        # Environment
        env_state = orchestrator.environment_analyzer.analyze(packet)

        # YOLO Inference
        t_yolo_start = time.perf_counter()
        raw_detections = orchestrator.detector.infer(packet)
        t_yolo = (time.perf_counter() - t_yolo_start) * 1000.0
        metrics["yolo_inference"].append(t_yolo)

        # Detection Filtering
        t_filt_start = time.perf_counter()
        camera_motion = orchestrator.camera_motion_estimator.update(img)
        filter_result = orchestrator.detection_filter.filter_detections(
            raw_detections=raw_detections,
            image_shape=img.shape,
            camera_motion=camera_motion,
        )
        operational_detections = filter_result.operational_detections
        t_filt = (time.perf_counter() - t_filt_start) * 1000.0
        metrics["detection_filtering"].append(t_filt)

        # ByteTrack
        t_track_start = time.perf_counter()
        tracks = orchestrator.tracker.update(operational_detections, camera_id=cam_id, timestamp_utc=ts, frame_id=frame_id)
        t_track = (time.perf_counter() - t_track_start) * 1000.0
        metrics["bytetrack"].append(t_track)

        # Spatial Reasoning
        t_spat_start = time.perf_counter()
        spatial_states = orchestrator.spatial_engine.process_tracks(tracks, cam_id, ts)
        t_spat = (time.perf_counter() - t_spat_start) * 1000.0
        metrics["spatial_reasoning"].append(t_spat)

        # Behavior Reasoning
        t_beh_start = time.perf_counter()
        behaviors = orchestrator.behavior_engine.process(tracks, spatial_states, ts, env_state)
        t_beh = (time.perf_counter() - t_beh_start) * 1000.0
        metrics["behavior_reasoning"].append(t_beh)

        # Fusion Engine
        t_fus_start = time.perf_counter()
        events = orchestrator.fusion_engine.process(
            tracks=tracks,
            spatial_states=spatial_states,
            environment_state=env_state,
            behavior_primitives=behaviors,
            camera_id=cam_id,
            timestamp_utc=ts,
        )
        t_fus = (time.perf_counter() - t_fus_start) * 1000.0
        metrics["fusion"].append(t_fus)

        # Evidence Generation
        t_ev_start = time.perf_counter()
        ev_count_triggered = 0
        for ev in events:
            if ev.priority in (EventPriority.HIGH, EventPriority.CRITICAL):
                matching_tr = next((t for t in tracks if t.track_id == ev.track_id), None)
                matching_sp = next((s for s in spatial_states if s.track_id == ev.track_id), None)
                if matching_tr and matching_sp and ev.duration_seconds <= 0.1:
                    ev_count_triggered += 1
                    pkg = orchestrator.evidence_packager.create_package(ev, matching_tr, matching_sp)
        t_ev = (time.perf_counter() - t_ev_start) * 1000.0
        metrics["evidence_generation"].append(t_ev)
        if ev_count_triggered > 0:
            evidence_times.append(t_ev)

        # Visualization
        t_vis_start = time.perf_counter()
        vis_img = orchestrator.visualizer.render_frame(
            frame=img,
            tracks=tracks,
            spatial_states=spatial_states,
            behavior_primitives=behaviors,
            events=events,
            environment=env_state,
            projected_border=orchestrator._latest_projected_border,
            is_calibrated=orchestrator._is_calibrated,
            fps=25.0,
            raw_detections_count=len(raw_detections),
            operational_detections_count=len(operational_detections),
            camera_motion=camera_motion,
        )
        t_vis = (time.perf_counter() - t_vis_start) * 1000.0
        metrics["visualization"].append(t_vis)

        # JPEG Encoding
        t_jpeg_start = time.perf_counter()
        update_latest_frame(cam_id, vis_img)
        t_jpeg = (time.perf_counter() - t_jpeg_start) * 1000.0
        metrics["jpeg_encoding"].append(t_jpeg)

        # WebSocket Broadcast Simulation (JSON format + sync broadcast)
        t_ws_start = time.perf_counter()
        telemetry_payload = {
            "camera_id": cam_id,
            "timestamp_utc": ts.isoformat(),
            "fps": 25.0,
            "tracks": len(tracks),
            "events": len(events),
        }
        broadcast_telemetry_sync(telemetry_payload)
        t_ws = (time.perf_counter() - t_ws_start) * 1000.0
        metrics["websocket_broadcast"].append(t_ws)

        # Total latency
        total_lat = (time.perf_counter() - frame_start) * 1000.0
        metrics["total_latency"].append(total_lat)

        # Frame age (time elapsed from packet timestamp to completion)
        frame_age = total_lat + t_acq
        metrics["frame_age"].append(frame_age)

        frames_processed += 1

    orchestrator.source.close()
    src.close()

    # Summarize Metrics
    print("\n" + "=" * 75)
    print("                 BENCHMARK RESULTS SUMMARY (16 METRICS)")
    print("=" * 75)

    def stats(arr):
        if not arr:
            return 0.0, 0.0, 0.0
        return np.mean(arr), np.min(arr), np.max(arr)

    mean_total, min_total, max_total = stats(metrics["total_latency"])
    effective_fps = 1000.0 / mean_total if mean_total > 0 else 0.0

    print(f"{'Metric':<32} | {'Mean (ms)':<10} | {'Min (ms)':<10} | {'Max (ms)':<10} | {'% Total':<8}")
    print("-" * 75)

    order = [
        ("2. Frame Acquisition / Decode", metrics["frame_acquisition"]),
        ("3. YOLO Inference", metrics["yolo_inference"]),
        ("4. Detection Filtering", metrics["detection_filtering"]),
        ("5. ByteTrack Tracking", metrics["bytetrack"]),
        ("6. Spatial Reasoning", metrics["spatial_reasoning"]),
        ("7. Behavior Reasoning", metrics["behavior_reasoning"]),
        ("8. Fusion Engine", metrics["fusion"]),
        ("9. Visualization (OpenCV HUD)", metrics["visualization"]),
        ("10. JPEG Encoding (MJPEG)", metrics["jpeg_encoding"]),
        ("11. WebSocket Broadcast", metrics["websocket_broadcast"]),
        ("12. Evidence Generation (When Act)", evidence_times),
    ]

    for name, arr in order:
        mean_v, min_v, max_v = stats(arr)
        pct = (mean_v / mean_total) * 100.0 if mean_total > 0 else 0.0
        print(f"{name:<32} | {mean_v:<10.2f} | {min_v:<10.2f} | {max_v:<10.2f} | {pct:<7.1f}%")

    print("-" * 75)
    print(f"13. Total Processing Latency:      {mean_total:.2f} ms (Min: {min_total:.2f} ms, Max: {max_total:.2f} ms)")
    print(f"14. Effective Processing FPS:      {effective_fps:.2f} FPS")
    print(f"15. Display / Output Target FPS:   25.00 FPS (Stream paced at 40ms)")
    mean_age, min_age, max_age = stats(metrics["frame_age"])
    print(f"16. Total Frame Age:               {mean_age:.2f} ms")
    print("=" * 75)

    # Sort bottlenecks
    stage_means = [
        ("YOLO Inference", np.mean(metrics["yolo_inference"])),
        ("Frame Acquisition / Decode", np.mean(metrics["frame_acquisition"])),
        ("Visualization (OpenCV HUD)", np.mean(metrics["visualization"])),
        ("JPEG Encoding (MJPEG)", np.mean(metrics["jpeg_encoding"])),
        ("Detection Filtering", np.mean(metrics["detection_filtering"])),
        ("ByteTrack Tracking", np.mean(metrics["bytetrack"])),
        ("Spatial Reasoning", np.mean(metrics["spatial_reasoning"])),
        ("Behavior Reasoning", np.mean(metrics["behavior_reasoning"])),
        ("Fusion Engine", np.mean(metrics["fusion"])),
        ("WebSocket Broadcast", np.mean(metrics["websocket_broadcast"])),
    ]
    stage_means.sort(key=lambda x: x[1], reverse=True)

    print("\nTOP 3 BOTTLENECKS IDENTIFIED:")
    for rank, (name, val) in enumerate(stage_means[:3], 1):
        pct = (val / mean_total) * 100.0
        print(f"  #{rank}: {name:<28} -> {val:.2f} ms per frame ({pct:.1f}% of total processing time)")

    return {
        "mp4_open_ms": t_mp4_open_ms,
        "effective_fps": effective_fps,
        "mean_latency_ms": mean_total,
        "mean_frame_age_ms": mean_age,
        "top3": stage_means[:3],
        "all_stages": stage_means,
    }

if __name__ == "__main__":
    profile_pipeline("storage/samples/test_video.mp4", num_frames=100, device="cpu")
