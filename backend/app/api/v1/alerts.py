"""
Alert Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.alert import Alert
from app.models.movement import Movement
from app.models.user import User
from app.schemas.alert import AlertCreate, AlertUpdate, AlertResponse, AlertAcknowledge, AlertResolve
from app.services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[AlertResponse])
async def list_alerts(
    domain: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    sla_breached: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List alerts with optional filtering"""
    query = db.query(Alert)

    if domain:
        query = query.filter(Alert.domain == domain)
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    if sla_breached is not None:
        query = query.filter(Alert.sla_breached == sla_breached)

    alerts = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()
    return alerts


@router.get("/stats")
async def get_alert_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get alert statistics"""
    total = db.query(Alert).count()
    open_alerts = db.query(Alert).filter(Alert.status == "open").count()
    critical = db.query(Alert).filter(Alert.severity == "Critical").count()
    high = db.query(Alert).filter(Alert.severity == "High").count()
    sla_breached = db.query(Alert).filter(Alert.sla_breached == True).count()  # noqa: E712

    return {
        "total": total,
        "open": open_alerts,
        "critical": critical,
        "high": high,
        "medium": db.query(Alert).filter(Alert.severity == "Medium").count(),
        "low": db.query(Alert).filter(Alert.severity == "Low").count(),
        "sla_breached": sla_breached
    }


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get alert by ID"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    return alert


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "supervisor", "admin"]))
):
    """Create a new alert manually"""
    if alert_data.movement_id:
        movement = db.query(Movement).filter(Movement.id == alert_data.movement_id).first()
        if not movement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movement not found"
            )

    alert = Alert(**alert_data.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)

    logger.info(f"Alert created manually: ID {alert.id} by {current_user.username}")

    # Send notification (non-blocking, errors are logged not raised)
    try:
        notification_service = NotificationService(db)
        await notification_service.notify_alert({
            "id": alert.id,
            "severity": alert.severity,
            "description": alert.description,
            "domain": alert.domain,
            "created_at": alert.created_at.isoformat() if alert.created_at else None
        })
    except Exception as e:
        logger.warning(f"Failed to send alert notification: {e}")

    return alert


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    alert_data: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    update_data = alert_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)

    db.commit()
    db.refresh(alert)

    logger.info(f"Alert updated: ID {alert_id} by {current_user.username}")
    return alert


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    ack_data: AlertAcknowledge = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Acknowledge an alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    if alert.status not in ["open"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert is not in open status"
        )

    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = current_user.id

    db.commit()

    logger.info(f"Alert acknowledged: ID {alert_id} by {current_user.username}")
    return {"message": "Alert acknowledged", "alert_id": alert_id}


@router.post("/{alert_id}/assign")
async def assign_alert(
    alert_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "supervisor", "admin"]))
):
    """Assign alert to a user"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    assignee = db.query(User).filter(User.id == user_id).first()
    if not assignee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    alert.status = "assigned"
    alert.assigned_to = user_id

    db.commit()

    logger.info(f"Alert assigned: ID {alert_id} to user {user_id} by {current_user.username}")

    # Notify assignee (non-blocking)
    try:
        notification_service = NotificationService(db)
        await notification_service.notify_alert(
            {
                "id": alert.id,
                "severity": alert.severity,
                "description": f"Alert assigned to you: {alert.description}",
                "domain": alert.domain,
            },
            target_user_ids=[user_id]
        )
    except Exception as e:
        logger.warning(f"Failed to send assignment notification: {e}")

    return {"message": "Alert assigned", "alert_id": alert_id, "assigned_to": user_id}


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    resolve_data: AlertResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resolve an alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    alert.status = "closed"
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by = current_user.id
    alert.resolution_notes = resolve_data.resolution_notes

    db.commit()

    logger.info(f"Alert resolved: ID {alert_id} by {current_user.username}")
    return {"message": "Alert resolved", "alert_id": alert_id}


@router.post("/{alert_id}/link-case")
async def link_alert_to_case(
    alert_id: int,
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "supervisor", "admin"]))
):
    """Link an alert to a case"""
    from app.models.case import Case

    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    alert.case_id = case_id
    db.commit()

    logger.info(f"Alert {alert_id} linked to case {case_id}")
    return {"message": "Alert linked to case", "alert_id": alert_id, "case_id": case_id}
