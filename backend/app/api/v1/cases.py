"""
Case Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.case import Case
from app.models.alert import Alert
from app.models.evidence import Evidence
from app.models.user import User
from app.schemas.case import CaseCreate, CaseUpdate, CaseResponse, CaseClose
from app.services.notification_service import NotificationService
from app.services.pdf_service import PDFReportService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def generate_case_number(db: Session) -> str:
    """Generate a unique case number with retry on collision."""
    from sqlalchemy import text
    year = datetime.now(timezone.utc).year
    # Use SELECT ... FOR UPDATE on a locked count to prevent race conditions on
    # Postgres; on SQLite it falls back to a plain count (tests only).
    for attempt in range(10):
        count = db.query(Case).filter(
            Case.case_number.like(f"CASE-{year}-%")
        ).with_for_update().count()
        candidate = f"CASE-{year}-{count + 1:04d}"
        # Check uniqueness explicitly before returning
        if not db.query(Case).filter(Case.case_number == candidate).first():
            return candidate
    # Fallback: use timestamp suffix to guarantee uniqueness
    ts = int(datetime.now(timezone.utc).timestamp())
    return f"CASE-{year}-{ts}"


@router.get("/", response_model=List[CaseResponse])
async def list_cases(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List cases with optional filtering"""
    query = db.query(Case)

    if status:
        query = query.filter(Case.status == status)
    if priority:
        query = query.filter(Case.priority == priority)
    if category:
        query = query.filter(Case.category == category)

    cases = query.order_by(Case.created_at.desc()).offset(skip).limit(limit).all()
    return cases


@router.get("/stats")
async def get_case_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get case statistics"""
    total = db.query(Case).count()
    open_cases = db.query(Case).filter(Case.status == "open").count()
    investigating = db.query(Case).filter(Case.status == "investigating").count()
    closed = db.query(Case).filter(Case.status == "closed").count()

    return {
        "total": total,
        "open": open_cases,
        "investigating": investigating,
        "closed": closed,
        "by_priority": {
            "critical": db.query(Case).filter(Case.priority == "critical").count(),
            "high": db.query(Case).filter(Case.priority == "high").count(),
            "medium": db.query(Case).filter(Case.priority == "medium").count(),
            "low": db.query(Case).filter(Case.priority == "low").count(),
        }
    }


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get case by ID"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    return case


@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "supervisor", "admin"]))
):
    """Create a new case"""
    case = Case(
        case_number=generate_case_number(db),
        title=case_data.title,
        overview=case_data.overview,
        priority=case_data.priority,
        category=case_data.category,
        created_by=current_user.id
    )

    db.add(case)
    db.commit()
    db.refresh(case)

    # Link alerts if provided
    if case_data.alert_ids:
        for alert_id in case_data.alert_ids:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                alert.case_id = case.id
        db.commit()

    logger.info(f"Case created: {case.case_number} by {current_user.username}")

    # Send notification
    notification_service = NotificationService(db)
    await notification_service.notify_case_update(
        {
            "id": case.id,
            "case_number": case.case_number,
            "title": case.title,
            "status": case.status,
            "priority": case.priority
        },
        update_type="created"
    )

    return case


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: int,
    case_data: CaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "supervisor", "admin"]))
):
    """Update a case"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    update_data = case_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(case, field, value)

    db.commit()
    db.refresh(case)

    logger.info(f"Case updated: {case.case_number} by {current_user.username}")

    # Send notification
    notification_service = NotificationService(db)
    await notification_service.notify_case_update(
        {
            "id": case.id,
            "case_number": case.case_number,
            "title": case.title,
            "status": case.status,
            "priority": case.priority
        },
        update_type="updated"
    )

    return case


@router.post("/{case_id}/close")
async def close_case(
    case_id: int,
    close_data: CaseClose,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "supervisor", "admin"]))
):
    """Close a case"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    case.status = "closed"
    case.closure_code = close_data.closure_code
    case.closed_at = datetime.now(timezone.utc)

    if close_data.final_costs is not None:
        case.costs = close_data.final_costs

    db.commit()

    logger.info(f"Case closed: {case.case_number} by {current_user.username}")

    # Send notification
    notification_service = NotificationService(db)
    await notification_service.notify_case_update(
        {
            "id": case.id,
            "case_number": case.case_number,
            "title": case.title,
            "status": case.status,
            "closure_code": case.closure_code
        },
        update_type="closed"
    )

    return {"message": "Case closed successfully", "case_number": case.case_number}


@router.get("/{case_id}/export")
async def export_case(
    case_id: int,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "supervisor", "admin"]))
):
    """Export case as compliance pack (JSON or PDF)"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Get related data
    alerts = db.query(Alert).filter(Alert.case_id == case_id).all()
    evidences = db.query(Evidence).filter(Evidence.case_id == case_id).all()

    case_data = {
        "id": case.id,
        "case_number": case.case_number,
        "title": case.title,
        "overview": case.overview,
        "status": case.status,
        "priority": case.priority,
        "costs": case.costs,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "closed_at": case.closed_at.isoformat() if case.closed_at else None,
    }

    alerts_data = [
        {
            "id": a.id,
            "severity": a.severity,
            "domain": a.domain,
            "description": a.description,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]

    evidences_data = [
        {
            "id": e.id,
            "evidence_type": e.evidence_type,
            "original_filename": e.original_filename,
            "verification_status": e.verification_status,
            "file_hash": e.file_hash,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in evidences
    ]

    if format == "pdf":
        pdf_service = PDFReportService()
        pdf_bytes = pdf_service.generate_case_report(
            case_data=case_data,
            alerts=alerts_data,
            evidences=evidences_data
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={case.case_number}_compliance_report.pdf"
            }
        )

    # Default: JSON export
    logger.info(f"Case exported: {case.case_number} by {current_user.username}")
    return {
        "case": case_data,
        "alerts": alerts_data,
        "alerts_count": len(alerts),
        "evidences": evidences_data,
        "evidences_count": len(evidences),
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "format": "JSON"
    }
