"""
Checkpoint Schemas
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class CheckpointCreate(BaseModel):
    shipment_id: int
    organization_id: int
    checkpoint_type: str  # departure, waypoint, border, port_entry, port_exit,
    # delivery, inspection, fuel_stop, emergency_stop, driver_change
    latitude: float
    longitude: float
    accuracy_meters: Optional[float] = None
    altitude_m: Optional[float] = None
    location_name: Optional[str] = None
    notes: Optional[str] = None
    offline_queued: bool = False
    device_id: Optional[str] = None
    client_event_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class CheckpointVerify(BaseModel):
    is_verified: bool
    notes: Optional[str] = None


class CheckpointResponse(BaseModel):
    id: int
    shipment_id: int
    organization_id: int
    user_id: int
    role: str
    checkpoint_type: str
    latitude: float
    longitude: float
    accuracy_meters: Optional[float]
    altitude_m: Optional[float]
    location_name: Optional[str]
    notes: Optional[str]
    is_verified: bool
    verified_by: Optional[int]
    verified_at: Optional[datetime]
    offline_queued: bool
    device_id: Optional[str]
    client_event_id: Optional[str]
    timestamp: datetime
    synced_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
