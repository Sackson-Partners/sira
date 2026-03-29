"""
Organization Model — Multi-Tenant Support
Each organization is a tenant (logistics company, port authority, mining co, etc.)
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from datetime import datetime, timezone

from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # URL-friendly ID
    type = Column(
        String(50), nullable=False, default="logistics"
    )  # logistics, port, government, mining, energy, agriculture
    country_code = Column(String(2), nullable=False, default="GH")
    timezone = Column(String(50), nullable=False, default="Africa/Accra")
    plan = Column(String(20), nullable=False, default="starter")  # starter, professional, enterprise
    settings = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Organization(id={self.id}, slug='{self.slug}', type='{self.type}')>"
