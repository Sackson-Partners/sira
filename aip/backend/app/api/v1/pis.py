from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from ...core.database import get_db
from ...core.security import get_current_user
from ...models.pis import PIS
from ...models.project import Project
from ...models.user import User
from ...services.ai_engine import generate_pis

router = APIRouter()


class PISCreate(BaseModel):
    project_id: int
    executive_summary: Optional[str] = None
    investment_thesis: Optional[str] = None
    key_highlights: Optional[List[str]] = []
    market_size: Optional[float] = None
    market_size_unit: str = "USD M"
    market_growth_rate: Optional[float] = None
    market_description: Optional[str] = None
    business_model: Optional[str] = None
    revenue_model: Optional[str] = None
    competitive_advantages: Optional[List[str]] = []
    key_risks: Optional[List[str]] = []
    risk_mitigants: Optional[List[str]] = []
    revenue_current: Optional[float] = None
    revenue_projected: Optional[float] = None
    ebitda_current: Optional[float] = None
    ebitda_projected: Optional[float] = None
    debt_equity_ratio: Optional[float] = None
    deal_structure: Optional[str] = None
    use_of_proceeds: Optional[str] = None
    exit_strategy: Optional[str] = None
    exit_options: Optional[List[str]] = []
    management_team: Optional[List[dict]] = []


class PISUpdate(PISCreate):
    project_id: Optional[int] = None


@router.get("/project/{project_id}")
def get_pis_by_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pis = db.query(PIS).filter(PIS.project_id == project_id).first()
    if not pis:
        raise HTTPException(status_code=404, detail="PIS not found for this project")
    return pis


@router.post("/", status_code=201)
def create_pis(
    req: PISCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == req.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    existing = db.query(PIS).filter(PIS.project_id == req.project_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="PIS already exists. Use PUT to update.")
    pis = PIS(**req.model_dump())
    db.add(pis)
    db.commit()
    db.refresh(pis)
    return pis


@router.put("/project/{project_id}")
def update_pis(
    project_id: int,
    req: PISUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pis = db.query(PIS).filter(PIS.project_id == project_id).first()
    if not pis:
        raise HTTPException(status_code=404, detail="PIS not found")
    for field, value in req.model_dump(exclude_unset=True, exclude={"project_id"}).items():
        setattr(pis, field, value)
    db.commit()
    db.refresh(pis)
    return pis


@router.post("/project/{project_id}/generate-ai")
async def generate_pis_with_ai(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Use AI to auto-generate PIS content based on project data."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    ai_result = await generate_pis(project)

    pis = db.query(PIS).filter(PIS.project_id == project_id).first()
    if not pis:
        pis = PIS(project_id=project_id)
        db.add(pis)

    for field, value in ai_result.items():
        if hasattr(pis, field):
            setattr(pis, field, value)

    pis.ai_generated = {k: True for k in ai_result.keys()}
    db.commit()
    db.refresh(pis)
    return pis
