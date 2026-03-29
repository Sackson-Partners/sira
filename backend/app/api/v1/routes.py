"""
Routes API — Predefined truck/transport route management
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.route import Route
from app.models.user import User
from app.schemas.route import RouteCreate, RouteUpdate, RouteResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
def create_route(
    payload: RouteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    route = Route(**payload.model_dump())
    db.add(route)
    db.commit()
    db.refresh(route)
    return route


@router.get("/", response_model=List[RouteResponse])
def list_routes(
    organization_id: Optional[int] = None,
    risk_profile: Optional[str] = None,
    is_active: bool = True,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Route).filter(Route.is_active == is_active)
    if organization_id:
        query = query.filter(Route.organization_id == organization_id)
    if risk_profile:
        query = query.filter(Route.risk_profile == risk_profile)
    return query.offset(skip).limit(limit).all()


@router.get("/{route_id}", response_model=RouteResponse)
def get_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.patch("/{route_id}", response_model=RouteResponse)
def update_route(
    route_id: int,
    payload: RouteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(route, field, value)

    db.commit()
    db.refresh(route)
    return route


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    route.is_active = False
    db.commit()
