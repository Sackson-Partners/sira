"""
API Dependencies — permission and role checking.
"""

from fastapi import Depends, HTTPException, status
from app.core.security import get_current_user
from app.core.roles import has_permission, ADMIN_ROLES


def require_permission(permission: str):
    """Dependency factory: require a specific permission."""
    async def check_permission(current_user=Depends(get_current_user)):
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Insufficient permissions",
                    "required": permission,
                    "your_role": current_user.role,
                },
            )
        return current_user
    return check_permission


def require_any_role(*roles: str):
    """Dependency factory: require one of the listed roles."""
    async def check_role(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Access denied",
                    "required_roles": list(roles),
                    "your_role": current_user.role,
                },
            )
        return current_user
    return check_role


def require_super_admin():
    """Require super_admin or legacy admin role."""
    return require_any_role("super_admin", "admin")


def require_org_admin_or_higher():
    """Require org_admin, super_admin, or admin."""
    return require_any_role("super_admin", "admin", "org_admin")
