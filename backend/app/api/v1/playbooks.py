"""
Playbook Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.playbook import Playbook
from app.models.user import User
from app.schemas.playbook import PlaybookCreate, PlaybookUpdate, PlaybookResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[PlaybookResponse])
async def list_playbooks(
    incident_type: Optional[str] = None,
    domain: Optional[str] = None,
    is_active: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List playbooks with optional filtering"""
    query = db.query(Playbook).filter(Playbook.is_active == is_active)

    if incident_type:
        query = query.filter(Playbook.incident_type == incident_type)
    if domain:
        query = query.filter(Playbook.domain == domain)

    playbooks = query.order_by(Playbook.title).all()
    return playbooks


@router.get("/{playbook_id}", response_model=PlaybookResponse)
async def get_playbook(
    playbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get playbook by ID"""
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id).first()
    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook not found"
        )
    return playbook


@router.post("/", response_model=PlaybookResponse, status_code=status.HTTP_201_CREATED)
async def create_playbook(
    playbook_data: PlaybookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "admin"]))
):
    """Create a new playbook"""
    playbook = Playbook(
        **playbook_data.model_dump(),
        created_by=current_user.id
    )

    db.add(playbook)
    db.commit()
    db.refresh(playbook)

    logger.info(f"Playbook created: {playbook.title} by {current_user.username}")
    return playbook


@router.put("/{playbook_id}", response_model=PlaybookResponse)
async def update_playbook(
    playbook_id: int,
    playbook_data: PlaybookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "admin"]))
):
    """Update a playbook"""
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id).first()
    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook not found"
        )

    update_data = playbook_data.model_dump(exclude_unset=True)

    # Increment version if steps are updated
    if "steps" in update_data:
        playbook.version += 1

    for field, value in update_data.items():
        setattr(playbook, field, value)

    db.commit()
    db.refresh(playbook)

    logger.info(f"Playbook updated: {playbook.title} by {current_user.username}")
    return playbook


@router.delete("/{playbook_id}")
async def delete_playbook(
    playbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Delete a playbook (soft delete - deactivate)"""
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id).first()
    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook not found"
        )

    playbook.is_active = False
    db.commit()

    logger.info(f"Playbook deactivated: {playbook.title} by {current_user.username}")
    return {"message": "Playbook deactivated successfully"}


@router.get("/search/{incident_type}")
async def search_playbooks(
    incident_type: str,
    domain: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search for playbooks by incident type"""
    query = db.query(Playbook).filter(
        Playbook.is_active == True,  # noqa: E712
        Playbook.incident_type.ilike(f"%{incident_type}%")
    )

    if domain:
        query = query.filter(Playbook.domain == domain)

    playbooks = query.all()
    return playbooks
