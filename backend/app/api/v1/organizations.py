"""
Organizations API — Multi-tenant organization management
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new organization (tenant). Requires admin role."""
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    existing = db.query(Organization).filter(Organization.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Organization slug already exists")

    org = Organization(**payload.model_dump())
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.get("/", response_model=List[OrganizationResponse])
def list_organizations(
    is_active: Optional[bool] = True,
    org_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Organization).filter(Organization.deleted_at.is_(None))
    if is_active is not None:
        query = query.filter(Organization.is_active == is_active)
    if org_type:
        query = query.filter(Organization.type == org_type)
    return query.offset(skip).limit(limit).all()


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = db.query(Organization).filter(
        Organization.id == org_id,
        Organization.deleted_at.is_(None),
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.patch("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: int,
    payload: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    org = db.query(Organization).filter(
        Organization.id == org_id,
        Organization.deleted_at.is_(None),
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(org, field, value)

    db.commit()
    db.refresh(org)
    return org
