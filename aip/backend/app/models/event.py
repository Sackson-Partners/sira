from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean, Enum as SAEnum
from sqlalchemy.sql import func
from ..core.database import Base
import enum


class EventType(str, enum.Enum):
    webinar = "webinar"
    roadshow = "roadshow"
    lp_meeting = "lp_meeting"
    ic_meeting = "ic_meeting"
    site_visit = "site_visit"
    conference = "conference"
    closing = "closing"
    other = "other"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    event_type = Column(SAEnum(EventType), default=EventType.other)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    location = Column(String(500), nullable=True)
    virtual_link = Column(String(1000), nullable=True)
    is_virtual = Column(Boolean, default=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    attendees = Column(JSON, default=list)  # list of {user_id, investor_id, name, status}
    max_attendees = Column(Integer, nullable=True)
    is_public = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
