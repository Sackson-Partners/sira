"""
Fleet & Asset Model - Trucks, rail wagons, equipment, and asset management
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    asset_type = Column(String(50), nullable=False, index=True)  # truck, rail_wagon, barge, crane, loader, trailer
    sub_type = Column(String(100))  # e.g., flatbed, tanker, hopper, gantry_crane
    owner = Column(String(255))
    operator = Column(String(255))

    # Specifications
    capacity = Column(Float)  # tonnes or TEU
    max_payload = Column(Float)
    fuel_type = Column(String(50))
    year_manufactured = Column(Integer)
    registration = Column(String(100))

    # Current status
    status = Column(String(50), default="available", index=True)  # available, in_transit, loading, unloading, maintenance, breakdown, idle
    current_location = Column(String(255))
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    current_speed = Column(Float, nullable=True)
    assigned_corridor_id = Column(Integer, ForeignKey("corridors.id"), nullable=True)
    assigned_shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)

    # Utilization
    utilization_pct = Column(Float, default=0.0)  # rolling 30-day utilization
    total_trips = Column(Integer, default=0)
    total_distance_km = Column(Float, default=0.0)
    last_trip_end = Column(DateTime(timezone=True))

    # Maintenance
    next_maintenance = Column(DateTime(timezone=True))
    maintenance_status = Column(String(50), default="ok")  # ok, due_soon, overdue
    odometer_km = Column(Float, default=0.0)

    # IoT
    iot_device_id = Column(String(100), nullable=True)
    last_telemetry_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    corridor = relationship("Corridor", back_populates="assets")
    shipment = relationship("Shipment", foreign_keys=[assigned_shipment_id])
    maintenance_records = relationship("MaintenanceRecord", back_populates="asset")
    dispatch_records = relationship("DispatchRecord", back_populates="asset")

    def __repr__(self):
        return f"<Asset(id={self.id}, code='{self.asset_code}', type='{self.asset_type}')>"


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    vessel_id = Column(Integer, ForeignKey("vessels.id"), nullable=True)
    maintenance_type = Column(String(100), nullable=False)  # scheduled, breakdown, inspection, overhaul
    description = Column(Text)
    scheduled_date = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    cost = Column(Float, default=0.0)
    vendor = Column(String(255))
    status = Column(String(50), default="scheduled")  # scheduled, in_progress, completed, cancelled
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    asset = relationship("Asset", back_populates="maintenance_records")
    vessel = relationship("Vessel", back_populates="maintenance_records")

    def __repr__(self):
        return f"<MaintenanceRecord(id={self.id}, type='{self.maintenance_type}')>"


class DispatchRecord(Base):
    __tablename__ = "dispatch_records"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    origin = Column(String(255), nullable=False)
    destination = Column(String(255), nullable=False)
    dispatched_at = Column(DateTime(timezone=True), nullable=False)
    estimated_arrival = Column(DateTime(timezone=True))
    actual_arrival = Column(DateTime(timezone=True))
    cargo_type = Column(String(100))
    cargo_volume = Column(Float)
    status = Column(String(50), default="dispatched")  # dispatched, in_transit, arrived, completed, cancelled
    driver_name = Column(String(255))
    driver_contact = Column(String(100))
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    asset = relationship("Asset", back_populates="dispatch_records")
    shipment = relationship("Shipment", back_populates="dispatch_records")

    def __repr__(self):
        return f"<DispatchRecord(id={self.id}, asset_id={self.asset_id})>"
