from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from ...core.database import get_db
from ...core.security import get_current_user
from ...models.ein import EIN
from ...models.project import Project
from ...models.user import User
from ...services.ai_engine import generate_ein

router = APIRouter()


class EINCreate(BaseModel):
    project_id: int
    jobs_created_direct: Optional[int] = None
    jobs_created_indirect: Optional[int] = None
    gdp_contribution: Optional[float] = None
    gdp_unit: str = "USD M"
    tax_revenue_generated: Optional[float] = None
    local_procurement_percent: Optional[float] = None
    communities_impacted: Optional[int] = None
    population_benefited: Optional[int] = None
    social_impact_areas: Optional[List[str]] = []
    sdg_alignment: Optional[List[int]] = []
    esg_score: Optional[float] = None
    co2_reduction_tonnes: Optional[float] = None
    renewable_energy_mw: Optional[float] = None
    water_saved_m3: Optional[float] = None
    waste_reduced_tonnes: Optional[float] = None
    environmental_certifications: Optional[List[str]] = []
    leverage_ratio: Optional[float] = None
    crowded_in_capital: Optional[float] = None
    blended_finance_structure: Optional[str] = None
    impact_thesis: Optional[str] = None
    impact_measurement_framework: Optional[str] = None
    impact_risks: Optional[List[dict]] = []
    impact_kpis: Optional[List[dict]] = []


class EINUpdate(EINCreate):
    project_id: Optional[int] = None


@router.get("/project/{project_id}")
def get_ein(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ein = db.query(EIN).filter(EIN.project_id == project_id).first()
    if not ein:
        raise HTTPException(status_code=404, detail="EIN not found for this project")
    return ein


@router.post("/", status_code=201)
def create_ein(
    req: EINCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == req.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    existing = db.query(EIN).filter(EIN.project_id == req.project_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="EIN already exists. Use PUT to update.")
    ein = EIN(**req.model_dump())
    db.add(ein)
    db.commit()
    db.refresh(ein)
    return ein


@router.put("/project/{project_id}")
def update_ein(
    project_id: int,
    req: EINUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ein = db.query(EIN).filter(EIN.project_id == project_id).first()
    if not ein:
        raise HTTPException(status_code=404, detail="EIN not found")
    for field, value in req.model_dump(exclude_unset=True, exclude={"project_id"}).items():
        setattr(ein, field, value)
    db.commit()
    db.refresh(ein)
    return ein


@router.post("/project/{project_id}/generate-ai")
async def generate_ein_with_ai(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Use AI to auto-generate Economic Impact Note."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    ai_result = await generate_ein(project)

    ein = db.query(EIN).filter(EIN.project_id == project_id).first()
    if not ein:
        ein = EIN(project_id=project_id)
        db.add(ein)

    for field, value in ai_result.items():
        if hasattr(ein, field):
            setattr(ein, field, value)

    ein.ai_generated = {k: True for k in ai_result.keys()}
    db.commit()
    db.refresh(ein)
    return ein
