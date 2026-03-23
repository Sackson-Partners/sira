"""
Driver Model — Extension of User with driver-specific data
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, Float, ForeignKey
from datetime import datetime, timezone

from app.core.database import Base


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    license_number = Column(String(100), nullable=False)
    license_class = Column(String(20), nullable=True)
    license_expiry = Column(Date, nullable=True)

    current_vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)

    # AI-computed performance score (0-100)
    performance_score = Column(Float, nullable=False, default=100.0)
    total_trips = Column(Integer, nullable=False, default=0)
    total_km = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Driver(id={self.id}, user_id={self.user_id}, license='{self.license_number}')>"
