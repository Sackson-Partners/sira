"""
SIRA Platform - Supabase Multi-Authentication Module
Phase 2: Multi-tenant auth with RBAC using Supabase Auth
Supabase Project: evpbetmgmhwhhhgwvnfb
"""

from __future__ import annotations

import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supabase client (singleton)
# ---------------------------------------------------------------------------

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Return a cached Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
        )
    return _supabase_client


# ---------------------------------------------------------------------------
# Token / User models
# ---------------------------------------------------------------------------

class TokenData(BaseModel):
    sub: str                     # Supabase user UUID
    email: Optional[str] = None
    role: str = "client"         # SIRA RBAC role
    org_id: Optional[str] = None


class CurrentUser(BaseModel):
    id: str
    email: Optional[str]
    role: str
    org_id: Optional[str]
    is_active: bool = True


# ---------------------------------------------------------------------------
# JWT verification
# ---------------------------------------------------------------------------

bearer_scheme = HTTPBearer(auto_error=True)


def _verify_supabase_jwt(token: str) -> dict:
    """Decode and verify a Supabase-issued JWT using the project JWT secret."""
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},   # Supabase uses 'authenticated' audience
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# FastAPI dependency: get current user from Bearer JWT
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    """
    Validate Supabase JWT and return the current authenticated user.
    Extracts SIRA role and org_id from the JWT app_metadata claim.
    """
    payload = _verify_supabase_jwt(credentials.credentials)

    user_id: str = payload.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    email: Optional[str] = payload.get("email")

    # SIRA role & org stored in app_metadata (set server-side via Supabase Admin API)
    app_meta: dict = payload.get("app_metadata", {})
    role: str = app_meta.get("sira_role", "client")
    org_id: Optional[str] = app_meta.get("org_id")

    return CurrentUser(
        id=user_id,
        email=email,
        role=role,
        org_id=org_id,
    )


# ---------------------------------------------------------------------------
# RBAC dependency factory
# ---------------------------------------------------------------------------

ROLE_HIERARCHY = {
    "super_admin": 100,
    "org_admin": 80,
    "logistics_manager": 60,
    "fleet_manager": 50,
    "analyst": 40,
    "driver": 20,
    "client": 10,
}


def require_role(*allowed_roles: str):
    """
    Dependency factory: raise 403 if current user does not have one of
    the specified roles.

    Usage::

        @router.get("/admin")
        async def admin_only(user = Depends(require_role("super_admin", "org_admin"))):
            ...
    """

    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not authorized for this action. Required: {allowed_roles}",
            )
        return user

    return _checker


def require_min_role(min_role: str):
    """
    Dependency: allow access if the user's role level is >= min_role level.
    """
    min_level = ROLE_HIERARCHY.get(min_role, 0)

    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        user_level = ROLE_HIERARCHY.get(user.role, 0)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Minimum role required: {min_role}",
            )
        return user

    return _checker


# ---------------------------------------------------------------------------
# Supabase Admin helpers (server-side user management)
# ---------------------------------------------------------------------------

async def set_user_role(user_id: str, role: str, org_id: Optional[str] = None) -> dict:
    """
    Update a user's app_metadata in Supabase to set SIRA RBAC role and org.
    Must be called with service role key (server-side only).
    """
    client = get_supabase_client()
    metadata: dict = {"sira_role": role}
    if org_id:
        metadata["org_id"] = org_id

    response = client.auth.admin.update_user_by_id(
        user_id,
        {"app_metadata": metadata},
    )
    return response.dict() if hasattr(response, "dict") else {}


async def list_users(page: int = 1, per_page: int = 50) -> list:
    """List all Supabase users (admin only)."""
    client = get_supabase_client()
    response = client.auth.admin.list_users(page=page, per_page=per_page)
    return response if isinstance(response, list) else []


async def invite_user(email: str, role: str, org_id: Optional[str] = None) -> dict:
    """
    Send a Supabase magic-link invitation to a new user and pre-assign SIRA role.
    """
    client = get_supabase_client()
    app_metadata: dict = {"sira_role": role}
    if org_id:
        app_metadata["org_id"] = org_id

    response = client.auth.admin.invite_user_by_email(
        email,
        options={"data": app_metadata},
    )
    return response.dict() if hasattr(response, "dict") else {}
