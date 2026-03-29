"""
Notification Service
Unified notification handling for WebSocket, Email, and database logging
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationPreference
from app.models.user import User
from app.services.websocket_manager import WebSocketManager
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Unified notification service that handles:
    - Real-time WebSocket notifications
    - Email notifications
    - Notification history/logging
    - User preferences
    """

    def __init__(self, db: Session):
        self.db = db
        self.ws_manager = WebSocketManager()
        self.email_service = EmailService()

    def _get_user_preferences(self, user_id: int) -> Optional[NotificationPreference]:
        """Get user's notification preferences"""
        return self.db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id
        ).first()

    def _should_send_email(
        self,
        preferences: Optional[NotificationPreference],
        notification_type: str,
        severity: Optional[str] = None
    ) -> bool:
        """Determine if email should be sent based on preferences"""
        if not preferences:
            # Default: send critical and high alerts
            return severity in ["Critical", "High"]

        if not preferences.email_enabled:
            return False

        # Check quiet hours
        if preferences.quiet_hours_enabled:
            now = datetime.now(timezone.utc).strftime("%H:%M")
            start = preferences.quiet_hours_start
            end = preferences.quiet_hours_end
            if start and end:
                if start <= now <= end:
                    # Only send critical during quiet hours
                    return severity == "Critical"

        # Check notification type preferences
        if notification_type == "alert":
            if severity == "Critical":
                return preferences.email_critical_alerts
            elif severity == "High":
                return preferences.email_high_alerts
            elif severity == "Medium":
                return preferences.email_medium_alerts
            elif severity == "Low":
                return preferences.email_low_alerts
        elif notification_type == "case_update":
            return preferences.email_case_updates

        return False

    def _log_notification(
        self,
        user_id: int,
        notification_type: str,
        channel: str,
        title: str,
        message: str,
        data: Optional[str] = None,
        priority: str = "normal",
        is_delivered: bool = False,
        delivery_error: Optional[str] = None
    ) -> Notification:
        """Log notification to database"""
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            channel=channel,
            title=title,
            message=message,
            data=data,
            priority=priority,
            is_delivered=is_delivered,
            delivered_at=datetime.now(timezone.utc) if is_delivered else None,
            delivery_error=delivery_error
        )
        self.db.add(notification)
        self.db.commit()
        return notification

    async def notify_alert(
        self,
        alert_data: Dict[str, Any],
        target_user_ids: Optional[List[int]] = None
    ):
        """
        Send alert notification via appropriate channels.
        If target_user_ids is None, broadcasts to all relevant users.
        """
        import json

        severity = alert_data.get("severity", "Medium")
        alert_id = alert_data.get("id")
        description = alert_data.get("description") or "New alert"

        # Determine priority based on severity
        priority_map = {
            "Critical": "urgent",
            "High": "high",
            "Medium": "normal",
            "Low": "low"
        }
        priority = priority_map.get(severity, "normal")

        # Get target users
        if target_user_ids:
            users = self.db.query(User).filter(
                User.id.in_(target_user_ids),
                User.is_active == True  # noqa: E712
            ).all()
        else:
            # Get all security personnel
            users = self.db.query(User).filter(
                User.role.in_(["security_lead", "supervisor", "admin"]),
                User.is_active == True  # noqa: E712
            ).all()

        for user in users:
            preferences = self._get_user_preferences(user.id)

            # Send WebSocket notification
            if not preferences or preferences.websocket_enabled:
                await self.ws_manager.send_alert_notification(
                    alert_id=alert_id,
                    alert_data=alert_data,
                    user_ids=[user.id]
                )
                self._log_notification(
                    user_id=user.id,
                    notification_type="alert",
                    channel="websocket",
                    title=f"Alert: {severity}",
                    message=description,
                    data=json.dumps(alert_data),
                    priority=priority,
                    is_delivered=True
                )

            # Send email notification
            if self._should_send_email(preferences, "alert", severity):
                success = await self.email_service.send_alert_notification(
                    to_emails=[user.email],
                    alert_data=alert_data
                )
                self._log_notification(
                    user_id=user.id,
                    notification_type="alert",
                    channel="email",
                    title=f"Alert: {severity}",
                    message=description,
                    data=json.dumps(alert_data),
                    priority=priority,
                    is_delivered=success,
                    delivery_error=None if success else "Email delivery failed"
                )

    async def notify_case_update(
        self,
        case_data: Dict[str, Any],
        update_type: str,
        target_user_ids: Optional[List[int]] = None
    ):
        """Send case update notification"""
        import json

        case_id = case_data.get("id")
        case_number = case_data.get("case_number", f"CASE-{case_id}")
        title = case_data.get("title", "Case Update")

        if target_user_ids:
            users = self.db.query(User).filter(
                User.id.in_(target_user_ids),
                User.is_active == True  # noqa: E712
            ).all()
        else:
            users = self.db.query(User).filter(
                User.role.in_(["security_lead", "supervisor", "admin"]),
                User.is_active == True  # noqa: E712
            ).all()

        for user in users:
            preferences = self._get_user_preferences(user.id)

            # WebSocket
            if not preferences or preferences.websocket_enabled:
                await self.ws_manager.send_case_update(
                    case_id=case_id,
                    action=update_type,
                    case_data=case_data,
                    user_ids=[user.id]
                )
                self._log_notification(
                    user_id=user.id,
                    notification_type="case_update",
                    channel="websocket",
                    title=f"Case {update_type}: {case_number}",
                    message=title,
                    data=json.dumps(case_data),
                    is_delivered=True
                )

            # Email
            if self._should_send_email(preferences, "case_update"):
                success = await self.email_service.send_case_update(
                    to_emails=[user.email],
                    case_data=case_data,
                    update_type=update_type
                )
                self._log_notification(
                    user_id=user.id,
                    notification_type="case_update",
                    channel="email",
                    title=f"Case {update_type}: {case_number}",
                    message=title,
                    data=json.dumps(case_data),
                    is_delivered=success
                )

    async def notify_sla_breach(self, alert_data: Dict[str, Any]):
        """Send SLA breach notification to supervisors and admins"""
        import json

        alert_id = alert_data.get("id")
        description = alert_data.get("description", "SLA Breach")

        # Get supervisors and admins
        users = self.db.query(User).filter(
            User.role.in_(["supervisor", "admin"]),
            User.is_active == True  # noqa: E712
        ).all()

        for user in users:
            # Always send SLA breach notifications
            await self.ws_manager.send_sla_breach_notification(
                alert_id=alert_id,
                alert_data=alert_data
            )

            # Always send email for SLA breaches
            await self.email_service.send_sla_breach_notification(
                to_emails=[user.email],
                alert_data=alert_data
            )

            self._log_notification(
                user_id=user.id,
                notification_type="sla_breach",
                channel="email",
                title=f"SLA BREACH: Alert {alert_id}",
                message=description,
                data=json.dumps(alert_data),
                priority="urgent",
                is_delivered=True
            )

    def mark_notification_read(self, notification_id: int, user_id: int) -> bool:
        """Mark a notification as read"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()

        if notification:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            self.db.commit()
            return True
        return False

    def mark_all_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user"""
        result = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False  # noqa: E712
        ).update({
            "is_read": True,
            "read_at": datetime.now(timezone.utc)
        })
        self.db.commit()
        return result

    def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """Get notifications for a user"""
        query = self.db.query(Notification).filter(
            Notification.user_id == user_id
        )

        if unread_only:
            query = query.filter(Notification.is_read == False)  # noqa: E712

        return query.order_by(
            Notification.created_at.desc()
        ).offset(offset).limit(limit).all()

    def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications"""
        return self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False  # noqa: E712
        ).count()
