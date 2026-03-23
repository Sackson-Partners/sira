"""
Route Model — Predefined truck/transport corridor routes
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON
from datetime import datetime, timezone

from app.core.database import Base


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    origin = Column(String(255), nullable=False)
    origin_lat = Column(Float, nullable=False)
    origin_lng = Column(Float, nullable=False)
    destination = Column(String(255), nullable=False)
    destination_lat = Column(Float, nullable=False)
    destination_lng = Column(Float, nullable=False)

    # JSON array of waypoints: [{name, lat, lng, type}]
    waypoints = Column(JSON, nullable=False, default=list)

    distance_km = Column(Float, nullable=True)
    estimated_hours = Column(Float, nullable=True)

    # AI-assessed route risk
    risk_profile = Column(String(20), nullable=False, default="low")  # low, medium, high, critical

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Route(id={self.id}, name='{self.name}', risk='{self.risk_profile}')>"
