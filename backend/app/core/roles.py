"""User roles and permission definitions for SIRA Platform."""
from enum import Enum
from typing import List


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    ANALYST = "analyst"
    VIEWER = "viewer"
    API_CLIENT = "api_client"
    # Legacy roles kept for backward compatibility
    ADMIN = "admin"
    SECURITY_LEAD = "security_lead"
    SUPERVISOR = "supervisor"


ROLE_PERMISSIONS: dict[str, List[str]] = {
    "super_admin": [
        "platform:manage", "platform:view_all", "platform:billing", "platform:system_settings",
        "org:create", "org:delete", "org:manage_all", "org:view_all",
        "users:create_any", "users:delete_any", "users:manage_any", "users:view_any",
        "data:read_all", "data:write_all", "data:delete_all", "data:export_all",
        "system:health", "system:logs", "system:audit", "system:config",
        "reports:create", "reports:view", "reports:export",
        "alerts:manage", "alerts:view", "alerts:acknowledge",
        "vehicles:manage", "vehicles:view", "vehicles:update_status",
    ],
    "admin": [  # legacy = same as super_admin for backward compat
        "platform:manage", "platform:view_all", "platform:billing", "platform:system_settings",
        "org:create", "org:delete", "org:manage_all", "org:view_all",
        "users:create_any", "users:delete_any", "users:manage_any", "users:view_any",
        "data:read_all", "data:write_all", "data:delete_all", "data:export_all",
        "system:health", "system:logs", "system:audit", "system:config",
        "reports:create", "reports:view", "reports:export",
        "alerts:manage", "alerts:view", "alerts:acknowledge",
        "vehicles:manage", "vehicles:view", "vehicles:update_status",
    ],
    "org_admin": [
        "org:manage_own", "org:view_own", "org:settings",
        "users:create_org", "users:delete_org", "users:manage_org", "users:view_org",
        "data:read_org", "data:write_org", "data:delete_org", "data:export_org",
        "reports:create", "reports:view", "reports:export",
        "alerts:manage", "alerts:view", "alerts:acknowledge",
    ],
    "manager": [
        "users:view_org",
        "data:read_org", "data:write_org", "data:export_org",
        "reports:create", "reports:view", "reports:export",
        "alerts:manage", "alerts:view", "alerts:acknowledge",
        "vehicles:manage", "vehicles:view",
    ],
    "supervisor": [  # legacy = same as manager
        "users:view_org",
        "data:read_org", "data:write_org", "data:export_org",
        "reports:create", "reports:view", "reports:export",
        "alerts:manage", "alerts:view", "alerts:acknowledge",
        "vehicles:manage", "vehicles:view",
    ],
    "operator": [
        "data:read_org", "data:write_org",
        "reports:view", "alerts:view", "alerts:acknowledge",
        "vehicles:view", "vehicles:update_status",
    ],
    "analyst": [
        "data:read_org", "data:export_org",
        "reports:create", "reports:view", "reports:export",
        "alerts:view", "vehicles:view",
    ],
    "security_lead": [  # legacy = similar to analyst+operator
        "data:read_org", "data:write_org", "data:export_org",
        "reports:create", "reports:view", "reports:export",
        "alerts:manage", "alerts:view", "alerts:acknowledge",
        "vehicles:view",
    ],
    "viewer": [
        "data:read_org", "reports:view", "alerts:view", "vehicles:view",
    ],
    "api_client": [
        "data:read_org", "data:write_org", "alerts:view", "vehicles:view",
    ],
}


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, [])


def get_permissions(role: str) -> List[str]:
    """Get all permissions for a role."""
    return ROLE_PERMISSIONS.get(role, [])


# Roles that can access admin areas
ADMIN_ROLES = {"super_admin", "admin"}
ORG_ADMIN_ROLES = {"super_admin", "admin", "org_admin"}
MANAGER_ROLES = {"super_admin", "admin", "org_admin", "manager", "supervisor"}
