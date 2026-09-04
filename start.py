"""
Production Entrypoint for IBVAP Web Service on Render / Linux Cloud.
Safely parses $PORT, binds to 0.0.0.0, and boots Uvicorn without shell-expansion failures.
"""

import os
import sys
from pathlib import Path

# Ensure repo root is in python module search path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn

if __name__ == "__main__":
    raw_port = os.environ.get("PORT", "8000")
    try:
        port = int(raw_port)
    except (ValueError, TypeError):
        port = 8000

    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[IBVAP Production Entrypoint] Launching application on {host}:{port}")
    uvicorn.run("backend.app.main:app", host=host, port=port, log_level="info")
