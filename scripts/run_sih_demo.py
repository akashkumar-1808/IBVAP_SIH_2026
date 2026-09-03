"""
IBVAP — Single-Command Deterministic SIH Jury Demo Launcher.

Starts the full stack with ONE command:
1. Launches FastAPI Backend with mounted React Operator Console
2. Automatically registers and starts the real 9-stage AI Pipeline on the input MP4 video
3. Evaluates real YOLOv8n detections, ByteTrack tracks, spatial border crossing, behaviors,
   multi-modal fusion events, and cryptographic evidence packaging
4. Opens http://localhost:8000/console in the default web browser

Usage:
    python scripts/run_sih_demo.py --video storage/samples/test_video.mp4
    python scripts/run_sih_demo.py --video storage/samples/test_video5.mp4 --device cuda
"""

import os
import sys
import time
import signal
import argparse
import webbrowser
import threading
import urllib.request
import json
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def wait_for_server(url: str, timeout_sec: float = 20.0) -> bool:
    """Polls backend health endpoint until online."""
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    parser = argparse.ArgumentParser(
        description="IBVAP Real MP4 SIH Demo Launcher",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--video", "-v",
        type=str,
        default="storage/samples/test_video.mp4",
        help="Path to input recorded MP4 video file",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Server port",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Server bind host",
    )
    parser.add_argument(
        "--device", "-d",
        type=str,
        default="cpu",
        help="Inference device: 'cpu' or 'cuda'",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser automatically",
    )

    args = parser.parse_args()

    # 1. Validate Video Path
    video_path = Path(args.video)
    if not video_path.is_absolute():
        video_path = PROJECT_ROOT / video_path

    if not video_path.exists():
        print(f"\n[ERROR] Video file not found: {video_path}")
        print("Please provide a valid MP4 file with --video <path>.\n")
        sys.exit(1)

    print("=" * 75)
    print("      IBVAP — REAL MP4 END-TO-END SIH DEMO RUNNER")
    print("=" * 75)
    print(f"Input MP4 Video:      {video_path}")
    print(f"Server Address:       http://{args.host}:{args.port}")
    print(f"Operator Console:     http://localhost:{args.port}/console")
    print(f"Inference Device:     {args.device.upper()}")
    print("=" * 75)

    # 2. Start Uvicorn Server in Background Thread
    import uvicorn
    from backend.app.main import app

    config = uvicorn.Config(
        app=app,
        host=args.host,
        port=args.port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, name="Uvicorn-Server", daemon=True)
    server_thread.start()

    # 3. Wait for Server to be Healthy
    health_url = f"http://{args.host}:{args.port}/health"
    print("\nStarting backend server...")
    if not wait_for_server(health_url, timeout_sec=25.0):
        print(f"[FATAL] Backend server failed to start on http://{args.host}:{args.port}")
        sys.exit(1)
    print("[OK] Backend server is online.")

    # 4. Connect Camera with the MP4 Video File
    connect_url = f"http://{args.host}:{args.port}/api/v1/cameras/connect"
    payload = json.dumps({
        "camera_id": "DEMO-CAM-01",
        "name": "SIH Recorded Breach Demo",
        "video_file_path": str(video_path),
        "sector_id": "SECTOR-B07",
        "sector_name": "Northern Border Sector",
        "device": args.device,
    }).encode("utf-8")

    req = urllib.request.Request(
        connect_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            conn_res = json.loads(resp.read().decode("utf-8"))
            print(f"[OK] Camera connected: {conn_res.get('message')}")
    except Exception as exc:
        print(f"[FATAL] Failed to connect camera: {exc}")
        server.should_exit = True
        sys.exit(1)

    # 5. Open Web Browser to Operator Console
    console_url = f"http://localhost:{args.port}/console"
    if not args.no_browser:
        print(f"\nOpening Operator Console in your browser: {console_url}")
        time.sleep(1.0)
        webbrowser.open(console_url)
    else:
        print(f"\nConsole available at: {console_url}")

    print("\n" + "=" * 75)
    print("PIPELINE IS LIVE! The real AI pipeline is processing frames.")
    print("Watch the Operator Console for real detections, tracks, crossing, and evidence.")
    print("Press Ctrl+C in this terminal to stop.")
    print("=" * 75 + "\n")

    # 6. Keep-Alive and Clean Shutdown Loop
    def _sig_handler(sig, frame):
        print("\n\nShutting down IBVAP Demo...")
        server.should_exit = True
        time.sleep(0.5)
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    try:
        while not server.should_exit:
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        server.should_exit = True
        print("Demo stopped.")


if __name__ == "__main__":
    main()
