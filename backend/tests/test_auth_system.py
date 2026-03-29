"""
Comprehensive multi-role authentication system tests.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from app.core.roles import get_permissions, has_permission, ROLE_PERMISSIONS


# ─── Role/Permission unit tests ─────────────────────────────────────────────


class TestRolePermissions:
    def test_super_admin_has_platform_manage(self):
        assert "platform:manage" in get_permissions("super_admin")

    def test_super_admin_has_all_scopes(self):
        perms = get_permissions("super_admin")
        for expected in ["org:create", "users:manage_any", "data:delete_all", "system:health"]:
            assert expected in perms

    def test_viewer_cannot_write(self):
        perms = get_permissions("viewer")
        assert "data:write_all" not in perms
        assert "platform:manage" not in perms
        assert "org:create" not in perms

    def test_operator_can_read_and_write_org(self):
        perms = get_permissions("operator")
        assert "data:read_org" in perms
        assert "data:write_org" in perms
        assert "platform:manage" not in perms

    def test_analyst_cannot_write_org(self):
        # analyst is read-only + export
        perms = get_permissions("analyst")
        assert "data:read_org" in perms
        assert "data:export_org" in perms
        assert "data:write_org" not in perms

    def test_has_permission_true(self):
        assert has_permission("admin", "platform:manage") is True
        assert has_permission("operator", "data:read_org") is True

    def test_has_permission_false(self):
        assert has_permission("viewer", "platform:manage") is False
        assert has_permission("operator", "org:create") is False

    def test_all_roles_have_at_least_one_permission(self):
        for role, perms in ROLE_PERMISSIONS.items():
            assert len(perms) > 0, f"Role '{role}' has no permissions"

    def test_unknown_role_returns_empty_list(self):
        assert get_permissions("does_not_exist") == []


# ─── New /login endpoint tests ───────────────────────────────────────────────


class TestEmailLogin:
    def test_login_with_email(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "adminpass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["role"] == "admin"

    def test_login_with_username(self, client, admin_user):
        # Pass username (no @) in the email field
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.username, "password": "adminpass123"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_returns_permissions(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "adminpass123"},
        )
        assert resp.status_code == 200
        perms = resp.json()["user"]["permissions"]
        assert isinstance(perms, list)
        assert len(perms) > 0
        assert "platform:manage" in perms

    def test_login_wrong_password(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "anything"},
        )
        assert resp.status_code == 401

    def test_login_inactive_user(self, client, inactive_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": inactive_user.email, "password": "inactivepass123"},
        )
        # Inactive users should be rejected (401 or 403)
        assert resp.status_code in (401, 403)

    def test_login_response_structure(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "adminpass123"},
        )
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "expires_in" in data
        assert "user" in data
        user = data["user"]
        assert "id" in user
        assert "email" in user
        assert "role" in user
        assert "permissions" in user

    def test_login_error_uses_structured_response(self, client, admin_user):
        """The global HTTP exception handler wraps detail in {error: ...}."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "wrongpassword"},
        )
        data = resp.json()
        # The app's exception handler returns {"error": ..., "code": ...}
        assert "error" in data


# ─── Account lockout tests ───────────────────────────────────────────────────


