"""
SIRA Platform - Authentication & RBAC Middleware
Phase 2: JWT verification via Supabase + Role-Based Access Control
"""

from __future__ import annotations
import logging
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


class TokenUser(BaseModel):
    sub: str
    email: Optional[str] = None
    role: str = "operator"
    org_id: Optional[str] = None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> TokenUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials
    if settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
            app_metadata = payload.get("app_metadata", {})
            user_metadata = payload.get("user_metadata", {})
            return TokenUser(
                sub=payload["sub"],
                email=payload.get("email"),
                role=app_metadata.get("role", user_metadata.get("role", "operator")),
                org_id=app_metadata.get("org_id"),
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.InvalidTokenError:
            pass
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return TokenUser(sub=str(payload.get("user_id", "")), email=payload.get("email"), role=payload.get("role", "operator"))
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


def require_role(*roles: str):
    async def checker(user: TokenUser = Depends(get_current_user)) -> TokenUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role '{user.role}' not permitted")
        return user
    return checker


require_admin = require_role("super_admin", "org_admin")
require_fleet_manager = require_role("super_admin", "org_admin", "fleet_manager")
require_analyst = require_role("super_admin", "org_admin", "fleet_manager", "logistics_manager", "analyst")
