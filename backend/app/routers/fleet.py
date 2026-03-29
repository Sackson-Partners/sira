"""
SIRA Platform - Fleet Management API Router
Phase 2: Full fleet management endpoints (vehicles, drivers, trips, alerts, GeoJSON)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import TokenUser, get_current_user, require_fleet_manager
from app.core.database import get_db
from app.models.telemetry import (
    Alert, MaintenancePrediction,
    Trip, Vehicle,
)

router = APIRouter(prefix="/fleet", tags=["Fleet Management"])


# ---------------------------------------------------------------------------
# Schemas (inline for simplicity; move to schemas/ if they grow)
# ---------------------------------------------------------------------------

class VehicleCreate(BaseModel):
    plate: str
    vehicle_type: str = "truck"
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    flespi_device_id: Optional[str] = None


class VehicleResponse(BaseModel):
    id: str
    plate: str
    vehicle_type: str
    status: str
    flespi_device_id: Optional[str]

    class Config:
        from_attributes = True


class TripCreate(BaseModel):
    vehicle_id: str
    driver_id: Optional[str] = None
    origin: str
    destination: str
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    dest_lat: Optional[float] = None
    dest_lon: Optional[float] = None
    cargo_type: Optional[str] = None
    cargo_weight_tonnes: Optional[float] = None
    scheduled_departure: Optional[str] = None


class TripStatusUpdate(BaseModel):
    status: str  # scheduled, departed, in_progress, arrived, delayed, cancelled
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Vehicle Endpoints
# ---------------------------------------------------------------------------

@router.get("/vehicles", summary="List all fleet vehicles")
async def list_vehicles(
    status: Optional[str] = Query(None, description="Filter by status"),
    vehicle_type: Optional[str] = Query(None, description="Filter by type"),
    db: Session = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    """Return all vehicles for the authenticated organisation."""
    q = db.query(Vehicle)
    if status:
        q = q.filter(Vehicle.status == status)
    if vehicle_type:
        q = q.filter(Vehicle.vehicle_type == vehicle_type)
    vehicles = q.limit(500).all()
    return [
        {
            "id": str(v.id),
            "plate": v.plate,
            "vehicle_type": v.vehicle_type,
            "status": v.status,
            "make": v.make,
            "model": v.model,
            "flespi_device_id": v.flespi_device_id,
        }
        for v in vehicles
    ]


@router.post("/vehicles", status_code=status.HTTP_201_CREATED, summary="Register new vehicle")
async def create_vehicle(
    payload: VehicleCreate,
    db: Session = Depends(get_db),
    user: TokenUser = Depends(require_fleet_manager()),
):
    """Register a new vehicle in the fleet."""
    vehicle = Vehicle(
        plate=payload.plate,
        vehicle_type=payload.vehicle_type,
        make=payload.make,
        model=payload.model,
        year=payload.year,
        flespi_device_id=payload.flespi_device_id,
        status="available",
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return {"id": str(vehicle.id), "plate": vehicle.plate, "status": vehicle.status}


@router.get("/vehicles/{vehicle_id}/telemetry", summary="Latest telemetry for a vehicle")
async def get_vehicle_telemetry(
    vehicle_id: str,
    db: Session = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    """Return the most recent telemetry event for a vehicle."""
    from app.models.telemetry import TelemetryEvent
    from sqlalchemy import desc

    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    event = (
        db.query(TelemetryEvent)
        .filter(TelemetryEvent.device_id == vehicle.flespi_device_id)
        .order_by(desc(TelemetryEvent.timestamp))
        .first()
    )
    if not event:
        return {"vehicle_id": vehicle_id, "telemetry": None}

    return {
        "vehicle_id": vehicle_id,
        "plate": vehicle.plate,
        "telemetry": {
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "lat": event.lat,
            "lon": event.lon,
            "speed": event.speed,
            "fuel_level": event.fuel_level,
            "engine_temp": event.engine_temp,
            "odometer": event.odometer,
            "ignition": event.ignition,
        },
    }


@router.get("/geojson", summary="GeoJSON of all active vehicles (for Mapbox)")
async def get_fleet_geojson(
    db: Session = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    """Return GeoJSON FeatureCollection of all active vehicle positions."""
    from app.models.telemetry import TelemetryEvent
    from sqlalchemy import desc

    # Get latest telemetry per device
    vehicles = db.query(Vehicle).filter(Vehicle.status.in_(["in_trip", "available"])).all()

    features = []
    for v in vehicles:
        if not v.flespi_device_id:
            continue
        event = (
            db.query(TelemetryEvent)
            .filter(TelemetryEvent.device_id == v.flespi_device_id)
            .order_by(desc(TelemetryEvent.timestamp))
            .first()
        )
        if event and event.lat and event.lon:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [event.lon, event.lat]},
                "properties": {
                    "vehicle_id": str(v.id),
                    "plate": v.plate,
                    "vehicle_type": v.vehicle_type,
                    "status": v.status,
                    "speed": event.speed,
                    "fuel_level": event.fuel_level,
                    "engine_temp": event.engine_temp,
                    "status_color": (
                        "#ff4444" if v.status == "in_trip" and event.speed == 0
                        else "#44ff44" if v.status == "in_trip"
                        else "#ffaa00"
                    ),
                    "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                },
            })

    return {"type": "FeatureCollection", "features": features}


# ---------------------------------------------------------------------------
# Trip Endpoints
# ---------------------------------------------------------------------------

@router.post("/trips", status_code=status.HTTP_201_CREATED, summary="Schedule a new trip")
async def create_trip(
    payload: TripCreate,
    db: Session = Depends(get_db),
    user: TokenUser = Depends(require_fleet_manager()),
):
    """Schedule a new trip for a vehicle."""
    trip = Trip(
        vehicle_id=payload.vehicle_id,
        driver_id=payload.driver_id,
        origin=payload.origin,
        destination=payload.destination,
        origin_lat=payload.origin_lat,
        origin_lon=payload.origin_lon,
        dest_lat=payload.dest_lat,
        dest_lon=payload.dest_lon,
        cargo_type=payload.cargo_type,
        cargo_weight_tonnes=payload.cargo_weight_tonnes,
        status="scheduled",
    )
    db.add(trip)

    # Update vehicle status
    vehicle = db.query(Vehicle).filter(Vehicle.id == payload.vehicle_id).first()
    if vehicle:
        vehicle.status = "in_trip"

    db.commit()
    db.refresh(trip)
    return {"id": str(trip.id), "status": trip.status, "vehicle_id": payload.vehicle_id}


@router.patch("/trips/{trip_id}/status", summary="Update trip status")
async def update_trip_status(
    trip_id: str,
    payload: TripStatusUpdate,
    db: Session = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    """Update the status of a trip (departed, arrived, delayed, etc.)."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    trip.status = payload.status
    if payload.notes:
        trip.notes = payload.notes

    if payload.status == "arrived":
        from datetime import datetime, timezone
        trip.actual_arrival = datetime.now(timezone.utc)
        # Free the vehicle
        if trip.vehicle_id:
            vehicle = db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).first()
            if vehicle:
                vehicle.status = "available"

    db.commit()
    return {"id": trip_id, "status": trip.status}


