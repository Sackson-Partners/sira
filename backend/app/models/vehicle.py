"""
Vehicle Model — Trucks, tankers, and other land/multi-modal transport assets
Distinct from the existing Asset model (which covers maritime/rail assets).
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON
from datetime import datetime, timezone

from app.core.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    plate_number = Column(String(50), nullable=False)
    vehicle_type = Column(
        String(30), nullable=False, default="truck"
    )  # truck, tanker, vessel, train, drone
    make = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    year = Column(Integer, nullable=True)
    capacity_tons = Column(Float, nullable=True)

    # IoT device linking
    iot_device_id = Column(String(100), unique=True, nullable=True, index=True)
    iot_device_type = Column(String(30), nullable=True)  # gps_tracker, obd2, asset_tracker

    # Last known location
    last_known_lat = Column(Float, nullable=True)
    last_known_lng = Column(Float, nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(
        String(30), nullable=False, default="available"
    )  # available, in_transit, maintenance, offline

    metadata_ = Column("metadata", JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Vehicle(id={self.id}, plate='{self.plate_number}', type='{self.vehicle_type}')>"
