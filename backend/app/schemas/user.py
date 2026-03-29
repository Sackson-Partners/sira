"""
User Schemas
"""

import re
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import Optional
from datetime import datetime

# Password must contain at least one uppercase letter, one lowercase letter,
# one digit, and one special character.
_PASSWORD_PATTERN = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};\'\\:"|,.<>\/?]).{8,}$'
)

# Username: alphanumeric, underscores, and hyphens only — no whitespace or special chars.
_USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=255)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        v = v.strip()
        if not _USERNAME_PATTERN.match(v):
            raise ValueError(
                "Username may only contain letters, digits, underscores, and hyphens"
            )
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_strip(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class UserCreate(UserBase):
    """Schema for creating a user"""
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(
        default="operator",
        pattern="^(operator|security_lead|supervisor|admin)$"
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not _PASSWORD_PATTERN.match(v):
            raise ValueError(
                "Password must be at least 8 characters and contain at least one "
                "uppercase letter, one lowercase letter, one digit, and one special character"
            )
        return v


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = Field(
        None,
        pattern="^(operator|security_lead|supervisor|admin)$"
    )
    is_active: Optional[bool] = None

    @field_validator("full_name")
    @classmethod
    def full_name_strip(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class UserResponse(UserBase):
    """Schema for user response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class UserInDB(UserResponse):
    """Schema for user in database (includes hashed password)"""
    hashed_password: str


class Token(BaseModel):
    """OAuth2 token response"""
    access_token: str
    token_type: str = "bearer"


class TokenPair(Token):
    """Token pair with refresh token"""
    refresh_token: str


class TokenData(BaseModel):
    """Data extracted from token"""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None


class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        if not _PASSWORD_PATTERN.match(v):
            raise ValueError(
                "New password must be at least 8 characters and contain at least one "
                "uppercase letter, one lowercase letter, one digit, and one special character"
            )
        return v
