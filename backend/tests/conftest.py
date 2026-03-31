"""
Pytest Configuration and Fixtures

Environment variables are set BEFORE any app imports so that Pydantic Settings
reads them from the environment rather than raising ValidationError.
"""

import os

# ── Test environment variables ────────────────────────────────────────────────
# Must be set before *any* app module is imported (settings is created at import
# time via @lru_cache).
# Use os.environ[] (not setdefault) for ENVIRONMENT so a shell ENVIRONMENT=production
# never leaks into the test run and causes the docs-visibility tests to fight each other.
os.environ["ENVIRONMENT"] = "staging"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")   # prevent empty-URL crash at import
os.environ.setdefault("SECRET_KEY", "sira-test-secret-key-for-tests-only-min-32-chars!")
os.environ.setdefault("ADMIN_INITIAL_PASSWORD", "TestAdmin@Sira1")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("ALLOWED_ORIGINS", "https://sira-teal.vercel.app")  # CORS allowlist for tests
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.user import User


# In-memory SQLite used for all test interactions (overrides the real engine
# via the dependency injection override on get_db).
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Fresh in-memory database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """TestClient wired to the in-memory test database."""
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ── User fixtures ─────────────────────────────────────────────────────────────
# Passwords here are intentionally simple (they bypass the schema validator
# because users are inserted directly into the DB). They are only used to
# authenticate via /token in tests — not via /register.

@pytest.fixture(scope="function")
def admin_user(db_session):
    user = User(
        username="admin",
        email="admin@test.com",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def operator_user(db_session):
    user = User(
        username="operator",
        email="operator@test.com",
        hashed_password=hash_password("operatorpass123"),
        role="operator",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def security_lead_user(db_session):
    user = User(
        username="sec_lead",
        email="sec_lead@test.com",
        hashed_password=hash_password("secleadpass123"),
        role="security_lead",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def inactive_user(db_session):
    user = User(
        username="inactive",
        email="inactive@test.com",
        hashed_password=hash_password("inactivepass123"),
        role="operator",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ── Token / header fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="function")
def admin_token(client, admin_user):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "adminpass123"},
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def operator_token(client, operator_user):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "operator", "password": "operatorpass123"},
    )
    assert response.status_code == 200, f"Operator login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset slowapi in-memory counter before every test to prevent cross-test interference."""
    from app.core.limiter import limiter
    try:
        if hasattr(limiter, "_storage") and hasattr(limiter._storage, "reset"):
            limiter._storage.reset()
    except Exception:
        pass
    yield


@pytest.fixture(scope="function")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="function")
def operator_headers(operator_token):
    return {"Authorization": f"Bearer {operator_token}"}
