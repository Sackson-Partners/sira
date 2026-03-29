"""
Vessel Model - Ship/vessel tracking and management
"""

from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class Vessel(Base):
    __tablename__ = "vessels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    imo_number = Column(String(20), unique=True, index=True)
    mmsi = Column(String(20), unique=True, nullable=True)
    vessel_type = Column(String(100), nullable=False)  # bulk_carrier, tanker, container, barge, tug
    flag = Column(String(100))
    dwt = Column(Float)  # Deadweight tonnage
    loa = Column(Float)  # Length overall (meters)
    beam = Column(Float)  # Beam width (meters)
    draft = Column(Float)  # Current draft (meters)
    year_built = Column(Integer)
    owner = Column(String(255))
    operator = Column(String(255))
    class_society = Column(String(100))

    # Current position
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    current_speed = Column(Float, nullable=True)  # knots
    current_heading = Column(Float, nullable=True)  # degrees
    current_destination = Column(String(255), nullable=True)
    position_updated_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(String(50), default="active", index=True)  # active, idle, maintenance, drydock, decommissioned
    ais_status = Column(String(50))  # AIS navigation status

    # Charter info
    charter_type = Column(String(50))  # owned, time_charter, voyage_charter, spot
    charter_rate = Column(Float, nullable=True)  # daily rate USD
    charter_start = Column(DateTime(timezone=True), nullable=True)
    charter_end = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    shipments = relationship("Shipment", back_populates="vessel")
    berth_bookings = relationship("BerthBooking", back_populates="vessel")
    maintenance_records = relationship("MaintenanceRecord", back_populates="vessel")

    def __repr__(self):
        return f"<Vessel(id={self.id}, name='{self.name}', imo='{self.imo_number}')>"
