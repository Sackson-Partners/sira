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
