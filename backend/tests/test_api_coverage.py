"""
API Coverage Tests

Comprehensive pytest suite covering:
  - users, organizations, vessels, vehicles, playbooks, notifications, movements
  - super_admin endpoints (dashboard, users, lock/unlock, change-role, system health)
  - Auth-protected route enforcement (401 without token)
  - Basic status-code and response-structure assertions

Fixtures from conftest.py:
  client, db_session, auth_headers, operator_headers, admin_user, operator_user
"""

import pytest
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _future_dt(days=1) -> str:
    """Return an ISO-8601 string that is `days` days in the future."""
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _past_dt(days=1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# ===========================================================================
# USERS
# ===========================================================================

class TestUsersAuth:
    """Auth protection — unauthenticated callers must get 401."""

    def test_list_users_requires_auth(self, client):
        r = client.get("/api/v1/users/")
        assert r.status_code == 401

    def test_get_user_requires_auth(self, client):
        r = client.get("/api/v1/users/1")
        assert r.status_code == 401

    def test_create_user_requires_auth(self, client):
        r = client.post("/api/v1/users/", json={})
        assert r.status_code == 401

    def test_update_user_requires_auth(self, client):
        r = client.put("/api/v1/users/1", json={})
        assert r.status_code == 401

    def test_delete_user_requires_auth(self, client):
        r = client.delete("/api/v1/users/1")
        assert r.status_code == 401


class TestUsersListAndGet:
    def test_list_users_returns_list(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/users/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_users_filter_by_role(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/users/?role=admin", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert all(u["role"] == "admin" for u in data)

    def test_list_users_filter_by_active(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/users/?is_active=true", headers=auth_headers)
        assert r.status_code == 200

    def test_get_existing_user(self, client, auth_headers, admin_user):
        r = client.get(f"/api/v1/users/{admin_user.id}", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == admin_user.id
        assert data["username"] == admin_user.username

    def test_get_nonexistent_user_returns_404(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/users/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_operator_cannot_list_users(self, client, operator_headers, operator_user):
        r = client.get("/api/v1/users/", headers=operator_headers)
        assert r.status_code == 403


class TestUsersCreate:
    def test_create_user_success(self, client, auth_headers, admin_user):
        payload = {
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "NewUser@Pass1",
            "full_name": "New User",
            "role": "operator",
        }
        r = client.post("/api/v1/users/", json=payload, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["username"] == "newuser"
        assert data["role"] == "operator"

    def test_create_user_duplicate_username_returns_400(self, client, auth_headers, admin_user):
        payload = {
            "username": admin_user.username,
            "email": "unique@test.com",
            "password": "Unique@Pass1",
            "role": "operator",
        }
        r = client.post("/api/v1/users/", json=payload, headers=auth_headers)
        assert r.status_code == 400

    def test_create_user_duplicate_email_returns_400(self, client, auth_headers, admin_user):
        payload = {
            "username": "uniqueuser",
            "email": admin_user.email,
            "password": "Unique@Pass1",
            "role": "operator",
        }
        r = client.post("/api/v1/users/", json=payload, headers=auth_headers)
        assert r.status_code == 400

    def test_create_user_operator_forbidden(self, client, operator_headers, operator_user):
        payload = {
            "username": "anotheruser",
            "email": "another@test.com",
            "password": "Another@Pass1",
            "role": "operator",
        }
        r = client.post("/api/v1/users/", json=payload, headers=operator_headers)
        assert r.status_code == 403


class TestUsersUpdate:
    def test_update_user_full_name(self, client, auth_headers, admin_user, operator_user):
        payload = {"full_name": "Updated Name"}
        r = client.put(f"/api/v1/users/{operator_user.id}", json=payload, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["full_name"] == "Updated Name"

    def test_update_nonexistent_user_returns_404(self, client, auth_headers, admin_user):
        r = client.put("/api/v1/users/99999", json={"full_name": "X"}, headers=auth_headers)
        assert r.status_code == 404


class TestUsersDelete:
    def test_delete_user_deactivates(self, client, auth_headers, admin_user, operator_user):
        r = client.delete(f"/api/v1/users/{operator_user.id}", headers=auth_headers)
        assert r.status_code == 200
        assert "deactivated" in r.json()["message"].lower()

    def test_cannot_delete_own_account(self, client, auth_headers, admin_user):
        r = client.delete(f"/api/v1/users/{admin_user.id}", headers=auth_headers)
        assert r.status_code == 400

    def test_delete_nonexistent_user_returns_404(self, client, auth_headers, admin_user):
        r = client.delete("/api/v1/users/99999", headers=auth_headers)
        assert r.status_code == 404


class TestUsersActivate:
    def test_activate_user(self, client, auth_headers, admin_user, operator_user):
        # Deactivate first
        client.delete(f"/api/v1/users/{operator_user.id}", headers=auth_headers)
        r = client.post(f"/api/v1/users/{operator_user.id}/activate", headers=auth_headers)
        assert r.status_code == 200
        assert "activated" in r.json()["message"].lower()

    def test_activate_nonexistent_user_returns_404(self, client, auth_headers, admin_user):
        r = client.post("/api/v1/users/99999/activate", headers=auth_headers)
        assert r.status_code == 404


# ===========================================================================
# ORGANIZATIONS
# ===========================================================================

class TestOrganizationsAuth:
    def test_list_orgs_requires_auth(self, client):
        r = client.get("/api/v1/organizations/")
        assert r.status_code == 401

    def test_create_org_requires_auth(self, client):
        r = client.post("/api/v1/organizations/", json={})
        assert r.status_code == 401


class TestOrganizationsCreate:
    def test_create_organization(self, client, auth_headers, admin_user):
        payload = {
            "name": "Test Org",
            "slug": "test-org",
            "type": "logistics",
            "country_code": "GH",
            "timezone": "Africa/Accra",
            "plan": "starter",
            "settings": {},
        }
        r = client.post("/api/v1/organizations/", json=payload, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["slug"] == "test-org"
        assert data["name"] == "Test Org"

    def test_create_org_duplicate_slug_returns_409(self, client, auth_headers, admin_user):
        payload = {
            "name": "Test Org",
            "slug": "duplicate-slug",
            "type": "logistics",
            "country_code": "GH",
            "timezone": "Africa/Accra",
            "plan": "starter",
            "settings": {},
        }
        client.post("/api/v1/organizations/", json=payload, headers=auth_headers)
        r = client.post("/api/v1/organizations/", json=payload, headers=auth_headers)
        assert r.status_code == 409

    def test_create_org_operator_forbidden(self, client, operator_headers, operator_user):
        payload = {
            "name": "Op Org",
            "slug": "op-org",
            "type": "logistics",
            "country_code": "GH",
            "timezone": "Africa/Accra",
            "plan": "starter",
            "settings": {},
        }
        r = client.post("/api/v1/organizations/", json=payload, headers=operator_headers)
        assert r.status_code == 403


class TestOrganizationsList:
    def _create_org(self, client, auth_headers, slug="listorg"):
        payload = {
            "name": "List Org",
            "slug": slug,
            "type": "logistics",
            "country_code": "GH",
            "timezone": "Africa/Accra",
            "plan": "starter",
            "settings": {},
        }
        return client.post("/api/v1/organizations/", json=payload, headers=auth_headers)

    def test_list_organizations_returns_list(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/organizations/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_orgs_filter_by_type(self, client, auth_headers, admin_user):
        self._create_org(client, auth_headers, "filter-org")
        r = client.get("/api/v1/organizations/?org_type=logistics", headers=auth_headers)
        assert r.status_code == 200

    def test_get_organization_by_id(self, client, auth_headers, admin_user):
        create_r = self._create_org(client, auth_headers, "get-org")
        org_id = create_r.json()["id"]
        r = client.get(f"/api/v1/organizations/{org_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == org_id

    def test_get_nonexistent_org_returns_404(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/organizations/99999", headers=auth_headers)
        assert r.status_code == 404


class TestOrganizationsUpdate:
    def _create_org(self, client, auth_headers, slug="update-org"):
        payload = {
            "name": "Update Org",
            "slug": slug,
            "type": "logistics",
            "country_code": "GH",
            "timezone": "Africa/Accra",
            "plan": "starter",
            "settings": {},
        }
        return client.post("/api/v1/organizations/", json=payload, headers=auth_headers)

    def test_update_organization(self, client, auth_headers, admin_user):
        org_id = self._create_org(client, auth_headers).json()["id"]
        r = client.patch(
            f"/api/v1/organizations/{org_id}",
            json={"name": "Renamed Org"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Renamed Org"

    def test_update_nonexistent_org_returns_404(self, client, auth_headers, admin_user):
        r = client.patch(
            "/api/v1/organizations/99999",
            json={"name": "Ghost"},
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_update_org_operator_forbidden(self, client, operator_headers, operator_user):
        r = client.patch(
            "/api/v1/organizations/1",
            json={"name": "Hack"},
            headers=operator_headers,
        )
        assert r.status_code == 403


# ===========================================================================
# VESSELS
# ===========================================================================

_VESSEL_PAYLOAD = {
    "name": "MV Test Vessel",
    "imo_number": "IMO9999999",
    "vessel_type": "bulk_carrier",
    "flag": "GH",
}


class TestVesselsAuth:
    def test_list_vessels_requires_auth(self, client):
        r = client.get("/api/v1/vessels/")
        assert r.status_code == 401

    def test_create_vessel_requires_auth(self, client):
        r = client.post("/api/v1/vessels/", json={})
        assert r.status_code == 401


class TestVesselsCreate:
    def test_create_vessel_success(self, client, auth_headers, admin_user):
        r = client.post("/api/v1/vessels/", json=_VESSEL_PAYLOAD, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == _VESSEL_PAYLOAD["name"]
        assert data["imo_number"] == _VESSEL_PAYLOAD["imo_number"]

    def test_create_vessel_duplicate_imo_returns_409(self, client, auth_headers, admin_user):
        client.post("/api/v1/vessels/", json=_VESSEL_PAYLOAD, headers=auth_headers)
        r = client.post("/api/v1/vessels/", json=_VESSEL_PAYLOAD, headers=auth_headers)
        assert r.status_code == 409

    def test_create_vessel_operator_can_create(self, client, operator_headers, operator_user):
        payload = {**_VESSEL_PAYLOAD, "imo_number": "IMO8888888"}
        r = client.post("/api/v1/vessels/", json=payload, headers=operator_headers)
        assert r.status_code == 201


class TestVesselsList:
    def _create(self, client, headers, imo="IMO1111111"):
        payload = {**_VESSEL_PAYLOAD, "imo_number": imo}
        return client.post("/api/v1/vessels/", json=payload, headers=headers)

    def test_list_vessels_returns_list(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/vessels/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_vessels_filter_by_type(self, client, auth_headers, admin_user):
        self._create(client, auth_headers)
        r = client.get("/api/v1/vessels/?vessel_type=bulk_carrier", headers=auth_headers)
        assert r.status_code == 200

    def test_get_vessel_positions(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/vessels/positions", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_vessel_by_id(self, client, auth_headers, admin_user):
        vessel_id = self._create(client, auth_headers).json()["id"]
        r = client.get(f"/api/v1/vessels/{vessel_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == vessel_id

    def test_get_nonexistent_vessel_returns_404(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/vessels/99999", headers=auth_headers)
        assert r.status_code == 404


class TestVesselsUpdate:
    def _create(self, client, headers):
        return client.post("/api/v1/vessels/", json=_VESSEL_PAYLOAD, headers=headers)

    def test_update_vessel(self, client, auth_headers, admin_user):
        vessel_id = self._create(client, auth_headers).json()["id"]
        r = client.put(
            f"/api/v1/vessels/{vessel_id}",
            json={"name": "Updated Vessel"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Vessel"

    def test_update_nonexistent_vessel_returns_404(self, client, auth_headers, admin_user):
        r = client.put("/api/v1/vessels/99999", json={"name": "X"}, headers=auth_headers)
        assert r.status_code == 404

    def test_update_vessel_position(self, client, auth_headers, admin_user):
        vessel_id = self._create(client, auth_headers).json()["id"]
        r = client.put(
            f"/api/v1/vessels/{vessel_id}/position",
            json={"latitude": 5.6037, "longitude": -0.1870, "speed": 12.5},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["current_lat"] == pytest.approx(5.6037, abs=1e-4)

    def test_update_position_nonexistent_vessel_returns_404(self, client, auth_headers, admin_user):
        r = client.put(
            "/api/v1/vessels/99999/position",
            json={"latitude": 0.0, "longitude": 0.0},
            headers=auth_headers,
        )
        assert r.status_code == 404


class TestVesselsDelete:
    def _create(self, client, headers, imo="IMO7777777"):
        payload = {**_VESSEL_PAYLOAD, "imo_number": imo}
        return client.post("/api/v1/vessels/", json=payload, headers=headers)

    def test_delete_vessel(self, client, auth_headers, admin_user):
        vessel_id = self._create(client, auth_headers).json()["id"]
        r = client.delete(f"/api/v1/vessels/{vessel_id}", headers=auth_headers)
        assert r.status_code == 200
        assert "deleted" in r.json()["message"].lower()

    def test_delete_nonexistent_vessel_returns_404(self, client, auth_headers, admin_user):
        r = client.delete("/api/v1/vessels/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_operator_cannot_delete_vessel(self, client, auth_headers, operator_headers, admin_user, operator_user):
        vessel_id = self._create(client, auth_headers, "IMO6666666").json()["id"]
        r = client.delete(f"/api/v1/vessels/{vessel_id}", headers=operator_headers)
        assert r.status_code == 403


# ===========================================================================
# VEHICLES
# ===========================================================================

class TestVehiclesAuth:
    def test_list_vehicles_requires_auth(self, client):
        r = client.get("/api/v1/vehicles/")
        assert r.status_code == 401

    def test_create_vehicle_requires_auth(self, client):
        r = client.post("/api/v1/vehicles/", json={})
        assert r.status_code == 401


def _create_org_and_vehicle(client, auth_headers, plate="GH-1234-A"):
    """Helper: create an org then a vehicle belonging to it. Returns vehicle JSON."""
    org_r = client.post(
        "/api/v1/organizations/",
        json={
            "name": "Vehicle Org",
            "slug": f"vehicle-org-{plate.replace(' ', '-').lower()}",
            "type": "logistics",
            "country_code": "GH",
            "timezone": "Africa/Accra",
            "plan": "starter",
            "settings": {},
        },
        headers=auth_headers,
    )
    org_id = org_r.json()["id"]
    v_r = client.post(
        "/api/v1/vehicles/",
        json={"organization_id": org_id, "plate_number": plate, "vehicle_type": "truck"},
        headers=auth_headers,
    )
    return v_r


class TestVehiclesCreate:
    def test_create_vehicle_success(self, client, auth_headers, admin_user):
        r = _create_org_and_vehicle(client, auth_headers, "GH-0001-A")
        assert r.status_code == 201
        data = r.json()
        assert data["plate_number"] == "GH-0001-A"

    def test_create_vehicle_duplicate_plate_same_org_returns_409(self, client, auth_headers, admin_user):
        _create_org_and_vehicle(client, auth_headers, "GH-0002-A")
        # Reuse the same plate + org — need to call the route directly
        # so we do a fresh create with same plate after the org already exists
        orgs = client.get("/api/v1/organizations/", headers=auth_headers).json()
        org_id = orgs[0]["id"]
        r = client.post(
            "/api/v1/vehicles/",
            json={"organization_id": org_id, "plate_number": "GH-0002-A", "vehicle_type": "truck"},
            headers=auth_headers,
        )
        assert r.status_code == 409


class TestVehiclesList:
    def test_list_vehicles_returns_list(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/vehicles/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_vehicle_by_id(self, client, auth_headers, admin_user):
        vehicle_id = _create_org_and_vehicle(client, auth_headers, "GH-0003-A").json()["id"]
        r = client.get(f"/api/v1/vehicles/{vehicle_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == vehicle_id

    def test_get_nonexistent_vehicle_returns_404(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/vehicles/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_get_vehicle_location(self, client, auth_headers, admin_user):
        vehicle_id = _create_org_and_vehicle(client, auth_headers, "GH-0004-A").json()["id"]
        r = client.get(f"/api/v1/vehicles/{vehicle_id}/location", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "vehicle_id" in data
        assert data["vehicle_id"] == vehicle_id

    def test_get_location_nonexistent_vehicle_returns_404(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/vehicles/99999/location", headers=auth_headers)
        assert r.status_code == 404


class TestVehiclesUpdate:
    def test_update_vehicle(self, client, auth_headers, admin_user):
        vehicle_id = _create_org_and_vehicle(client, auth_headers, "GH-0005-A").json()["id"]
        r = client.patch(
            f"/api/v1/vehicles/{vehicle_id}",
            json={"make": "Toyota", "model": "Hilux"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["make"] == "Toyota"

    def test_update_nonexistent_vehicle_returns_404(self, client, auth_headers, admin_user):
        r = client.patch("/api/v1/vehicles/99999", json={"make": "X"}, headers=auth_headers)
        assert r.status_code == 404


class TestVehiclesDelete:
    def test_delete_vehicle_returns_204(self, client, auth_headers, admin_user):
        vehicle_id = _create_org_and_vehicle(client, auth_headers, "GH-0006-A").json()["id"]
        r = client.delete(f"/api/v1/vehicles/{vehicle_id}", headers=auth_headers)
        assert r.status_code == 204

    def test_delete_nonexistent_vehicle_returns_404(self, client, auth_headers, admin_user):
        r = client.delete("/api/v1/vehicles/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_deleted_vehicle_not_found(self, client, auth_headers, admin_user):
        vehicle_id = _create_org_and_vehicle(client, auth_headers, "GH-0007-A").json()["id"]
        client.delete(f"/api/v1/vehicles/{vehicle_id}", headers=auth_headers)
        r = client.get(f"/api/v1/vehicles/{vehicle_id}", headers=auth_headers)
        assert r.status_code == 404


# ===========================================================================
# PLAYBOOKS
# ===========================================================================

_PLAYBOOK_PAYLOAD = {
    "incident_type": "oil_spill",
    "domain": "maritime",
    "title": "Oil Spill Response",
    "description": "Steps to handle an oil spill.",
    "steps": '["Assess area", "Deploy booms", "Notify authorities"]',
    "estimated_duration": 120,
}


class TestPlaybooksAuth:
    def test_list_playbooks_requires_auth(self, client):
        r = client.get("/api/v1/playbooks/")
        assert r.status_code == 401

    def test_create_playbook_requires_auth(self, client):
        r = client.post("/api/v1/playbooks/", json={})
        assert r.status_code == 401


class TestPlaybooksList:
    def test_list_playbooks_returns_list(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/playbooks/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_playbooks_filter_by_incident_type(self, client, auth_headers, admin_user):
        client.post("/api/v1/playbooks/", json=_PLAYBOOK_PAYLOAD, headers=auth_headers)
        r = client.get("/api/v1/playbooks/?incident_type=oil_spill", headers=auth_headers)
        assert r.status_code == 200

    def test_list_playbooks_filter_by_domain(self, client, auth_headers, admin_user):
        client.post("/api/v1/playbooks/", json=_PLAYBOOK_PAYLOAD, headers=auth_headers)
        r = client.get("/api/v1/playbooks/?domain=maritime", headers=auth_headers)
        assert r.status_code == 200


class TestPlaybooksCreate:
    def test_create_playbook_success(self, client, auth_headers, admin_user):
        r = client.post("/api/v1/playbooks/", json=_PLAYBOOK_PAYLOAD, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == _PLAYBOOK_PAYLOAD["title"]
        assert data["incident_type"] == _PLAYBOOK_PAYLOAD["incident_type"]
        assert data["version"] == 1

    def test_create_playbook_operator_forbidden(self, client, operator_headers, operator_user):
        r = client.post("/api/v1/playbooks/", json=_PLAYBOOK_PAYLOAD, headers=operator_headers)
        assert r.status_code == 403


class TestPlaybooksGetById:
    def test_get_playbook_by_id(self, client, auth_headers, admin_user):
        playbook_id = client.post(
            "/api/v1/playbooks/", json=_PLAYBOOK_PAYLOAD, headers=auth_headers
        ).json()["id"]
        r = client.get(f"/api/v1/playbooks/{playbook_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == playbook_id

    def test_get_nonexistent_playbook_returns_404(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/playbooks/99999", headers=auth_headers)
        assert r.status_code == 404


class TestPlaybooksUpdate:
    def test_update_playbook_title(self, client, auth_headers, admin_user):
        playbook_id = client.post(
            "/api/v1/playbooks/", json=_PLAYBOOK_PAYLOAD, headers=auth_headers
        ).json()["id"]
        r = client.put(
            f"/api/v1/playbooks/{playbook_id}",
            json={"title": "Updated Playbook"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["title"] == "Updated Playbook"

    def test_update_playbook_steps_increments_version(self, client, auth_headers, admin_user):
        playbook_id = client.post(
            "/api/v1/playbooks/", json=_PLAYBOOK_PAYLOAD, headers=auth_headers
        ).json()["id"]
        r = client.put(
            f"/api/v1/playbooks/{playbook_id}",
            json={"steps": '["New step 1", "New step 2"]'},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["version"] == 2

    def test_update_nonexistent_playbook_returns_404(self, client, auth_headers, admin_user):
        r = client.put("/api/v1/playbooks/99999", json={"title": "X"}, headers=auth_headers)
        assert r.status_code == 404


class TestPlaybooksDelete:
    def test_delete_playbook_deactivates(self, client, auth_headers, admin_user):
        playbook_id = client.post(
            "/api/v1/playbooks/", json=_PLAYBOOK_PAYLOAD, headers=auth_headers
        ).json()["id"]
        r = client.delete(f"/api/v1/playbooks/{playbook_id}", headers=auth_headers)
        assert r.status_code == 200
        assert "deactivated" in r.json()["message"].lower()

    def test_delete_nonexistent_playbook_returns_404(self, client, auth_headers, admin_user):
        r = client.delete("/api/v1/playbooks/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_delete_playbook_operator_forbidden(self, client, auth_headers, operator_headers, admin_user, operator_user):
        playbook_id = client.post(
            "/api/v1/playbooks/", json=_PLAYBOOK_PAYLOAD, headers=auth_headers
        ).json()["id"]
        r = client.delete(f"/api/v1/playbooks/{playbook_id}", headers=operator_headers)
        assert r.status_code == 403


class TestPlaybooksSearch:
    def test_search_playbooks_by_incident_type(self, client, auth_headers, admin_user):
        client.post("/api/v1/playbooks/", json=_PLAYBOOK_PAYLOAD, headers=auth_headers)
        r = client.get("/api/v1/playbooks/search/oil_spill", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_search_playbooks_requires_auth(self, client):
        r = client.get("/api/v1/playbooks/search/oil_spill")
        assert r.status_code == 401


# ===========================================================================
# NOTIFICATIONS
# ===========================================================================

class TestNotificationsAuth:
    def test_list_notifications_requires_auth(self, client):
        r = client.get("/api/v1/notifications/")
        assert r.status_code == 401

    def test_unread_count_requires_auth(self, client):
        r = client.get("/api/v1/notifications/unread-count")
        assert r.status_code == 401

    def test_preferences_requires_auth(self, client):
        r = client.get("/api/v1/notifications/preferences")
        assert r.status_code == 401


class TestNotificationsList:
    def test_list_notifications_returns_list(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/notifications/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_notifications_unread_only(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/notifications/?unread_only=true", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_unread_count(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/notifications/unread-count", headers=auth_headers)
        assert r.status_code == 200
        assert "unread_count" in r.json()
        assert isinstance(r.json()["unread_count"], int)


class TestNotificationsReadAll:
    def test_mark_all_read(self, client, auth_headers, admin_user):
        r = client.post("/api/v1/notifications/read-all", headers=auth_headers)
        assert r.status_code == 200
        assert "message" in r.json()

    def test_mark_nonexistent_notification_read_returns_404(self, client, auth_headers, admin_user):
        r = client.post("/api/v1/notifications/99999/read", headers=auth_headers)
        assert r.status_code == 404


class TestNotificationPreferences:
    def test_get_preferences_creates_default(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/notifications/preferences", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "email_enabled" in data
        assert "user_id" in data

    def test_update_preferences(self, client, auth_headers, admin_user):
        r = client.put(
            "/api/v1/notifications/preferences",
            json={"email_enabled": False, "websocket_sound": False},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["email_enabled"] is False

    def test_update_preferences_requires_auth(self, client):
        r = client.put("/api/v1/notifications/preferences", json={"email_enabled": False})
        assert r.status_code == 401


# ===========================================================================
# MOVEMENTS
# ===========================================================================

_MOVEMENT_PAYLOAD = {
    "cargo": "Iron Ore",
    "route": "Port Tema -> Ouagadougou",
    "laycan_start": _past_dt(2),
    "laycan_end": _future_dt(5),
}


class TestMovementsAuth:
    def test_list_movements_requires_auth(self, client):
        r = client.get("/api/v1/movements/")
        assert r.status_code == 401

    def test_create_movement_requires_auth(self, client):
        r = client.post("/api/v1/movements/", json={})
        assert r.status_code == 401


class TestMovementsList:
    def test_list_movements_returns_list(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/movements/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_movements_filter_by_status(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/movements/?status=active", headers=auth_headers)
        assert r.status_code == 200


class TestMovementsCreate:
    def test_create_movement_success(self, client, auth_headers, admin_user):
        r = client.post("/api/v1/movements/", json=_MOVEMENT_PAYLOAD, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert data["cargo"] == _MOVEMENT_PAYLOAD["cargo"]
        assert data["status"] == "active"

    def test_create_movement_invalid_laycan_returns_400(self, client, auth_headers, admin_user):
        payload = {
            **_MOVEMENT_PAYLOAD,
            "laycan_start": _future_dt(5),
            "laycan_end": _future_dt(1),
        }
        r = client.post("/api/v1/movements/", json=payload, headers=auth_headers)
        assert r.status_code == 400

    def test_create_movement_operator_allowed(self, client, operator_headers, operator_user):
        r = client.post("/api/v1/movements/", json=_MOVEMENT_PAYLOAD, headers=operator_headers)
        assert r.status_code == 201


class TestMovementsGetById:
    def test_get_movement_by_id(self, client, auth_headers, admin_user):
        movement_id = client.post(
            "/api/v1/movements/", json=_MOVEMENT_PAYLOAD, headers=auth_headers
        ).json()["id"]
        r = client.get(f"/api/v1/movements/{movement_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == movement_id

    def test_get_nonexistent_movement_returns_404(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/movements/99999", headers=auth_headers)
        assert r.status_code == 404


class TestMovementsUpdate:
    def test_update_movement(self, client, auth_headers, admin_user):
        movement_id = client.post(
            "/api/v1/movements/", json=_MOVEMENT_PAYLOAD, headers=auth_headers
        ).json()["id"]
        r = client.put(
            f"/api/v1/movements/{movement_id}",
            json={"status": "completed"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

    def test_update_nonexistent_movement_returns_404(self, client, auth_headers, admin_user):
        r = client.put("/api/v1/movements/99999", json={"status": "completed"}, headers=auth_headers)
        assert r.status_code == 404

    def test_update_movement_location(self, client, auth_headers, admin_user):
        movement_id = client.post(
            "/api/v1/movements/", json=_MOVEMENT_PAYLOAD, headers=auth_headers
        ).json()["id"]
        r = client.put(
            f"/api/v1/movements/{movement_id}/location?location=Kumasi&lat=6.69&lng=-1.62",
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["location"] == "Kumasi"

    def test_update_location_nonexistent_movement_returns_404(self, client, auth_headers, admin_user):
        r = client.put(
            "/api/v1/movements/99999/location?location=Nowhere",
            headers=auth_headers,
        )
        assert r.status_code == 404


class TestMovementsDelete:
    def test_delete_movement(self, client, auth_headers, admin_user):
        movement_id = client.post(
            "/api/v1/movements/", json=_MOVEMENT_PAYLOAD, headers=auth_headers
        ).json()["id"]
        r = client.delete(f"/api/v1/movements/{movement_id}", headers=auth_headers)
        assert r.status_code == 200
        assert "deleted" in r.json()["message"].lower()

    def test_delete_nonexistent_movement_returns_404(self, client, auth_headers, admin_user):
        r = client.delete("/api/v1/movements/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_operator_cannot_delete_movement(self, client, auth_headers, operator_headers, admin_user, operator_user):
        movement_id = client.post(
            "/api/v1/movements/", json=_MOVEMENT_PAYLOAD, headers=auth_headers
        ).json()["id"]
        r = client.delete(f"/api/v1/movements/{movement_id}", headers=operator_headers)
        assert r.status_code == 403


# ===========================================================================
# SUPER ADMIN
# ===========================================================================

class TestSuperAdminAuth:
    """All super-admin endpoints must reject non-super-admin callers."""

    def test_dashboard_requires_auth(self, client):
        r = client.get("/api/v1/super-admin/dashboard")
        assert r.status_code == 401

    def test_list_all_users_requires_auth(self, client):
        r = client.get("/api/v1/super-admin/users")
        assert r.status_code == 401

    def test_system_health_requires_auth(self, client):
        r = client.get("/api/v1/super-admin/system/health")
        assert r.status_code == 401

    def test_lock_user_requires_auth(self, client):
        r = client.post("/api/v1/super-admin/users/1/lock")
        assert r.status_code == 401

    def test_unlock_user_requires_auth(self, client):
        r = client.post("/api/v1/super-admin/users/1/unlock")
        assert r.status_code == 401

    def test_change_role_requires_auth(self, client):
        r = client.post("/api/v1/super-admin/users/1/change-role?new_role=operator")
        assert r.status_code == 401

    def test_operator_cannot_access_dashboard(self, client, operator_headers, operator_user):
        r = client.get("/api/v1/super-admin/dashboard", headers=operator_headers)
        assert r.status_code == 403


class TestSuperAdminDashboard:
    def test_dashboard_returns_summary(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/super-admin/dashboard", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "total_users" in data
        assert "active_users" in data
        assert "total_organizations" in data
        assert "users_by_role" in data
        assert "timestamp" in data

    def test_dashboard_counts_are_ints(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/super-admin/dashboard", headers=auth_headers)
        data = r.json()
        assert isinstance(data["total_users"], int)
        assert isinstance(data["active_users"], int)
        assert isinstance(data["total_organizations"], int)


class TestSuperAdminListUsers:
    def test_list_all_users(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/super-admin/users", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_list_all_users_filter_by_role(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/super-admin/users?role=admin", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1

    def test_list_all_users_pagination(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/super-admin/users?skip=0&limit=5", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()["items"]) <= 5


class TestSuperAdminOrganizations:
    def test_list_organizations(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/super-admin/organizations", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "items" in data


class TestSuperAdminLockUnlock:
    def test_lock_user(self, client, auth_headers, admin_user, operator_user):
        r = client.post(
            f"/api/v1/super-admin/users/{operator_user.id}/lock",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert "locked" in r.json()["message"].lower()

    def test_lock_nonexistent_user_returns_404(self, client, auth_headers, admin_user):
        r = client.post("/api/v1/super-admin/users/99999/lock", headers=auth_headers)
        assert r.status_code == 404

    def test_cannot_lock_own_account(self, client, auth_headers, admin_user):
        r = client.post(
            f"/api/v1/super-admin/users/{admin_user.id}/lock",
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_unlock_user(self, client, auth_headers, admin_user, operator_user):
        # Lock first
        client.post(f"/api/v1/super-admin/users/{operator_user.id}/lock", headers=auth_headers)
        r = client.post(
            f"/api/v1/super-admin/users/{operator_user.id}/unlock",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert "unlocked" in r.json()["message"].lower()

    def test_unlock_nonexistent_user_returns_404(self, client, auth_headers, admin_user):
        r = client.post("/api/v1/super-admin/users/99999/unlock", headers=auth_headers)
        assert r.status_code == 404


class TestSuperAdminChangeRole:
    def test_change_role_success(self, client, auth_headers, admin_user, operator_user):
        r = client.post(
            f"/api/v1/super-admin/users/{operator_user.id}/change-role?new_role=supervisor",
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "supervisor" in data["message"]

    def test_change_role_invalid_role_returns_422(self, client, auth_headers, admin_user, operator_user):
        r = client.post(
            f"/api/v1/super-admin/users/{operator_user.id}/change-role?new_role=hacker",
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_change_role_nonexistent_user_returns_404(self, client, auth_headers, admin_user):
        r = client.post(
            "/api/v1/super-admin/users/99999/change-role?new_role=operator",
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_cannot_change_own_role(self, client, auth_headers, admin_user):
        r = client.post(
            f"/api/v1/super-admin/users/{admin_user.id}/change-role?new_role=operator",
            headers=auth_headers,
        )
        assert r.status_code == 400


class TestSuperAdminSystemHealth:
    def test_system_health_returns_db_status(self, client, auth_headers, admin_user):
        r = client.get("/api/v1/super-admin/system/health", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "database" in data
        assert data["database"] == "healthy"
        assert "timestamp" in data