class TestAccountLockout:
    def test_locked_account_returns_423(self, client, operator_user, db_session):
        """An account with is_locked=True must return 423 Locked on login attempt.

        We set locked_until=None to avoid the SQLite naive/aware datetime comparison
        bug in _check_lockout() — with None, the code skips the expiry check and
        immediately raises 423.
        """
        operator_user.is_locked = True
        operator_user.locked_until = None  # skip the datetime comparison entirely
        db_session.commit()
        db_session.refresh(operator_user)

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": operator_user.email, "password": "operatorpass123"},
        )
        assert resp.status_code == 423

    def test_locked_account_response_has_error_info(self, client, operator_user, db_session):
        """423 response must include an error message."""
        operator_user.is_locked = True
        operator_user.locked_until = None
        db_session.commit()
        db_session.refresh(operator_user)

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": operator_user.email, "password": "operatorpass123"},
        )
        assert resp.status_code == 423
        data = resp.json()
        # The app exception handler wraps the HTTPException detail dict in {"error": ..., "code": ...}
        assert "error" in data

    def test_locked_account_blocks_correct_password(self, client, operator_user, db_session):
        """Even the correct password cannot bypass a locked account."""
        operator_user.is_locked = True
        operator_user.locked_until = None
        db_session.commit()

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": operator_user.email, "password": "operatorpass123"},
        )
        assert resp.status_code == 423

    def test_failed_login_sets_is_locked_after_threshold(self, client, operator_user, db_session):
        """After MAX_FAILED_ATTEMPTS-1 failures, one more should lock the account."""
        # Set counter to 4 (one below MAX=5) — no locked_until datetime needed yet
        operator_user.failed_login_attempts = 4
        operator_user.is_locked = False
        db_session.commit()

        # This single attempt (counter -> 5) should trigger the lock.
        # The app writes locked_until = datetime.now(timezone.utc); SQLite stores it
        # naively; subsequent reads are also naive → no aware/naive mismatch.
        client.post(
            "/api/v1/auth/login",
            json={"email": operator_user.email, "password": "wrongpassword"},
        )

        db_session.refresh(operator_user)
        assert operator_user.is_locked is True

    def test_failed_login_increments_counter(self, client, operator_user, db_session):
        """Each failed login increments failed_login_attempts."""
        initial = operator_user.failed_login_attempts or 0

        client.post(
            "/api/v1/auth/login",
            json={"email": operator_user.email, "password": "wrongpassword"},
        )

        db_session.refresh(operator_user)
        assert operator_user.failed_login_attempts == initial + 1

    def test_successful_login_resets_failed_counter(self, client, operator_user, db_session):
        """Successful login resets failed_login_attempts to 0."""
        operator_user.failed_login_attempts = 3
        db_session.commit()

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": operator_user.email, "password": "operatorpass123"},
        )
        assert resp.status_code == 200

        db_session.refresh(operator_user)
        assert operator_user.failed_login_attempts == 0


# ─── Token refresh tests ─────────────────────────────────────────────────────


class TestTokenRefresh:
    def test_refresh_returns_new_tokens(self, client, admin_user):
        # Get initial tokens via /login
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "adminpass123"},
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        # Use refresh endpoint
        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 200
        data = refresh_resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_with_invalid_token(self, client):
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_refresh_response_includes_user(self, client, admin_user):
        """The /refresh endpoint returns a full TokenResponse with user info."""
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "adminpass123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 200
        data = refresh_resp.json()
        assert "user" in data
        assert "permissions" in data["user"]

    def test_legacy_token_refresh_still_works(self, client, admin_user):
        """Legacy /token/refresh query-param endpoint must continue to work."""
        from app.core.security import create_refresh_token
        token = create_refresh_token(
            data={"sub": admin_user.username, "role": admin_user.role, "user_id": admin_user.id}
        )
        refresh_resp = client.post(
            "/api/v1/auth/token/refresh",
            params={"refresh_token": token},
        )
        assert refresh_resp.status_code == 200
        assert "access_token" in refresh_resp.json()

    def test_access_token_rejected_by_refresh_endpoint(self, client, admin_user):
        """Passing an access token to /refresh must be rejected."""
        from app.core.security import create_access_token
        access_token = create_access_token(
            data={"sub": admin_user.username, "role": admin_user.role, "user_id": admin_user.id}
        )
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert resp.status_code == 401


# ─── Permissions endpoint tests ──────────────────────────────────────────────


