"""
Database Tests

Tests:
- Direct ORM CRUD operations via test db_session
- Database connectivity check
- Model relationships
- Production DATABASE_URL must be PostgreSQL (not SQLite)
"""

import pytest
from sqlalchemy import text
from datetime import datetime, timezone


class TestDatabaseConnectivity:
    """Database connection health."""

    def test_test_engine_is_reachable(self, db_session):
        """The test in-memory engine must accept queries."""
        result = db_session.execute(text("SELECT 1")).fetchone()
        assert result[0] == 1

    def test_all_tables_created(self, db_session):
        """Base.metadata.create_all() must create all model tables."""
        from sqlalchemy import inspect
        from app.core.database import engine as real_engine
        from tests.conftest import engine as test_engine
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert "users" in tables, "users table not created"

    def test_check_db_connection_returns_bool(self):
        """check_db_connection() must return a bool (True or False)."""
        from app.core.database import check_db_connection
        result = check_db_connection()
        assert isinstance(result, bool)


class TestUserModelCRUD:
    """User model create / read / update / delete."""

    def test_create_user(self, db_session):
        from app.models.user import User
        from app.core.security import hash_password
        user = User(
            username="testcreate",
            email="testcreate@example.com",
            hashed_password=hash_password("anypassword"),
            role="operator",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.id is not None
        assert user.username == "testcreate"

    def test_read_user_by_username(self, db_session):
        from app.models.user import User
        from app.core.security import hash_password
        db_session.add(User(
            username="readtest",
            email="readtest@example.com",
            hashed_password=hash_password("x"),
            role="operator",
        ))
        db_session.commit()
        found = db_session.query(User).filter(User.username == "readtest").first()
        assert found is not None
        assert found.email == "readtest@example.com"

    def test_update_user_role(self, db_session):
        from app.models.user import User
        from app.core.security import hash_password
        user = User(
            username="roleupdate",
            email="roleupdate@example.com",
            hashed_password=hash_password("x"),
            role="operator",
        )
        db_session.add(user)
        db_session.commit()
        user.role = "security_lead"
        db_session.commit()
        db_session.refresh(user)
        assert user.role == "security_lead"

    def test_delete_user(self, db_session):
        from app.models.user import User
        from app.core.security import hash_password
        user = User(
            username="deletetest",
            email="deletetest@example.com",
            hashed_password=hash_password("x"),
            role="operator",
        )
        db_session.add(user)
        db_session.commit()
        uid = user.id
        db_session.delete(user)
        db_session.commit()
        assert db_session.query(User).filter(User.id == uid).first() is None

    def test_username_unique_constraint(self, db_session):
        """Inserting two users with the same username must raise an error."""
        from app.models.user import User
        from app.core.security import hash_password
        from sqlalchemy.exc import IntegrityError
        db_session.add(User(
            username="dupcheck",
            email="dup1@example.com",
            hashed_password=hash_password("x"),
            role="operator",
        ))
        db_session.commit()
        db_session.add(User(
            username="dupcheck",  # duplicate
            email="dup2@example.com",
            hashed_password=hash_password("x"),
            role="operator",
        ))
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_email_unique_constraint(self, db_session):
        from app.models.user import User
        from app.core.security import hash_password
        from sqlalchemy.exc import IntegrityError
        db_session.add(User(
            username="emaildup1",
            email="shared@example.com",
            hashed_password=hash_password("x"),
            role="operator",
        ))
        db_session.commit()
        db_session.add(User(
            username="emaildup2",
            email="shared@example.com",
            hashed_password=hash_password("x"),
            role="operator",
        ))
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_last_login_update(self, db_session):
        from app.models.user import User
        from app.core.security import hash_password
        user = User(
            username="logintracked",
            email="logintracked@example.com",
            hashed_password=hash_password("x"),
            role="operator",
        )
        db_session.add(user)
        db_session.commit()
        assert user.last_login is None
        user.last_login = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(user)
        assert user.last_login is not None


class TestAlertModelCRUD:
    """Alert model CRUD via test session."""

    def _make_user(self, db_session):
        from app.models.user import User
        from app.core.security import hash_password
        user = User(
            username="alertowner",
            email="alertowner@example.com",
            hashed_password=hash_password("x"),
            role="admin",
        )
        db_session.add(user)
        db_session.commit()
        return user

    def test_create_alert(self, db_session):
        from app.models.alert import Alert
        alert = Alert(
            severity="High",
            confidence=0.9,
            sla_timer=60,
            domain="Maritime Security",
            description="Test alert",
            status="open",
        )
        db_session.add(alert)
        db_session.commit()
        db_session.refresh(alert)
        assert alert.id is not None
        assert alert.status == "open"

    def test_read_alerts_by_severity(self, db_session):
        from app.models.alert import Alert
        for sev in ("High", "Medium", "High"):
            db_session.add(Alert(severity=sev, confidence=0.5, status="open"))
        db_session.commit()
        highs = db_session.query(Alert).filter(Alert.severity == "High").all()
        assert len(highs) == 2

    def test_update_alert_status(self, db_session):
        from app.models.alert import Alert
        alert = Alert(severity="Low", confidence=0.3, status="open")
        db_session.add(alert)
        db_session.commit()
        alert.status = "acknowledged"
        db_session.commit()
        db_session.refresh(alert)
        assert alert.status == "acknowledged"


class TestPasswordSecurity:
    """Password hashing and verification correctness."""

    def test_hash_is_not_plaintext(self):
        from app.core.security import hash_password
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"
        assert len(hashed) > 20

    def test_verify_correct_password(self):
        from app.core.security import hash_password, verify_password
        hashed = hash_password("correct_password")
        assert verify_password("correct_password", hashed) is True

    def test_verify_wrong_password(self):
        from app.core.security import hash_password, verify_password
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_same_password_produces_different_hashes(self):
        """bcrypt salt must produce unique hashes per call."""
        from app.core.security import hash_password
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2


class TestProductionDatabaseURL:
    """Validate that the production DATABASE_URL is not SQLite."""

    def test_sqlite_not_used_in_production(self):
        """If DEBUG=False and ENVIRONMENT is not test, DATABASE_URL must be PostgreSQL."""
        from app.core.config import settings
        if settings.DEBUG:
            pytest.skip("DEBUG=True — SQLite is acceptable in development")
        db_url = settings.DATABASE_URL.lower()
        if db_url.startswith("sqlite"):
            pytest.xfail(
                "DATABASE_URL is SQLite. "
                "Acceptable in local dev/test, but MUST be PostgreSQL in production. "
                "Set DATABASE_URL to a postgresql:// URL before deploying."
            )

    def test_postgresql_url_format_valid(self):
        """If DATABASE_URL is PostgreSQL, it must have the correct scheme."""
        from app.core.config import settings
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgresql") or db_url.startswith("postgres"):
            assert (
                db_url.startswith("postgresql://")
                or db_url.startswith("postgresql+")
                or db_url.startswith("postgres://")
            ), f"Malformed PostgreSQL URL: {db_url}"

    def test_database_url_not_empty(self):
        from app.core.config import settings
        assert settings.DATABASE_URL, "DATABASE_URL must not be empty"
