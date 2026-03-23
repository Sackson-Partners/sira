"""
Route Schemas
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class RouteCreate(BaseModel):
    organization_id: int
    name: str
    origin: str
    origin_lat: float
    origin_lng: float
    destination: str
    destination_lat: float
    destination_lng: float
    waypoints: List[Dict[str, Any]] = []
    distance_km: Optional[float] = None
    estimated_hours: Optional[float] = None
    risk_profile: str = "low"  # low, medium, high, critical


class RouteUpdate(BaseModel):
    name: Optional[str] = None
    origin: Optional[str] = None
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination: Optional[str] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    waypoints: Optional[List[Dict[str, Any]]] = None
    distance_km: Optional[float] = None
    estimated_hours: Optional[float] = None
    risk_profile: Optional[str] = None
    is_active: Optional[bool] = None


class RouteResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    origin: str
    origin_lat: float
    origin_lng: float
    destination: str
    destination_lat: float
    destination_lng: float
    waypoints: List[Dict[str, Any]]
    distance_km: Optional[float]
    estimated_hours: Optional[float]
    risk_profile: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
