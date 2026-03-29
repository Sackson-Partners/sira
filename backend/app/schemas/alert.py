"""
Alert Schemas
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class AlertBase(BaseModel):
    """Base alert schema"""
    severity: str = Field(
        ...,
        pattern="^(Critical|High|Medium|Low)$"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    sla_timer: Optional[int] = Field(None, gt=0)
    domain: Optional[str] = Field(None, max_length=100)
    site_zone: Optional[str] = Field(None, max_length=100)
    movement_id: Optional[int] = None
    event_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=2000)
    rule_id: Optional[str] = Field(None, max_length=100)
    rule_name: Optional[str] = Field(None, max_length=255)


class AlertCreate(AlertBase):
    """Schema for creating an alert"""
    pass


class AlertUpdate(BaseModel):
    """Schema for updating an alert"""
    status: Optional[str] = Field(
        None,
        pattern="^(open|acknowledged|assigned|investigating|closed)$"
    )
    assigned_to: Optional[int] = None
    case_id: Optional[int] = None
    resolution_notes: Optional[str] = None


class AlertResponse(AlertBase):
    """Schema for alert response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    sla_breached: bool
    case_id: Optional[int] = None
    assigned_to: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert"""
    notes: Optional[str] = None


class AlertResolve(BaseModel):
    """Schema for resolving an alert"""
    resolution_notes: str = Field(..., min_length=1)
