"""
Shipment Model - End-to-end multimodal shipment tracking with chain-of-custody
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    shipment_ref = Column(String(50), unique=True, index=True, nullable=False)
    corridor_id = Column(Integer, ForeignKey("corridors.id"), nullable=True)
    vessel_id = Column(Integer, ForeignKey("vessels.id"), nullable=True)

    # Cargo details
    cargo_type = Column(String(100), nullable=False)  # iron_ore, copper_concentrate, crude_oil, lng, bauxite
    cargo_grade = Column(String(100))
    volume_tonnes = Column(Float)
    bill_of_lading = Column(String(100))

    # Origin/Destination
    origin = Column(String(255), nullable=False)
    destination = Column(String(255), nullable=False)
    origin_port_id = Column(Integer, ForeignKey("ports.id"), nullable=True)
    destination_port_id = Column(Integer, ForeignKey("ports.id"), nullable=True)

    # Laycan window
    laycan_start = Column(DateTime(timezone=True), nullable=False)
    laycan_end = Column(DateTime(timezone=True), nullable=False)

    # Status & tracking
    status = Column(String(50), default="planned", index=True)  # planned, loading, in_transit, at_port, discharging, completed, cancelled
    current_leg = Column(String(100))  # e.g., "mine_to_rail", "rail_to_port", "port_loading", "ocean", "discharge"
    current_mode = Column(String(50))  # truck, rail, barge, vessel, storage

    # ETA
    eta_destination = Column(DateTime(timezone=True))
    eta_confidence = Column(Float)  # 0-1 confidence score
    eta_updated_at = Column(DateTime(timezone=True))

    # Demurrage
    demurrage_risk_score = Column(Float, default=0.0)  # 0-100
    demurrage_exposure_usd = Column(Float, default=0.0)
    demurrage_rate_usd = Column(Float)  # per day
    demurrage_days = Column(Float, default=0.0)

    # Milestones (actual timestamps)
    loading_started = Column(DateTime(timezone=True))
    loading_completed = Column(DateTime(timezone=True))
    departed_origin = Column(DateTime(timezone=True))
    arrived_destination = Column(DateTime(timezone=True))
    discharge_started = Column(DateTime(timezone=True))
    discharge_completed = Column(DateTime(timezone=True))

    # Stakeholders
    shipper = Column(String(255))
    receiver = Column(String(255))
    freight_forwarder = Column(String(255))
    insurance_ref = Column(String(100))

    # Chain of custody
    custody_seal_id = Column(String(100))
    custody_status = Column(String(50), default="intact")  # intact, broken, tampered, verified

    # Financials
    freight_cost = Column(Float)
    insurance_cost = Column(Float)
    total_cost = Column(Float)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    corridor = relationship("Corridor", back_populates="shipments")
    vessel = relationship("Vessel", back_populates="shipments")
    berth_booking = relationship("BerthBooking", back_populates="shipment", uselist=False)
    milestones = relationship("ShipmentMilestone", back_populates="shipment", cascade="all, delete-orphan", order_by="ShipmentMilestone.planned_time")
    custody_events = relationship("CustodyEvent", back_populates="shipment", cascade="all, delete-orphan", order_by="CustodyEvent.timestamp")
    documents = relationship("ShipmentDocument", back_populates="shipment", cascade="all, delete-orphan")
    dispatch_records = relationship("DispatchRecord", back_populates="shipment")
    exceptions = relationship("ShipmentException", back_populates="shipment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Shipment(id={self.id}, ref='{self.shipment_ref}', status='{self.status}')>"


class ShipmentMilestone(Base):
    __tablename__ = "shipment_milestones"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    milestone_type = Column(String(100), nullable=False)  # departure, arrival, berth_allocated, loading_start, loading_complete, etc.
    description = Column(String(500))
    location = Column(String(255))
    mode = Column(String(50))  # truck, rail, barge, vessel
    planned_time = Column(DateTime(timezone=True))
    actual_time = Column(DateTime(timezone=True))
    variance_hours = Column(Float)  # positive = late, negative = early
    status = Column(String(50), default="pending")  # pending, completed, skipped, delayed

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    shipment = relationship("Shipment", back_populates="milestones")

    def __repr__(self):
        return f"<ShipmentMilestone(id={self.id}, type='{self.milestone_type}')>"


class CustodyEvent(Base):
    __tablename__ = "custody_events"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    event_type = Column(String(100), nullable=False)  # handover, seal_applied, seal_verified, seal_broken, inspection, weighing
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    location = Column(String(255))
    latitude = Column(Float)
    longitude = Column(Float)

    # Parties
    from_party = Column(String(255))
    to_party = Column(String(255))
    witnessed_by = Column(String(255))

    # Seal info
    seal_number = Column(String(100))
    seal_status = Column(String(50))  # applied, intact, broken, tampered

    # Cargo verification
    measured_volume = Column(Float)  # tonnes
    expected_volume = Column(Float)
    volume_variance_pct = Column(Float)

    # Digital verification
    photo_ref = Column(String(500))  # reference to photo evidence
    document_ref = Column(String(500))
    digital_signature = Column(Text)  # hash of event data
    blockchain_tx = Column(String(255))  # optional blockchain notarization

    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    shipment = relationship("Shipment", back_populates="custody_events")

    def __repr__(self):
        return f"<CustodyEvent(id={self.id}, type='{self.event_type}')>"


class ShipmentDocument(Base):
    __tablename__ = "shipment_documents"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    document_type = Column(String(100), nullable=False)  # bill_of_lading, certificate_of_origin, survey_report, invoice, sof, customs_declaration
    title = Column(String(255), nullable=False)
    file_ref = Column(String(500))
    file_hash = Column(String(128))
    status = Column(String(50), default="pending")  # pending, verified, rejected, expired
    issued_by = Column(String(255))
    issued_at = Column(DateTime(timezone=True))
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True))
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    shipment = relationship("Shipment", back_populates="documents")

    def __repr__(self):
        return f"<ShipmentDocument(id={self.id}, type='{self.document_type}')>"


class ShipmentException(Base):
    __tablename__ = "shipment_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    exception_type = Column(String(100), nullable=False)  # delay, route_deviation, volume_discrepancy, document_missing, weather, equipment_failure
    severity = Column(String(20), nullable=False)  # critical, high, medium, low
    description = Column(Text)
    impact_description = Column(Text)
    estimated_delay_hours = Column(Float)
    estimated_cost_usd = Column(Float)
    status = Column(String(50), default="open")  # open, acknowledged, mitigating, resolved
    resolution = Column(Text)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # AI-generated recommendations
    ai_recommendation = Column(Text)
    ai_confidence = Column(Float)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    shipment = relationship("Shipment", back_populates="exceptions")

    def __repr__(self):
        return f"<ShipmentException(id={self.id}, type='{self.exception_type}')>"
