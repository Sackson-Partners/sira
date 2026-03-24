from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base
import enum


class ProjectStatus(str, enum.Enum):
    draft = "draft"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"
    active = "active"
    closed = "closed"
    on_hold = "on_hold"


class ProjectType(str, enum.Enum):
    equity = "equity"
    debt = "debt"
    mezzanine = "mezzanine"
    real_estate = "real_estate"
    infrastructure = "infrastructure"
    venture = "venture"
    private_equity = "private_equity"
    other = "other"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False, index=True)
    code = Column(String(50), unique=True, index=True)  # e.g. PRJ-001
    description = Column(Text, nullable=True)
    status = Column(SAEnum(ProjectStatus), default=ProjectStatus.draft, nullable=False)
    project_type = Column(SAEnum(ProjectType), default=ProjectType.equity)

    # Financials
    target_raise = Column(Float, nullable=True)
    minimum_investment = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    irr_target = Column(Float, nullable=True)
    equity_multiple_target = Column(Float, nullable=True)
    hold_period_years = Column(Float, nullable=True)

    # Location & Sector
    country = Column(String(100), nullable=True)
    sector = Column(String(200), nullable=True)
    sub_sector = Column(String(200), nullable=True)

    # Dates
    deal_open_date = Column(DateTime(timezone=True), nullable=True)
    deal_close_date = Column(DateTime(timezone=True), nullable=True)
    expected_close_date = Column(DateTime(timezone=True), nullable=True)

    # Contacts
    lead_analyst_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    sponsor_name = Column(String(500), nullable=True)
    sponsor_contact = Column(String(255), nullable=True)

    # Meta
    tags = Column(JSON, default=list)
    custom_fields = Column(JSON, default=dict)
    source = Column(String(255), nullable=True)  # how the deal was sourced
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    documents = relationship("ProjectDocument", back_populates="project", cascade="all, delete-orphan")
    notes = relationship("ProjectNote", back_populates="project", cascade="all, delete-orphan")


class ProjectDocument(Base):
    __tablename__ = "project_documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=True)
    file_size = Column(Integer, nullable=True)
    storage_path = Column(String(1000), nullable=False)
    doc_category = Column(String(100), default="general")
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="documents")


class ProjectNote(Base):
    __tablename__ = "project_notes"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    content = Column(Text, nullable=False)
    note_type = Column(String(100), default="general")
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="notes")
