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

    def test_docs_accessible(self, client):
        """Docs are visible in non-production environments (ENVIRONMENT != 'production')."""
        from app.main import app
        from app.core.config import settings
        if settings.ENVIRONMENT == "production":
            pytest.skip("ENVIRONMENT=production — docs hidden by design")
        assert app.docs_url == "/docs", "docs_url must be /docs"
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

    def test_redoc_accessible(self, client):
        """ReDoc visible in non-production environments."""
        from app.main import app
        from app.core.config import settings
        if settings.ENVIRONMENT == "production":
            pytest.skip("ENVIRONMENT=production — docs hidden by design")
        assert app.redoc_url == "/redoc", "redoc_url must be /redoc"
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_openapi_schema_accessible(self, client):
        """/openapi.json visible in non-production environments."""
        from app.main import app
        from app.core.config import settings
        if settings.ENVIRONMENT == "production":
            pytest.skip("ENVIRONMENT=production — docs hidden by design")
        assert app.openapi_url == "/openapi.json", "openapi_url must be /openapi.json"
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data


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
