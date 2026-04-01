"""
Security Utilities
Password hashing, JWT token management, and authentication
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import logging

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token"""
    from app.core.roles import get_permissions
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    role = data.get("role", "viewer")
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "permissions": get_permissions(role),
    })
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Verify Supabase JWT or legacy custom JWT and return the matching user.

    Security properties enforced here:
      H2  — token_version mismatch rejects tokens issued before a password change
      H3  — Supabase audience "authenticated" verified when SUPABASE_JWT_SECRET is set
      M5  — must_change_password blocks all endpoints except /change-password & /logout
    """
    from app.models.user import User
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # ── Path 1: Supabase JWT ──────────────────────────────────────────────────
    # H3: audience verification enabled — Supabase tokens carry aud="authenticated"
    if settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
            email: str | None = payload.get("email")
            if email:
                user = db.query(User).filter(User.email == email).first()
                if user is None:
                    raise credentials_exception
                if not user.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Inactive user",
                    )
                _enforce_must_change_password(user, request)
                return user
        except jwt.InvalidTokenError:
            pass  # fall through to legacy path

    # ── Path 2: legacy custom JWT (issued by this app's SECRET_KEY) ──────────
    try:
        payload = decode_token(token)
        username: str = payload.get("sub", "")
        if not username:
            raise credentials_exception

        user = db.query(User).filter(User.username == username).first()
        if user is None or not user.is_active:
            raise credentials_exception

        # H2: validate token_version — mismatch means token was issued before
        #     the last password change and must be rejected
        token_ver: int = payload.get("ver", 0)
        if token_ver != (user.token_version or 0):
            raise credentials_exception

        _enforce_must_change_password(user, request)
        return user
    except HTTPException:
        raise
    except Exception:
        raise credentials_exception


def _enforce_must_change_password(user, request: Request) -> None:
    """M5: Raise 403 if the account requires a password change.

    The /change-password and /logout endpoints are explicitly exempted so the
    user can actually satisfy the requirement without being locked out entirely.
    """
    if not getattr(user, "must_change_password", False):
        return
    exempt_suffixes = ("/change-password", "/logout", "/auth/me")
    path = request.url.path
    if not any(path.endswith(suffix) for suffix in exempt_suffixes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Password change required before continuing.", "code": "MUST_CHANGE_PASSWORD"},
        )


def require_same_org(resource_org_id: int, current_user) -> None:
    """M8: Raise 403 if current_user does not belong to resource_org_id.

    Platform admins (super_admin / admin) are exempt.
    Call this at the start of any endpoint that accesses org-scoped data.
    """
    platform_admin_roles = {"admin", "super_admin"}
    if current_user.role in platform_admin_roles:
        return
    if current_user.organization_id != resource_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: resource belongs to a different organisation.",
        )


def require_role(allowed_roles: list):
    """Dependency factory to check user role"""
    async def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


def require_admin():
    """Shortcut for admin-only endpoints"""
    return require_role(["admin", "super_admin"])


def require_security_lead():
    """Shortcut for security lead or higher"""
    return require_role(["security_lead", "supervisor", "admin", "super_admin", "org_admin", "manager"])


def require_operator():
    """Shortcut for operator or higher"""
    return require_role(["operator", "security_lead", "supervisor", "admin", "super_admin", "org_admin", "manager", "analyst"])
