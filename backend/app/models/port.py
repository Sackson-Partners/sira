"""
Port & Terminal Model - Port facilities, berths, and terminal operations
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class Port(Base):
    __tablename__ = "ports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(20), unique=True, index=True)  # UN/LOCODE
    country = Column(String(100), nullable=False)
    region = Column(String(100))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    port_type = Column(String(100))  # deep_water, river, coastal, offshore
    max_draft = Column(Float)  # meters
    max_loa = Column(Float)  # meters
    anchorage_capacity = Column(Integer)
    status = Column(String(50), default="operational")  # operational, congested, closed, restricted

    # Congestion metrics
    current_queue = Column(Integer, default=0)
    avg_wait_days = Column(Float, default=0.0)
    avg_dwell_days = Column(Float, default=0.0)

    # Contact info
    authority = Column(String(255))
    timezone = Column(String(50))
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    berths = relationship("Berth", back_populates="port", cascade="all, delete-orphan")
    corridors_origin = relationship("Corridor", foreign_keys="Corridor.origin_port_id", back_populates="origin_port")
    corridors_destination = relationship("Corridor", foreign_keys="Corridor.destination_port_id", back_populates="destination_port")

    def __repr__(self):
        return f"<Port(id={self.id}, name='{self.name}', code='{self.code}')>"


class Berth(Base):
    __tablename__ = "berths"

    id = Column(Integer, primary_key=True, index=True)
    port_id = Column(Integer, ForeignKey("ports.id"), nullable=False)
    name = Column(String(255), nullable=False)
    berth_type = Column(String(100))  # ore, container, tanker, general, multi_purpose
    max_draft = Column(Float)
    max_loa = Column(Float)
    max_beam = Column(Float)
    cargo_types = Column(Text)  # JSON array of supported cargo types
    equipment = Column(Text)  # JSON: cranes, loaders, etc.
    loading_rate = Column(Float)  # tonnes per hour
    status = Column(String(50), default="available")  # available, occupied, maintenance, reserved

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    port = relationship("Port", back_populates="berths")
    bookings = relationship("BerthBooking", back_populates="berth")

    def __repr__(self):
        return f"<Berth(id={self.id}, name='{self.name}', port_id={self.port_id})>"


class BerthBooking(Base):
    __tablename__ = "berth_bookings"

    id = Column(Integer, primary_key=True, index=True)
    berth_id = Column(Integer, ForeignKey("berths.id"), nullable=False)
    vessel_id = Column(Integer, ForeignKey("vessels.id"), nullable=False)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    scheduled_arrival = Column(DateTime(timezone=True), nullable=False)
    scheduled_departure = Column(DateTime(timezone=True), nullable=False)
    actual_arrival = Column(DateTime(timezone=True))
    actual_departure = Column(DateTime(timezone=True))
    status = Column(String(50), default="scheduled")  # scheduled, confirmed, active, completed, cancelled
    cargo_type = Column(String(100))
    cargo_volume = Column(Float)  # tonnes
    priority = Column(Integer, default=5)  # 1=highest

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    berth = relationship("Berth", back_populates="bookings")
    vessel = relationship("Vessel", back_populates="berth_bookings")
    shipment = relationship("Shipment", back_populates="berth_booking")

    def __repr__(self):
        return f"<BerthBooking(id={self.id}, berth_id={self.berth_id}, vessel_id={self.vessel_id})>"
