"""
EIN = Economic Impact Note (or Enterprise Investment Note).
Captures the economic/social impact analysis of a project.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from ..core.database import Base


class EIN(Base):
    __tablename__ = "ein"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, unique=True)

    # Economic Impact
    jobs_created_direct = Column(Integer, nullable=True)
    jobs_created_indirect = Column(Integer, nullable=True)
    gdp_contribution = Column(Float, nullable=True)
    gdp_unit = Column(String(50), default="USD M")
    tax_revenue_generated = Column(Float, nullable=True)
    local_procurement_percent = Column(Float, nullable=True)  # % of spend local

    # Social Impact
    communities_impacted = Column(Integer, nullable=True)
    population_benefited = Column(Integer, nullable=True)
    social_impact_areas = Column(JSON, default=list)  # education, health, infrastructure...
    sdg_alignment = Column(JSON, default=list)  # UN Sustainable Development Goals (1-17)
    esg_score = Column(Float, nullable=True)  # 0-100

    # Environmental Impact
    co2_reduction_tonnes = Column(Float, nullable=True)
    renewable_energy_mw = Column(Float, nullable=True)
    water_saved_m3 = Column(Float, nullable=True)
    waste_reduced_tonnes = Column(Float, nullable=True)
    environmental_certifications = Column(JSON, default=list)

    # Financial Additionality
    leverage_ratio = Column(Float, nullable=True)  # private : public funding
    crowded_in_capital = Column(Float, nullable=True)
    blended_finance_structure = Column(Text, nullable=True)

    # Narrative
    impact_thesis = Column(Text, nullable=True)
    impact_measurement_framework = Column(Text, nullable=True)
    impact_risks = Column(JSON, default=list)
    impact_kpis = Column(JSON, default=list)  # [{kpi, baseline, target, unit}]

    # AI
    ai_generated = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
