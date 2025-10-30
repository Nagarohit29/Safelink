"""
WebSocket connection manager for real-time push notifications.
Handles client connections, message broadcasting, and session lifecycle.
"""
from __future__ import annotations

import asyncio
import json
from typing import List, Dict, Any
from fastapi import WebSocket
from config.logger_config import setup_logger

logger = setup_logger("WebSocketManager")


class ConnectionManager:
    """Manages WebSocket connections and broadcasts messages to connected clients."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection from the active pool."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket client."""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast(self, message: str):
        """Broadcast a message to all connected WebSocket clients."""
        if not self.active_connections:
            return
        
        disconnected = []
        async with self._lock:
            for connection in self.active_connections[:]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.warning(f"Error broadcasting to client: {e}")
                    disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_json(self, data: Dict[str, Any]):
        """Broadcast JSON data to all connected clients."""
        await self.broadcast(json.dumps(data))
    
    def get_connection_count(self) -> int:
        """Return the number of active connections."""
        return len(self.active_connections)


# Global manager instance
manager = ConnectionManager()
