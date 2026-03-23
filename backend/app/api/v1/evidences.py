"""
Evidence Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
import hashlib
import json

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.evidence import Evidence
from app.models.case import Case
from app.models.user import User
from app.schemas.evidence import EvidenceCreate, EvidenceResponse, EvidenceVerify
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# MIME types that are images and should be preprocessed before storage / AI use.
_IMAGE_MIME_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/gif",
    "image/webp", "image/bmp", "image/tiff",
}


def _preprocess_image_content(content: bytes, filename: str) -> bytes:
    """
    Resize and compress image bytes so max(w, h) <= 1568px (Claude API safe limit).

    Returns the processed JPEG bytes, or the original bytes if the file is not
    a recognised image or preprocessing fails gracefully.
    """
    try:
        from services.ai.image_utils import encode_image_bytes_for_claude
        b64, _ = encode_image_bytes_for_claude(
            content,
            source_label=filename,
        )
        import base64
        return base64.b64decode(b64)
    except Exception as exc:
        logger.warning(
            "Image preprocessing skipped for '%s' — %s. "
            "Original bytes will be stored.",
            filename, exc,
        )
        return content


@router.get("/case/{case_id}", response_model=List[EvidenceResponse])
async def list_case_evidences(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all evidence for a case"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    evidences = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    return evidences


@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get evidence by ID"""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )
    return evidence


@router.post("/", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    evidence_data: EvidenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create evidence record (file reference)"""
    case = db.query(Case).filter(Case.id == evidence_data.case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Compute hash for integrity
    evidence_hash = hashlib.sha256(evidence_data.file_ref.encode()).hexdigest()

    evidence = Evidence(
        **evidence_data.model_dump(),
        file_hash=evidence_hash,
        uploaded_by=current_user.id
    )

    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    logger.info(f"Evidence created: ID {evidence.id} for case {evidence_data.case_id}")
    return evidence


@router.post("/upload/{case_id}", response_model=EvidenceResponse)
async def upload_evidence(
    case_id: int,
    file: UploadFile = File(...),
    evidence_type: str = "document",
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload evidence file"""
    from app.core.config import settings
    from pathlib import Path
    import os

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Check file size
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    # Preprocess image files: resize to <= 1568px and convert to JPEG so that
    # any subsequent Claude API call never hits the 2000px dimension error.
    is_image = (file.content_type or "").lower() in _IMAGE_MIME_TYPES
    if is_image:
        original_size = len(content)
        content = _preprocess_image_content(content, file.filename or "upload")
        logger.info(
            "Evidence image preprocessed: '%s' %d bytes -> %d bytes (case %d)",
            file.filename, original_size, len(content), case_id,
        )

    # Compute hash on the (possibly preprocessed) content
    file_hash = hashlib.sha256(content).hexdigest()

    # Save file
    upload_dir = os.path.join(settings.UPLOAD_DIR, f"case_{case_id}")
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename; normalise to .jpg for preprocessed images
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    original_name = file.filename or "upload"
    if is_image:
        stem = Path(original_name).stem
        safe_filename = f"{timestamp}_{stem}.jpg"
    else:
        safe_filename = f"{timestamp}_{original_name}"
    file_path = os.path.join(upload_dir, safe_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    # Create evidence record
    evidence = Evidence(
        case_id=case_id,
        evidence_type=evidence_type,
        file_ref=file_path,
        original_filename=file.filename,
        file_size=len(content),
        mime_type="image/jpeg" if is_image else file.content_type,
        file_hash=file_hash,
        notes=notes,
        uploaded_by=current_user.id,
        metadata=json.dumps({
            "uploader": current_user.username,
            "upload_time": datetime.now(timezone.utc).isoformat()
        })
    )

    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    logger.info(f"Evidence uploaded: {file.filename} for case {case_id}")
    return evidence


@router.post("/{evidence_id}/verify")
async def verify_evidence(
    evidence_id: int,
    verify_data: EvidenceVerify,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "supervisor", "admin"]))
):
    """Verify or reject evidence"""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )

    evidence.verification_status = verify_data.status
    evidence.verified_by = current_user.id
    evidence.verified_at = datetime.now(timezone.utc)

    if verify_data.notes:
        evidence.notes = (evidence.notes or "") + f"\n[Verification]: {verify_data.notes}"

    db.commit()

    logger.info(f"Evidence {evidence_id} {verify_data.status} by {current_user.username}")
    return {
        "message": f"Evidence {verify_data.status}",
        "evidence_id": evidence_id
    }


@router.delete("/{evidence_id}")
async def delete_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "supervisor", "admin"]))
):
    """Delete evidence"""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )

    db.delete(evidence)
    db.commit()

    logger.info(f"Evidence deleted: ID {evidence_id} by {current_user.username}")
    return {"message": "Evidence deleted successfully"}
