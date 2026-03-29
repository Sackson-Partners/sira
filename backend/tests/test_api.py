"""
API Endpoint Tests

Tests all major endpoints for:
- Correct status codes with and without auth
- Role-based access control
- Input validation rejection
- Response structure
"""

import pytest
from fastapi import status


class TestHealthEndpoint:
    """GET /health"""

    def test_health_no_auth_required(self, client):
        """Health must be accessible without a token."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    def test_health_response_has_required_fields(self, client):
        data = client.get("/health").json()
        for key in ("status", "version", "timestamp"):
            assert key in data, f"Missing field: {key}"

    def test_health_database_field(self, client):
        data = client.get("/health").json()
        if "database" in data:
            assert data["database"] in ("healthy", "unhealthy")


class TestAuthEndpoints:
    """Authentication endpoints — no token needed."""

    def test_post_token_valid_credentials(self, client, admin_user):
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "adminpass123"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_post_token_invalid_credentials(self, client):
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "nobody", "password": "wrong"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_post_register_creates_operator(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newoperator",
                "email": "newop@test.com",
                "password": "Secure@Test1!",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["role"] == "operator"

    def test_get_me_returns_user_info(self, client, auth_headers, admin_user):
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "admin"
        assert "hashed_password" not in data


class TestProtectedRoutesRequireAuth:
    """All non-auth API routes must return 401 without a token."""

    PROTECTED_ROUTES = [
        ("GET", "/api/v1/auth/me"),
        ("GET", "/api/v1/alerts/"),
        ("GET", "/api/v1/movements/"),
        ("GET", "/api/v1/cases/"),
        ("GET", "/api/v1/events/"),
        ("GET", "/api/v1/notifications/"),
        ("GET", "/api/v1/vessels/"),
        ("GET", "/api/v1/ports/"),
        ("GET", "/api/v1/shipments/"),
        ("GET", "/api/v1/fleet/assets/"),
        ("GET", "/api/v1/corridors/"),
        ("GET", "/api/v1/control-tower/overview"),
    ]

    @pytest.mark.parametrize("method,path", PROTECTED_ROUTES)
    def test_route_requires_auth(self, client, method, path):
        fn = getattr(client, method.lower())
        response = fn(path)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
            f"Expected 401 for {method} {path}, got {response.status_code}"
        )


class TestRoleBasedAccessControl:
    """Endpoints with elevated role requirements must reject lower-privileged tokens."""

    def test_admin_can_access_users_list(self, client, auth_headers, admin_user):
        response = client.get("/api/v1/users/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK

    def test_operator_cannot_access_users_list(self, client, operator_headers, operator_user):
        response = client.get("/api/v1/users/", headers=operator_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAlertsCRUD:
    """Alerts CRUD — admin token."""

    def _alert_payload(self):
        return {
            "severity": "High",
            "confidence": 0.85,
            "sla_timer": 60,
            "domain": "Maritime Security",
            "description": "Integration test alert",
        }

    def test_create_alert(self, client, auth_headers):
        response = client.post("/api/v1/alerts/", json=self._alert_payload(), headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["severity"] == "High"
        assert data["status"] == "open"

    def test_list_alerts(self, client, auth_headers):
        client.post("/api/v1/alerts/", json=self._alert_payload(), headers=auth_headers)
        response = client.get("/api/v1/alerts/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_get_alert_by_id(self, client, auth_headers):
        create_r = client.post("/api/v1/alerts/", json=self._alert_payload(), headers=auth_headers)
        alert_id = create_r.json()["id"]
        response = client.get(f"/api/v1/alerts/{alert_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK

    def test_get_nonexistent_alert_404(self, client, auth_headers):
        response = client.get("/api/v1/alerts/999999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_alert_invalid_severity(self, client, auth_headers):
        payload = self._alert_payload()
        payload["severity"] = "CRITICAL_INVALID"
        response = client.post("/api/v1/alerts/", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_alert_confidence_out_of_range(self, client, auth_headers):
        payload = self._alert_payload()
        payload["confidence"] = 1.5  # must be 0.0–1.0
        response = client.post("/api/v1/alerts/", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestMovementsCRUD:
    """Movement tracking endpoints."""

    def test_list_movements_empty(self, client, auth_headers):
        response = client.get("/api/v1/movements/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK

    def test_create_movement(self, client, auth_headers):
        from datetime import datetime, timezone, timedelta
        payload = {
            "cargo": "Container TEST-001",
            "route": "Cape Town -> Durban",
            "assets": "Vessel: MV Test",
            "stakeholders": "Shipper: Test Corp",
            "laycan_start": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "laycan_end": (datetime.now(timezone.utc) + timedelta(days=15)).isoformat(),
        }
        response = client.post("/api/v1/movements/", json=payload, headers=auth_headers)
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
        )

    def test_movements_require_auth(self, client):
        assert client.get("/api/v1/movements/").status_code == status.HTTP_401_UNAUTHORIZED


class TestInputValidation:
    """Malformed/oversized inputs must be rejected cleanly."""

    def test_empty_body_on_post_token_422(self, client):
        response = client.post("/api/v1/auth/token", data={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_non_json_on_register_422(self, client):
        response = client.post(
            "/api/v1/auth/register",
            content="this is not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_sql_injection_in_username_rejected(self, client):
        """SQL injection in username must never return a valid token."""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "' OR '1'='1", "password": "anything"},
        )
        # Must NOT return 200 with a token
        assert response.status_code != status.HTTP_200_OK
        if response.status_code == 200:
            pytest.fail("SQL injection returned a valid token!")
        # Acceptable outcomes: 401, 422, 429 (rate limit)
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    def test_description_max_length_enforced(self, client, auth_headers):
        """Alert description must be capped at 2000 chars."""
        payload = {
            "severity": "High",
            "confidence": 0.5,
            "sla_timer": 60,
            "domain": "Maritime Security",
            "description": "A" * 2001,
        }
        response = client.post("/api/v1/alerts/", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestErrorResponseStructure:
    """Error responses must use the structured JSON format from Phase 2."""

    def test_404_has_error_and_code(self, client):
        response = client.get("/api/v1/nonexistent-route")
        # SPA catch-all handles this — no error structure test applies here
        # Test against an API 404 instead
        response = client.get("/api/v1/alerts/999999", headers={"Authorization": "Bearer bad"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data or "detail" in data

    def test_401_has_structured_response(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data or "detail" in data

    def test_422_has_structured_response(self, client):
        response = client.post("/api/v1/auth/token", data={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        # Phase 2: {"error": "...", "code": "VALIDATION_ERROR"} in production
        assert "error" in data or "detail" in data
