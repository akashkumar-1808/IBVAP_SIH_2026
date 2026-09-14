"""
WebSocket telemetry stream endpoint delivering high-frequency perception,
tracking, spatial, behavior, and event updates to the React Operator Console.

Architecture Decision: DEC-0010 / DEC-0011
"""

import json
import logging
import asyncio
from typing import List, Set, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket Telemetry"])


class ConnectionManager:
    """Manages active operator console WebSocket connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._latest_telemetry: Dict[str, Any] = {}

    async def connect(self, websocket: WebSocket):
        global _MAIN_LOOP
        if _MAIN_LOOP is None:
            try:
                _MAIN_LOOP = asyncio.get_running_loop()
            except Exception:
                pass
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Operator console connected. Total active sessions: {len(self.active_connections)}")
        # Send latest known telemetry immediately upon connection
        if self._latest_telemetry:
            try:
                await websocket.send_text(json.dumps(self._latest_telemetry))
            except Exception:
                pass

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"Operator console disconnected. Total active sessions: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        self._latest_telemetry = message
        if not self.active_connections:
            return
        payload = json.dumps(message)
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.active_connections.discard(dead)


manager = ConnectionManager()


@router.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """Real-time bi-directional telemetry connection with prototype API authentication."""
    from ...config import settings
    from fastapi import status

    if settings.get_api_key_value():
        # Check query parameter (?api_key=... or ?token=...)
        token = websocket.query_params.get("api_key") or websocket.query_params.get("token")
        if not token:
            token = websocket.headers.get("x-api-key")
        if not token:
            auth_h = websocket.headers.get("authorization", "")
            if auth_h.startswith("Bearer "):
                token = auth_h[7:].strip()

        if not settings.verify_api_token(token):
            logger.warning("[WebSocket] Connection rejected: unauthorized API token.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
            return

    await manager.connect(websocket)
    try:
        while True:
            # Keep-alive receive loop
            data = await websocket.receive_text()
            # Handle client ping or operator ack commands if sent via WS
    except WebSocketDisconnect:
        manager.disconnect(websocket)

    except Exception as exc:
        logger.warning(f"WebSocket session closed: {exc}")
        manager.disconnect(websocket)


_MAIN_LOOP: Any = None


def set_main_event_loop(loop: Any) -> None:
    global _MAIN_LOOP
    _MAIN_LOOP = loop


def broadcast_telemetry_sync(payload: Dict[str, Any]) -> None:
    """Thread-safe helper for background worker loops to push telemetry."""
    global _MAIN_LOOP
    try:
        if _MAIN_LOOP and not _MAIN_LOOP.is_closed() and _MAIN_LOOP.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(payload), _MAIN_LOOP)
        else:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(manager.broadcast(payload))
            except RuntimeError:
                pass
    except Exception as e:
        logger.debug(f"Telemetry broadcast warning: {e}")
