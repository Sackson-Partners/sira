from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional

from ...core.database import get_db
from ...core.security import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token, decode_token,
    get_current_user, verify_b2c_token,
)
from ...models.user import User, UserRole

router = APIRouter()


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    role: str
    full_name: str
    email: str


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: Optional[UserRole] = UserRole.viewer
    organization: Optional[str] = None
    phone: Optional[str] = None


class B2CTokenRequest(BaseModel):
    b2c_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is inactive")

    user.last_login = datetime.utcnow()
    db.commit()

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        role=user.role,
        full_name=user.full_name,
        email=user.email,
    )


@router.post("/b2c-login", response_model=Token)
async def b2c_login(req: B2CTokenRequest, db: Session = Depends(get_db)):
    """Exchange an Azure AD B2C token for a platform JWT."""
    try:
        claims = await verify_b2c_token(req.b2c_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid B2C token: {e}")

    oid = claims.get("oid") or claims.get("sub")
    email = claims.get("email") or claims.get("emails", [None])[0] if isinstance(claims.get("emails"), list) else claims.get("preferred_username")
    full_name = claims.get("name") or claims.get("given_name", "") + " " + claims.get("family_name", "")
    full_name = full_name.strip() or email

    if not email:
        raise HTTPException(status_code=400, detail="B2C token missing email claim")

    user = db.query(User).filter(User.azure_b2c_oid == oid).first()
    if not user:
        user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            email=email,
            full_name=full_name,
            azure_b2c_oid=oid,
            azure_b2c_sub=claims.get("sub"),
            role=UserRole.viewer,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.azure_b2c_oid = oid
        user.last_login = datetime.utcnow()
        db.commit()

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        role=user.role,
        full_name=user.full_name,
        email=user.email,
    )


@router.post("/register", response_model=Token)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=req.email,
        full_name=req.full_name,
        hashed_password=get_password_hash(req.password),
        role=req.role,
        organization=req.organization,
        phone=req.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        role=user.role,
        full_name=user.full_name,
        email=user.email,
    )


@router.post("/refresh", response_model=Token)
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    new_refresh = create_refresh_token({"sub": str(user.id)})
    return Token(
        access_token=access_token,
        refresh_token=new_refresh,
        user_id=user.id,
        role=user.role,
        full_name=user.full_name,
        email=user.email,
    )


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "organization": current_user.organization,
        "phone": current_user.phone,
        "title": current_user.title,
        "avatar_url": current_user.avatar_url,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login,
    }


@router.post("/change-password")
def change_password(
    req: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="B2C users cannot change password here")
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    return {"message": "Password changed successfully"}
