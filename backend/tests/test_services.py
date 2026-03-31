"""
Tests for pure-logic services: anomaly detection, demurrage risk,
ETA prediction, and chain of custody.
No external APIs or database required.
"""

import math
from datetime import datetime, timedelta, timezone

import pytest

from app.services.anomaly_detection import AnomalyDetectionService
from app.services.demurrage_risk import DemurrageRiskService
from app.services.eta_prediction import ETAPredictionService
from app.services.chain_of_custody import ChainOfCustodyService


# ─── AnomalyDetectionService ─────────────────────────────────────────────────

class TestAnomalyDetection:
    def setup_method(self):
        self.svc = AnomalyDetectionService()

    def test_route_deviation_no_route(self):
        result = self.svc.check_route_deviation(5.0, -0.2, [])
        assert result["anomaly"] is False

    def test_route_deviation_within_corridor(self):
        route = [{"lat": 5.0, "lng": -0.2}, {"lat": 5.5, "lng": -0.3}]
        result = self.svc.check_route_deviation(5.25, -0.25, route, max_deviation_km=50.0)
        assert result["anomaly"] is False
        assert result["severity"] == "low"

    def test_route_deviation_outside_corridor(self):
        # Point far from the route (Accra to London straight line vs point in Brazil)
        route = [{"lat": 5.0, "lng": -0.2}, {"lat": 51.0, "lng": 0.0}]
        result = self.svc.check_route_deviation(-10.0, -50.0, route, max_deviation_km=5.0)
        assert result["anomaly"] is True
        assert result["type"] == "route_deviation"
        assert result["deviation_km"] > 5.0

    def test_route_deviation_high_severity(self):
        route = [{"lat": 5.0, "lng": -0.2}, {"lat": 5.1, "lng": -0.2}]
        # Far away — should be high severity (> 3x threshold)
        result = self.svc.check_route_deviation(10.0, 10.0, route, max_deviation_km=5.0)
        assert result["anomaly"] is True
        assert result["severity"] == "high"

    def test_volume_discrepancy_no_anomaly(self):
        result = self.svc.check_volume_discrepancy(100.0, 100.0)
        assert result["anomaly"] is False

    def test_volume_discrepancy_within_tolerance(self):
        result = self.svc.check_volume_discrepancy(101.5, 100.0, tolerance_pct=2.0)
        assert result["anomaly"] is False

    def test_volume_discrepancy_detected_medium(self):
        result = self.svc.check_volume_discrepancy(103.0, 100.0, tolerance_pct=2.0)
        assert result["anomaly"] is True
        assert result["severity"] == "medium"
        assert result["variance_pct"] == pytest.approx(3.0, abs=0.1)

    def test_volume_discrepancy_critical(self):
        result = self.svc.check_volume_discrepancy(115.0, 100.0, tolerance_pct=2.0)
        assert result["anomaly"] is True
        assert result["severity"] == "critical"

    def test_volume_discrepancy_zero_expected(self):
        result = self.svc.check_volume_discrepancy(50.0, 0.0)
        assert result["anomaly"] is False

    def test_volume_discrepancy_negative(self):
        result = self.svc.check_volume_discrepancy(90.0, 100.0, tolerance_pct=2.0)
        assert result["anomaly"] is True
        assert result["variance_pct"] == pytest.approx(-10.0, abs=0.1)

    def test_speed_anomaly_normal(self):
        result = self.svc.check_speed_anomaly(60.0, mode="truck")
        assert result["anomaly"] is False
        assert result["anomalies"] == []

    def test_speed_anomaly_overspeed(self):
        result = self.svc.check_speed_anomaly(120.0, mode="truck")
        assert result["anomaly"] is True
        types = [a["type"] for a in result["anomalies"]]
        assert "overspeed" in types

    def test_speed_anomaly_high_speed(self):
        result = self.svc.check_speed_anomaly(85.0, mode="truck")
        assert result["anomaly"] is True
        types = [a["type"] for a in result["anomalies"]]
        assert "high_speed" in types

    def test_speed_anomaly_vessel(self):
        result = self.svc.check_speed_anomaly(10.0, mode="vessel")
        assert result["anomaly"] is False

    def test_speed_anomaly_unknown_mode(self):
        result = self.svc.check_speed_anomaly(60.0, mode="unknown_mode")
        assert result["anomaly"] is False  # falls back to truck limits

    def test_dwell_time_ok(self):
        entry = datetime.now(timezone.utc) - timedelta(minutes=30)
        result = self.svc.check_dwell_time(entry, "Port Lagos", max_dwell_minutes=120)
        assert result["anomaly"] is False

    def test_dwell_time_excessive(self):
        entry = datetime.now(timezone.utc) - timedelta(minutes=200)
        result = self.svc.check_dwell_time(entry, "Port Lagos", max_dwell_minutes=120)
        assert result["anomaly"] is True
        assert result["type"] == "excessive_dwell"

    def test_dwell_time_high_severity(self):
        entry = datetime.now(timezone.utc) - timedelta(minutes=400)
        result = self.svc.check_dwell_time(entry, "Port Lagos", max_dwell_minutes=120)
        assert result["severity"] == "high"

    def test_sensor_tampering_insufficient_readings(self):
        result = self.svc.check_sensor_tampering([{"timestamp": datetime.now(timezone.utc)}])
        assert result["anomaly"] is False

    def test_sensor_tampering_normal(self):
        now = datetime.now(timezone.utc)
        readings = [
            {"timestamp": now - timedelta(seconds=600), "latitude": 5.0, "longitude": -0.2},
            {"timestamp": now - timedelta(seconds=300), "latitude": 5.01, "longitude": -0.2},
            {"timestamp": now, "latitude": 5.02, "longitude": -0.2},
        ]
        result = self.svc.check_sensor_tampering(readings, expected_interval_sec=300)
        assert result["anomaly"] is False

    def test_sensor_tampering_gap(self):
        now = datetime.now(timezone.utc)
        readings = [
            {"timestamp": now - timedelta(hours=5), "latitude": 5.0, "longitude": -0.2},
            {"timestamp": now, "latitude": 5.01, "longitude": -0.2},
        ]
        result = self.svc.check_sensor_tampering(readings, expected_interval_sec=300)
        assert result["anomaly"] is True
        types = [a["type"] for a in result["anomalies"]]
        assert "reporting_gap" in types

    def test_sensor_tampering_position_jump(self):
        now = datetime.now(timezone.utc)
        readings = [
            {"timestamp": now - timedelta(seconds=300), "latitude": 5.0, "longitude": -0.2},
            {"timestamp": now, "latitude": 50.0, "longitude": 10.0},  # impossible jump
        ]
        result = self.svc.check_sensor_tampering(readings, expected_interval_sec=300)
        assert result["anomaly"] is True
        types = [a["type"] for a in result["anomalies"]]
        assert "position_jump" in types

    def test_haversine_known_distance(self):
        # London to Paris ≈ 340 km
        dist = self.svc._haversine(51.5074, -0.1278, 48.8566, 2.3522)
        assert 320 < dist < 360


