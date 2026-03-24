from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean, Enum as SAEnum
from sqlalchemy.sql import func
from ..core.database import Base
import enum


class VerificationType(str, enum.Enum):
    kyc = "kyc"       # Know Your Customer
    kyb = "kyb"       # Know Your Business
    aml = "aml"       # Anti-Money Laundering
    accreditation = "accreditation"
    identity = "identity"


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"
    more_info_needed = "more_info_needed"


class Verification(Base):
    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, index=True)
    investor_id = Column(Integer, ForeignKey("investors.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verification_type = Column(SAEnum(VerificationType), nullable=False)
    status = Column(SAEnum(VerificationStatus), default=VerificationStatus.pending)

    # Documents submitted
    documents = Column(JSON, default=list)  # list of {name, path, type, uploaded_at}

    # Review
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Validity
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    # External verification reference (e.g. Jumio, Onfido)
    external_ref = Column(String(255), nullable=True)
    external_status = Column(String(100), nullable=True)
    external_data = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
