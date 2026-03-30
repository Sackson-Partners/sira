"""
Tests for NotificationService._should_send_email logic (pure preference logic,
no WebSocket or email infrastructure needed).
"""

import pytest
from unittest.mock import MagicMock, patch
from app.services.notification_service import NotificationService
from app.models.notification import NotificationPreference


class TestShouldSendEmail:
    """Test the email-send-decision logic without hitting real DB or WS."""

    def _make_svc(self):
        db = MagicMock()
        with patch("app.services.notification_service.WebSocketManager"), \
             patch("app.services.notification_service.EmailService"):
            svc = NotificationService(db)
        return svc

    def _prefs(self, **kwargs):
        defaults = dict(
            email_enabled=True,
            quiet_hours_enabled=False,
            quiet_hours_start=None,
            quiet_hours_end=None,
            email_critical_alerts=True,
            email_high_alerts=True,
            email_medium_alerts=False,
            email_low_alerts=False,
            email_case_updates=True,
        )
        defaults.update(kwargs)
        p = MagicMock(spec=NotificationPreference)
        for k, v in defaults.items():
            setattr(p, k, v)
        return p

    def test_no_preferences_critical(self):
        svc = self._make_svc()
        assert svc._should_send_email(None, "alert", "Critical") is True

    def test_no_preferences_high(self):
        svc = self._make_svc()
        assert svc._should_send_email(None, "alert", "High") is True

    def test_no_preferences_medium(self):
        svc = self._make_svc()
        assert svc._should_send_email(None, "alert", "Medium") is False

    def test_no_preferences_low(self):
        svc = self._make_svc()
        assert svc._should_send_email(None, "alert", "Low") is False

    def test_email_disabled(self):
        svc = self._make_svc()
        p = self._prefs(email_enabled=False)
        assert svc._should_send_email(p, "alert", "Critical") is False

    def test_quiet_hours_non_critical(self):
        svc = self._make_svc()
        # Set quiet hours to cover midnight to 11pm (always active)
        p = self._prefs(
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="23:59",
        )
        assert svc._should_send_email(p, "alert", "High") is False

    def test_quiet_hours_critical_passes(self):
        svc = self._make_svc()
        p = self._prefs(
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="23:59",
        )
        assert svc._should_send_email(p, "alert", "Critical") is True

    def test_quiet_hours_disabled_uses_prefs(self):
        svc = self._make_svc()
        p = self._prefs(quiet_hours_enabled=False, email_critical_alerts=True)
        assert svc._should_send_email(p, "alert", "Critical") is True

    def test_alert_critical_prefs(self):
        svc = self._make_svc()
        p = self._prefs(email_critical_alerts=True)
        assert svc._should_send_email(p, "alert", "Critical") is True

    def test_alert_critical_blocked(self):
        svc = self._make_svc()
        p = self._prefs(email_critical_alerts=False)
        assert svc._should_send_email(p, "alert", "Critical") is False

    def test_alert_high_prefs(self):
        svc = self._make_svc()
        p = self._prefs(email_high_alerts=True)
        assert svc._should_send_email(p, "alert", "High") is True

    def test_alert_high_blocked(self):
        svc = self._make_svc()
        p = self._prefs(email_high_alerts=False)
        assert svc._should_send_email(p, "alert", "High") is False

    def test_alert_medium_prefs(self):
        svc = self._make_svc()
        p = self._prefs(email_medium_alerts=True)
        assert svc._should_send_email(p, "alert", "Medium") is True

    def test_alert_low_prefs(self):
        svc = self._make_svc()
        p = self._prefs(email_low_alerts=True)
        assert svc._should_send_email(p, "alert", "Low") is True

    def test_case_update_enabled(self):
        svc = self._make_svc()
        p = self._prefs(email_case_updates=True)
        assert svc._should_send_email(p, "case_update", None) is True

    def test_case_update_disabled(self):
        svc = self._make_svc()
        p = self._prefs(email_case_updates=False)
        assert svc._should_send_email(p, "case_update", None) is False

    def test_unknown_type_returns_false(self):
        svc = self._make_svc()
        p = self._prefs()
        assert svc._should_send_email(p, "unknown_type", "High") is False

    def test_quiet_hours_no_start(self):
        """quiet_hours_enabled=True but no start/end → falls through to prefs check."""
        svc = self._make_svc()
        p = self._prefs(
            quiet_hours_enabled=True,
            quiet_hours_start=None,
            quiet_hours_end=None,
            email_high_alerts=True,
        )
        assert svc._should_send_email(p, "alert", "High") is True
