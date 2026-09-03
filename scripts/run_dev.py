"""
IBVAP — Single-Command Concurrent Development Runner.
Runs both:
1. FastAPI Backend (port 8000)
2. Vite Frontend Dev Server with HMR (port 5173)

Usage:
    python scripts/run_dev.py
"""

import sys
import subprocess
import signal
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def main():
    print("=" * 70)
    print("       IBVAP — CONCURRENT DEV LAUNCHER (BACKEND + FRONTEND)")
    print("=" * 70)
    print("1. Backend API & Stream: http://127.0.0.1:8000")
    print("2. Frontend Vite (HMR):  http://localhost:5173")
    print("=" * 70)
    print("Press Ctrl+C to stop both processes.\n")

    # 1. Start FastAPI Backend
    backend_cmd = [
        sys.executable, "-m", "uvicorn", "backend.app.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload"
    ]
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=str(PROJECT_ROOT)
    )

    # 2. Start Vite Frontend
    frontend_dir = PROJECT_ROOT / "frontend"
    # On Windows, npm is npm.cmd
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(frontend_dir)
    )

    def cleanup(sig=None, frame=None):
        print("\n[SHUTDOWN] Terminating Backend and Frontend...")
        try:
            backend_proc.terminate()
            frontend_proc.terminate()
            backend_proc.wait(timeout=3)
            frontend_proc.wait(timeout=3)
        except Exception:
            backend_proc.kill()
            frontend_proc.kill()
        print("[SHUTDOWN] Done.")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        while True:
            time.sleep(1)
            # If any process dies, exit
            if backend_proc.poll() is not None or frontend_proc.poll() is not None:
                break
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()
