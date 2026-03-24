from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.sql import func
from ..core.database import Base
import enum


class DealStage(str, enum.Enum):
    sourcing = "sourcing"
    initial_review = "initial_review"
    due_diligence = "due_diligence"
    ic_review = "ic_review"
    term_sheet = "term_sheet"
    negotiation = "negotiation"
    closing = "closing"
    closed_won = "closed_won"
    closed_lost = "closed_lost"
    on_hold = "on_hold"


class PipelineDeal(Base):
    __tablename__ = "pipeline_deals"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    name = Column(String(500), nullable=False)
    stage = Column(SAEnum(DealStage), default=DealStage.sourcing, nullable=False)
    probability = Column(Float, default=0.0)  # 0-100%
    deal_size = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    expected_close_date = Column(DateTime(timezone=True), nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    investor_id = Column(Integer, ForeignKey("investors.id"), nullable=True)
    description = Column(Text, nullable=True)
    next_action = Column(String(500), nullable=True)
    next_action_date = Column(DateTime(timezone=True), nullable=True)
    tags = Column(JSON, default=list)
    custom_fields = Column(JSON, default=dict)
    lost_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    stage_changed_at = Column(DateTime(timezone=True), nullable=True)
