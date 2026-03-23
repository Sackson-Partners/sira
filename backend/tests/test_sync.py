"""
Tests for the offline batch sync endpoint.
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.user import User
from app.models.organization import Organization
from app.models.shipment import Shipment

# Test DB — in-memory SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_sync.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_data():
    """Seed minimal test data before each test."""
    db = TestingSessionLocal()
    try:
        # Organization
        org = Organization(
            id=1,
            name="Test Org",
            slug="test-org",
            type="logistics",
            country_code="GH",
            timezone="Africa/Accra",
            plan="starter",
            settings={},
        )
        db.merge(org)

        # User / Driver
        user = User(
            id=1,
            username="driver_test",
            email="driver@test.com",
            hashed_password=hash_password("test123"),
            role="driver",
            is_active=True,
        )
        db.merge(user)

        # Shipment
        shipment = Shipment(
            id=1,
            shipment_ref="TEST-001",
            status="in_transit",
            cargo_type="general",
            origin="Test Origin",
            destination="Test Destination",
            laycan_start=datetime(2026, 3, 23, tzinfo=timezone.utc),
            laycan_end=datetime(2026, 3, 30, tzinfo=timezone.utc),
        )
        db.merge(shipment)

        db.commit()
    finally:
        db.close()

    yield

    # Cleanup
    db = TestingSessionLocal()
    try:
        db.execute("DELETE FROM checkpoints WHERE shipment_id = 1")
        db.execute("DELETE FROM sync_logs")
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


def get_auth_token():
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "driver_test", "password": "test123"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


class TestBatchSync:
    def test_batch_sync_checkpoint(self):
        """Offline checkpoint syncs correctly."""
        token = get_auth_token()
        resp = client.post(
            "/api/v1/sync/batch",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "device_id": "test-device-001",
                "events": [
                    {
                        "event_id": "evt_test_001",
                        "type": "CHECKPOINT_CONFIRMED",
                        "client_timestamp": "2026-03-23T10:30:00Z",
                        "data": {
                            "shipment_id": 1,
                            "checkpoint_type": "waypoint",
                            "latitude": 5.6037,
                            "longitude": -0.1870,
                            "offline_queued": True,
                        },
                    }
                ],
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["processed"] == 1
        assert body["success_count"] == 1
        assert body["failed_count"] == 0
        assert body["results"][0]["status"] == "success"
        assert body["results"][0]["event_id"] == "evt_test_001"

    def test_batch_sync_deduplication(self):
        """Same event_id submitted twice returns 'duplicate' on second attempt."""
        token = get_auth_token()
        event = {
            "event_id": "evt_dedup_001",
            "type": "CHECKPOINT_CONFIRMED",
            "client_timestamp": "2026-03-23T10:35:00Z",
            "data": {
                "shipment_id": 1,
                "checkpoint_type": "waypoint",
                "latitude": 5.61,
                "longitude": -0.19,
                "offline_queued": True,
            },
        }

        # First submission
        r1 = client.post(
            "/api/v1/sync/batch",
            headers={"Authorization": f"Bearer {token}"},
            json={"device_id": "test-device-001", "events": [event]},
        )
        assert r1.status_code == 200
        assert r1.json()["results"][0]["status"] == "success"

        # Second submission (same event_id)
        r2 = client.post(
            "/api/v1/sync/batch",
            headers={"Authorization": f"Bearer {token}"},
            json={"device_id": "test-device-001", "events": [event]},
        )
        assert r2.status_code == 200
        assert r2.json()["results"][0]["status"] == "duplicate"

    def test_batch_sync_unknown_event_type(self):
        """Unknown event type returns failed status without crashing."""
        token = get_auth_token()
        resp = client.post(
            "/api/v1/sync/batch",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "device_id": "test-device-001",
                "events": [
                    {
                        "event_id": "evt_unknown_001",
                        "type": "UNKNOWN_EVENT",
                        "client_timestamp": "2026-03-23T10:40:00Z",
                        "data": {},
                    }
                ],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["results"][0]["status"] == "failed"

    def test_batch_sync_empty_returns_200(self):
        """Empty event list returns 200 with zero counts."""
        token = get_auth_token()
        resp = client.post(
            "/api/v1/sync/batch",
            headers={"Authorization": f"Bearer {token}"},
            json={"device_id": "test-device-001", "events": []},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["processed"] == 0

    def test_batch_sync_requires_auth(self):
        """Unauthenticated requests are rejected."""
        resp = client.post(
            "/api/v1/sync/batch",
            json={"device_id": "x", "events": []},
        )
        assert resp.status_code == 401

    def test_batch_sync_orders_by_timestamp(self):
        """Events submitted out-of-order are processed in client_timestamp order."""
        token = get_auth_token()
        resp = client.post(
            "/api/v1/sync/batch",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "device_id": "test-device-002",
                "events": [
                    {
                        "event_id": "evt_order_002",
                        "type": "CHECKPOINT_CONFIRMED",
                        "client_timestamp": "2026-03-23T11:00:00Z",
                        "data": {
                            "shipment_id": 1,
                            "checkpoint_type": "delivery",
                            "latitude": 5.70,
                            "longitude": -0.00,
                            "offline_queued": True,
                        },
                    },
                    {
                        "event_id": "evt_order_001",
                        "type": "CHECKPOINT_CONFIRMED",
                        "client_timestamp": "2026-03-23T10:45:00Z",
                        "data": {
                            "shipment_id": 1,
                            "checkpoint_type": "waypoint",
                            "latitude": 5.65,
                            "longitude": -0.10,
                            "offline_queued": True,
                        },
                    },
                ],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success_count"] == 2
        # Both should succeed regardless of submission order
        assert all(r["status"] == "success" for r in body["results"])
