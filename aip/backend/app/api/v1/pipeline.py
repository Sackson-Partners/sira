from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.pipeline import PipelineDeal, DealStage
from ...models.user import User

router = APIRouter()


class DealCreate(BaseModel):
    name: str
    stage: DealStage = DealStage.sourcing
    probability: float = 0.0
    deal_size: Optional[float] = None
    currency: str = "USD"
    expected_close_date: Optional[datetime] = None
    project_id: Optional[int] = None
    investor_id: Optional[int] = None
    description: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[datetime] = None
    tags: Optional[List[str]] = []
    custom_fields: Optional[dict] = {}


class DealUpdate(DealCreate):
    name: Optional[str] = None
    lost_reason: Optional[str] = None


class StageUpdate(BaseModel):
    stage: DealStage
    probability: Optional[float] = None
    lost_reason: Optional[str] = None


@router.get("/")
def list_deals(
    skip: int = 0,
    limit: int = Query(100, le=500),
    stage: Optional[DealStage] = None,
    assigned_to_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(PipelineDeal)
    if stage:
        q = q.filter(PipelineDeal.stage == stage)
    if assigned_to_id:
        q = q.filter(PipelineDeal.assigned_to_id == assigned_to_id)
    if search:
        q = q.filter(PipelineDeal.name.ilike(f"%{search}%"))
    total = q.count()
    items = q.order_by(PipelineDeal.created_at.desc()).offset(skip).limit(limit).all()

    # Kanban view: group by stage
    kanban = {}
    for s in DealStage:
        kanban[s.value] = [d for d in items if d.stage == s]

    return {"total": total, "items": items, "kanban": kanban}


@router.post("/", status_code=201)
def create_deal(
    req: DealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = PipelineDeal(**req.model_dump(), assigned_to_id=current_user.id)
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@router.get("/stats")
def pipeline_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    all_deals = db.query(PipelineDeal).all()
    by_stage = {s.value: {"count": 0, "total_value": 0.0} for s in DealStage}
    for d in all_deals:
        by_stage[d.stage.value]["count"] += 1
        if d.deal_size:
            by_stage[d.stage.value]["total_value"] += d.deal_size
    total_pipeline_value = sum(d.deal_size or 0 for d in all_deals if d.stage not in (DealStage.closed_won, DealStage.closed_lost))
    return {
        "total_deals": len(all_deals),
        "by_stage": by_stage,
        "total_pipeline_value": total_pipeline_value,
    }


@router.get("/{deal_id}")
def get_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(PipelineDeal).filter(PipelineDeal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.put("/{deal_id}")
def update_deal(
    deal_id: int,
    req: DealUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(PipelineDeal).filter(PipelineDeal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(deal, field, value)
    db.commit()
    db.refresh(deal)
    return deal


@router.patch("/{deal_id}/stage")
def move_stage(
    deal_id: int,
    req: StageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(PipelineDeal).filter(PipelineDeal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    deal.stage = req.stage
    deal.stage_changed_at = datetime.utcnow()
    if req.probability is not None:
        deal.probability = req.probability
    if req.lost_reason:
        deal.lost_reason = req.lost_reason
    db.commit()
    db.refresh(deal)
    return deal


@router.delete("/{deal_id}", status_code=204)
def delete_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst")),
):
    deal = db.query(PipelineDeal).filter(PipelineDeal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    db.delete(deal)
    db.commit()
