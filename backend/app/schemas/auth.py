"""Auth schemas for multi-role authentication."""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime


class LoginRequest(BaseModel):
    """Login with email or username."""
    email: str  # Accepts either email or username
    password: str

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Password is required")
        return v


class TokenResponse(BaseModel):
    """Token pair returned on login."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserAuthResponse"


class UserAuthResponse(BaseModel):
    """User info included in login response."""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    permissions: List[str]
    organization_id: Optional[int]
    is_verified: bool
    must_change_password: bool

    model_config = {"from_attributes": True}


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors = []
        if len(v) < 12:
            errors.append("at least 12 characters")
        if not any(c.isupper() for c in v):
            errors.append("an uppercase letter")
        if not any(c.islower() for c in v):
            errors.append("a lowercase letter")
        if not any(c.isdigit() for c in v):
            errors.append("a number")
        if not any(c in "!@#$%^&*()" for c in v):
            errors.append("a special character (!@#$%^&*())")
        if errors:
            raise ValueError(f"Password must contain: {', '.join(errors)}")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


TokenResponse.model_rebuild()