# ─── DemurrageRiskService ─────────────────────────────────────────────────────

class TestDemurrageRisk:
    def setup_method(self):
        self.svc = DemurrageRiskService()

    def test_low_risk_scenario(self):
        result = self.svc.calculate_risk_score(
            eta_variance_hours=2.0,
            port_congestion_level="low",
            documents_complete_pct=100.0,
            berth_available=True,
            weather_severity="good",
            counterparty_delay_history_pct=5.0,
        )
        assert result["risk_level"] == "low"
        assert result["risk_score"] < 40

    def test_high_risk_scenario(self):
        result = self.svc.calculate_risk_score(
            eta_variance_hours=60.0,
            port_congestion_level="high",
            documents_complete_pct=50.0,
            berth_available=False,
            weather_severity="severe",
            counterparty_delay_history_pct=40.0,
        )
        assert result["risk_level"] in ("high", "critical")
        assert result["risk_score"] >= 60
        assert len(result["recommendations"]) > 0

    def test_exposure_calculated_when_rate_provided(self):
        result = self.svc.calculate_risk_score(
            eta_variance_hours=60.0,
            port_congestion_level="high",
            berth_available=False,
            demurrage_rate_usd=15000.0,
        )
        assert result["exposure_usd"] > 0

    def test_no_exposure_without_rate(self):
        result = self.svc.calculate_risk_score(eta_variance_hours=60.0)
        assert result["exposure_usd"] == 0.0

    def test_laycan_past(self):
        past = datetime.now() - timedelta(hours=5)
        eta = datetime.now() + timedelta(hours=10)
        result = self.svc.calculate_risk_score(
            laycan_end=past,
            eta_destination=eta,
        )
        # Past laycan should add recommendation
        assert any("PAST LAYCAN" in r for r in result["recommendations"])

    def test_laycan_near(self):
        near_laycan = datetime.now() + timedelta(hours=12)
        eta = datetime.now() + timedelta(hours=10)
        result = self.svc.calculate_risk_score(
            laycan_end=near_laycan,
            eta_destination=eta,
        )
        assert any("laycan" in r.lower() for r in result["recommendations"])

    def test_document_urgent_recommendation(self):
        result = self.svc.calculate_risk_score(documents_complete_pct=40.0)
        assert any("URGENT" in r for r in result["recommendations"])

    def test_unknown_eta_variance(self):
        result = self.svc.calculate_risk_score()
        # Default eta_variance factor = 50 (unknown = moderate)
        assert result["factors"]["eta_variance"] == 50

    def test_critical_risk_5_day_delay(self):
        result = self.svc.calculate_risk_score(
            eta_variance_hours=72.0,
            port_congestion_level="high",
            documents_complete_pct=40.0,
            berth_available=False,
            weather_severity="severe",
            counterparty_delay_history_pct=50.0,
            demurrage_rate_usd=10000.0,
        )
        if result["risk_score"] >= 80:
            assert result["expected_delay_days"] == 5.0


