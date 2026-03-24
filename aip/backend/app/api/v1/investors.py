from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.investor import Investor, InvestorType, InvestorStatus
from ...models.user import User

router = APIRouter()


class InvestorCreate(BaseModel):
    name: str
    investor_type: InvestorType = InvestorType.individual
    status: InvestorStatus = InvestorStatus.prospect
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    aum: Optional[float] = None
    investment_min: Optional[float] = None
    investment_max: Optional[float] = None
    currency: str = "USD"
    preferred_sectors: Optional[List[str]] = []
    preferred_geographies: Optional[List[str]] = []
    risk_appetite: Optional[str] = None
    tax_id: Optional[str] = None
    registration_number: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = []
    custom_fields: Optional[dict] = {}


class InvestorUpdate(InvestorCreate):
    name: Optional[str] = None


@router.get("/")
def list_investors(
    skip: int = 0,
    limit: int = Query(50, le=200),
    investor_type: Optional[InvestorType] = None,
    status: Optional[InvestorStatus] = None,
    country: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Investor)
    if investor_type:
        q = q.filter(Investor.investor_type == investor_type)
    if status:
        q = q.filter(Investor.status == status)
    if country:
        q = q.filter(Investor.country.ilike(f"%{country}%"))
    if search:
        q = q.filter(
            (Investor.name.ilike(f"%{search}%")) |
            (Investor.email.ilike(f"%{search}%"))
        )
    total = q.count()
    items = q.order_by(Investor.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


@router.post("/", status_code=201)
def create_investor(
    req: InvestorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst")),
):
    investor = Investor(**req.model_dump(), relationship_manager_id=current_user.id)
    db.add(investor)
    db.commit()
    db.refresh(investor)
    return investor


@router.get("/stats")
def investor_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total = db.query(Investor).count()
    by_type = {t.value: db.query(Investor).filter(Investor.investor_type == t).count() for t in InvestorType}
    by_status = {s.value: db.query(Investor).filter(Investor.status == s).count() for s in InvestorStatus}
    return {"total": total, "by_type": by_type, "by_status": by_status}


@router.get("/{investor_id}")
def get_investor(
    investor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = db.query(Investor).filter(Investor.id == investor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investor not found")
    return inv


@router.put("/{investor_id}")
def update_investor(
    investor_id: int,
    req: InvestorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst")),
):
    inv = db.query(Investor).filter(Investor.id == investor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investor not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(inv, field, value)
    db.commit()
    db.refresh(inv)
    return inv


@router.delete("/{investor_id}", status_code=204)
def delete_investor(
    investor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    inv = db.query(Investor).filter(Investor.id == investor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investor not found")
    db.delete(inv)
    db.commit()
