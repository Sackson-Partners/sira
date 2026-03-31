"""
Authentication Routes
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import secrets
import logging

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import (
    verify_password, hash_password, create_access_token, create_refresh_token,
    decode_token, get_current_user
)
from app.core.roles import get_permissions
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse, PasswordChange
from app.schemas.auth import (
    LoginRequest, TokenResponse, UserAuthResponse,
    RefreshRequest, PasswordResetRequest, PasswordResetConfirm
)

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 30
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # shorter for new /login endpoint


def _check_lockout(user: User):
    """Raise 423 if account is currently locked."""
    if user.is_locked:
        if user.locked_until and datetime.now(timezone.utc) > user.locked_until:
            # Auto-unlock after lockout period
            user.is_locked = False
            user.locked_until = None
            user.failed_login_attempts = 0
        else:
            remaining = None
            if user.locked_until:
                delta = user.locked_until - datetime.now(timezone.utc)
                remaining = max(0, int(delta.total_seconds() / 60))
            raise HTTPException(
                status_code=423,
                detail={
                    "error": "Account locked",
                    "message": "Account locked due to too many failed attempts.",
                    "unlock_in_minutes": remaining,
                }
            )


def _handle_failed_login(user: User, db: Session):
    """Increment failure counter and lock if threshold reached."""
    if user.failed_login_attempts is None:
        user.failed_login_attempts = 0
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.is_locked = True
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
    db.commit()


def _handle_successful_login(user: User, request: Request, db: Session):
    """Reset failure counter and update login metadata."""
    user.failed_login_attempts = 0
    user.is_locked = False
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)
    if request.client:
        user.last_login_ip = request.client.host
    db.commit()


def _build_token_response(user: User) -> TokenResponse:
    """Build the full token response for a successful login."""
    token_data = {"sub": user.username, "role": user.role, "user_id": user.id}
    if user.organization_id:
        token_data["org_id"] = user.organization_id

    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(data=token_data)

    user_resp = UserAuthResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        permissions=get_permissions(user.role),
        organization_id=user.organization_id,
        is_verified=user.is_verified,
        must_change_password=getattr(user, 'must_change_password', False) or False,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_resp,
    )


# ── NEW: Email/username login ─────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login_email(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login with email or username. Returns access + refresh token + user info."""
    # Support both email and username login
    identifier = login_data.email.strip()
    if "@" in identifier:
        user = db.query(User).filter(User.email == identifier).first()
    else:
        user = db.query(User).filter(User.username == identifier).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Check lockout BEFORE verifying password
    _check_lockout(user)

    if not verify_password(login_data.password, user.hashed_password):
        _handle_failed_login(user, db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support.",
        )

    _handle_successful_login(user, request, db)
    logger.info(f"Login: user_id={user.id} role={user.role}")
    return _build_token_response(user)


# ── LEGACY: Username/password form login (kept for backward compatibility) ────

@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login to obtain access token (legacy OAuth2 form endpoint)"""
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _check_lockout(user)

    if not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for username: {form_data.username!r}")
        _handle_failed_login(user, db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id}
    )

    logger.info(f"Successful login: user_id={user.id}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/token/refresh", response_model=Token)
@limiter.limit("10/minute")
async def refresh_token_legacy(
    request: Request,
    response: Response,
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token (legacy query-param endpoint)"""
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        access_token = create_access_token(
            data={"sub": user.username, "role": user.role, "user_id": user.id}
        )

        return {"access_token": access_token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_token_v2(
    request: Request,
    response: Response,
    body: RefreshRequest,
    db: Session = Depends(get_db)
):
    """Refresh token (JSON body, returns full token pair with user info)."""
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        return _build_token_response(user)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/logout")
async def logout(
    request: Request,
    current_user=Depends(get_current_user)
):
    """Logout current user (client should discard tokens)."""
    logger.info(f"Logout: user_id={current_user.id}")
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    response: Response,
    body: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request a password reset email."""
    user = db.query(User).filter(User.email == body.email).first()
    # Always return success to prevent email enumeration
    if user and user.is_active:
        token = secrets.token_urlsafe(32)
        user.password_reset_token = hash_password(token)  # Store hash, not plaintext
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
        # TODO: Send email with reset link containing token
        logger.info(f"Password reset requested: user_id={user.id}")
    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    response: Response,
    body: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Reset password using reset token."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset token"
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(
    request: Request,
    response: Response,
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user (self-registration as operator)"""
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hash_password(user_data.password),
        role="operator",
        is_active=True,
        is_verified=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"New user registered: user_id={new_user.id}")
    return new_user


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def signup(
    request: Request,
    response: Response,
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Sign up for a new account (alias for /register)."""
    return await register(request=request, response=response, user_data=user_data, db=db)


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    response: Response,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change current user's password"""
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    current_user.hashed_password = hash_password(password_data.new_password)
    if hasattr(current_user, 'must_change_password'):
        current_user.must_change_password = False
    db.commit()

    logger.info(f"Password changed: user_id={current_user.id}")
    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.get("/me/permissions")
async def get_my_permissions(current_user=Depends(get_current_user)):
    """Get current user's permissions."""
    return {
        "role": current_user.role,
        "permissions": get_permissions(current_user.role),
    }