# ─── ETAPredictionService ─────────────────────────────────────────────────────

class TestETAPrediction:
    def setup_method(self):
        self.svc = ETAPredictionService()

    def test_no_position_no_history(self):
        result = self.svc.predict_eta(None, None, 5.0, -0.2)
        assert result["eta"] is None
        assert result["confidence"] == 0.0

    def test_no_position_with_history(self):
        result = self.svc.predict_eta(None, None, 5.0, -0.2, historical_avg_hours=48.0)
        assert result["eta"] is not None
        assert result["confidence"] == 0.4

    def test_vessel_eta_simple(self):
        result = self.svc.predict_eta(
            current_lat=5.0, current_lng=-0.2,
            dest_lat=6.0, dest_lng=-0.3,
            mode="vessel",
            port_congestion="low",
            weather="good",
            document_status="complete",
        )
        assert result["eta"] is not None
        assert result["confidence"] > 0
        assert result["variance_hours"] >= 0

    def test_truck_eta(self):
        result = self.svc.predict_eta(
            current_lat=5.0, current_lng=-0.2,
            dest_lat=5.5, dest_lng=-0.3,
            mode="truck",
        )
        assert result["eta"] is not None

    def test_delay_factors_applied(self):
        result_good = self.svc.predict_eta(5.0, -0.2, 6.0, -0.3, mode="truck", weather="good")
        result_severe = self.svc.predict_eta(5.0, -0.2, 6.0, -0.3, mode="truck", weather="severe")
        assert result_severe["eta"] > result_good["eta"]

    def test_confidence_with_actual_speed(self):
        result_no_speed = self.svc.predict_eta(5.0, -0.2, 6.0, -0.3, mode="truck")
        result_with_speed = self.svc.predict_eta(5.0, -0.2, 6.0, -0.3, mode="truck", current_speed=40.0)
        assert result_with_speed["confidence"] > result_no_speed["confidence"]

    def test_historical_blend(self):
        result = self.svc.predict_eta(
            5.0, -0.2, 6.0, -0.3, mode="truck", historical_avg_hours=20.0
        )
        assert any("historical" in f.lower() for f in result["factors"])

    def test_high_delays_lower_confidence(self):
        result = self.svc.predict_eta(
            5.0, -0.2, 6.0, -0.3, mode="truck",
            port_congestion="high", weather="severe", document_status="incomplete"
        )
        assert result["confidence"] <= 0.7

    def test_haversine_consistency(self):
        d1 = self.svc._haversine(5.0, -0.2, 6.0, -0.3)
        d2 = self.svc._haversine(6.0, -0.3, 5.0, -0.2)  # reverse
        assert abs(d1 - d2) < 0.01  # should be symmetric


# ─── ChainOfCustodyService ────────────────────────────────────────────────────

