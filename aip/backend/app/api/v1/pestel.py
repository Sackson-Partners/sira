from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from ...core.database import get_db
from ...core.security import get_current_user
from ...models.pestel import PESTEL, ImpactLevel
from ...models.project import Project
from ...models.user import User
from ...services.ai_engine import generate_pestel

router = APIRouter()


class PESTELFactor(BaseModel):
    factor: str
    description: str
    impact: str = "medium"
    likelihood: str = "medium"
    mitigant: Optional[str] = None


class PESTELCreate(BaseModel):
    project_id: int
    political_factors: Optional[List[dict]] = []
    political_score: Optional[float] = None
    political_summary: Optional[str] = None
    economic_factors: Optional[List[dict]] = []
    economic_score: Optional[float] = None
    economic_summary: Optional[str] = None
    social_factors: Optional[List[dict]] = []
    social_score: Optional[float] = None
    social_summary: Optional[str] = None
    technological_factors: Optional[List[dict]] = []
    technological_score: Optional[float] = None
    technological_summary: Optional[str] = None
    environmental_factors: Optional[List[dict]] = []
    environmental_score: Optional[float] = None
    environmental_summary: Optional[str] = None
    legal_factors: Optional[List[dict]] = []
    legal_score: Optional[float] = None
    legal_summary: Optional[str] = None
    overall_score: Optional[float] = None
    overall_assessment: Optional[str] = None
    overall_impact: Optional[ImpactLevel] = None


class PESTELUpdate(PESTELCreate):
    project_id: Optional[int] = None


@router.get("/project/{project_id}")
def get_pestel(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = db.query(PESTEL).filter(PESTEL.project_id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="PESTEL analysis not found for this project")
    return p


@router.post("/", status_code=201)
def create_pestel(
    req: PESTELCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == req.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    existing = db.query(PESTEL).filter(PESTEL.project_id == req.project_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="PESTEL already exists. Use PUT to update.")
    pestel = PESTEL(**req.model_dump())
    db.add(pestel)
    db.commit()
    db.refresh(pestel)
    return pestel


@router.put("/project/{project_id}")
def update_pestel(
    project_id: int,
    req: PESTELUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pestel = db.query(PESTEL).filter(PESTEL.project_id == project_id).first()
    if not pestel:
        raise HTTPException(status_code=404, detail="PESTEL not found")
    for field, value in req.model_dump(exclude_unset=True, exclude={"project_id"}).items():
        setattr(pestel, field, value)
    db.commit()
    db.refresh(pestel)
    return pestel


@router.post("/project/{project_id}/generate-ai")
async def generate_pestel_with_ai(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Use AI to auto-generate PESTEL analysis."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    ai_result = await generate_pestel(project)

    pestel = db.query(PESTEL).filter(PESTEL.project_id == project_id).first()
    if not pestel:
        pestel = PESTEL(project_id=project_id)
        db.add(pestel)

    for field, value in ai_result.items():
        if hasattr(pestel, field):
            setattr(pestel, field, value)

    pestel.ai_generated = {k: True for k in ai_result.keys()}
    db.commit()
    db.refresh(pestel)
    return pestel
