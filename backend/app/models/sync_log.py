"""
SyncLog Model — Audit trail for offline batch sync operations
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from datetime import datetime, timezone

from app.core.database import Base


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(100), nullable=False, index=True)

    sync_type = Column(String(20), nullable=False, default="batch")  # full, batch, delta

    events_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    conflicts_count = Column(Integer, nullable=False, default=0)

    payload = Column(JSON, nullable=True)
    response = Column(JSON, nullable=True)

    status = Column(
        String(20), nullable=False, default="pending"
    )  # pending, processing, completed, partial, failed

    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SyncLog(id={self.id}, user_id={self.user_id}, status='{self.status}')>"
