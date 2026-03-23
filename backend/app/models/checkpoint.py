"""
Checkpoint Model — GPS-based driver checkpoint confirmations along a shipment route
Supports both online and offline (queued) creation.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, JSON
from datetime import datetime, timezone

from app.core.database import Base


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)

    checkpoint_type = Column(
        String(50), nullable=False
    )  # departure, waypoint, border, port_entry, port_exit,
    # delivery, inspection, fuel_stop, emergency_stop, driver_change

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_meters = Column(Float, nullable=True)
    altitude_m = Column(Float, nullable=True)
    location_name = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    is_verified = Column(Boolean, nullable=False, default=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Offline-first fields
    offline_queued = Column(Boolean, nullable=False, default=False)
    device_id = Column(String(100), nullable=True)
    client_event_id = Column(String(100), nullable=True, unique=True)  # Deduplication key

    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    synced_at = Column(DateTime(timezone=True), nullable=True)

    extra_metadata = Column("metadata", JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Checkpoint(id={self.id}, shipment_id={self.shipment_id}, type='{self.checkpoint_type}')>"