class TestChainOfCustody:
    def setup_method(self):
        self.svc = ChainOfCustodyService()

    def test_generate_seal_id_format(self):
        seal = self.svc.generate_seal_id("SHIP-001", "SEAL-A")
        assert seal.startswith("SEAL-")
        assert len(seal) == 21  # "SEAL-" + 16 hex chars

    def test_seal_ids_are_unique(self):
        # Different inputs → different seals
        s1 = self.svc.generate_seal_id("SHIP-001", "SEAL-A")
        s2 = self.svc.generate_seal_id("SHIP-002", "SEAL-B")
        assert s1 != s2

    def test_digital_signature_deterministic(self):
        data = {"event": "load", "location": "Accra", "volume": 100}
        sig1 = self.svc.generate_digital_signature(data)
        sig2 = self.svc.generate_digital_signature(data)
        assert sig1 == sig2

    def test_digital_signature_changes_with_data(self):
        sig1 = self.svc.generate_digital_signature({"v": 1})
        sig2 = self.svc.generate_digital_signature({"v": 2})
        assert sig1 != sig2

    def test_verify_signature_valid(self):
        data = {"event": "unload", "volume": 99.5}
        sig = self.svc.generate_digital_signature(data)
        assert self.svc.verify_signature(data, sig) is True

    def test_verify_signature_tampered(self):
        data = {"event": "unload", "volume": 99.5}
        sig = self.svc.generate_digital_signature(data)
        tampered = {**data, "volume": 90.0}  # changed
        assert self.svc.verify_signature(tampered, sig) is False

    def test_build_custody_chain_empty(self):
        result = self.svc.build_custody_chain([])
        assert result["chain_length"] == 0
        assert result["integrity"] == "empty"

    def test_build_custody_chain_intact(self):
        events = [
            {
                "timestamp": "2024-01-01T00:00:00",
                "event_type": "load",
                "from_party": "Supplier",
                "to_party": "Carrier A",
                "seal_status": "intact",
                "volume_variance_pct": 0.5,
                "digital_signature": "abc123",
                "location": "Port A",
            },
            {
                "timestamp": "2024-01-02T00:00:00",
                "event_type": "transit",
                "from_party": "Carrier A",
                "to_party": "Carrier B",
                "seal_status": "intact",
                "volume_variance_pct": 0.3,
                "digital_signature": "def456",
                "location": "Port B",
            },
        ]
        result = self.svc.build_custody_chain(events)
        assert result["chain_length"] == 2
        assert result["integrity"] == "intact"
        assert result["gaps"] == []

    def test_build_custody_chain_with_gap(self):
        events = [
            {
                "timestamp": "2024-01-01T00:00:00",
                "from_party": "Supplier",
                "to_party": "Carrier A",
                "seal_status": "intact",
            },
            {
                "timestamp": "2024-01-02T00:00:00",
                "from_party": "Unknown",  # gap: expected Carrier A
                "to_party": "Carrier B",
                "seal_status": "intact",
            },
        ]
        result = self.svc.build_custody_chain(events)
        assert result["integrity"] == "compromised"
        assert len(result["gaps"]) == 1

    def test_build_custody_chain_broken_seal(self):
        events = [
            {
                "timestamp": "2024-01-01T00:00:00",
                "from_party": "A",
                "to_party": "B",
                "seal_status": "broken",
                "volume_variance_pct": 0.1,
            }
        ]
        result = self.svc.build_custody_chain(events)
        assert result["integrity"] == "compromised"
        assert len(result["seal_issues"]) == 1

    def test_build_custody_chain_volume_warning(self):
        events = [
            {
                "timestamp": "2024-01-01T00:00:00",
                "from_party": "A",
                "to_party": "B",
                "seal_status": "intact",
                "volume_variance_pct": 2.5,  # above 2% → warning
                "measured_volume": 102.5,
                "expected_volume": 100.0,
            }
        ]
        result = self.svc.build_custody_chain(events)
        assert result["integrity"] == "warning"
        assert len(result["volume_issues"]) == 1

    def test_build_custody_chain_critical_volume_variance(self):
        events = [
            {
                "timestamp": "2024-01-01T00:00:00",
                "from_party": "A",
                "to_party": "B",
                "seal_status": "intact",
                "volume_variance_pct": 6.0,  # above 5% → compromised
                "measured_volume": 106.0,
                "expected_volume": 100.0,
            }
        ]
        result = self.svc.build_custody_chain(events)
        assert result["integrity"] == "compromised"

    def test_generate_compliance_report(self):
        chain = {
            "integrity": "intact",
            "chain_length": 2,
            "gaps": [],
            "seal_issues": [],
            "volume_issues": [],
            "events": [],
        }
        shipment = {
            "cargo_type": "crude_oil",
            "volume_tonnes": 50000,
            "origin": "Lagos",
            "destination": "Rotterdam",
        }
        report = self.svc.generate_compliance_report("SHIP-001", chain, shipment)
        assert report["report_type"] == "chain_of_custody"
        assert report["compliance_status"] == "pass"
        assert report["shipment_ref"] == "SHIP-001"

    def test_generate_compliance_report_review_required(self):
        chain = {
            "integrity": "compromised",
            "chain_length": 2,
            "gaps": [{"between_events": [1, 2]}],
            "seal_issues": [],
            "volume_issues": [],
            "events": [],
        }
        report = self.svc.generate_compliance_report("SHIP-002", chain, {})
        assert report["compliance_status"] == "review_required"
        assert report["custody_gaps"] == 1
