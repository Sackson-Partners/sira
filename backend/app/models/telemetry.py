"""
SIRA Platform - Telemetry & Fleet Models
Phase 2: TimescaleDB hypertables for telematics, AIS vessel positions,
fleet assets, maintenance, and AI insights.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


# ---------------------------------------------------------------------------
# Organisations (multi-tenant)
# ---------------------------------------------------------------------------

class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    plan = Column(String(50), default="standard")
    settings_json = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    vehicles = relationship("Vehicle", back_populates="organisation", lazy="select")
    shipments = relationship("Shipment", back_populates="organisation", lazy="select")


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False)
    plate = Column(String(50), unique=True, nullable=False)
    vehicle_type = Column(String(50), default="truck")  # truck, train, barge
    make = Column(String(100))
    model = Column(String(100))
    year = Column(Integer)
    status = Column(String(30), default="available")  # available, in_trip, maintenance, inactive
    flespi_device_id = Column(String(100), unique=True)  # Flespi ident
    assigned_driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organisation = relationship("Organisation", back_populates="vehicles")
    driver = relationship("Driver", foreign_keys=[assigned_driver_id])
    trips = relationship("Trip", back_populates="vehicle", lazy="select")
    maintenance_records = relationship("MaintenanceRecord", back_populates="vehicle")
    maintenance_predictions = relationship("MaintenancePrediction", back_populates="vehicle")


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"))
    supabase_user_id = Column(String(36), unique=True)  # Supabase auth.uid
    full_name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    licence_number = Column(String(100))
    licence_expiry = Column(DateTime(timezone=True))
    hours_driven_total = Column(Float, default=0.0)
    performance_score = Column(Float, default=100.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Trips
# ---------------------------------------------------------------------------

class Trip(Base):
    __tablename__ = "trips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"))
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"))
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=True)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=True)
    origin = Column(String(500))
    destination = Column(String(500))
    origin_lat = Column(Float)
    origin_lon = Column(Float)
    dest_lat = Column(Float)
    dest_lon = Column(Float)
    cargo_type = Column(String(100))
    cargo_weight_tonnes = Column(Float)
    status = Column(String(30), default="scheduled")  # scheduled, departed, in_progress, arrived, delayed, cancelled
    scheduled_departure = Column(DateTime(timezone=True))
    actual_departure = Column(DateTime(timezone=True))
    scheduled_arrival = Column(DateTime(timezone=True))
    actual_arrival = Column(DateTime(timezone=True))
    ai_delay_risk = Column(String(20))  # LOW, MEDIUM, HIGH, CRITICAL
    ai_delay_hours_estimate = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    vehicle = relationship("Vehicle", back_populates="trips")
    driver = relationship("Driver", foreign_keys=[driver_id])
    shipment = relationship("Shipment", back_populates="trips")


# ---------------------------------------------------------------------------
# Shipments (Import / Export)
# ---------------------------------------------------------------------------

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"))
    reference = Column(String(100), unique=True)
    shipment_type = Column(String(20))  # import, export
    commodity = Column(String(100))     # oil, iron_ore, bauxite
    quantity_tonnes = Column(Float)
    origin_port = Column(String(200))
    destination = Column(String(200))
    vessel_mmsi = Column(String(20))    # For maritime leg
    status = Column(String(50), default="pending")
    customs_cleared = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organisation = relationship("Organisation", back_populates="shipments")
    trips = relationship("Trip", back_populates="shipment")


# ---------------------------------------------------------------------------
# Telemetry Events (TimescaleDB hypertable — partitioned by timestamp)
# NOTE: The hypertable conversion is done via Alembic migration, not here.
# ---------------------------------------------------------------------------

class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    # Composite PK for hypertable compatibility
    timestamp = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(String(100), primary_key=True, nullable=False)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=True)
    lat = Column(Float)
    lon = Column(Float)
    speed = Column(Float)           # km/h
    fuel_level = Column(Float)      # %
    engine_temp = Column(Float)     # °C
    odometer = Column(Float)        # km
    heading = Column(Float)         # degrees
    ignition = Column(Boolean)
    ext_voltage = Column(Float)     # V
    alarm_event_id = Column(Integer)
    raw_payload = Column(JSONB)


# ---------------------------------------------------------------------------
# Vessel Positions (TimescaleDB hypertable)
# ---------------------------------------------------------------------------

class VesselPosition(Base):
    __tablename__ = "vessel_positions"

    timestamp = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    mmsi = Column(String(20), primary_key=True, nullable=False)
    imo = Column(String(20))
    vessel_name = Column(String(200))
    lat = Column(Float)
    lon = Column(Float)
    speed = Column(Float)           # knots
    heading = Column(Float)
    course = Column(Float)
    status = Column(String(50))
    destination_port = Column(String(200))
    eta = Column(DateTime(timezone=True))
    draught = Column(Float)
    vessel_type = Column(String(100))


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"))
    service_type = Column(String(100))
    service_date = Column(DateTime(timezone=True))
    odometer_at_service = Column(Float)
    cost = Column(Float)
    technician = Column(String(200))
    notes = Column(Text)
    next_service_due_km = Column(Float)
    next_service_due_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    vehicle = relationship("Vehicle", back_populates="maintenance_records")


class MaintenancePrediction(Base):
    __tablename__ = "maintenance_predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"))
    predicted_at = Column(DateTime(timezone=True), server_default=func.now())
    urgency = Column(String(20))    # LOW, MEDIUM, HIGH, CRITICAL
    failure_type = Column(String(100))
    days_to_failure = Column(Integer)
    ai_reasoning = Column(Text)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True))

    vehicle = relationship("Vehicle", back_populates="maintenance_predictions")


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class Alert(Base):
    __tablename__ = "phase2_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=True)
    alert_type = Column(String(100))    # LOW_FUEL, ENGINE_OVERHEAT, ROUTE_DEVIATION, etc.
    severity = Column(String(20))       # LOW, MEDIUM, HIGH, CRITICAL
    message = Column(Text)
    ai_analysis = Column(JSONB)
    resolved = Column(Boolean, default=False)
    resolved_by = Column(String(100))
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Geofences
# ---------------------------------------------------------------------------

class Geofence(Base):
    __tablename__ = "geofences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"))
    name = Column(String(255), nullable=False)
    geofence_type = Column(String(50))  # mine_site, port, storage, restricted
    geometry_json = Column(JSONB)       # GeoJSON polygon
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Market Data
# ---------------------------------------------------------------------------

class MarketDataPoint(Base):
    __tablename__ = "market_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commodity = Column(String(100))     # oil, iron_ore, bauxite, fuel
    price = Column(Float)
    currency = Column(String(10), default="USD")
    unit = Column(String(50))           # per_tonne, per_barrel
    source = Column(String(100))        # quandl, refinitiv
    captured_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# AI Insights (stored AI analysis outputs for auditability)
# ---------------------------------------------------------------------------

class AIInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    context_type = Column(String(50))   # shipment, vehicle, market
    context_id = Column(String(100))    # UUID of related entity
    model = Column(String(100))         # claude-3-5-sonnet, gpt-4o
    prompt_type = Column(String(100))   # delay_risk, maintenance, market_intel
    response_json = Column(JSONB)
    tokens_used = Column(Integer)
    latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
