from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.sql import func
from ..core.database import Base


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    integration_type = Column(String(100), nullable=False)  # azure_ad, crm, email, etc.
    is_enabled = Column(Boolean, default=False)
    config = Column(JSON, default=dict)   # masked config (no secrets)
    status = Column(String(50), default="disconnected")  # connected/disconnected/error
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
