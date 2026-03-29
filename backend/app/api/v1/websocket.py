"""
WebSocket Routes for Real-time Notifications
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_user_from_token(token: str, db: Session) -> User:
    """Validate token and return user"""
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        if not username:
            return None

        user = db.query(User).filter(User.username == username).first()
        return user if user and user.is_active else None
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return None


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time notifications.

    Authentication flow (token is NOT passed in the URL):
    1. Connect: ws://host/api/v1/ws/notifications
    2. Immediately send: {"action": "auth", "token": "<jwt>"}
    3. Server responds with welcome message or closes with code 4001.
    """
    # Accept the connection so we can receive the auth message
    await websocket.accept()

    # Step 1: Receive auth token as first message (10-second window)
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        auth = json.loads(raw)
        token = auth.get("token", "")
    except asyncio.TimeoutError:
        await websocket.close(code=4008, reason="Authentication timeout")
        return
    except (json.JSONDecodeError, Exception):
        await websocket.close(code=4001, reason="Invalid auth message — expected JSON {\"action\":\"auth\",\"token\":\"...\"}")
        return

    # Step 2: Validate the token
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Step 3: Register with the connection manager
    await ws_manager.connect(websocket, user.id)
    logger.info(f"WebSocket connected: user {user.username}")

    # Join default rooms based on role
    await ws_manager.join_room(user.id, "all_users")

    if user.role in ["security_lead", "supervisor", "admin"]:
        await ws_manager.join_room(user.id, "security_alerts")
        await ws_manager.join_room(user.id, "cases")

    if user.role in ["supervisor", "admin"]:
        await ws_manager.join_room(user.id, "supervisors")

    if user.role in ["operator", "supervisor", "admin"]:
        await ws_manager.join_room(user.id, "movements")

    # Send welcome message
    await ws_manager.send_personal_message(
        {
            "type": "system",
            "action": "connected",
            "message": f"Welcome {user.username}! Real-time notifications active.",
            "user_id": user.id,
            "role": user.role
        },
        user.id
    )

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "ping":
                    # Keep-alive ping
                    await ws_manager.send_personal_message(
                        {"type": "pong", "timestamp": message.get("timestamp")},
                        user.id
                    )

                elif action == "subscribe":
                    # Subscribe to a room
                    room = message.get("room")
                    if room:
                        await ws_manager.join_room(user.id, room)
                        await ws_manager.send_personal_message(
                            {"type": "subscribed", "room": room},
                            user.id
                        )

                elif action == "unsubscribe":
                    # Unsubscribe from a room
                    room = message.get("room")
                    if room:
                        await ws_manager.leave_room(user.id, room)
                        await ws_manager.send_personal_message(
                            {"type": "unsubscribed", "room": room},
                            user.id
                        )

            except json.JSONDecodeError:
                await ws_manager.send_personal_message(
                    {"type": "error", "message": "Invalid JSON format"},
                    user.id
                )

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, user.id)
        logger.info(f"WebSocket disconnected: user {user.username}")


@router.get("/connections")
async def get_active_connections(
    db: Session = Depends(get_db)
):
    """Get count of active WebSocket connections (admin only)"""
    connected_users = ws_manager.get_connected_users()
    return {
        "active_connections": len(connected_users),
        "connected_user_ids": connected_users
    }
