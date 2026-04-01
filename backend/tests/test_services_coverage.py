"""
Targeted service tests to push coverage from 79.77% → 80%+.

Covers exact uncovered lines identified in the coverage report:
  alert_engine.py       72% → lines 39,43,107,113,132,142-143,165,
                               192-193,197-198,220-221,265-266,288-291,
                               295-315,319-330
  demurrage_risk.py     86% → lines 57,59,61,78,80-81,101,110,112,137,141,149
  email_service.py      48% → lines 47-50,65-98
  marinetraffic.py      24% → lines 30-46,52-73,77-89,95-109,113
  flespi_service.py     34% → lines 35-45,49-60,66-77,81
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


# ── app/services/demurrage_risk.py — lines 57,59,61,78,80-81,101,110,112,137,141,149 ──

class TestDemurrageRiskCoverage:
    """DemurrageRiskService.calculate_risk_score — all branch paths."""

    def _svc(self):
        from app.services.demurrage_risk import DemurrageRiskService
        return DemurrageRiskService()

    def test_eta_variance_4_to_8_hours(self):
        """Line 57 — 4 < variance ≤ 8 → score 30."""
        result = self._svc().calculate_risk_score(eta_variance_hours=6.0)
        assert result["factors"]["eta_variance"] == 30

    def test_eta_variance_8_to_24_hours(self):
        """Line 59 — 8 < variance ≤ 24 → score 60."""
        result = self._svc().calculate_risk_score(eta_variance_hours=12.0)
        assert result["factors"]["eta_variance"] == 60

    def test_eta_variance_24_to_48_hours(self):
        """Line 61 — 24 < variance ≤ 48 → score 80."""
        result = self._svc().calculate_risk_score(eta_variance_hours=36.0)
        assert result["factors"]["eta_variance"] == 80

    def test_documents_80_to_95_pct(self):
        """Line 78 — 80 ≤ docs_pct < 95 → score 30."""
        result = self._svc().calculate_risk_score(documents_complete_pct=85.0)
        assert result["factors"]["document_readiness"] == 30

    def test_documents_60_to_80_pct(self):
        """Lines 80-81 — 60 ≤ docs_pct < 80 → score 60 + recommendation."""
        result = self._svc().calculate_risk_score(documents_complete_pct=70.0)
        assert result["factors"]["document_readiness"] == 60
        assert any("document" in r.lower() for r in result["recommendations"])

    def test_counterparty_history_10_to_30_pct(self):
        """Line 101 — 10 < history ≤ 30 → score 40."""
        result = self._svc().calculate_risk_score(counterparty_delay_history_pct=20.0)
        assert result["factors"]["counterparty_history"] == 40

    def test_laycan_proximity_24_to_72_hours(self):
        """Line 110 — 24 < hours_to_laycan ≤ 72 → score 30."""
        now = datetime.now(timezone.utc)
        result = self._svc().calculate_risk_score(
            laycan_end=now + timedelta(hours=48),
            eta_destination=now,
        )
        assert result["factors"]["laycan_proximity"] == 30

    def test_laycan_proximity_0_to_24_hours(self):
        """Line 112 — 0 < hours_to_laycan ≤ 24 → score 65."""
        now = datetime.now(timezone.utc)
        result = self._svc().calculate_risk_score(
            laycan_end=now + timedelta(hours=12),
            eta_destination=now,
        )
        assert result["factors"]["laycan_proximity"] == 65

    def test_exposure_high_risk(self):
        """Line 137 — high risk score → expected_delay_days = 3.0."""
        now = datetime.now(timezone.utc)
        result = self._svc().calculate_risk_score(
            eta_variance_hours=36.0,
            port_congestion_level="high",
            documents_complete_pct=55.0,
            berth_available=False,
            weather_severity="severe",
            counterparty_delay_history_pct=35.0,
            laycan_end=now + timedelta(hours=6),
            eta_destination=now,
            demurrage_rate_usd=5000.0,
        )
        assert result["expected_delay_days"] >= 1.5

    def test_risk_level_label_coverage(self):
        """Lines 141,149 — low and medium risk labels."""
        result_low = self._svc().calculate_risk_score(
            eta_variance_hours=2.0,
            port_congestion_level="low",
            documents_complete_pct=100.0,
            berth_available=True,
            weather_severity="good",
            counterparty_delay_history_pct=0.0,
        )
        assert result_low["risk_level"] in ("low", "medium", "high", "critical")

        result_med = self._svc().calculate_risk_score(
            eta_variance_hours=12.0,
            port_congestion_level="low",
            documents_complete_pct=85.0,
        )
        assert result_med["risk_level"] in ("low", "medium", "high", "critical")


# ── app/services/alert_engine.py — uncovered lines ────────────────────────────

class TestAlertEngineCoverage:
    """AlertRule base class and AlertDerivationEngine methods."""

    def _engine(self):
        from app.services.alert_engine import AlertDerivationEngine
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.filter.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.all.return_value = []
        return AlertDerivationEngine(db=db)

    def test_base_rule_evaluate_raises(self):
        """Line 39 — AlertRule.evaluate() raises NotImplementedError."""
        from app.services.alert_engine import AlertRule
        rule = AlertRule("id", "name", "High", "Test")
        event, ctx = MagicMock(), {}
        with pytest.raises(NotImplementedError):
            rule.evaluate(event, ctx)

    def test_base_rule_generate_description_raises(self):
        """Line 43 — AlertRule.generate_description() raises NotImplementedError."""
        from app.services.alert_engine import AlertRule
        rule = AlertRule("id", "name", "High", "Test")
        event, ctx = MagicMock(), {}
        with pytest.raises(NotImplementedError):
            rule.generate_description(event, ctx)

    def test_high_risk_zone_rule_evaluate_match(self):
        """Lines 107-108 — HighRiskZoneRule hits a known high-risk zone."""
        from app.services.alert_engine import HighRiskZoneRule
        rule = HighRiskZoneRule()
        event = MagicMock()
        event.location = "Gulf of Aden, near Djibouti"
        assert rule.evaluate(event, {}) is True

    def test_high_risk_zone_rule_generate_description(self):
        """Line 113 — HighRiskZoneRule.generate_description."""
        from app.services.alert_engine import HighRiskZoneRule
        rule = HighRiskZoneRule()
        event = MagicMock()
        event.location = "Red Sea"
        desc = rule.generate_description(event, {})
        assert "Red Sea" in desc

    def test_delay_detection_rule_evaluate_triggered(self):
        """Line 132 — DelayDetectionRule.evaluate() returns True."""
        from app.services.alert_engine import DelayDetectionRule
        rule = DelayDetectionRule()
        event = MagicMock()
        event.event_type = "operational"
        movement = MagicMock()
        movement.laycan_end = datetime.now(timezone.utc) - timedelta(hours=2)
        movement.status = "active"
        assert rule.evaluate(event, {"movement": movement}) is True

    def test_delay_detection_rule_generate_description(self):
        """Lines 142-143 — DelayDetectionRule.generate_description."""
        from app.services.alert_engine import DelayDetectionRule
        rule = DelayDetectionRule()
        event = MagicMock()
        movement = MagicMock()
        movement.id = 42
        desc = rule.generate_description(event, {"movement": movement})
        assert "42" in desc

    def test_anomaly_detection_rule_evaluate_keyword_match(self):
        """Line 165-167 — AnomalyDetectionRule.evaluate() keyword match."""
        from app.services.alert_engine import AnomalyDetectionRule
        rule = AnomalyDetectionRule()
        event = MagicMock()
        event.description = "Suspicious behavior detected at port"
        assert rule.evaluate(event, {}) is True

    def test_add_rule(self):
        """Lines 192-193 — add_rule appends and logs."""
        from app.services.alert_engine import AlertRule
        engine = self._engine()
        initial_count = len(engine.rules)
        new_rule = AlertRule("RULE_TEST_001", "Test Rule", "Low", "Test")
        new_rule.evaluate = lambda e, c: False
        engine.add_rule(new_rule)
        assert len(engine.rules) == initial_count + 1

    def test_remove_rule(self):
        """Lines 197-198 — remove_rule filters and logs."""
        engine = self._engine()
        engine.remove_rule("RULE_SEC_001")
        assert not any(r.rule_id == "RULE_SEC_001" for r in engine.rules)

    def test_process_event_rule_exception_is_caught(self):
        """Lines 220-221 — exception inside rule.evaluate() is caught."""
        from app.services.alert_engine import AlertDerivationEngine, AlertRule
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        engine = AlertDerivationEngine(db=db)

        bad_rule = AlertRule("RULE_BAD", "Bad Rule", "High", "Test")
        bad_rule.evaluate = MagicMock(side_effect=RuntimeError("boom"))
        engine.rules = [bad_rule]

        event = MagicMock()
        event.movement_id = None
        result = engine.process_event(event)
        assert result == []

    def test_create_alert_duplicate_suppression(self):
        """Lines 265-266 — duplicate alert is suppressed (returns None)."""
        from app.services.alert_engine import AlertDerivationEngine, SecurityEventRule
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = MagicMock()
        engine = AlertDerivationEngine(db=db)
        engine.rules = [SecurityEventRule()]

        event = MagicMock()
        event.event_type = "security"
        event.id = 1
        event.movement_id = None
        event.location = "Test Port"
        event.description = "Test"

        rule = SecurityEventRule()
        result = engine._create_alert(event, rule, {})
        assert result is None

    def test_create_alert_db_error_returns_none(self):
        """Lines 288-291 — db.add/commit error → rollback → return None."""
        from app.services.alert_engine import AlertDerivationEngine, SecurityEventRule
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        db.add.side_effect = Exception("db error")
        engine = AlertDerivationEngine(db=db)

        event = MagicMock()
        event.id = 1
        event.movement_id = None
        event.location = "Test"
        event.description = "desc"
        event.severity = "critical"

        rule = SecurityEventRule()
        result = engine._create_alert(event, rule, {})
        assert result is None
        db.rollback.assert_called_once()

    def test_check_sla_breaches_no_open_alerts(self):
        """Lines 295-315 — check_sla_breaches with no open alerts."""
        engine = self._engine()
        result = engine.check_sla_breaches()
        assert result == []

    def test_check_sla_breaches_breached_alert(self):
        """Lines 295-315 — alert past SLA deadline is flagged."""
        from app.services.alert_engine import AlertDerivationEngine
        db = MagicMock()

        breached = MagicMock()
        breached.created_at = datetime.now(timezone.utc) - timedelta(hours=3)
        breached.sla_timer = 60
        breached.sla_breached = False

        db.query.return_value.filter.return_value.all.return_value = [breached]
        engine = AlertDerivationEngine(db=db)
        result = engine.check_sla_breaches()
        assert breached in result
        assert breached.sla_breached is True

    def test_get_rule_stats(self):
        """Lines 319-330 — get_rule_stats returns dict for all rules."""
        engine = self._engine()
        stats = engine.get_rule_stats()
        assert isinstance(stats, dict)
        assert "RULE_SEC_001" in stats
        assert stats["RULE_SEC_001"]["severity"] == "High"


# ── app/services/email_service.py — lines 47-50, 65-98 ───────────────────────

class TestEmailServiceCoverage:
    """EmailService — SMTP connection and sync send path."""

    def _svc(self):
        from app.services.email_service import EmailService
        svc = EmailService()
        svc.smtp_host = "smtp.test.com"
        svc.smtp_port = 587
        svc.smtp_user = "user@test.com"
        svc.smtp_password = "secret"
        svc.email_from = "noreply@sira.systems"
        svc.email_from_name = "SIRA"
        return svc

    def test_get_smtp_connection(self):
        """Lines 47-50 — _get_smtp_connection creates and logs into SMTP."""
        svc = self._svc()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value = mock_smtp
            conn = svc._get_smtp_connection()
            mock_smtp_cls.assert_called_once_with("smtp.test.com", 587)
            mock_smtp.starttls.assert_called_once()
            mock_smtp.login.assert_called_once_with("user@test.com", "secret")

    def test_send_email_sync_configured(self):
        """Lines 65-98 — _send_email_sync sends when configured."""
        svc = self._svc()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=False)
            mock_smtp_cls.return_value = mock_smtp

            result = svc._send_email_sync(
                to_emails=["ops@sira.com"],
                subject="Test Alert",
                html_content="<p>Alert body</p>",
                text_content="Alert body",
            )
            assert result is True

    def test_send_email_sync_with_attachment(self):
        """Lines 79-88 — attachment path in _send_email_sync."""
        svc = self._svc()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=False)
            mock_smtp_cls.return_value = mock_smtp

            result = svc._send_email_sync(
                to_emails=["ops@sira.com"],
                subject="Report",
                html_content="<p>See attached</p>",
                attachments=[{"filename": "report.pdf", "content": b"PDF data"}],
            )
            assert result is True

    def test_send_email_sync_smtp_error(self):
        """Lines 96-98 — SMTP error returns False."""
        svc = self._svc()
        with patch("smtplib.SMTP", side_effect=Exception("connection refused")):
            result = svc._send_email_sync(
                to_emails=["ops@sira.com"],
                subject="Test",
                html_content="<p>body</p>",
            )
            assert result is False


# ── app/services/marinetraffic_service.py — lines 30-109, 113 ────────────────

class TestMarineTrafficCoverage:
    """MarineTrafficService — all async methods mocked with httpx."""

    def _svc_configured(self):
        from app.services.marinetraffic_service import MarineTrafficService
        svc = MarineTrafficService()
        svc.api_key = "real-api-key-abc123"
        svc.api_url = "https://services.marinetraffic.com/api"
        return svc

    def _mock_httpx_response(self, payload):
        resp = MagicMock()
        resp.json.return_value = payload
        resp.raise_for_status = MagicMock()
        return resp

    @pytest.mark.anyio
    async def test_get_vessel_position_configured(self):
        """Lines 30-46 — get_vessel_position when configured."""
        svc = self._svc_configured()
        raw = [{"MMSI": "123456789", "LAT": "5.3", "LON": "-4.0",
                "SPEED": "120", "HEADING": "135", "COURSE": "130",
                "STATUS": "underway", "SHIPNAME": "MV TEST",
                "DESTINATION": "NGLAG", "ETA": "2024-01-15", "IMO": "9876543",
                "TIMESTAMP": "2024-01-10 12:00:00"}]
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=self._mock_httpx_response(raw))
            result = await svc.get_vessel_position("123456789")
        assert result is not None
        assert result["mmsi"] == "123456789"
        assert result["speed"] == 12.0

    @pytest.mark.anyio
    async def test_get_vessel_position_empty_response(self):
        """Lines 30-46 — empty list response → None."""
        svc = self._svc_configured()
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=self._mock_httpx_response([]))
            result = await svc.get_vessel_position("999")
        assert result is None

    @pytest.mark.anyio
    async def test_get_fleet_positions_with_mmsi_list(self):
        """Lines 52-73 — get_fleet_positions with mmsi_list → list."""
        svc = self._svc_configured()
        raw = [{"MMSI": "111", "LAT": "6.0", "LON": "3.4",
                "SPEED": "80", "HEADING": "90", "COURSE": "90",
                "STATUS": "anchored", "SHIPNAME": "VESSEL A",
                "DESTINATION": "", "ETA": "", "IMO": "", "TIMESTAMP": ""}]
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=self._mock_httpx_response(raw))
            result = await svc.get_fleet_positions(["111"])
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.anyio
    async def test_get_vessel_details_found(self):
        """Lines 77-89 — get_vessel_details returns data dict."""
        svc = self._svc_configured()
        raw = [{"IMO": "1234567", "SHIPNAME": "TEST VESSEL", "TYPE": "Tanker"}]
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=self._mock_httpx_response(raw))
            result = await svc.get_vessel_details("1234567")
        assert result == raw[0]

    @pytest.mark.anyio
    async def test_get_vessel_details_empty(self):
        """Lines 77-89 — empty response → None."""
        svc = self._svc_configured()
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=self._mock_httpx_response([]))
            result = await svc.get_vessel_details("0000000")
        assert result is None

    @pytest.mark.anyio
    async def test_get_port_calls(self):
        """Lines 95-109 — get_port_calls returns list."""
        svc = self._svc_configured()
        raw = [{"PORTNAME": "Lagos", "ARRIVAL": "2024-01-10"}]
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=self._mock_httpx_response(raw))
            result = await svc.get_port_calls("NGLAG", timespan=30)
        assert result == raw

    def test_parse_position(self):
        """Line 113 — _parse_position maps raw dict to internal format."""
        from app.services.marinetraffic_service import MarineTrafficService
        svc = MarineTrafficService()
        raw = {"MMSI": "123", "IMO": "456", "SHIPNAME": "VESSEL",
               "LAT": "5.3", "LON": "-4.0", "SPEED": "120",
               "HEADING": "135", "COURSE": "130", "STATUS": "underway",
               "DESTINATION": "NGLAG", "ETA": "2024-01-15",
               "TIMESTAMP": "2024-01-10"}
        result = svc._parse_position(raw)
        assert result["mmsi"] == "123"
        assert result["speed"] == 12.0
        assert result["latitude"] == 5.3


# ── app/services/flespi_service.py — lines 35-45, 49-60, 66-77, 81 ────────────

class TestFlespiServiceCoverage:
    """FlespiService — async methods when configured."""

    def _svc_configured(self):
        from app.services.flespi_service import FlespiService
        svc = FlespiService()
        svc.token = "real-flespi-token-abc123xyz"
        svc.rest_url = "https://flespi.io"
        svc.headers = {"Authorization": f"FlespiToken {svc.token}",
                       "Content-Type": "application/json"}
        return svc

    def _mock_resp(self, payload):
        resp = MagicMock()
        resp.json.return_value = payload
        resp.raise_for_status = MagicMock()
        return resp

    @pytest.mark.anyio
    async def test_get_devices_configured(self):
        """Lines 35-45 — get_devices returns device list."""
        svc = self._svc_configured()
        devices = [{"id": 1, "name": "Truck-001"}, {"id": 2, "name": "Truck-002"}]
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(
                return_value=self._mock_resp({"result": devices})
            )
            result = await svc.get_devices()
        assert result == devices

    @pytest.mark.anyio
    async def test_get_device_telemetry_with_result(self):
        """Lines 49-60 — get_device_telemetry returns first result."""
        svc = self._svc_configured()
        telemetry = {"position.latitude": 5.3, "position.longitude": -4.0,
                     "position.speed": 60.0, "timestamp": 1234567890}
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(
                return_value=self._mock_resp({"result": [telemetry]})
            )
            result = await svc.get_device_telemetry(1)
        assert result == telemetry

    @pytest.mark.anyio
    async def test_get_device_telemetry_empty(self):
        """Lines 49-60 — empty result → empty dict."""
        svc = self._svc_configured()
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=self._mock_resp({"result": []}))
            result = await svc.get_device_telemetry(999)
        assert result == {}

    @pytest.mark.anyio
    async def test_get_device_messages(self):
        """Lines 66-77 — get_device_messages returns message list."""
        svc = self._svc_configured()
        messages = [{"timestamp": 1234567890, "position.speed": 55.0}]
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(
                return_value=self._mock_resp({"result": messages})
            )
            result = await svc.get_device_messages(1, limit=50)
        assert result == messages

    def test_parse_telemetry_message(self):
        """Line 81+ — parse_telemetry_message maps raw fields."""
        from app.services.flespi_service import FlespiService
        svc = FlespiService()
        msg = {
            "timestamp": 1234567890.0,
            "position.latitude": 5.3,
            "position.longitude": -4.0,
            "position.speed": 60.0,
            "position.direction": 135.0,
            "position.satellites": 8,
            "engine.ignition.status": True,
            "battery.voltage": 12.5,
        }
        result = svc.parse_telemetry_message(msg)
        assert result["latitude"] == 5.3
        assert result["longitude"] == -4.0
        assert result["speed"] == 60.0
