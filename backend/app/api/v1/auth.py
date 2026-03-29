"""
Authentication Routes
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import (
    verify_password, hash_password, create_access_token,
    decode_token, get_current_user
)
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse, PasswordChange
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login to obtain access token"""
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        # Generic message — do not reveal whether username or password is wrong
        logger.warning(f"Failed login attempt for username: {form_data.username!r}")
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

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id}
    )

    logger.info(f"Successful login: user_id={user.id}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/token/refresh", response_model=Token)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
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
        role="operator",  # Force operator role for self-registration
        is_active=True,
        is_verified=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"New user registered: user_id={new_user.id}")
    return new_user


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
    db.commit()

    logger.info(f"Password changed: user_id={current_user.id}")
    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user
