from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, JSON, Boolean, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base
import enum


class ICSessionStatus(str, enum.Enum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class ICDecision(str, enum.Enum):
    approved = "approved"
    rejected = "rejected"
    deferred = "deferred"
    conditional = "conditional"
    pending = "pending"


class ICSession(Base):
    __tablename__ = "ic_sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    session_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(SAEnum(ICSessionStatus), default=ICSessionStatus.scheduled)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    agenda = Column(Text, nullable=True)
    minutes = Column(Text, nullable=True)
    decision = Column(SAEnum(ICDecision), default=ICDecision.pending)
    decision_notes = Column(Text, nullable=True)
    conditions = Column(Text, nullable=True)  # for conditional approvals
    quorum_required = Column(Integer, default=3)
    quorum_met = Column(Boolean, default=False)
    chaired_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    documents = Column(JSON, default=list)
    attendees = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    votes = relationship("ICVote", back_populates="session", cascade="all, delete-orphan")


class ICVote(Base):
    __tablename__ = "ic_votes"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("ic_sessions.id"), nullable=False)
    voter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vote = Column(SAEnum(ICDecision), nullable=False)
    rationale = Column(Text, nullable=True)
    conditions = Column(Text, nullable=True)
    voted_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ICSession", back_populates="votes")
