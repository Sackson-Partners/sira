"""
Assignment Schemas
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AssignmentCreate(BaseModel):
    shipment_id: int
    driver_id: int
    vehicle_id: int
    notes: Optional[str] = None


class AssignmentUpdate(BaseModel):
    status: Optional[str] = None  # pending, accepted, rejected, active, completed
    notes: Optional[str] = None


class AssignmentResponse(BaseModel):
    id: int
    shipment_id: int
    driver_id: int
    vehicle_id: int
    assigned_by: int
    status: str
    driver_accepted_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
