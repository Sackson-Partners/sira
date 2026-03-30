"""
Comprehensive API coverage tests for:
  - shipments, fleet, ports, market, assignments, corridors,
    events, evidences, reports, routes

Uses fixtures from conftest.py: client, db_session, auth_headers,
operator_headers, admin_user, operator_user.
"""

import pytest
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_str(delta_days: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=delta_days)).isoformat()


# ---------------------------------------------------------------------------
# Shipments
# ---------------------------------------------------------------------------

class TestShipmentsUnauthenticated:
    def test_list_shipments_no_token(self, client):
        r = client.get("/api/v1/shipments/")
        assert r.status_code == 401

    def test_get_shipment_no_token(self, client):
        r = client.get("/api/v1/shipments/1")
        assert r.status_code == 401

    def test_create_shipment_no_token(self, client):
        r = client.post("/api/v1/shipments/", json={})
        assert r.status_code == 401


class TestShipmentsCRUD:
    def _create_payload(self):
        return {
            "shipment_ref": "SHIP-TEST-001",
            "cargo_type": "iron_ore",
            "origin": "Mine A",
            "destination": "Port B",
            "laycan_start": _utc_str(0),
            "laycan_end": _utc_str(5),
        }

    def test_list_shipments_empty(self, client, auth_headers):
        r = client.get("/api/v1/shipments/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_active_shipments(self, client, auth_headers):
        r = client.get("/api/v1/shipments/active", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_at_risk_shipments(self, client, auth_headers):
        r = client.get("/api/v1/shipments/at-risk", headers=auth_headers)
        assert r.status_code == 200

    def test_create_shipment(self, client, auth_headers):
        r = client.post("/api/v1/shipments/", json=self._create_payload(), headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["shipment_ref"] == "SHIP-TEST-001"
        assert data["status"] == "planned"

    def test_create_shipment_invalid_laycan(self, client, auth_headers):
        payload = self._create_payload()
        payload["laycan_start"] = _utc_str(5)
        payload["laycan_end"] = _utc_str(0)
        r = client.post("/api/v1/shipments/", json=payload, headers=auth_headers)
        assert r.status_code == 400

    def test_create_shipment_duplicate_ref(self, client, auth_headers):
        client.post("/api/v1/shipments/", json=self._create_payload(), headers=auth_headers)
        r = client.post("/api/v1/shipments/", json=self._create_payload(), headers=auth_headers)
        assert r.status_code == 409

    def test_get_shipment_found(self, client, auth_headers):
        create_r = client.post("/api/v1/shipments/", json=self._create_payload(), headers=auth_headers)
        ship_id = create_r.json()["id"]
        r = client.get(f"/api/v1/shipments/{ship_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == ship_id

    def test_get_shipment_not_found(self, client, auth_headers):
        r = client.get("/api/v1/shipments/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_update_shipment(self, client, auth_headers):
        create_r = client.post("/api/v1/shipments/", json=self._create_payload(), headers=auth_headers)
        ship_id = create_r.json()["id"]
        r = client.put(f"/api/v1/shipments/{ship_id}", json={"status": "loading"}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "loading"

    def test_update_shipment_not_found(self, client, auth_headers):
        r = client.put("/api/v1/shipments/99999", json={"status": "loading"}, headers=auth_headers)
        assert r.status_code == 404

    def test_update_shipment_invalid_status(self, client, auth_headers):
        create_r = client.post("/api/v1/shipments/", json=self._create_payload(), headers=auth_headers)
        ship_id = create_r.json()["id"]
        r = client.put(f"/api/v1/shipments/{ship_id}", json={"status": "invalid_status"}, headers=auth_headers)
        assert r.status_code == 422

    def test_operator_can_create_shipment(self, client, operator_headers):
        payload = self._create_payload()
        payload["shipment_ref"] = "SHIP-OP-001"
        r = client.post("/api/v1/shipments/", json=payload, headers=operator_headers)
        assert r.status_code == 201

    def test_list_shipments_with_filters(self, client, auth_headers):
        r = client.get("/api/v1/shipments/?status_filter=planned&corridor_id=1", headers=auth_headers)
        assert r.status_code == 200


class TestShipmentMilestones:
    def _create_shipment(self, client, auth_headers, ref="SHIP-MS-001"):
        payload = {
            "shipment_ref": ref,
            "cargo_type": "copper",
            "origin": "Mine X",
            "destination": "Port Y",
            "laycan_start": _utc_str(0),
            "laycan_end": _utc_str(3),
        }
        r = client.post("/api/v1/shipments/", json=payload, headers=auth_headers)
        return r.json()["id"]

    def test_list_milestones(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers)
        r = client.get(f"/api/v1/shipments/{ship_id}/milestones", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_milestone(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers)
        payload = {
            "shipment_id": ship_id,
            "milestone_type": "departure",
            "location": "Mine X",
            "planned_time": _utc_str(1),
        }
        r = client.post(f"/api/v1/shipments/{ship_id}/milestones", json=payload, headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["milestone_type"] == "departure"

    def test_update_milestone(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers)
        payload = {
            "shipment_id": ship_id,
            "milestone_type": "arrival",
            "planned_time": _utc_str(2),
        }
        create_r = client.post(f"/api/v1/shipments/{ship_id}/milestones", json=payload, headers=auth_headers)
        ms_id = create_r.json()["id"]
        r = client.put(f"/api/v1/shipments/milestones/{ms_id}", json={"status": "completed"}, headers=auth_headers)
        assert r.status_code == 200

    def test_update_milestone_not_found(self, client, auth_headers):
        r = client.put("/api/v1/shipments/milestones/99999", json={"status": "completed"}, headers=auth_headers)
        assert r.status_code == 404


class TestShipmentCustody:
    def _create_shipment(self, client, auth_headers, ref="SHIP-CUS-001"):
        r = client.post("/api/v1/shipments/", json={
            "shipment_ref": ref,
            "cargo_type": "bauxite",
            "origin": "A",
            "destination": "B",
            "laycan_start": _utc_str(0),
            "laycan_end": _utc_str(4),
        }, headers=auth_headers)
        return r.json()["id"]

    def test_list_custody_events(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers)
        r = client.get(f"/api/v1/shipments/{ship_id}/custody", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_custody_event(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers)
        payload = {
            "shipment_id": ship_id,
            "event_type": "handover",
            "from_party": "Shipper Co",
            "to_party": "Carrier LLC",
        }
        r = client.post(f"/api/v1/shipments/{ship_id}/custody", json=payload, headers=auth_headers)
        assert r.status_code == 201
        assert "digital_signature" in r.json()

    def test_create_custody_event_with_volumes(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers, ref="SHIP-CUS-002")
        payload = {
            "shipment_id": ship_id,
            "event_type": "weighing",
            "measured_volume": 9800.0,
            "expected_volume": 10000.0,
        }
        r = client.post(f"/api/v1/shipments/{ship_id}/custody", json=payload, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["volume_variance_pct"] is not None


class TestShipmentDocuments:
    def _create_shipment(self, client, auth_headers, ref="SHIP-DOC-001"):
        r = client.post("/api/v1/shipments/", json={
            "shipment_ref": ref,
            "cargo_type": "lng",
            "origin": "A",
            "destination": "B",
            "laycan_start": _utc_str(0),
            "laycan_end": _utc_str(4),
        }, headers=auth_headers)
        return r.json()["id"]

    def test_list_documents(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers)
        r = client.get(f"/api/v1/shipments/{ship_id}/documents", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_document(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers)
        payload = {
            "shipment_id": ship_id,
            "document_type": "bill_of_lading",
            "title": "BL-001",
        }
        r = client.post(f"/api/v1/shipments/{ship_id}/documents", json=payload, headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["title"] == "BL-001"

    def test_update_document(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers)
        create_r = client.post(f"/api/v1/shipments/{ship_id}/documents", json={
            "shipment_id": ship_id,
            "document_type": "invoice",
            "title": "INV-001",
        }, headers=auth_headers)
        doc_id = create_r.json()["id"]
        r = client.put(f"/api/v1/shipments/documents/{doc_id}", json={"status": "verified"}, headers=auth_headers)
        assert r.status_code == 200

    def test_update_document_not_found(self, client, auth_headers):
        r = client.put("/api/v1/shipments/documents/99999", json={"status": "verified"}, headers=auth_headers)
        assert r.status_code == 404


class TestShipmentExceptions:
    def _create_shipment(self, client, auth_headers, ref="SHIP-EXC-001"):
        r = client.post("/api/v1/shipments/", json={
            "shipment_ref": ref,
            "cargo_type": "crude_oil",
            "origin": "A",
            "destination": "B",
            "laycan_start": _utc_str(0),
            "laycan_end": _utc_str(4),
        }, headers=auth_headers)
        return r.json()["id"]

    def test_list_exceptions(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers)
        r = client.get(f"/api/v1/shipments/{ship_id}/exceptions", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_exception(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers)
        payload = {
            "shipment_id": ship_id,
            "exception_type": "delay",
            "severity": "high",
            "description": "Port congestion",
        }
        r = client.post(f"/api/v1/shipments/{ship_id}/exceptions", json=payload, headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["exception_type"] == "delay"

    def test_create_exception_invalid_severity(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers, ref="SHIP-EXC-002")
        payload = {
            "shipment_id": ship_id,
            "exception_type": "delay",
            "severity": "EXTREME",
        }
        r = client.post(f"/api/v1/shipments/{ship_id}/exceptions", json=payload, headers=auth_headers)
        assert r.status_code == 422

    def test_update_exception(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers, ref="SHIP-EXC-003")
        create_r = client.post(f"/api/v1/shipments/{ship_id}/exceptions", json={
            "shipment_id": ship_id,
            "exception_type": "weather",
            "severity": "medium",
        }, headers=auth_headers)
        exc_id = create_r.json()["id"]
        r = client.put(f"/api/v1/shipments/exceptions/{exc_id}", json={"status": "resolved"}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "resolved"

    def test_update_exception_not_found(self, client, auth_headers):
        r = client.put("/api/v1/shipments/exceptions/99999", json={"status": "acknowledged"}, headers=auth_headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Ports
# ---------------------------------------------------------------------------

class TestPortsUnauthenticated:
    def test_list_ports_no_token(self, client):
        r = client.get("/api/v1/ports/")
        assert r.status_code == 401

    def test_create_port_no_token(self, client):
        r = client.post("/api/v1/ports/", json={})
        assert r.status_code == 401


class TestPortsCRUD:
    def _port_payload(self, code="TPRT"):
        return {
            "name": "Test Port",
            "code": code,
            "country": "Ghana",
            "latitude": 5.556,
            "longitude": -0.197,
        }

    def test_list_ports_empty(self, client, auth_headers):
        r = client.get("/api/v1/ports/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_port(self, client, auth_headers):
        r = client.post("/api/v1/ports/", json=self._port_payload(), headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["code"] == "TPRT"
        assert data["status"] == "operational"

    def test_create_port_duplicate_code(self, client, auth_headers):
        client.post("/api/v1/ports/", json=self._port_payload(), headers=auth_headers)
        r = client.post("/api/v1/ports/", json=self._port_payload(), headers=auth_headers)
        assert r.status_code == 409

    def test_get_port_found(self, client, auth_headers):
        create_r = client.post("/api/v1/ports/", json=self._port_payload(), headers=auth_headers)
        port_id = create_r.json()["id"]
        r = client.get(f"/api/v1/ports/{port_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == port_id

    def test_get_port_not_found(self, client, auth_headers):
        r = client.get("/api/v1/ports/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_update_port(self, client, auth_headers):
        create_r = client.post("/api/v1/ports/", json=self._port_payload(), headers=auth_headers)
        port_id = create_r.json()["id"]
        r = client.put(f"/api/v1/ports/{port_id}", json={"status": "congested", "current_queue": 5}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "congested"

    def test_update_port_not_found(self, client, auth_headers):
        r = client.put("/api/v1/ports/99999", json={"notes": "test"}, headers=auth_headers)
        assert r.status_code == 404

    def test_congestion_summary(self, client, auth_headers):
        r = client.get("/api/v1/ports/congestion/summary", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_ports_filter_country(self, client, auth_headers):
        client.post("/api/v1/ports/", json=self._port_payload(), headers=auth_headers)
        r = client.get("/api/v1/ports/?country=Ghana", headers=auth_headers)
        assert r.status_code == 200


class TestBerths:
    def _create_port(self, client, auth_headers, code="BPRT"):
        r = client.post("/api/v1/ports/", json={
            "name": "Berth Test Port",
            "code": code,
            "country": "Ghana",
            "latitude": 5.0,
            "longitude": -0.1,
        }, headers=auth_headers)
        return r.json()["id"]

    def test_list_berths(self, client, auth_headers):
        port_id = self._create_port(client, auth_headers)
        r = client.get(f"/api/v1/ports/{port_id}/berths", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_berth(self, client, auth_headers):
        port_id = self._create_port(client, auth_headers)
        payload = {
            "port_id": port_id,
            "name": "Berth 1",
            "berth_type": "ore",
        }
        r = client.post(f"/api/v1/ports/{port_id}/berths", json=payload, headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["name"] == "Berth 1"

    def test_create_berth_port_not_found(self, client, auth_headers):
        r = client.post("/api/v1/ports/99999/berths", json={"port_id": 99999, "name": "X"}, headers=auth_headers)
        assert r.status_code == 404

    def test_update_berth(self, client, auth_headers):
        port_id = self._create_port(client, auth_headers)
        create_r = client.post(f"/api/v1/ports/{port_id}/berths", json={
            "port_id": port_id,
            "name": "Berth 2",
        }, headers=auth_headers)
        berth_id = create_r.json()["id"]
        r = client.put(f"/api/v1/ports/berths/{berth_id}", json={"status": "maintenance"}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "maintenance"

    def test_update_berth_not_found(self, client, auth_headers):
        r = client.put("/api/v1/ports/berths/99999", json={"status": "available"}, headers=auth_headers)
        assert r.status_code == 404


class TestBerthBookings:
    def _setup(self, client, auth_headers):
        """Creates a port, berth, and vessel stub — returns berth_id."""
        from app.models.vessel import Vessel
        # We need a vessel in DB; create via session indirectly
        # by creating a port and berth first
        port_id = client.post("/api/v1/ports/", json={
            "name": "Booking Port",
            "code": "BKPRT",
            "country": "Nigeria",
            "latitude": 6.5,
            "longitude": 3.3,
        }, headers=auth_headers).json()["id"]

        berth_id = client.post(f"/api/v1/ports/{port_id}/berths", json={
            "port_id": port_id,
            "name": "Booking Berth",
        }, headers=auth_headers).json()["id"]

        return berth_id

    def test_list_berth_bookings(self, client, auth_headers):
        r = client.get("/api/v1/ports/bookings/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_berth_booking_invalid_times(self, client, auth_headers, db_session):
        berth_id = self._setup(client, auth_headers)
        payload = {
            "berth_id": berth_id,
            "vessel_id": 1,
            "scheduled_arrival": _utc_str(5),
            "scheduled_departure": _utc_str(0),  # departure before arrival
        }
        r = client.post("/api/v1/ports/bookings/", json=payload, headers=auth_headers)
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Corridors
# ---------------------------------------------------------------------------

class TestCorridorsUnauthenticated:
    def test_list_corridors_no_token(self, client):
        r = client.get("/api/v1/corridors/")
        assert r.status_code == 401

    def test_create_corridor_no_token(self, client):
        r = client.post("/api/v1/corridors/", json={})
        assert r.status_code == 401


class TestCorridorsCRUD:
    def _corridor_payload(self, code="COR-TEST"):
        return {
            "name": "Test Corridor",
            "code": code,
            "corridor_type": "mining",
            "country": "Guinea",
        }

    def test_list_corridors_empty(self, client, auth_headers):
        r = client.get("/api/v1/corridors/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_corridor(self, client, auth_headers):
        r = client.post("/api/v1/corridors/", json=self._corridor_payload(), headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["code"] == "COR-TEST"

    def test_create_corridor_duplicate_code(self, client, auth_headers):
        client.post("/api/v1/corridors/", json=self._corridor_payload(), headers=auth_headers)
        r = client.post("/api/v1/corridors/", json=self._corridor_payload(), headers=auth_headers)
        assert r.status_code == 409

    def test_get_corridor_found(self, client, auth_headers):
        create_r = client.post("/api/v1/corridors/", json=self._corridor_payload(), headers=auth_headers)
        corridor_id = create_r.json()["id"]
        r = client.get(f"/api/v1/corridors/{corridor_id}", headers=auth_headers)
        assert r.status_code == 200

    def test_get_corridor_not_found(self, client, auth_headers):
        r = client.get("/api/v1/corridors/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_update_corridor(self, client, auth_headers):
        create_r = client.post("/api/v1/corridors/", json=self._corridor_payload(), headers=auth_headers)
        corridor_id = create_r.json()["id"]
        r = client.put(f"/api/v1/corridors/{corridor_id}", json={"status": "disrupted"}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "disrupted"

    def test_update_corridor_not_found(self, client, auth_headers):
        r = client.put("/api/v1/corridors/99999", json={"status": "active"}, headers=auth_headers)
        assert r.status_code == 404

    def test_list_corridors_with_filters(self, client, auth_headers):
        r = client.get("/api/v1/corridors/?country=Guinea&status_filter=active", headers=auth_headers)
        assert r.status_code == 200


class TestGeofences:
    def _create_corridor(self, client, auth_headers, code="GEO-COR"):
        r = client.post("/api/v1/corridors/", json={
            "name": "Geo Test Corridor",
            "code": code,
        }, headers=auth_headers)
        return r.json()["id"]

    def test_list_geofences(self, client, auth_headers):
        corridor_id = self._create_corridor(client, auth_headers)
        r = client.get(f"/api/v1/corridors/{corridor_id}/geofences", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_geofence(self, client, auth_headers):
        corridor_id = self._create_corridor(client, auth_headers)
        payload = {
            "corridor_id": corridor_id,
            "name": "Zone A",
            "fence_type": "checkpoint",
            "geometry": '{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}',
        }
        r = client.post("/api/v1/corridors/geofences/", json=payload, headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["name"] == "Zone A"

    def test_create_geofence_missing_geometry(self, client, auth_headers):
        corridor_id = self._create_corridor(client, auth_headers, code="GEO-COR2")
        payload = {
            "corridor_id": corridor_id,
            "name": "No Geo",
        }
        r = client.post("/api/v1/corridors/geofences/", json=payload, headers=auth_headers)
        assert r.status_code == 422

    def test_update_geofence(self, client, auth_headers):
        corridor_id = self._create_corridor(client, auth_headers, code="GEO-COR3")
        create_r = client.post("/api/v1/corridors/geofences/", json={
            "corridor_id": corridor_id,
            "name": "Zone B",
            "geometry": '{"type":"Circle"}',
        }, headers=auth_headers)
        gf_id = create_r.json()["id"]
        r = client.put(f"/api/v1/corridors/geofences/{gf_id}", json={"is_active": False}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_update_geofence_not_found(self, client, auth_headers):
        r = client.put("/api/v1/corridors/geofences/99999", json={"is_active": True}, headers=auth_headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Fleet / Assets
# ---------------------------------------------------------------------------

class TestFleetUnauthenticated:
    def test_list_assets_no_token(self, client):
        r = client.get("/api/v1/fleet/assets/")
        assert r.status_code == 401

    def test_create_asset_no_token(self, client):
        r = client.post("/api/v1/fleet/assets/", json={})
        assert r.status_code == 401


class TestAssetsCRUD:
    def _asset_payload(self, code="AST-001"):
        return {
            "asset_code": code,
            "asset_type": "vessel",
            "name": "MV Test Vessel",
        }

    def test_list_assets_empty(self, client, auth_headers):
        r = client.get("/api/v1/fleet/assets/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_asset_availability(self, client, auth_headers):
        r = client.get("/api/v1/fleet/assets/availability", headers=auth_headers)
        assert r.status_code == 200

    def test_fleet_utilization(self, client, auth_headers):
        r = client.get("/api/v1/fleet/assets/utilization", headers=auth_headers)
        assert r.status_code == 200

    def test_create_asset(self, client, auth_headers):
        r = client.post("/api/v1/fleet/assets/", json=self._asset_payload(), headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["asset_code"] == "AST-001"

    def test_create_asset_duplicate_code(self, client, auth_headers):
        client.post("/api/v1/fleet/assets/", json=self._asset_payload(), headers=auth_headers)
        r = client.post("/api/v1/fleet/assets/", json=self._asset_payload(), headers=auth_headers)
        assert r.status_code == 409

    def test_get_asset_found(self, client, auth_headers):
        create_r = client.post("/api/v1/fleet/assets/", json=self._asset_payload(), headers=auth_headers)
        asset_id = create_r.json()["id"]
        r = client.get(f"/api/v1/fleet/assets/{asset_id}", headers=auth_headers)
        assert r.status_code == 200

    def test_get_asset_not_found(self, client, auth_headers):
        r = client.get("/api/v1/fleet/assets/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_update_asset(self, client, auth_headers):
        create_r = client.post("/api/v1/fleet/assets/", json=self._asset_payload(), headers=auth_headers)
        asset_id = create_r.json()["id"]
        r = client.put(f"/api/v1/fleet/assets/{asset_id}", json={"status": "in_transit"}, headers=auth_headers)
        assert r.status_code == 200

    def test_update_asset_not_found(self, client, auth_headers):
        r = client.put("/api/v1/fleet/assets/99999", json={"status": "available"}, headers=auth_headers)
        assert r.status_code == 404


class TestDispatch:
    def _create_asset(self, client, auth_headers, code="DSP-AST"):
        r = client.post("/api/v1/fleet/assets/", json={
            "asset_code": code,
            "asset_type": "truck",
            "name": "Dispatch Truck",
        }, headers=auth_headers)
        return r.json()["id"]

    def test_list_dispatches(self, client, auth_headers):
        r = client.get("/api/v1/fleet/dispatch/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_dispatch(self, client, auth_headers):
        asset_id = self._create_asset(client, auth_headers)
        payload = {
            "asset_id": asset_id,
            "origin": "Mine A",
            "destination": "Port B",
            "dispatched_at": _utc_str(0),
        }
        r = client.post("/api/v1/fleet/dispatch/", json=payload, headers=auth_headers)
        assert r.status_code == 201

    def test_create_dispatch_asset_not_found(self, client, auth_headers):
        r = client.post("/api/v1/fleet/dispatch/", json={
            "asset_id": 99999,
            "origin": "X",
            "destination": "Y",
            "dispatched_at": _utc_str(0),
        }, headers=auth_headers)
        assert r.status_code == 404

    def test_update_dispatch(self, client, auth_headers):
        asset_id = self._create_asset(client, auth_headers, code="DSP-AST2")
        create_r = client.post("/api/v1/fleet/dispatch/", json={
            "asset_id": asset_id,
            "origin": "A",
            "destination": "B",
            "dispatched_at": _utc_str(0),
        }, headers=auth_headers)
        dispatch_id = create_r.json()["id"]
        r = client.put(f"/api/v1/fleet/dispatch/{dispatch_id}", json={"status": "completed"}, headers=auth_headers)
        assert r.status_code == 200

    def test_update_dispatch_not_found(self, client, auth_headers):
        r = client.put("/api/v1/fleet/dispatch/99999", json={"status": "completed"}, headers=auth_headers)
        assert r.status_code == 404


class TestMaintenance:
    def test_list_maintenance(self, client, auth_headers):
        r = client.get("/api/v1/fleet/maintenance/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_maintenance(self, client, auth_headers):
        payload = {
            "maintenance_type": "oil_change",
            "scheduled_date": _utc_str(1),
            "status": "scheduled",
        }
        r = client.post("/api/v1/fleet/maintenance/", json=payload, headers=auth_headers)
        assert r.status_code == 201

    def test_update_maintenance(self, client, auth_headers):
        create_r = client.post("/api/v1/fleet/maintenance/", json={
            "maintenance_type": "inspection",
            "scheduled_date": _utc_str(2),
        }, headers=auth_headers)
        rec_id = create_r.json()["id"]
        r = client.put(f"/api/v1/fleet/maintenance/{rec_id}", json={"status": "completed"}, headers=auth_headers)
        assert r.status_code == 200

    def test_update_maintenance_not_found(self, client, auth_headers):
        r = client.put("/api/v1/fleet/maintenance/99999", json={"status": "completed"}, headers=auth_headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Market Intelligence
# ---------------------------------------------------------------------------

class TestMarketUnauthenticated:
    def test_list_rates_no_token(self, client):
        r = client.get("/api/v1/market/rates/")
        assert r.status_code == 401

    def test_list_indices_no_token(self, client):
        r = client.get("/api/v1/market/indices/")
        assert r.status_code == 401


class TestFreightRates:
    def _rate_payload(self):
        return {
            "lane": "Conakry-Rotterdam",
            "mode": "vessel",
            "rate_usd": 15.50,
            "rate_unit": "per_tonne",
            "effective_date": _utc_str(0),
        }

    def test_list_freight_rates_empty(self, client, auth_headers):
        r = client.get("/api/v1/market/rates/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_freight_rate(self, client, auth_headers):
        r = client.post("/api/v1/market/rates/", json=self._rate_payload(), headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["lane"] == "Conakry-Rotterdam"

    def test_get_rate_benchmarks(self, client, auth_headers):
        r = client.get("/api/v1/market/rates/benchmark", headers=auth_headers)
        assert r.status_code == 200

    def test_get_rate_benchmarks_with_data(self, client, auth_headers):
        client.post("/api/v1/market/rates/", json=self._rate_payload(), headers=auth_headers)
        r = client.get("/api/v1/market/rates/benchmark?lane=Conakry&days=90", headers=auth_headers)
        assert r.status_code == 200
        assert "benchmarks" in r.json()

    def test_list_rates_with_filters(self, client, auth_headers):
        r = client.get("/api/v1/market/rates/?mode=vessel&rate_type=spot", headers=auth_headers)
        assert r.status_code == 200


class TestMarketIndices:
    def _index_payload(self):
        return {
            "index_name": "BDI",
            "index_type": "freight",
            "value": 1200.0,
            "unit": "points",
            "recorded_at": _utc_str(0),
        }

    def test_list_market_indices(self, client, auth_headers):
        r = client.get("/api/v1/market/indices/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_market_index(self, client, auth_headers):
        r = client.post("/api/v1/market/indices/", json=self._index_payload(), headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["index_name"] == "BDI"

    def test_get_latest_indices(self, client, auth_headers):
        r = client.get("/api/v1/market/indices/latest", headers=auth_headers)
        assert r.status_code == 200

    def test_get_latest_indices_with_data(self, client, auth_headers):
        client.post("/api/v1/market/indices/", json=self._index_payload(), headers=auth_headers)
        r = client.get("/api/v1/market/indices/latest", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)


class TestDemurrage:
    def _create_shipment(self, client, auth_headers, ref="DEM-SHIP-001"):
        r = client.post("/api/v1/shipments/", json={
            "shipment_ref": ref,
            "cargo_type": "iron_ore",
            "origin": "A",
            "destination": "B",
            "laycan_start": _utc_str(0),
            "laycan_end": _utc_str(5),
        }, headers=auth_headers)
        return r.json()["id"]

    def test_list_demurrage_records(self, client, auth_headers):
        r = client.get("/api/v1/market/demurrage/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_demurrage_exposure(self, client, auth_headers):
        r = client.get("/api/v1/market/demurrage/exposure", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "total_exposure_usd" in data

    def test_create_demurrage_record(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers)
        r = client.post("/api/v1/market/demurrage/", json={
            "shipment_id": ship_id,
            "demurrage_rate_usd": 25000.0,
        }, headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["shipment_id"] == ship_id

    def test_update_demurrage_record(self, client, auth_headers):
        ship_id = self._create_shipment(client, auth_headers, ref="DEM-SHIP-002")
        create_r = client.post("/api/v1/market/demurrage/", json={
            "shipment_id": ship_id,
        }, headers=auth_headers)
        rec_id = create_r.json()["id"]
        r = client.put(f"/api/v1/market/demurrage/{rec_id}", json={"demurrage_days": 2.5, "status": "calculated"}, headers=auth_headers)
        assert r.status_code == 200

    def test_update_demurrage_not_found(self, client, auth_headers):
        r = client.put("/api/v1/market/demurrage/99999", json={"status": "settled"}, headers=auth_headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Events (require Movement)
# ---------------------------------------------------------------------------

class TestEventsUnauthenticated:
    def test_list_events_no_token(self, client):
        r = client.get("/api/v1/events/")
        assert r.status_code == 401

    def test_get_event_no_token(self, client):
        r = client.get("/api/v1/events/1")
        assert r.status_code == 401


class TestEventsCRUD:
    def _create_movement(self, db_session):
        from app.models.movement import Movement
        mv = Movement(
            cargo="iron ore",
            route="Mine A → Port B",
            laycan_start=datetime.now(timezone.utc),
            laycan_end=datetime.now(timezone.utc) + timedelta(days=5),
        )
        db_session.add(mv)
        db_session.commit()
        db_session.refresh(mv)
        return mv.id

    def test_list_events_empty(self, client, auth_headers):
        r = client.get("/api/v1/events/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_events_with_filters(self, client, auth_headers):
        r = client.get("/api/v1/events/?event_type=security&severity=critical", headers=auth_headers)
        assert r.status_code == 200

    def test_get_event_not_found(self, client, auth_headers):
        r = client.get("/api/v1/events/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_create_event(self, client, auth_headers, db_session):
        mv_id = self._create_movement(db_session)
        payload = {
            "movement_id": mv_id,
            "timestamp": _utc_str(0),
            "event_type": "operational",
            "severity": "info",
            "description": "Checkpoint cleared",
        }
        r = client.post("/api/v1/events/", json=payload, headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["event_type"] == "operational"

    def test_create_event_movement_not_found(self, client, auth_headers):
        payload = {
            "movement_id": 99999,
            "timestamp": _utc_str(0),
            "event_type": "operational",
            "severity": "info",
        }
        r = client.post("/api/v1/events/", json=payload, headers=auth_headers)
        assert r.status_code == 404

    def test_get_event_found(self, client, auth_headers, db_session):
        mv_id = self._create_movement(db_session)
        create_r = client.post("/api/v1/events/", json={
            "movement_id": mv_id,
            "timestamp": _utc_str(0),
            "event_type": "actual",
            "severity": "info",
        }, headers=auth_headers)
        event_id = create_r.json()["id"]
        r = client.get(f"/api/v1/events/{event_id}", headers=auth_headers)
        assert r.status_code == 200

    def test_delete_event(self, client, auth_headers, db_session):
        mv_id = self._create_movement(db_session)
        create_r = client.post("/api/v1/events/", json={
            "movement_id": mv_id,
            "timestamp": _utc_str(0),
            "event_type": "planned",
            "severity": "info",
        }, headers=auth_headers)
        event_id = create_r.json()["id"]
        r = client.delete(f"/api/v1/events/{event_id}", headers=auth_headers)
        assert r.status_code == 200

    def test_delete_event_not_found(self, client, auth_headers):
        r = client.delete("/api/v1/events/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_create_security_event(self, client, auth_headers, db_session):
        """Security events trigger alert derivation engine."""
        mv_id = self._create_movement(db_session)
        payload = {
            "movement_id": mv_id,
            "timestamp": _utc_str(0),
            "event_type": "security",
            "severity": "critical",
            "description": "Unauthorized access detected",
        }
        r = client.post("/api/v1/events/", json=payload, headers=auth_headers)
        # Should succeed even if alert engine finds nothing to process
        assert r.status_code == 201


# ---------------------------------------------------------------------------
# Evidences (require Case)
# ---------------------------------------------------------------------------

class TestEvidencesUnauthenticated:
    def test_list_evidences_no_token(self, client):
        r = client.get("/api/v1/evidences/case/1")
        assert r.status_code == 401

    def test_get_evidence_no_token(self, client):
        r = client.get("/api/v1/evidences/1")
        assert r.status_code == 401


class TestEvidencesCRUD:
    def _create_case(self, db_session):
        from app.models.case import Case
        case = Case(
            case_number="CASE-TEST-001",
            title="Test Case",
            status="open",
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)
        return case.id

    def test_list_evidences_case_not_found(self, client, auth_headers):
        r = client.get("/api/v1/evidences/case/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_list_evidences_for_case(self, client, auth_headers, db_session):
        case_id = self._create_case(db_session)
        r = client.get(f"/api/v1/evidences/case/{case_id}", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_evidence_not_found(self, client, auth_headers):
        r = client.get("/api/v1/evidences/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_create_evidence(self, client, auth_headers, db_session):
        case_id = self._create_case(db_session)
        payload = {
            "case_id": case_id,
            "evidence_type": "document",
            "file_ref": "/uploads/test.pdf",
        }
        r = client.post("/api/v1/evidences/", json=payload, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["evidence_type"] == "document"
        assert data["file_hash"] is not None

    def test_create_evidence_case_not_found(self, client, auth_headers):
        payload = {
            "case_id": 99999,
            "evidence_type": "photo",
            "file_ref": "/uploads/photo.jpg",
        }
        r = client.post("/api/v1/evidences/", json=payload, headers=auth_headers)
        assert r.status_code == 404

    def test_get_evidence_found(self, client, auth_headers, db_session):
        case_id = self._create_case(db_session)
        create_r = client.post("/api/v1/evidences/", json={
            "case_id": case_id,
            "evidence_type": "photo",
            "file_ref": "/uploads/img.jpg",
        }, headers=auth_headers)
        ev_id = create_r.json()["id"]
        r = client.get(f"/api/v1/evidences/{ev_id}", headers=auth_headers)
        assert r.status_code == 200

    def test_verify_evidence(self, client, auth_headers, db_session):
        case_id = self._create_case(db_session)
        create_r = client.post("/api/v1/evidences/", json={
            "case_id": case_id,
            "evidence_type": "document",
            "file_ref": "/uploads/doc.pdf",
        }, headers=auth_headers)
        ev_id = create_r.json()["id"]
        r = client.post(f"/api/v1/evidences/{ev_id}/verify", json={"status": "verified", "notes": "OK"}, headers=auth_headers)
        assert r.status_code == 200

    def test_verify_evidence_not_found(self, client, auth_headers):
        r = client.post("/api/v1/evidences/99999/verify", json={"status": "verified"}, headers=auth_headers)
        assert r.status_code == 404

    def test_delete_evidence(self, client, auth_headers, db_session):
        case_id = self._create_case(db_session)
        create_r = client.post("/api/v1/evidences/", json={
            "case_id": case_id,
            "evidence_type": "log",
            "file_ref": "/uploads/log.txt",
        }, headers=auth_headers)
        ev_id = create_r.json()["id"]
        r = client.delete(f"/api/v1/evidences/{ev_id}", headers=auth_headers)
        assert r.status_code == 200

    def test_delete_evidence_not_found(self, client, auth_headers):
        r = client.delete("/api/v1/evidences/99999", headers=auth_headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

class TestReportsUnauthenticated:
    def test_dashboard_no_token(self, client):
        r = client.get("/api/v1/reports/dashboard")
        assert r.status_code == 401

    def test_alerts_summary_no_token(self, client):
        r = client.get("/api/v1/reports/alerts/summary")
        assert r.status_code == 401


class TestReports:
    def test_dashboard(self, client, auth_headers):
        r = client.get("/api/v1/reports/dashboard", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "alerts" in data
        assert "cases" in data
        assert "sla" in data

    def test_alerts_summary(self, client, auth_headers):
        r = client.get("/api/v1/reports/alerts/summary", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "stats" in data
        assert "alerts" in data

    def test_alerts_summary_with_date_range(self, client, auth_headers):
        r = client.get(
            "/api/v1/reports/alerts/summary"
            "?start_date=2026-01-01T00:00:00Z&end_date=2026-12-31T23:59:59Z",
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_activity_report(self, client, auth_headers):
        r = client.get("/api/v1/reports/activity?days=7", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data

    def test_activity_report_operator_forbidden(self, client, operator_headers):
        # activity requires supervisor/admin
        r = client.get("/api/v1/reports/activity", headers=operator_headers)
        assert r.status_code == 403

    def test_alerts_summary_operator_forbidden(self, client, operator_headers):
        r = client.get("/api/v1/reports/alerts/summary", headers=operator_headers)
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Routes (Truck)
# ---------------------------------------------------------------------------

class TestRoutesUnauthenticated:
    def test_list_routes_no_token(self, client):
        r = client.get("/api/v1/routes/")
        assert r.status_code == 401

    def test_create_route_no_token(self, client):
        r = client.post("/api/v1/routes/", json={})
        assert r.status_code == 401


class TestRoutesCRUD:
    def _create_org(self, db_session):
        from app.models.organization import Organization
        org = Organization(
            name="Test Org",
            slug="test-org",
            type="logistics",
            country_code="GH",
            timezone="Africa/Accra",
        )
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)
        return org.id

    def _route_payload(self, org_id):
        return {
            "organization_id": org_id,
            "name": "Mine to Port Route",
            "origin": "Mine A",
            "origin_lat": 9.5,
            "origin_lng": -13.5,
            "destination": "Port Conakry",
            "destination_lat": 9.54,
            "destination_lng": -13.67,
            "waypoints": [],
            "risk_profile": "medium",
        }

    def test_list_routes_empty(self, client, auth_headers):
        r = client.get("/api/v1/routes/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_route(self, client, auth_headers, db_session):
        org_id = self._create_org(db_session)
        r = client.post("/api/v1/routes/", json=self._route_payload(org_id), headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Mine to Port Route"
        assert data["is_active"] is True

    def test_get_route_found(self, client, auth_headers, db_session):
        org_id = self._create_org(db_session)
        create_r = client.post("/api/v1/routes/", json=self._route_payload(org_id), headers=auth_headers)
        route_id = create_r.json()["id"]
        r = client.get(f"/api/v1/routes/{route_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == route_id

    def test_get_route_not_found(self, client, auth_headers):
        r = client.get("/api/v1/routes/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_update_route(self, client, auth_headers, db_session):
        org_id = self._create_org(db_session)
        create_r = client.post("/api/v1/routes/", json=self._route_payload(org_id), headers=auth_headers)
        route_id = create_r.json()["id"]
        r = client.patch(f"/api/v1/routes/{route_id}", json={"risk_profile": "high"}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["risk_profile"] == "high"

    def test_update_route_not_found(self, client, auth_headers):
        r = client.patch("/api/v1/routes/99999", json={"risk_profile": "low"}, headers=auth_headers)
        assert r.status_code == 404

    def test_delete_route(self, client, auth_headers, db_session):
        org_id = self._create_org(db_session)
        create_r = client.post("/api/v1/routes/", json=self._route_payload(org_id), headers=auth_headers)
        route_id = create_r.json()["id"]
        r = client.delete(f"/api/v1/routes/{route_id}", headers=auth_headers)
        assert r.status_code == 204

    def test_delete_route_not_found(self, client, auth_headers):
        r = client.delete("/api/v1/routes/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_deleted_route_not_in_list(self, client, auth_headers, db_session):
        org_id = self._create_org(db_session)
        create_r = client.post("/api/v1/routes/", json=self._route_payload(org_id), headers=auth_headers)
        route_id = create_r.json()["id"]
        client.delete(f"/api/v1/routes/{route_id}", headers=auth_headers)
        # Deleted routes have is_active=False, default filter is is_active=True
        r = client.get("/api/v1/routes/", headers=auth_headers)
        ids = [item["id"] for item in r.json()]
        assert route_id not in ids


# ---------------------------------------------------------------------------
# Assignments (require Shipment, Vehicle, User/driver)
# ---------------------------------------------------------------------------

class TestAssignmentsUnauthenticated:
    def test_list_assignments_no_token(self, client):
        r = client.get("/api/v1/assignments/")
        assert r.status_code == 401

    def test_create_assignment_no_token(self, client):
        r = client.post("/api/v1/assignments/", json={})
        assert r.status_code == 401


class TestAssignmentsCRUD:
    def _setup(self, client, auth_headers, db_session):
        """Returns (shipment_id, vehicle_id, driver_id)."""
        from app.models.organization import Organization
        from app.models.vehicle import Vehicle
        from app.models.user import User
        from app.core.security import hash_password

        # Organization
        org = Organization(name="Assign Org", slug="assign-org", type="logistics", country_code="GH", timezone="UTC")
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)

        # Vehicle
        v = Vehicle(organization_id=org.id, plate_number="GH-1234-XX", vehicle_type="truck")
        db_session.add(v)
        db_session.commit()
        db_session.refresh(v)

        # Driver user
        driver = User(
            username="driver1",
            email="driver1@test.com",
            hashed_password=hash_password("driverpass"),
            role="operator",
            is_active=True,
        )
        db_session.add(driver)
        db_session.commit()
        db_session.refresh(driver)

        # Shipment
        create_r = client.post("/api/v1/shipments/", json={
            "shipment_ref": "ASSIGN-SHIP-001",
            "cargo_type": "iron_ore",
            "origin": "A",
            "destination": "B",
            "laycan_start": _utc_str(0),
            "laycan_end": _utc_str(5),
        }, headers=auth_headers)
        ship_id = create_r.json()["id"]

        return ship_id, v.id, driver.id

    def test_list_assignments_empty(self, client, auth_headers):
        r = client.get("/api/v1/assignments/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_assignment(self, client, auth_headers, db_session):
        ship_id, vehicle_id, driver_id = self._setup(client, auth_headers, db_session)
        payload = {
            "shipment_id": ship_id,
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
        }
        r = client.post("/api/v1/assignments/", json=payload, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["shipment_id"] == ship_id
        assert data["status"] == "pending"

    def test_create_assignment_shipment_not_found(self, client, auth_headers, db_session):
        _, vehicle_id, driver_id = self._setup(client, auth_headers, db_session)
        r = client.post("/api/v1/assignments/", json={
            "shipment_id": 99999,
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
        }, headers=auth_headers)
        assert r.status_code == 404

    def test_create_assignment_vehicle_not_found(self, client, auth_headers, db_session):
        ship_id, _, driver_id = self._setup(client, auth_headers, db_session)
        r = client.post("/api/v1/assignments/", json={
            "shipment_id": ship_id,
            "vehicle_id": 99999,
            "driver_id": driver_id,
        }, headers=auth_headers)
        assert r.status_code == 404

    def test_get_assignment_found(self, client, auth_headers, db_session):
        ship_id, vehicle_id, driver_id = self._setup(client, auth_headers, db_session)
        create_r = client.post("/api/v1/assignments/", json={
            "shipment_id": ship_id,
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
        }, headers=auth_headers)
        asgn_id = create_r.json()["id"]
        r = client.get(f"/api/v1/assignments/{asgn_id}", headers=auth_headers)
        assert r.status_code == 200

    def test_get_assignment_not_found(self, client, auth_headers):
        r = client.get("/api/v1/assignments/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_update_assignment(self, client, auth_headers, db_session):
        ship_id, vehicle_id, driver_id = self._setup(client, auth_headers, db_session)
        create_r = client.post("/api/v1/assignments/", json={
            "shipment_id": ship_id,
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
        }, headers=auth_headers)
        asgn_id = create_r.json()["id"]
        r = client.patch(f"/api/v1/assignments/{asgn_id}", json={"status": "accepted"}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"

    def test_update_assignment_not_found(self, client, auth_headers):
        r = client.patch("/api/v1/assignments/99999", json={"status": "accepted"}, headers=auth_headers)
        assert r.status_code == 404