# ---------------------------------------------------------------------------
# Alert Endpoints
# ---------------------------------------------------------------------------

@router.get("/alerts", summary="List active alerts")
async def list_alerts(
    resolved: bool = Query(False),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    """Return paginated active alerts."""
    q = db.query(Alert).filter(Alert.resolved == resolved)
    if severity:
        q = q.filter(Alert.severity == severity)
    alerts = q.order_by(Alert.created_at.desc()).limit(100).all()
    return [
        {
            "id": str(a.id),
            "alert_type": a.alert_type,
            "severity": a.severity,
            "message": a.message,
            "vehicle_id": str(a.vehicle_id) if a.vehicle_id else None,
            "ai_analysis": a.ai_analysis,
            "resolved": a.resolved,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/resolve", summary="Resolve an alert")
async def resolve_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    user: TokenUser = Depends(require_fleet_manager()),
):
    """Mark an alert as resolved."""
    from datetime import datetime, timezone

    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.resolved = True
    alert.resolved_by = user.sub
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": alert_id, "resolved": True}


# ---------------------------------------------------------------------------
# Maintenance Endpoints
# ---------------------------------------------------------------------------

@router.get("/maintenance/due", summary="Vehicles with upcoming service due")
async def maintenance_due(
    db: Session = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    """Return AI maintenance predictions that are not resolved."""
    predictions = (
        db.query(MaintenancePrediction)
        .filter(MaintenancePrediction.resolved == False)  # noqa: E712
        .order_by(MaintenancePrediction.days_to_failure)
        .limit(50)
        .all()
    )
    return [
        {
            "id": str(p.id),
            "vehicle_id": str(p.vehicle_id),
            "urgency": p.urgency,
            "failure_type": p.failure_type,
            "days_to_failure": p.days_to_failure,
            "ai_reasoning": p.ai_reasoning,
            "predicted_at": p.predicted_at.isoformat() if p.predicted_at else None,
        }
        for p in predictions
    ]
