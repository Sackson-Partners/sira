"""
Assignments API — Shipment ↔ Driver ↔ Vehicle assignment management
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.assignment import Assignment
from app.models.shipment import Shipment
from app.models.vehicle import Vehicle
from app.models.user import User
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate, AssignmentResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assign a driver and vehicle to a shipment."""
    # Validate shipment
    shipment = db.query(Shipment).filter(Shipment.id == payload.shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Validate vehicle
    vehicle = db.query(Vehicle).filter(Vehicle.id == payload.vehicle_id, Vehicle.deleted_at.is_(None)).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    # Validate driver user exists
    driver = db.query(User).filter(User.id == payload.driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    assignment = Assignment(
        shipment_id=payload.shipment_id,
        driver_id=payload.driver_id,
        vehicle_id=payload.vehicle_id,
        assigned_by=current_user.id,
        notes=payload.notes,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    logger.info(
        f"Assignment created: id={assignment.id}, shipment={payload.shipment_id}, "
        f"driver={payload.driver_id}, vehicle={payload.vehicle_id}"
    )
    return assignment


@router.get("/", response_model=List[AssignmentResponse])
def list_assignments(
    shipment_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    assignment_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Assignment)
    if shipment_id:
        query = query.filter(Assignment.shipment_id == shipment_id)
    if driver_id:
        query = query.filter(Assignment.driver_id == driver_id)
    if assignment_status:
        query = query.filter(Assignment.status == assignment_status)
    return query.order_by(Assignment.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{assignment_id}", response_model=AssignmentResponse)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@router.patch("/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(
    assignment_id: int,
    payload: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update assignment status (e.g. driver accepts/rejects, fleet manager marks active)."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if payload.status:
        assignment.status = payload.status
        if payload.status == "accepted":
            assignment.driver_accepted_at = datetime.now(timezone.utc)
    if payload.notes is not None:
        assignment.notes = payload.notes

    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/{assignment_id}/accept", response_model=AssignmentResponse)
def accept_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Driver accepts their assignment."""
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.driver_id == current_user.id,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    assignment.status = "accepted"
    assignment.driver_accepted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/{assignment_id}/reject", response_model=AssignmentResponse)
def reject_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Driver rejects their assignment."""
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.driver_id == current_user.id,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    assignment.status = "rejected"
    db.commit()
    db.refresh(assignment)
    return assignment
