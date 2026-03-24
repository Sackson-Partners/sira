"""
PESTEL = Political, Economic, Social, Technological, Environmental, Legal analysis.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.sql import func
from ..core.database import Base
import enum


class ImpactLevel(str, enum.Enum):
    very_low = "very_low"
    low = "low"
    medium = "medium"
    high = "high"
    very_high = "very_high"


class PESTEL(Base):
    __tablename__ = "pestel"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, unique=True)

    # Political
    political_factors = Column(JSON, default=list)   # [{factor, description, impact, likelihood}]
    political_score = Column(Float, nullable=True)   # 1-10
    political_summary = Column(Text, nullable=True)

    # Economic
    economic_factors = Column(JSON, default=list)
    economic_score = Column(Float, nullable=True)
    economic_summary = Column(Text, nullable=True)

    # Social
    social_factors = Column(JSON, default=list)
    social_score = Column(Float, nullable=True)
    social_summary = Column(Text, nullable=True)

    # Technological
    technological_factors = Column(JSON, default=list)
    technological_score = Column(Float, nullable=True)
    technological_summary = Column(Text, nullable=True)

    # Environmental
    environmental_factors = Column(JSON, default=list)
    environmental_score = Column(Float, nullable=True)
    environmental_summary = Column(Text, nullable=True)

    # Legal
    legal_factors = Column(JSON, default=list)
    legal_score = Column(Float, nullable=True)
    legal_summary = Column(Text, nullable=True)

    # Overall
    overall_score = Column(Float, nullable=True)
    overall_assessment = Column(Text, nullable=True)
    overall_impact = Column(SAEnum(ImpactLevel), nullable=True)

    # AI-generated
    ai_generated = Column(JSON, default=dict)
    ai_model_used = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
