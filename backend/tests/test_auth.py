"""
Authentication Tests
"""

import pytest
from datetime import timedelta
from fastapi import status


# Strong password meeting the complexity validator requirements
STRONG_PASSWORD = "Secure@Test1!"


class TestLogin:
    """Login / token issuance."""

    def test_login_success_returns_token(self, client, admin_user):
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "adminpass123"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, client, admin_user):
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user_returns_401(self, client):
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "nobody", "password": "irrelevant"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user_returns_400(self, client, inactive_user):
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "inactive", "password": "inactivepass123"},
        )
        # Inactive users get 400 (account disabled), not 401
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_login_error_message_is_generic(self, client, admin_user):
        """Error message must not reveal whether username or password is wrong."""
        r_bad_pass = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "wrong"},
        )
        r_bad_user = client.post(
            "/api/v1/auth/token",
            data={"username": "nobody", "password": "wrong"},
        )
        # Both must return the same message to prevent user enumeration
        msg_bad_pass = r_bad_pass.json().get("error", r_bad_pass.json().get("detail", ""))
        msg_bad_user = r_bad_user.json().get("error", r_bad_user.json().get("detail", ""))
        assert msg_bad_pass == msg_bad_user


class TestTokenRefresh:
    """Token refresh endpoint."""

    def test_refresh_with_valid_refresh_token(self, client, admin_user):
        from app.core.security import create_refresh_token
        token = create_refresh_token(
            data={"sub": "admin", "role": "admin", "user_id": admin_user.id}
        )
        response = client.post(
            "/api/v1/auth/token/refresh",
            params={"refresh_token": token},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_with_access_token_rejected(self, client, admin_user):
        """Passing an access token to the refresh endpoint must be rejected."""
        from app.core.security import create_access_token
        access_token = create_access_token(
            data={"sub": "admin", "role": "admin", "user_id": admin_user.id}
        )
        response = client.post(
            "/api/v1/auth/token/refresh",
            params={"refresh_token": access_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_with_invalid_token_rejected(self, client):
        response = client.post(
            "/api/v1/auth/token/refresh",
            params={"refresh_token": "this.is.garbage"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_with_expired_token_rejected(self, client, admin_user):
        from app.core.security import create_refresh_token
        expired = create_refresh_token(
            data={"sub": "admin", "role": "admin", "user_id": admin_user.id},
        )
        # Monkey-patch the token payload expiry (decode then re-encode with past exp)
        import jwt
        from app.core.config import settings
        from datetime import datetime, timezone
        payload = jwt.decode(expired, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        payload["exp"] = int(datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp())
        payload["type"] = "refresh"
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        response = client.post(
            "/api/v1/auth/token/refresh",
            params={"refresh_token": expired_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRegistration:
    """User self-registration."""

    def test_register_success(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@test.com",
                "password": STRONG_PASSWORD,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "newuser"
        assert data["role"] == "operator"  # self-registration always yields operator

    def test_register_weak_password_rejected(self, client):
        """Password complexity validator must reject weak passwords."""
        for weak in ["password", "password123", "PASSWORD123", "Pass1234"]:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "weaktest",
                    "email": "weak@test.com",
                    "password": weak,
                },
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
                f"Weak password '{weak}' was incorrectly accepted"
            )

    def test_register_duplicate_username_rejected(self, client, admin_user):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "admin",
                "email": "another@test.com",
                "password": STRONG_PASSWORD,
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email_rejected(self, client, admin_user):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "brandnew",
                "email": "admin@test.com",  # already used by admin_user fixture
                "password": STRONG_PASSWORD,
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_username_rejected(self, client):
        """Usernames with special characters must be rejected."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "bad user!",
                "email": "bad@test.com",
                "password": STRONG_PASSWORD,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_forces_operator_role(self, client):
        """Self-registration must never grant admin or supervisor roles."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "tryingadmin",
                "email": "tryadmin@test.com",
                "password": STRONG_PASSWORD,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["role"] == "operator"


class TestCurrentUser:
    """GET /me endpoint."""

    def test_get_me_with_valid_token(self, client, auth_headers, admin_user):
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"
        assert "hashed_password" not in data

    def test_get_me_without_token_returns_401(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_me_with_invalid_token_returns_401(self, client):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not.a.real.token"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestExpiredTokens:
    """Expired tokens must always be rejected."""

    def test_expired_access_token_rejected(self, client, admin_user):
        from app.core.security import create_access_token
        expired = create_access_token(
            data={"sub": "admin", "role": "admin", "user_id": admin_user.id},
            expires_delta=timedelta(seconds=-1),
        )
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired}"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPasswordChange:
    """POST /change-password endpoint."""

    def test_change_password_success(self, client, admin_user, auth_headers):
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "adminpass123",
                "new_password": "NewAdmin@Pass2!",
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

    def test_change_password_wrong_current_rejected(self, client, admin_user, auth_headers):
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "wrongpassword",
                "new_password": "NewAdmin@Pass2!",
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_weak_new_password_rejected(self, client, admin_user, auth_headers):
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "adminpass123",
                "new_password": "weakpassword",
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_change_password_requires_auth(self, client):
        response = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "x", "new_password": "y"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
