import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np

from worker.ingestion import FileVideoSource, BoundedFrameQueue
from worker.perception import ObjectDetector
from worker.tracking import ByteTrackTracker, draw_tracks
from worker.environment import EnvironmentAnalyzer


def run_pipeline(
    video_path: str,
    output_path: str = "storage/output/annotated_output.mp4",
    show_window: bool = True,
    confidence_threshold: float = 0.35,
    max_frames: int = 0,
):
    if not os.path.exists(video_path):
        print(f"\n[ERROR] Video file not found at: {video_path}")
        print("Please place your video file at that location or specify the path using --video <path>.\n")
        return

    print("=" * 70)
    print("      IBVAP — AI Video Analytics Pipeline Prototype Runner")
    print("=" * 70)
    print(f"Input Video:        {video_path}")
    print(f"Output Video:       {output_path}")
    print(f"Confidence Thresh:  {confidence_threshold}")
    print("=" * 70)

    # 1. Initialize Ingestion Subsystem (Phase 2)
    source = FileVideoSource(
        camera_id="cam_demo_01",
        file_path=video_path,
        loop=False,
        realtime_pacing=False,
    )
    if not source.connect():
        print(f"[ERROR] Could not open video file: {video_path}")
        return

    meta = source.get_metadata()
    width = meta["width"]
    height = meta["height"]
    fps = meta["fps"] or 25.0
    total_frames = meta["total_frames"]
    print(f"Video Specs: {width}x{height} @ {fps:.1f} FPS | Total Frames: {total_frames}")

    queue = BoundedFrameQueue(max_size=30)

    # 2. Initialize Baseline Perception Detector (Phase 3)
    print("\nLoading Object Detector (YOLOv8n)...")
    detector = ObjectDetector(confidence_threshold=confidence_threshold)
    detector.load()
    detector.warmup(input_size=(width, height))

    # 3. Initialize Multi-Object Tracker (Phase 4)
    print("Initializing ByteTrack Multi-Object Tracker...")
    tracker = ByteTrackTracker(camera_id="cam_demo_01", min_hits=2, max_lost_frames=30)

    # 4. Initialize Environment Engine (Phase 5)
    print("Initializing Environment Engine...")
    env_analyzer = EnvironmentAnalyzer()

    # Setup Video Writer for output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print("\nStarting Pipeline Execution (Press 'q' in window to stop)...")
    print("-" * 70)

    frame_idx = 0
    start_time = time.perf_counter()

    try:
        while True:
            # Phase 2: Ingestion
            pkt = source.read()
            if pkt is None:
                break

            queue.put(pkt)
            frame_pkt = queue.get(timeout=0.1)
            if frame_pkt is None:
                continue

            frame_idx += 1
            if max_frames > 0 and frame_idx > max_frames:
                break

            t0 = time.perf_counter()

            # Phase 5: Environment Observation
            env_state = env_analyzer.analyze(frame_pkt)

            # Phase 3: Object Detection
            detections = detector.infer(frame_pkt)

            # Phase 4: Multi-Object Tracking
            tracks = tracker.update(
                detections=detections,
                frame_id=frame_pkt.frame_id,
                timestamp_utc=frame_pkt.timestamp_utc,
                camera_id=frame_pkt.camera_id,
            )

            dt_ms = (time.perf_counter() - t0) * 1000.0
            current_fps = 1000.0 / dt_ms if dt_ms > 0 else 0.0

            # Render Tracking & Bounding Box Overlays
            annotated = draw_tracks(frame_pkt.image, tracks, draw_trajectory=True)

            # Render Telemetry HUD Overlay (Top-Left Bar)
            hud_bg_w = 420
            hud_bg_h = 105
            overlay = annotated.copy()
            cv2.rectangle(overlay, (10, 10), (10 + hud_bg_w, 10 + hud_bg_h), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, annotated, 0.3, 0, annotated)

            # Text Lines on HUD
            cv2.putText(
                annotated,
                f"IBVAP AI Engine | Frame {frame_idx}/{total_frames} ({current_fps:.1f} FPS)",
                (20, 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 255),
                1,
                cv2.LINE_AA,
            )
            cv2.putText(
                annotated,
                f"Environment: {env_state.lighting.value.upper()} | Quality: {env_state.visibility.value.upper()} ({env_state.quality_score:.2f})",
                (20, 56),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.50,
                (0, 255, 0),
                1,
                cv2.LINE_AA,
            )
            active_tracks = len([t for t in tracks if t.status.value == "tracked"])
            cv2.putText(
                annotated,
                f"Detections: {len(detections)} | Active Tracks: {active_tracks} | Blur: {env_state.blur_score:.1f}",
                (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.50,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            cv2.putText(
                annotated,
                f"Luminance: {env_state.brightness:.2f} | Contrast: {env_state.contrast:.2f} | Noise: {env_state.noise_estimate:.3f}",
                (20, 102),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (200, 200, 200),
                1,
                cv2.LINE_AA,
            )

            # Save annotated frame to output video file
            writer.write(annotated)

            # Optional Live Window Display
            if show_window:
                cv2.imshow("IBVAP AI Engine Prototype Preview", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    print("\nProcessing stopped by user (key 'q').")
                    break

            if frame_idx % 30 == 0 or frame_idx == total_frames:
                print(f"Processed Frame {frame_idx}/{total_frames} | Detections: {len(detections)} | Active Tracks: {active_tracks} | Throughput: {current_fps:.1f} FPS")

    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    finally:
        total_time = time.perf_counter() - start_time
        avg_fps = frame_idx / total_time if total_time > 0 else 0.0

        source.close()
        queue.close()
        detector.close()
        tracker.close()
        env_analyzer.close()
        writer.release()
        if show_window:
            cv2.destroyAllWindows()

        print("=" * 70)
        print(f"Pipeline Completed:")
        print(f"Total Frames Processed: {frame_idx}")
        print(f"Total Time Taken:       {total_time:.2f}s")
        print(f"Average Pipeline FPS:   {avg_fps:.2f} FPS")
        print(f"Annotated Video Saved:  {os.path.abspath(output_path)}")
        print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run IBVAP Video Analytics Pipeline Prototype")
    parser.add_argument(
        "--video",
        type=str,
        default="storage/samples/test_video.mp4",
        help="Path to input video file (e.g. storage/samples/test_video.mp4)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="storage/output/annotated_output.mp4",
        help="Path to save annotated output video",
    )
    parser.add_argument(
        "--no-window",
        action="store_true",
        help="Disable GUI display window (recommended for headless or background execution)",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.35,
        help="Detector confidence threshold (default: 0.35)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Maximum frames to process (0 = all frames)",
    )

    args = parser.parse_args()
    run_pipeline(
        video_path=args.video,
        output_path=args.output,
        show_window=not args.no_window,
        confidence_threshold=args.conf,
        max_frames=args.max_frames,
    )
