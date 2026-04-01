"""
Tests for ConnectionManager and WebSocketManager.
Uses mocked WebSocket objects so no real network connections are needed.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.websocket_manager import ConnectionManager, WebSocketManager


def run(coro):
    """Run a coroutine in a fresh event loop to avoid loop pollution from anyio tests."""
    return asyncio.run(coro)


# ─── ConnectionManager ────────────────────────────────────────────────────────

class TestConnectionManager:
    def setup_method(self):
        self.mgr = ConnectionManager()

    def _mock_ws(self):
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        ws.accept = AsyncMock()
        return ws

    def test_connect_adds_user(self):
        ws = self._mock_ws()
        run(self.mgr.connect(ws, user_id=1))
        assert 1 in self.mgr.active_connections
        assert ws in self.mgr.active_connections[1]

    def test_connect_multiple_sockets_same_user(self):
        ws1, ws2 = self._mock_ws(), self._mock_ws()
        run(self.mgr.connect(ws1, user_id=5))
        run(self.mgr.connect(ws2, user_id=5))
        assert len(self.mgr.active_connections[5]) == 2

    def test_disconnect_removes_socket(self):
        ws = self._mock_ws()
        run(self.mgr.connect(ws, user_id=2))
        run(self.mgr.disconnect(ws, user_id=2))
        assert 2 not in self.mgr.active_connections

    def test_disconnect_non_existent_user(self):
        ws = self._mock_ws()
        # Should not raise
        run(self.mgr.disconnect(ws, user_id=999))

    def test_join_room(self):
        run(self.mgr.join_room(user_id=3, room_id="security_alerts"))
        assert 3 in self.mgr.rooms["security_alerts"]

    def test_join_room_multiple_users(self):
        run(self.mgr.join_room(1, "room1"))
        run(self.mgr.join_room(2, "room1"))
        assert len(self.mgr.rooms["room1"]) == 2

    def test_leave_room_removes_user(self):
        run(self.mgr.join_room(4, "room2"))
        run(self.mgr.leave_room(4, "room2"))
        assert "room2" not in self.mgr.rooms

    def test_leave_room_non_existent(self):
        # Should not raise
        run(self.mgr.leave_room(99, "nonexistent_room"))

    def test_leave_room_partial(self):
        run(self.mgr.join_room(1, "room3"))
        run(self.mgr.join_room(2, "room3"))
        run(self.mgr.leave_room(1, "room3"))
        assert 2 in self.mgr.rooms["room3"]
        assert 1 not in self.mgr.rooms["room3"]

    def test_send_personal_message_to_connected_user(self):
        ws = self._mock_ws()
        run(self.mgr.connect(ws, user_id=10))
        run(self.mgr.send_personal_message({"type": "test"}, user_id=10))
        ws.send_json.assert_called_once_with({"type": "test"})

    def test_send_personal_message_no_connection(self):
        # Should not raise when user is not connected
        run(self.mgr.send_personal_message({"type": "test"}, user_id=999))

    def test_send_personal_message_cleans_up_failed_socket(self):
        ws = self._mock_ws()
        ws.send_json.side_effect = Exception("connection closed")
        run(self.mgr.connect(ws, user_id=11))
        # Should not raise; socket should be cleaned up
        run(self.mgr.send_personal_message({"type": "test"}, user_id=11))
        # After failed send, user should be disconnected
        assert 11 not in self.mgr.active_connections

    def test_broadcast_to_room(self):
        ws1, ws2 = self._mock_ws(), self._mock_ws()
        run(self.mgr.connect(ws1, user_id=20))
        run(self.mgr.connect(ws2, user_id=21))
        run(self.mgr.join_room(20, "test_room"))
        run(self.mgr.join_room(21, "test_room"))
        run(self.mgr.broadcast_to_room({"type": "broadcast"}, "test_room"))
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    def test_broadcast_to_room_no_such_room(self):
        # Should not raise
        run(self.mgr.broadcast_to_room({"type": "test"}, "nonexistent"))

    def test_broadcast_to_all(self):
        ws1, ws2 = self._mock_ws(), self._mock_ws()
        run(self.mgr.connect(ws1, user_id=30))
        run(self.mgr.connect(ws2, user_id=31))
        run(self.mgr.broadcast_to_all({"type": "system"}))
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    def test_get_connected_users(self):
        ws = self._mock_ws()
        run(self.mgr.connect(ws, user_id=40))
        assert 40 in self.mgr.get_connected_users()

    def test_is_user_connected_true(self):
        ws = self._mock_ws()
        run(self.mgr.connect(ws, user_id=50))
        assert self.mgr.is_user_connected(50) is True

    def test_is_user_connected_false(self):
        assert self.mgr.is_user_connected(999) is False


# ─── WebSocketManager (high-level) ───────────────────────────────────────────

class TestWebSocketManager:
    def setup_method(self):
        self.mgr = WebSocketManager()
        # Replace the connection manager with a mock
        self.mgr.connection_manager = MagicMock()
        self.mgr.connection_manager.send_personal_message = AsyncMock()
        self.mgr.connection_manager.broadcast_to_room = AsyncMock()
        self.mgr.connection_manager.broadcast_to_all = AsyncMock()

    def test_send_alert_notification_broadcast(self):
        run(self.mgr.send_alert_notification(
            alert_id=1,
            alert_data={"title": "Intruder", "severity": "Critical"},
        ))
        self.mgr.connection_manager.broadcast_to_room.assert_called_once()
        args = self.mgr.connection_manager.broadcast_to_room.call_args
        assert args[0][1] == "security_alerts"

    def test_send_alert_notification_targeted(self):
        run(self.mgr.send_alert_notification(
            alert_id=2,
            alert_data={"title": "Alert"},
            user_ids=[5, 6],
        ))
        assert self.mgr.connection_manager.send_personal_message.call_count == 2

    def test_send_alert_update_broadcast(self):
        run(self.mgr.send_alert_update(
            alert_id=3, action="acknowledged",
            alert_data={"status": "acknowledged"},
        ))
        self.mgr.connection_manager.broadcast_to_room.assert_called_once()

    def test_send_alert_update_targeted(self):
        run(self.mgr.send_alert_update(
            alert_id=4, action="closed",
            alert_data={},
            user_ids=[7],
        ))
        self.mgr.connection_manager.send_personal_message.assert_called_once()

    def test_send_case_update_broadcast(self):
        run(self.mgr.send_case_update(
            case_id=10, action="updated", case_data={"status": "open"}
        ))
        self.mgr.connection_manager.broadcast_to_room.assert_called_once()
        args = self.mgr.connection_manager.broadcast_to_room.call_args
        assert args[0][1] == "cases"

    def test_send_case_update_targeted(self):
        run(self.mgr.send_case_update(
            case_id=11, action="closed", case_data={}, user_ids=[8, 9]
        ))
        assert self.mgr.connection_manager.send_personal_message.call_count == 2

    def test_send_movement_update(self):
        run(self.mgr.send_movement_update(
            movement_id=100, action="updated", movement_data={"status": "in_transit"}
        ))
        self.mgr.connection_manager.broadcast_to_room.assert_called_once()
        args = self.mgr.connection_manager.broadcast_to_room.call_args
        assert args[0][1] == "movements"

    def test_send_sla_breach_notification(self):
        run(self.mgr.send_sla_breach_notification(
            alert_id=20, alert_data={"breach_type": "demurrage"}
        ))
        self.mgr.connection_manager.broadcast_to_room.assert_called_once()
        args = self.mgr.connection_manager.broadcast_to_room.call_args
        assert args[0][1] == "supervisors"

    def test_send_system_notification(self):
        run(self.mgr.send_system_notification(
            title="System Maintenance",
            message_text="Scheduled downtime at 2am",
            priority="high",
        ))
        self.mgr.connection_manager.broadcast_to_all.assert_called_once()
        msg = self.mgr.connection_manager.broadcast_to_all.call_args[0][0]
        assert msg["type"] == "system"
        assert msg["priority"] == "high"
        assert msg["data"]["title"] == "System Maintenance"
