"""
AIP Users Management Router
------------------------------
Admin-only CRUD for platform users.

Endpoints:
    GET    /api/users            - List all users
    GET    /api/users/{id}       - Get user by id
    POST   /api/users            - Create user (admin)
    PUT    /api/users/{id}       - Update user (admin)
    DELETE /api/users/{id}       - Delete user (admin)
    POST   /api/users/{id}/activate   - Activate user
    POST   /api/users/{id}/deactivate - Deactivate user
    GET    /api/users/stats/summary   - Role/status stats
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.security.auth import get_current_user, require_admin, hash_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["Users"])

ROLES = ("viewer", "analyst", "admin", "ic_member", "gov_partner", "epc", "investor")


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    organisation: Optional[str] = None
    role: str = "viewer"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    organisation: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    organisation: Optional[str]
    role: str
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("/stats/summary")
async def user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Return user count broken down by role and status."""
    all_users = db.query(User).all()
    by_role: dict = {}
    for u in all_users:
        by_role[u.role] = by_role.get(u.role, 0) + 1
    return {
        "total": len(all_users),
        "active": sum(1 for u in all_users if u.is_active),
        "inactive": sum(1 for u in all_users if not u.is_active),
        "verified": sum(1 for u in all_users if u.is_verified),
        "by_role": by_role,
    }


@router.get("", response_model=list[UserOut])
async def list_users(
    skip: int = Query(0),
    limit: int = Query(100, le=500),
    role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all platform users. Admin only."""
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if search:
        q = q.filter(
            (User.email.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%")) |
            (User.organisation.ilike(f"%{search}%"))
        )
    return q.offset(skip).limit(limit).all()


@router.post("", response_model=UserOut, status_code=201)
async def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new platform user. Admin only."""
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    if user_in.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {ROLES}")
    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        organisation=user_in.organisation,
        role=user_in.role,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("User created by admin %s: %s", current_user.email, user.email)
    return user


@router.get("/me", response_model=UserOut)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get a single user by ID. Admin only."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update user fields. Admin only."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user_in.role and user_in.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {ROLES}")
    for field, value in user_in.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    logger.info("User %s updated by admin %s", user.email, current_user.email)
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a user. Admin only."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    db.delete(user)
    db.commit()
    logger.info("User %s deleted by admin %s", user_id, current_user.email)


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Activate a user account. Admin only."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_active = True
    db.commit()
    return {"message": f"User {user.email} activated."}


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Deactivate a user account. Admin only."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_active = False
    db.commit()
    return {"message": f"User {user.email} deactivated."}


@router.post("/{user_id}/verify")
async def verify_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Mark a user as verified (KYC complete). Admin only."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_verified = True
    db.commit()
    return {"message": f"User {user.email} verified."}
