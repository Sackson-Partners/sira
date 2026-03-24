"""
PIS = Project Information Summary
A structured summary sheet for each investment project.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from ..core.database import Base


class PIS(Base):
    __tablename__ = "pis"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, unique=True)

    # Executive Summary
    executive_summary = Column(Text, nullable=True)
    investment_thesis = Column(Text, nullable=True)
    key_highlights = Column(JSON, default=list)  # bullet points

    # Market Overview
    market_size = Column(Float, nullable=True)
    market_size_unit = Column(String(50), default="USD M")
    market_growth_rate = Column(Float, nullable=True)
    market_description = Column(Text, nullable=True)

    # Business Description
    business_model = Column(Text, nullable=True)
    revenue_model = Column(Text, nullable=True)
    competitive_advantages = Column(JSON, default=list)
    key_risks = Column(JSON, default=list)
    risk_mitigants = Column(JSON, default=list)

    # Financial Summary
    revenue_current = Column(Float, nullable=True)
    revenue_projected = Column(Float, nullable=True)
    ebitda_current = Column(Float, nullable=True)
    ebitda_projected = Column(Float, nullable=True)
    debt_equity_ratio = Column(Float, nullable=True)

    # Deal Structure
    deal_structure = Column(Text, nullable=True)
    use_of_proceeds = Column(Text, nullable=True)
    exit_strategy = Column(Text, nullable=True)
    exit_options = Column(JSON, default=list)

    # Team
    management_team = Column(JSON, default=list)  # [{name, title, bio}]
    board_members = Column(JSON, default=list)
    key_advisors = Column(JSON, default=list)

    # AI-generated content flags
    ai_generated = Column(JSON, default=dict)  # track which fields were AI-generated

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
