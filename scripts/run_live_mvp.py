"""
IBVAP — Live MVP Execution CLI Entrypoint.

Connects the full 9-stage intelligence pipeline to a physical live RTSP camera or test stream.

Usage:
  python scripts/run_live_mvp.py --rtsp-url rtsp://user:pass@192.168.1.50:554/stream1 --visual
  python scripts/run_live_mvp.py --video-file samples/border_breach.mp4 --record-debug
  python scripts/run_live_mvp.py --synthetic --max-runtime 10 --headless

Environment Variables:
  IBVAP_RTSP_URL           RTSP stream URL (credentials are automatically masked in logs)
  IBVAP_CAMERA_ID          Camera identifier (default: LIVE-01)
  IBVAP_RUN_ID             Unique execution run ID
  IBVAP_DISPLAY            Execution mode: headless | visual | record_debug
  IBVAP_MAX_RUNTIME_SECONDS Maximum runtime in seconds before auto-shutdown

Architecture Decision: DEC-0010
"""

import os
import sys
import argparse
import signal
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from worker.pipeline import (
    LivePipelineOrchestrator,
    PipelineConfig,
    RunMode,
)
from worker.ingestion import mask_rtsp_url


def parse_arguments() -> PipelineConfig:
    """Parses CLI arguments with fallback to environment variables."""
    parser = argparse.ArgumentParser(
        description="IBVAP Live MVP Execution Pipeline (Headless / Visual / Record)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Ingestion Source
    parser.add_argument("--rtsp-url", "-u", type=str, default=os.getenv("IBVAP_RTSP_URL"),
                        help="RTSP camera stream URL (or set IBVAP_RTSP_URL env var)")
    parser.add_argument("--video-file", "-f", type=str, default=None,
                        help="Path to offline MP4 video file for testing")
    parser.add_argument("--synthetic", action="store_true",
                        help="Generate a synthetic live camera stream for integration testing")

    # Camera & Execution Identifiers
    parser.add_argument("--camera-id", "-c", type=str, default=os.getenv("IBVAP_CAMERA_ID", "LIVE-01"),
                        help="Camera ID")
    parser.add_argument("--run-id", type=str, default=os.getenv("IBVAP_RUN_ID"),
                        help="Execution Run ID")

    # Execution Modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--headless", action="store_true", help="Run without GUI (terminal status only)")
    mode_group.add_argument("--visual", "-v", action="store_true", help="Open real-time OpenCV analytical overlay window")
    mode_group.add_argument("--record-debug", "-r", action="store_true", help="Record annotated OpenCV video to results/live_runs/")

    # Limits and Tuning
    parser.add_argument("--max-runtime", "-t", type=float, default=float(os.getenv("IBVAP_MAX_RUNTIME_SECONDS", "0")) or None,
                        help="Maximum runtime in seconds before stopping")
    parser.add_argument("--status-interval", "-s", type=float, default=1.0,
                        help="Interval in seconds for terminal status print")
    parser.add_argument("--model-path", "-m", type=str, default="yolov8n.pt",
                        help="YOLO model checkpoint path")
    parser.add_argument("--device", "-d", type=str, default="cpu",
                        help="Inference device: cpu | cuda")
    parser.add_argument("--conf", type=float, default=0.40,
                        help="Detection confidence threshold")
    parser.add_argument("--queue-size", type=int, default=30,
                        help="Bounded ingestion frame queue size")

    args = parser.parse_args()

    # Determine Run Mode
    env_display = os.getenv("IBVAP_DISPLAY", "").lower()
    if args.visual or env_display == "visual":
        run_mode = RunMode.VISUAL
    elif args.record_debug or env_display in ("record", "record_debug"):
        run_mode = RunMode.RECORD_DEBUG
    else:
        run_mode = RunMode.HEADLESS

    # Validate Source
    if not args.rtsp_url and not args.video_file and not args.synthetic:
        # Check if an existing sample exists for fallback
        sample_path = PROJECT_ROOT / "storage" / "samples" / "border_breach_sample.mp4"
        if sample_path.exists():
            print(f"[INFO] No RTSP URL supplied. Falling back to sample video: {sample_path}")
            args.video_file = str(sample_path)
        else:
            print("[INFO] No RTSP URL or video file provided. Defaulting to synthetic live test source.")
            args.synthetic = True

    return PipelineConfig(
        camera_id=args.camera_id,
        run_id=args.run_id,
        rtsp_url=args.rtsp_url,
        file_path=args.video_file,
        synthetic_stream=args.synthetic,
        run_mode=run_mode,
        max_runtime_seconds=args.max_runtime,
        status_interval_seconds=args.status_interval,
        queue_max_size=args.queue_size,
        model_path=args.model_path,
        device=args.device,
        detection_confidence=args.conf,
    )


def main():
    config = parse_arguments()

    orchestrator = LivePipelineOrchestrator(config)

    # Configure Prototype World Border Calibration
    orchestrator.setup_prototype_border()

    # Signal Handling for Clean Shutdown
    def _signal_handler(sig, frame):
        print("\n[SIGNAL] Interrupt received. Terminating orchestrator cleanly...")
        orchestrator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Initialize Video Source
    if config.synthetic_stream:
        # Create a synthetic source by writing a temporary MP4
        import cv2
        import numpy as np
        temp_synthetic_mp4 = orchestrator.run_output_dir / "synthetic_stream.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(temp_synthetic_mp4), fourcc, 25.0, (640, 480))
        for f in range(120):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.rectangle(frame, (0, 0), (640, 240), (40, 50, 40), -1)
            cv2.rectangle(frame, (0, 240), (640, 480), (30, 30, 50), -1)
            cv2.line(frame, (0, 240), (640, 240), (0, 0, 255), 2)
            tx, ty = 320, int(80 + f * 3)
            cv2.rectangle(frame, (tx - 15, ty - 40), (tx + 15, ty), (0, 255, 255), 2)
            cv2.circle(frame, (tx, ty), 4, (0, 255, 0), -1)
            cv2.putText(frame, f"{config.camera_id} | F:{f}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            writer.write(frame)
        writer.release()
        orchestrator.config.file_path = str(temp_synthetic_mp4)

    try:
        orchestrator.initialize_source()
    except Exception as e:
        print(f"\n[FATAL] Failed to initialize video source: {e}", file=sys.stderr)
        sys.exit(1)

    # Run Pipeline
    metrics = orchestrator.run()

    print("\n" + "=" * 60)
    print("   IBVAP LIVE RUN COMPLETE")
    print("=" * 60)
    print(f"Run ID:            {metrics.run_id}")
    print(f"Frames Processed:  {metrics.frames_processed}")
    print(f"Effective FPS:     {metrics.effective_fps:.2f}")
    print(f"Events Emitted:    {metrics.total_events_generated}")
    print(f"Evidence Packages: {metrics.total_evidence_packages}")
    print(f"Report Directory:  {orchestrator.run_output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
