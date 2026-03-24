from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import os, shutil, uuid

from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...core.config import settings
from ...models.verification import Verification, VerificationType, VerificationStatus
from ...models.user import User

router = APIRouter()


class VerificationCreate(BaseModel):
    investor_id: Optional[int] = None
    user_id: Optional[int] = None
    verification_type: VerificationType
    external_ref: Optional[str] = None


class VerificationReview(BaseModel):
    status: VerificationStatus
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    expires_at: Optional[datetime] = None


@router.get("/")
def list_verifications(
    skip: int = 0,
    limit: int = Query(50, le=200),
    status: Optional[VerificationStatus] = None,
    verification_type: Optional[VerificationType] = None,
    investor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Verification)
    if status:
        q = q.filter(Verification.status == status)
    if verification_type:
        q = q.filter(Verification.verification_type == verification_type)
    if investor_id:
        q = q.filter(Verification.investor_id == investor_id)
    total = q.count()
    items = q.order_by(Verification.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


@router.post("/", status_code=201)
def create_verification(
    req: VerificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not req.investor_id and not req.user_id:
        raise HTTPException(status_code=400, detail="Either investor_id or user_id is required")
    v = Verification(**req.model_dump())
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@router.get("/{verification_id}")
def get_verification(
    verification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    v = db.query(Verification).filter(Verification.id == verification_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Verification not found")
    return v


@router.post("/{verification_id}/documents", status_code=201)
async def upload_verification_document(
    verification_id: int,
    file: UploadFile = File(...),
    doc_type: str = Form("identity"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    v = db.query(Verification).filter(Verification.id == verification_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Verification not found")

    upload_dir = os.path.join(settings.UPLOAD_DIR, "verifications", str(verification_id))
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    stored_name = f"{uuid.uuid4()}{ext}"
    storage_path = os.path.join(upload_dir, stored_name)

    with open(storage_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    docs = list(v.documents or [])
    docs.append({
        "name": file.filename,
        "stored_name": stored_name,
        "path": storage_path,
        "type": doc_type,
        "uploaded_at": datetime.utcnow().isoformat(),
    })
    v.documents = docs
    db.commit()
    return {"message": "Document uploaded", "stored_name": stored_name}


@router.post("/{verification_id}/review")
def review_verification(
    verification_id: int,
    req: VerificationReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst")),
):
    v = db.query(Verification).filter(Verification.id == verification_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Verification not found")
    v.status = req.status
    v.reviewer_id = current_user.id
    v.reviewed_at = datetime.utcnow()
    v.review_notes = req.review_notes
    v.rejection_reason = req.rejection_reason
    v.expires_at = req.expires_at
    if req.status == VerificationStatus.approved:
        v.is_active = True
    db.commit()
    db.refresh(v)
    return v
