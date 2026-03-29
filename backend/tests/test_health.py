"""
Health Check Tests
"""

import pytest
from fastapi import status


class TestHealth:
    """Health and root endpoint tests."""

    def test_health_check_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    def test_health_check_structure(self, client):
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data

    def test_health_check_status_value(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] in ("healthy", "degraded")

    def test_root_endpoint(self, client):
        """Root returns SPA index or JSON fallback — both are 200."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK

    def test_docs_hidden_in_production(self, client):
        """When DEBUG=False, FastAPI must have docs_url=None (Swagger UI disabled)."""
        from app.core.config import settings
        from app.main import app
        if settings.DEBUG:
            pytest.skip("DEBUG=True in this environment — docs are intentionally visible")
        # The SPA catch-all returns 200 for /docs (it serves the React app).
        # The real check is that FastAPI's docs_url is None, meaning no Swagger UI route.
        assert app.docs_url is None, "docs_url should be None in production"
        # Verify the response is NOT the Swagger UI HTML
        response = client.get("/docs")
        assert "swagger" not in response.text.lower()
        assert "openapi" not in response.text.lower() or response.headers.get("content-type", "").startswith("text/html")

    def test_redoc_hidden_in_production(self, client):
        from app.core.config import settings
        from app.main import app
        if settings.DEBUG:
            pytest.skip("DEBUG=True in this environment")
        assert app.redoc_url is None, "redoc_url should be None in production"

    def test_openapi_schema_hidden_in_production(self, client):
        """When DEBUG=False, /openapi.json must NOT return an OpenAPI schema."""
        from app.core.config import settings
        from app.main import app
        if settings.DEBUG:
            pytest.skip("DEBUG=True in this environment")
        assert app.openapi_url is None, "openapi_url should be None in production"
        # The SPA catch-all may return 200 but it must not be a valid OpenAPI document
        response = client.get("/openapi.json")
        if response.status_code == 200:
            data = response.json() if "application/json" in response.headers.get("content-type", "") else {}
            assert "openapi" not in data, "openapi.json must not return an OpenAPI schema in production"


class TestApiV1HealthEndpoints:
    """Tests for the /api/v1/health/* endpoints (versioned health router)."""

    def test_health_check_returns_200(self, client):
        resp = client.get("/api/v1/health/")
        assert resp.status_code == status.HTTP_200_OK

    def test_health_check_has_status_field(self, client):
        resp = client.get("/api/v1/health/")
        data = resp.json()
        assert "status" in data

    def test_health_check_has_timestamp(self, client):
        resp = client.get("/api/v1/health/")
        data = resp.json()
        assert "timestamp" in data

    def test_health_check_has_checks(self, client):
        resp = client.get("/api/v1/health/")
        data = resp.json()
        assert "checks" in data
        assert "database" in data["checks"]

    def test_health_database_is_healthy(self, client):
        resp = client.get("/api/v1/health/")
        data = resp.json()
        assert data["checks"]["database"]["status"] == "healthy"

    def test_health_status_value_is_valid(self, client):
        resp = client.get("/api/v1/health/")
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")

    def test_health_has_version(self, client):
        resp = client.get("/api/v1/health/")
        data = resp.json()
        assert "version" in data

    def test_health_without_slash_also_works(self, client):
        """Both /api/v1/health and /api/v1/health/ should respond."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == status.HTTP_200_OK

    def test_readiness_probe_returns_200(self, client):
        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == status.HTTP_200_OK

    def test_readiness_probe_returns_ready_status(self, client):
        resp = client.get("/api/v1/health/ready")
        data = resp.json()
        assert data.get("status") == "ready"

    def test_liveness_probe_returns_200(self, client):
        resp = client.get("/api/v1/health/live")
        assert resp.status_code == status.HTTP_200_OK

    def test_liveness_probe_returns_alive_status(self, client):
        resp = client.get("/api/v1/health/live")
        data = resp.json()
        assert data.get("status") == "alive"

    def test_health_without_auth_is_public(self, client):
        """Health endpoint must be publicly accessible without a token."""
        resp = client.get("/api/v1/health/")
        assert resp.status_code not in (401, 403)

    def test_readiness_without_auth_is_public(self, client):
        resp = client.get("/api/v1/health/ready")
        assert resp.status_code not in (401, 403)

    def test_liveness_without_auth_is_public(self, client):
        resp = client.get("/api/v1/health/live")
        assert resp.status_code not in (401, 403)
