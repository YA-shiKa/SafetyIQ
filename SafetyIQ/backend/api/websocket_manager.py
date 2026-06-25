"""
SafetyIQ — WebSocket Connection Manager
=========================================
Manages all active WebSocket connections and broadcasts.
Extracted from main.py so it can be imported by route modules
without circular imports.

Author: SafetyIQ Team
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Thread-safe WebSocket connection pool.

    Manages connect/disconnect lifecycle and fan-out broadcasts.
    Production: replace with Redis pub/sub for multi-worker deployments.
    """

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Remaining: {len(self.active_connections)}")

    async def send_personal(self, data: dict[str, Any], websocket: WebSocket):
        """Send a message to a single connection."""
        try:
            await websocket.send_text(json.dumps(data, default=str))
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")
            self.disconnect(websocket)

    async def broadcast(self, data: dict[str, Any]):
        """
        Broadcast to all active connections.
        Dead connections are automatically pruned.
        """
        dead: list[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(data, default=str))
            except Exception:
                dead.append(connection)

        for d in dead:
            self.disconnect(d)

        if dead:
            logger.warning(f"Pruned {len(dead)} dead WebSocket connection(s).")

    async def broadcast_alert(self, alert: dict[str, Any]):
        """Convenience: broadcast an alert event with typed envelope."""
        await self.broadcast({
            "type": "ALERT",
            "alert": alert,
        })

    async def broadcast_risk_update(self, plant_risk_score: int, zone_scores: list[dict]):
        """Broadcast plant risk score and zone-level scores."""
        await self.broadcast({
            "type": "RISK_UPDATE",
            "plant_risk_score": plant_risk_score,
            "zones": zone_scores,
        })

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


# Singleton — import this everywhere instead of creating new instances
ws_manager = ConnectionManager()