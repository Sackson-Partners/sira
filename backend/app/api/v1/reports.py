"""
Report Generation Routes
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone, timedelta

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.alert import Alert
from app.models.case import Case
from app.models.user import User
from app.services.pdf_service import PDFReportService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/alerts/summary")
async def get_alerts_summary_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "supervisor", "admin"]))
):
    """Generate alert summary report"""
    # Default to last 7 days
    if not end_date:
        end_dt = datetime.now(timezone.utc)
    else:
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

    if not start_date:
        start_dt = end_dt - timedelta(days=7)
    else:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))

    # Query alerts in date range
    alerts = db.query(Alert).filter(
        Alert.created_at >= start_dt,
        Alert.created_at <= end_dt
    ).all()

    # Calculate stats
    stats = {
        "total": len(alerts),
        "critical": len([a for a in alerts if a.severity == "Critical"]),
        "high": len([a for a in alerts if a.severity == "High"]),
        "medium": len([a for a in alerts if a.severity == "Medium"]),
        "low": len([a for a in alerts if a.severity == "Low"]),
        "resolved": len([a for a in alerts if a.status == "closed"]),
        "sla_breached": len([a for a in alerts if a.sla_breached]),
    }

    alerts_data = [
        {
            "id": a.id,
            "severity": a.severity,
            "domain": a.domain,
            "status": a.status,
            "sla_breached": a.sla_breached,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]

    if format == "pdf":
        pdf_service = PDFReportService()
        pdf_bytes = pdf_service.generate_alert_summary_report(
            start_date=start_dt,
            end_date=end_dt,
            alerts=alerts_data,
            stats=stats
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=alert_summary_{start_dt.strftime('%Y%m%d')}_{end_dt.strftime('%Y%m%d')}.pdf"
            }
        )

    return {
        "period": {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat()
        },
        "stats": stats,
        "alerts": alerts_data
    }


@router.get("/dashboard")
async def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard overview data"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Alert stats
    total_alerts = db.query(Alert).count()
    open_alerts = db.query(Alert).filter(Alert.status == "open").count()
    critical_alerts = db.query(Alert).filter(
        Alert.severity == "Critical",
        Alert.status != "closed"
    ).count()
    alerts_today = db.query(Alert).filter(Alert.created_at >= today_start).count()
    alerts_week = db.query(Alert).filter(Alert.created_at >= week_start).count()

    # Case stats
    total_cases = db.query(Case).count()
    open_cases = db.query(Case).filter(Case.status != "closed").count()
    cases_today = db.query(Case).filter(Case.created_at >= today_start).count()

    # SLA stats
    sla_breached = db.query(Alert).filter(Alert.sla_breached == True).count()  # noqa: E712
    sla_at_risk = db.query(Alert).filter(
        Alert.status.in_(["open", "acknowledged"]),
        Alert.sla_breached == False  # noqa: E712
    ).count()

    # Recent alerts
    recent_alerts = db.query(Alert).order_by(
        Alert.created_at.desc()
    ).limit(5).all()

    return {
        "alerts": {
            "total": total_alerts,
            "open": open_alerts,
            "critical": critical_alerts,
            "today": alerts_today,
            "this_week": alerts_week
        },
        "cases": {
            "total": total_cases,
            "open": open_cases,
            "today": cases_today
        },
        "sla": {
            "breached": sla_breached,
            "at_risk": sla_at_risk
        },
        "recent_alerts": [
            {
                "id": a.id,
                "severity": a.severity,
                "description": a.description[:100] if a.description else None,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in recent_alerts
        ],
        "generated_at": now.isoformat()
    }


@router.get("/activity")
async def get_activity_report(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["supervisor", "admin"]))
):
    """Get activity report for specified number of days"""
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    # Alerts per day
    alerts = db.query(Alert).filter(Alert.created_at >= start_date).all()

    # Group by day
    alerts_by_day = {}
    for alert in alerts:
        day = alert.created_at.strftime("%Y-%m-%d")
        if day not in alerts_by_day:
            alerts_by_day[day] = {"total": 0, "critical": 0, "high": 0, "resolved": 0}
        alerts_by_day[day]["total"] += 1
        if alert.severity == "Critical":
            alerts_by_day[day]["critical"] += 1
        elif alert.severity == "High":
            alerts_by_day[day]["high"] += 1
        if alert.status == "closed":
            alerts_by_day[day]["resolved"] += 1

    # Cases per day
    cases = db.query(Case).filter(Case.created_at >= start_date).all()
    cases_by_day = {}
    for case in cases:
        day = case.created_at.strftime("%Y-%m-%d")
        if day not in cases_by_day:
            cases_by_day[day] = 0
        cases_by_day[day] += 1

    return {
        "period": {
            "start": start_date.isoformat(),
            "end": now.isoformat(),
            "days": days
        },
        "alerts_by_day": alerts_by_day,
        "cases_by_day": cases_by_day,
        "summary": {
            "total_alerts": len(alerts),
            "total_cases": len(cases),
            "avg_alerts_per_day": len(alerts) / days if days > 0 else 0
        }
    }
