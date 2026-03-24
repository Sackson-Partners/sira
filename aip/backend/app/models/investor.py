from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.sql import func
from ..core.database import Base
import enum


class InvestorType(str, enum.Enum):
    individual = "individual"
    family_office = "family_office"
    institutional = "institutional"
    corporate = "corporate"
    fund = "fund"
    pension = "pension"
    sovereign = "sovereign"
    endowment = "endowment"


class InvestorStatus(str, enum.Enum):
    prospect = "prospect"
    onboarding = "onboarding"
    active = "active"
    inactive = "inactive"
    blocked = "blocked"


class Investor(Base):
    __tablename__ = "investors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False, index=True)
    investor_type = Column(SAEnum(InvestorType), default=InvestorType.individual)
    status = Column(SAEnum(InvestorStatus), default=InvestorStatus.prospect)

    # Contact
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    website = Column(String(500), nullable=True)

    # Address
    address_line1 = Column(String(500), nullable=True)
    address_line2 = Column(String(500), nullable=True)
    city = Column(String(200), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)

    # Investment Profile
    aum = Column(Float, nullable=True)  # assets under management
    investment_min = Column(Float, nullable=True)
    investment_max = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    preferred_sectors = Column(JSON, default=list)
    preferred_geographies = Column(JSON, default=list)
    risk_appetite = Column(String(50), nullable=True)  # low/medium/high

    # KYC
    kyc_status = Column(String(50), default="pending")  # pending/approved/rejected
    kyc_date = Column(DateTime(timezone=True), nullable=True)
    kyc_documents = Column(JSON, default=list)
    tax_id = Column(String(100), nullable=True)
    registration_number = Column(String(100), nullable=True)

    # Relationship
    relationship_manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, default=dict)
    tags = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
