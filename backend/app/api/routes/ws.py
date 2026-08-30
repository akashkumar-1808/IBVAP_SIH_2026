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
    """Real-time bi-directional telemetry connection."""
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


def broadcast_telemetry_sync(payload: Dict[str, Any]) -> None:
    """Synchronous helper for worker loops to push telemetry."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(manager.broadcast(payload))
        else:
            loop.run_until_complete(manager.broadcast(payload))
    except RuntimeError:
        pass
