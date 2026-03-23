"""
Vehicle Schemas
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class VehicleCreate(BaseModel):
    organization_id: int
    plate_number: str
    vehicle_type: str = "truck"  # truck, tanker, vessel, train, drone
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    capacity_tons: Optional[float] = None
    iot_device_id: Optional[str] = None
    iot_device_type: Optional[str] = None  # gps_tracker, obd2, asset_tracker
    metadata_: Optional[Dict[str, Any]] = None


class VehicleUpdate(BaseModel):
    plate_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    capacity_tons: Optional[float] = None
    iot_device_id: Optional[str] = None
    iot_device_type: Optional[str] = None
    status: Optional[str] = None  # available, in_transit, maintenance, offline
    last_known_lat: Optional[float] = None
    last_known_lng: Optional[float] = None


class VehicleResponse(BaseModel):
    id: int
    organization_id: int
    plate_number: str
    vehicle_type: str
    make: Optional[str]
    model: Optional[str]
    year: Optional[int]
    capacity_tons: Optional[float]
    iot_device_id: Optional[str]
    iot_device_type: Optional[str]
    last_known_lat: Optional[float]
    last_known_lng: Optional[float]
    last_seen_at: Optional[datetime]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
