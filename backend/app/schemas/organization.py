"""
Organization Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class OrganizationCreate(BaseModel):
    name: str
    slug: str = Field(..., pattern=r'^[a-z0-9-]+$', description="URL-friendly identifier")
    type: str = Field(default="logistics")
    country_code: str = Field(default="GH", min_length=2, max_length=2)
    timezone: str = Field(default="Africa/Accra")
    plan: str = Field(default="starter")
    settings: Dict[str, Any] = Field(default_factory=dict)


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    country_code: Optional[str] = None
    timezone: Optional[str] = None
    plan: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    type: str
    country_code: str
    timezone: str
    plan: str
    settings: Dict[str, Any]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
