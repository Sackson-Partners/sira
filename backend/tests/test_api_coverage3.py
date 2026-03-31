"""
Coverage-boosting tests for control_tower, intelligence, checkpoints,
telemetry (status only), AIS (status only), and schema imports.
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.models.shipment import Shipment
from app.models.organization import Organization


# ─── Control Tower ────────────────────────────────────────────────────────────

class TestControlTower:
    def test_overview_unauthenticated(self, client):
        r = client.get("/api/v1/control-tower/overview")
        assert r.status_code == 401

    def test_overview_authenticated(self, client, auth_headers):
        r = client.get("/api/v1/control-tower/overview", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "shipments" in data
        assert "vessels" in data
        assert "fleet" in data
        assert "ports" in data
        assert "corridors" in data
        assert "exceptions" in data

    def test_map_data_unauthenticated(self, client):
        r = client.get("/api/v1/control-tower/map-data")
        assert r.status_code == 401

    def test_map_data_authenticated(self, client, auth_headers):
        r = client.get("/api/v1/control-tower/map-data", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "vessels" in data
        assert "assets" in data
        assert "ports" in data
        assert "corridors" in data

    def test_kpis_unauthenticated(self, client):
        r = client.get("/api/v1/control-tower/kpis")
        assert r.status_code == 401

    def test_kpis_authenticated(self, client, auth_headers):
        r = client.get("/api/v1/control-tower/kpis", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "period_days" in data
        assert "shipments_completed" in data
        assert "demurrage" in data
        assert "fleet" in data
        assert "eta_accuracy" in data

    def test_kpis_custom_period(self, client, auth_headers):
        r = client.get("/api/v1/control-tower/kpis?days=7", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["period_days"] == 7


# ─── AI Intelligence ──────────────────────────────────────────────────────────

class TestIntelligence:
    def test_status_unauthenticated(self, client):
        r = client.get("/api/v1/ai/status")
        assert r.status_code == 401

    def test_status_authenticated(self, client, auth_headers):
        r = client.get("/api/v1/ai/status", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "configured" in data
        assert "providers" in data
        assert "model" in data

    def test_chat_unauthenticated(self, client):
        r = client.post("/api/v1/ai/chat", json={"message": "hello"})
        assert r.status_code == 401

    def test_chat_no_api_key(self, client, auth_headers):
        r = client.post(
            "/api/v1/ai/chat",
            json={"message": "What is the ETA?"},
            headers=auth_headers,
        )
        # Returns 200 with "AI Engine is not configured" message (no key in test env)
        assert r.status_code == 200
        assert "response" in r.json()

    def test_chat_with_history(self, client, auth_headers):
        r = client.post(
            "/api/v1/ai/chat",
            json={
                "message": "Follow up question",
                "history": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}],
                "context": {"shipment_id": 1},
            },
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_predict_eta_unauthenticated(self, client):
        r = client.post("/api/v1/ai/predict-eta", json={
            "origin": "Lagos", "destination": "Rotterdam", "departure_time": "2024-01-01T00:00:00"
        })
        assert r.status_code == 401

    def test_predict_eta_authenticated(self, client, auth_headers):
        r = client.post(
            "/api/v1/ai/predict-eta",
            json={
                "origin": "Lagos",
                "destination": "Rotterdam",
                "departure_time": "2024-01-01T00:00:00",
                "vessel_speed": 12.0,
                "weather_conditions": "moderate",
            },
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_analyze_risk_no_data(self, client, auth_headers):
        r = client.post(
            "/api/v1/ai/analyze-risk",
            json={},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_analyze_risk_with_data(self, client, auth_headers):
        r = client.post(
            "/api/v1/ai/analyze-risk",
            json={"shipment_data": {"id": 1, "cargo": "oil", "status": "in_transit"}},
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_analyze_risk_shipment_not_found(self, client, auth_headers, db_session):
        r = client.post(
            "/api/v1/ai/analyze-risk",
            json={"shipment_id": 99999},
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_demurrage_risk_unauthenticated(self, client):
        r = client.post("/api/v1/ai/demurrage-risk", json={
            "vessel_data": {}, "port_data": {}
        })
        assert r.status_code == 401

    def test_demurrage_risk_authenticated(self, client, auth_headers):
        r = client.post(
            "/api/v1/ai/demurrage-risk",
            json={"vessel_data": {"name": "MV Test"}, "port_data": {"name": "Port Lagos"}},
            headers=auth_headers,
        )
        assert r.status_code == 200


# ─── Checkpoints ─────────────────────────────────────────────────────────────

class TestCheckpoints:
    @pytest.fixture
    def shipment(self, db_session, admin_user):
        now = datetime.now(timezone.utc)
        s = Shipment(
            shipment_ref="SHIP-CP-001",
            cargo_type="general",
            origin="Port A",
            destination="Port B",
            laycan_start=now,
            laycan_end=now + timedelta(days=7),
            status="in_transit",
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)
        return s

    def test_create_checkpoint_unauthenticated(self, client):
        r = client.post("/api/v1/checkpoints/", json={
            "shipment_id": 1, "organization_id": 1,
            "checkpoint_type": "waypoint", "latitude": 5.0, "longitude": -0.2
        })
        assert r.status_code == 401

    def test_create_checkpoint_shipment_not_found(self, client, auth_headers):
        r = client.post(
            "/api/v1/checkpoints/",
            json={
                "shipment_id": 99999, "organization_id": 1,
                "checkpoint_type": "waypoint", "latitude": 5.0, "longitude": -0.2,
            },
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_create_checkpoint_success(self, client, auth_headers, shipment):
        r = client.post(
            "/api/v1/checkpoints/",
            json={
                "shipment_id": shipment.id,
                "organization_id": 1,
                "checkpoint_type": "waypoint",
                "latitude": 5.123,
                "longitude": -0.456,
                "location_name": "Test Waypoint",
                "notes": "All good",
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["checkpoint_type"] == "waypoint"
        assert data["latitude"] == pytest.approx(5.123, abs=0.001)

    def test_create_checkpoint_deduplication(self, client, auth_headers, shipment):
        payload = {
            "shipment_id": shipment.id,
            "organization_id": 1,
            "checkpoint_type": "departure",
            "latitude": 5.0,
            "longitude": -0.2,
            "client_event_id": "unique-event-001",
        }
        r1 = client.post("/api/v1/checkpoints/", json=payload, headers=auth_headers)
        r2 = client.post("/api/v1/checkpoints/", json=payload, headers=auth_headers)
        assert r1.status_code == 201
        assert r2.status_code == 201
        # Same id returned for duplicate
        assert r1.json()["id"] == r2.json()["id"]

    def test_list_checkpoints_for_shipment(self, client, auth_headers, shipment):
        # Create a checkpoint first
        client.post(
            "/api/v1/checkpoints/",
            json={
                "shipment_id": shipment.id, "organization_id": 1,
                "checkpoint_type": "waypoint", "latitude": 5.0, "longitude": -0.2,
            },
            headers=auth_headers,
        )
        r = client.get(f"/api/v1/checkpoints/shipment/{shipment.id}", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_checkpoints_shipment_not_found(self, client, auth_headers):
        r = client.get("/api/v1/checkpoints/shipment/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_get_checkpoint_not_found(self, client, auth_headers):
        r = client.get("/api/v1/checkpoints/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_get_checkpoint_success(self, client, auth_headers, shipment):
        create_resp = client.post(
            "/api/v1/checkpoints/",
            json={
                "shipment_id": shipment.id, "organization_id": 1,
                "checkpoint_type": "border", "latitude": 6.0, "longitude": 1.0,
            },
            headers=auth_headers,
        )
        cp_id = create_resp.json()["id"]
        r = client.get(f"/api/v1/checkpoints/{cp_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == cp_id

    def test_verify_checkpoint_not_found(self, client, auth_headers):
        r = client.post(
            "/api/v1/checkpoints/99999/verify",
            json={"is_verified": True},
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_verify_checkpoint_success(self, client, auth_headers, shipment):
        create_resp = client.post(
            "/api/v1/checkpoints/",
            json={
                "shipment_id": shipment.id, "organization_id": 1,
                "checkpoint_type": "delivery", "latitude": 7.0, "longitude": 2.0,
            },
            headers=auth_headers,
        )
        cp_id = create_resp.json()["id"]
        r = client.post(
            f"/api/v1/checkpoints/{cp_id}/verify",
            json={"is_verified": True, "notes": "Verified by manager"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["is_verified"] is True


# ─── Telemetry status (no Flespi key in tests) ───────────────────────────────

class TestTelemetry:
    def test_status_unauthenticated(self, client):
        r = client.get("/api/v1/telemetry/status")
        assert r.status_code == 401

    def test_status_authenticated(self, client, auth_headers):
        r = client.get("/api/v1/telemetry/status", headers=auth_headers)
        assert r.status_code == 200
        assert "configured" in r.json()

    def test_devices_unconfigured(self, client, auth_headers):
        r = client.get("/api/v1/telemetry/devices", headers=auth_headers)
        assert r.status_code == 503

    def test_device_telemetry_unconfigured(self, client, auth_headers):
        r = client.get("/api/v1/telemetry/devices/123/telemetry", headers=auth_headers)
        assert r.status_code == 503

    def test_device_messages_unconfigured(self, client, auth_headers):
        r = client.get("/api/v1/telemetry/devices/123/messages", headers=auth_headers)
        assert r.status_code == 503

    def test_sync_devices_unconfigured(self, client, auth_headers):
        r = client.post("/api/v1/telemetry/sync-devices", headers=auth_headers)
        assert r.status_code == 503


# ─── AIS (MarineTraffic) ─────────────────────────────────────────────────────

class TestAIS:
    def test_status_unauthenticated(self, client):
        r = client.get("/api/v1/ais/status")
        assert r.status_code == 401

    def test_status_authenticated(self, client, auth_headers):
        r = client.get("/api/v1/ais/status", headers=auth_headers)
        assert r.status_code == 200
        assert "configured" in r.json()

    def test_vessel_position_not_configured(self, client, auth_headers):
        r = client.get("/api/v1/ais/vessel/123456789", headers=auth_headers)
        assert r.status_code == 503

    def test_vessel_details_not_configured(self, client, auth_headers):
        r = client.get("/api/v1/ais/vessel/1234567/details", headers=auth_headers)
        assert r.status_code == 503

    def test_fleet_not_configured(self, client, auth_headers):
        r = client.get("/api/v1/ais/fleet", headers=auth_headers)
        assert r.status_code == 503

    def test_sync_positions_not_configured(self, client, auth_headers):
        r = client.post("/api/v1/ais/sync-positions", headers=auth_headers)
        assert r.status_code == 503


# ─── Import-time coverage for modules never imported during test collection ───

class TestModuleImports:
    def test_prompts_importable(self):
        """Importing prompts covers the prompt string definitions."""
        import app.prompts  # noqa: F401
        assert app.prompts is not None

    def test_demurrage_risk_service_import(self):
        from app.services.demurrage_risk import demurrage_risk_service
        assert demurrage_risk_service is not None

    def test_eta_service_import(self):
        from app.services.eta_prediction import eta_service
        assert eta_service is not None

    def test_chain_of_custody_import(self):
        from app.services.chain_of_custody import custody_service
        assert custody_service is not None

    def test_anomaly_service_import(self):
        from app.services.anomaly_detection import anomaly_service
        assert anomaly_service is not None

    def test_ai_engine_import(self):
        from app.services.ai_engine import ai_engine
        assert ai_engine is not None
        # is_configured should be False in test env (no API keys set)
        assert ai_engine.is_configured is False
