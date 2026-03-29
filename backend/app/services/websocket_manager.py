"""
WebSocket Manager for Real-time Notifications
"""

import logging
from typing import Dict, List, Set, Any, Optional
from datetime import datetime, timezone
from fastapi import WebSocket
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        # Map of user_id to set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Map of room_id to set of user_ids (for broadcast groups)
        self.rooms: Dict[str, Set[int]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    async def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection"""
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def join_room(self, user_id: int, room_id: str):
        """Add a user to a room for group broadcasts"""
        async with self._lock:
            if room_id not in self.rooms:
                self.rooms[room_id] = set()
            self.rooms[room_id].add(user_id)
        logger.debug(f"User {user_id} joined room {room_id}")

    async def leave_room(self, user_id: int, room_id: str):
        """Remove a user from a room"""
        async with self._lock:
            if room_id in self.rooms:
                self.rooms[room_id].discard(user_id)
                if not self.rooms[room_id]:
                    del self.rooms[room_id]
        logger.debug(f"User {user_id} left room {room_id}")

    async def send_personal_message(
        self,
        message: Dict[str, Any],
        user_id: int
    ):
        """Send a message to a specific user"""
        if user_id not in self.active_connections:
            logger.debug(f"User {user_id} not connected, message not sent")
            return

        disconnected = []
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for ws in disconnected:
            await self.disconnect(ws, user_id)

    async def broadcast_to_room(
        self,
        message: Dict[str, Any],
        room_id: str
    ):
        """Broadcast a message to all users in a room"""
        if room_id not in self.rooms:
            return

        for user_id in self.rooms[room_id]:
            await self.send_personal_message(message, user_id)

    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast a message to all connected users"""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)

    def get_connected_users(self) -> List[int]:
        """Get list of connected user IDs"""
        return list(self.active_connections.keys())

    def is_user_connected(self, user_id: int) -> bool:
        """Check if a user has active connections"""
        return user_id in self.active_connections


# Global connection manager instance
ws_manager = ConnectionManager()


class WebSocketManager:
    """High-level WebSocket manager for SIRA notifications"""

    def __init__(self):
        self.connection_manager = ws_manager

    async def send_alert_notification(
        self,
        alert_id: int,
        alert_data: Dict[str, Any],
        user_ids: Optional[List[int]] = None
    ):
        """Send alert notification to specific users or broadcast"""
        message = {
            "type": "alert",
            "action": "created",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "alert_id": alert_id,
                **alert_data
            }
        }

        if user_ids:
            for user_id in user_ids:
                await self.connection_manager.send_personal_message(message, user_id)
        else:
            # Broadcast to security room
            await self.connection_manager.broadcast_to_room(message, "security_alerts")

    async def send_alert_update(
        self,
        alert_id: int,
        action: str,
        alert_data: Dict[str, Any],
        user_ids: Optional[List[int]] = None
    ):
        """Send alert status update"""
        message = {
            "type": "alert",
            "action": action,  # acknowledged, assigned, closed, etc.
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "alert_id": alert_id,
                **alert_data
            }
        }

        if user_ids:
            for user_id in user_ids:
                await self.connection_manager.send_personal_message(message, user_id)
        else:
            await self.connection_manager.broadcast_to_room(message, "security_alerts")

    async def send_case_update(
        self,
        case_id: int,
        action: str,
        case_data: Dict[str, Any],
        user_ids: Optional[List[int]] = None
    ):
        """Send case update notification"""
        message = {
            "type": "case",
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "case_id": case_id,
                **case_data
            }
        }

        if user_ids:
            for user_id in user_ids:
                await self.connection_manager.send_personal_message(message, user_id)
        else:
            await self.connection_manager.broadcast_to_room(message, "cases")

    async def send_movement_update(
        self,
        movement_id: int,
        action: str,
        movement_data: Dict[str, Any]
    ):
        """Send movement status update"""
        message = {
            "type": "movement",
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "movement_id": movement_id,
                **movement_data
            }
        }
        await self.connection_manager.broadcast_to_room(message, "movements")

    async def send_sla_breach_notification(
        self,
        alert_id: int,
        alert_data: Dict[str, Any]
    ):
        """Send SLA breach notification"""
        message = {
            "type": "sla_breach",
            "action": "breached",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "priority": "urgent",
            "data": {
                "alert_id": alert_id,
                **alert_data
            }
        }
        # Broadcast to all supervisors and admins
        await self.connection_manager.broadcast_to_room(message, "supervisors")

    async def send_system_notification(
        self,
        title: str,
        message_text: str,
        priority: str = "normal"
    ):
        """Send system-wide notification"""
        message = {
            "type": "system",
            "action": "notification",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "priority": priority,
            "data": {
                "title": title,
                "message": message_text
            }
        }
        await self.connection_manager.broadcast_to_all(message)
