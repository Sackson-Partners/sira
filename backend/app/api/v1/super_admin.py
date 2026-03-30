"""
Super Admin Routes — Platform-level management.
All routes require super_admin or admin role.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
import logging

from app.core.database import get_db
from app.api.deps import require_super_admin
from app.models.user import User
from app.models.organization import Organization

logger = logging.getLogger(__name__)
router = APIRouter()

_require_sa = Depends(require_super_admin())


@router.get("/dashboard")
async def super_admin_dashboard(
    db: Session = Depends(get_db),
    _: User = _require_sa,
):
    """Platform overview dashboard."""
    total_users = db.query(func.count(User.id)).scalar()
    total_orgs = db.query(func.count(Organization.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()  # noqa: E712

    users_by_role = {}
    rows = db.query(User.role, func.count(User.id)).group_by(User.role).all()
    for role, count in rows:
        users_by_role[role] = count

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_organizations": total_orgs,
        "users_by_role": users_by_role,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/organizations")
async def list_organizations(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = _require_sa,
):
    """List all organizations."""
    orgs = db.query(Organization).offset(skip).limit(limit).all()
    total = db.query(func.count(Organization.id)).scalar()
    return {"total": total, "items": orgs}


@router.get("/users")
async def list_all_users(
    skip: int = 0,
    limit: int = 50,
    role: str = None,
    db: Session = Depends(get_db),
    _: User = _require_sa,
):
    """List all users across all organizations."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    return {"total": total, "items": users}


@router.post("/users/{user_id}/lock")
async def lock_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = _require_sa,
):
    """Lock a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot lock your own account")
    user.is_locked = True
    user.is_active = False
    db.commit()
    return {"message": f"User {user.username} locked"}


@router.post("/users/{user_id}/unlock")
async def unlock_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = _require_sa,
):
    """Unlock a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_locked = False
    user.is_active = True
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    return {"message": f"User {user.username} unlocked"}


VALID_ROLES = {
    "operator", "security_lead", "supervisor", "admin",
    "super_admin", "org_admin", "manager", "analyst", "viewer", "api_client",
}


@router.post("/users/{user_id}/change-role")
async def change_user_role(
    user_id: int,
    new_role: str,
    db: Session = Depends(get_db),
    current_user: User = _require_sa,
):
    """Change a user's role."""
    if new_role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{new_role}'. Must be one of: {sorted(VALID_ROLES)}",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    old_role = user.role
    user.role = new_role
    db.commit()
    logger.info(f"Role changed: user_id={user_id} {old_role} -> {new_role} by admin={current_user.id}")
    return {"message": f"Role changed from {old_role} to {new_role}"}


@router.get("/system/health")
async def system_health(
    db: Session = Depends(get_db),
    _: User = _require_sa,
):
    """Detailed system health (admin only)."""
    from sqlalchemy import text
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    return {
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
