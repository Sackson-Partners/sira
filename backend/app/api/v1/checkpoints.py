"""
Checkpoints API — Driver GPS checkpoint confirmations
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.checkpoint import Checkpoint
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas.checkpoint import CheckpointCreate, CheckpointResponse, CheckpointVerify

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=CheckpointResponse, status_code=status.HTTP_201_CREATED)
def create_checkpoint(
    payload: CheckpointCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a driver checkpoint confirmation.
    Works both online (direct) and is also called by the sync engine for offline events.
    """
    # Verify shipment exists
    shipment = db.query(Shipment).filter(Shipment.id == payload.shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Deduplication by client_event_id
    if payload.client_event_id:
        existing = (
            db.query(Checkpoint)
            .filter(Checkpoint.client_event_id == payload.client_event_id)
            .first()
        )
        if existing:
            return existing

    cp = Checkpoint(
        shipment_id=payload.shipment_id,
        organization_id=payload.organization_id,
        user_id=current_user.id,
        role=current_user.role,
        checkpoint_type=payload.checkpoint_type,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_meters=payload.accuracy_meters,
        altitude_m=payload.altitude_m,
        location_name=payload.location_name,
        notes=payload.notes,
        offline_queued=payload.offline_queued,
        device_id=payload.device_id,
        client_event_id=payload.client_event_id,
        timestamp=payload.timestamp or datetime.now(timezone.utc),
        synced_at=datetime.now(timezone.utc) if not payload.offline_queued else None,
        extra_metadata=payload.metadata or {},
    )
    db.add(cp)
    db.commit()
    db.refresh(cp)

    logger.info(
        f"Checkpoint created: id={cp.id}, shipment={cp.shipment_id}, "
        f"type={cp.checkpoint_type}, user={current_user.id}"
    )
    return cp


@router.get("/shipment/{shipment_id}", response_model=List[CheckpointResponse])
def list_checkpoints(
    shipment_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all checkpoints for a given shipment, ordered by timestamp."""
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    checkpoints = (
        db.query(Checkpoint)
        .filter(Checkpoint.shipment_id == shipment_id)
        .order_by(Checkpoint.timestamp.asc())
        .limit(limit)
        .all()
    )
    return checkpoints


@router.get("/{checkpoint_id}", response_model=CheckpointResponse)
def get_checkpoint(
    checkpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cp = db.query(Checkpoint).filter(Checkpoint.id == checkpoint_id).first()
    if not cp:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return cp


@router.post("/{checkpoint_id}/verify", response_model=CheckpointResponse)
def verify_checkpoint(
    checkpoint_id: int,
    payload: CheckpointVerify,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fleet manager or port officer verifies a checkpoint."""
    cp = db.query(Checkpoint).filter(Checkpoint.id == checkpoint_id).first()
    if not cp:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    cp.is_verified = payload.is_verified
    cp.verified_by = current_user.id
    cp.verified_at = datetime.now(timezone.utc)
    if payload.notes:
        cp.notes = payload.notes
    db.commit()
    db.refresh(cp)
    return cp
