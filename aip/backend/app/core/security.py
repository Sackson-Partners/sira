from datetime import datetime, timedelta
from typing import Optional, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import httpx
import json

from .config import settings
from .database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ------------------------------------------------------------------
# Azure AD B2C token validation
# ------------------------------------------------------------------
_b2c_jwks_cache: Optional[dict] = None


async def get_b2c_jwks() -> dict:
    global _b2c_jwks_cache
    if _b2c_jwks_cache:
        return _b2c_jwks_cache
    if not settings.AZURE_AD_B2C_JWKS_URI:
        return {}
    async with httpx.AsyncClient() as client:
        resp = await client.get(settings.AZURE_AD_B2C_JWKS_URI)
        _b2c_jwks_cache = resp.json()
    return _b2c_jwks_cache


async def verify_b2c_token(token: str) -> dict:
    """Validate an Azure AD B2C JWT and return its claims."""
    from jose import jwk, jwt as jose_jwt
    jwks = await get_b2c_jwks()
    headers = jose_jwt.get_unverified_headers(token)
    kid = headers.get("kid")
    key = next((k for k in jwks.get("keys", []) if k["kid"] == kid), None)
    if not key:
        raise HTTPException(status_code=401, detail="Invalid B2C token: key not found")
    public_key = jwk.construct(key)
    payload = jose_jwt.decode(
        token,
        public_key.to_pem().decode(),
        algorithms=["RS256"],
        audience=settings.AZURE_AD_B2C_CLIENT_ID or None,
        options={"verify_aud": bool(settings.AZURE_AD_B2C_CLIENT_ID)},
    )
    return payload


# ------------------------------------------------------------------
# Current user dependency
# ------------------------------------------------------------------
def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    from ..models.user import User
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except HTTPException:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user


def require_roles(*roles: str):
    def checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not authorized. Required: {roles}",
            )
        return current_user
    return checker