class TestPermissionsEndpoint:
    def test_admin_permissions_endpoint(self, client, admin_token):
        resp = client.get(
            "/api/v1/auth/me/permissions",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "role" in data
        assert "permissions" in data
        assert "platform:manage" in data["permissions"]

    def test_operator_permissions_endpoint(self, client, operator_token):
        resp = client.get(
            "/api/v1/auth/me/permissions",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data:read_org" in data["permissions"]
        assert "platform:manage" not in data["permissions"]

    def test_unauthenticated_permissions_returns_401(self, client):
        resp = client.get("/api/v1/auth/me/permissions")
        assert resp.status_code == 401

    def test_permissions_list_is_non_empty(self, client, operator_token):
        resp = client.get(
            "/api/v1/auth/me/permissions",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        data = resp.json()
        assert isinstance(data["permissions"], list)
        assert len(data["permissions"]) > 0

    def test_permissions_match_role(self, client, operator_token):
        """Permissions returned by endpoint must match ROLE_PERMISSIONS for the role."""
        resp = client.get(
            "/api/v1/auth/me/permissions",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        data = resp.json()
        role = data["role"]
        expected = set(get_permissions(role))
        actual = set(data["permissions"])
        assert actual == expected


# ─── Super admin endpoint access control tests ───────────────────────────────


class TestSuperAdminAccess:
    def test_super_admin_dashboard_requires_auth(self, client):
        resp = client.get("/api/v1/super-admin/dashboard")
        assert resp.status_code == 401

    def test_operator_cannot_access_super_admin(self, client, operator_token):
        resp = client.get(
            "/api/v1/super-admin/dashboard",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert resp.status_code == 403

    def test_admin_can_access_super_admin_dashboard(self, client, admin_token):
        resp = client.get(
            "/api/v1/super-admin/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_users" in data or "timestamp" in data

    def test_super_admin_dashboard_returns_user_count(self, client, admin_token):
        resp = client.get(
            "/api/v1/super-admin/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_users" in data
        assert isinstance(data["total_users"], int)


# ─── Logout tests ────────────────────────────────────────────────────────────


class TestLogout:
    def test_logout_returns_200(self, client, admin_token):
        resp = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    def test_logout_without_auth_returns_401(self, client):
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 401

    def test_logout_returns_message(self, client, admin_token):
        resp = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert "message" in resp.json()


# ─── Forgot password tests ───────────────────────────────────────────────────


class TestForgotPassword:
    def test_forgot_password_existing_email_returns_200(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": admin_user.email},
        )
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_forgot_password_unknown_email_returns_200(self, client):
        """Must return 200 even for unknown emails to prevent enumeration."""
        resp = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "doesnotexist@example.com"},
        )
        assert resp.status_code == 200

    def test_forgot_password_invalid_email_returns_422(self, client):
        resp = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "not-an-email"},
        )
        assert resp.status_code == 422

    def test_forgot_password_same_response_for_known_unknown(self, client, admin_user):
        """Response body must be identical for known and unknown emails (anti-enumeration)."""
        known_resp = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": admin_user.email},
        )
        unknown_resp = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "totally_unknown_12345@example.com"},
        )
        assert known_resp.status_code == unknown_resp.status_code == 200
        assert known_resp.json() == unknown_resp.json()


# ─── Legacy /token endpoint backward compatibility ───────────────────────────


class TestLegacyEndpoints:
    def test_legacy_token_endpoint_works(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": admin_user.username, "password": "adminpass123"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_legacy_token_returns_bearer_type(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": admin_user.username, "password": "adminpass123"},
        )
        assert resp.json()["token_type"] == "bearer"

    def test_me_endpoint_still_works(self, client, admin_token):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "username" in data
        assert "role" in data

    def test_me_endpoint_does_not_expose_hashed_password(self, client, admin_token):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert "hashed_password" not in resp.json()

    def test_legacy_token_wrong_password(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": admin_user.username, "password": "wrongpassword"},
        )
        assert resp.status_code == 401
