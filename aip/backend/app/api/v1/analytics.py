from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta

from ...core.database import get_db
from ...core.security import get_current_user
from ...models.project import Project, ProjectStatus, ProjectType
from ...models.investor import Investor, InvestorStatus
from ...models.pipeline import PipelineDeal, DealStage
from ...models.ic import ICSession, ICDecision
from ...models.user import User

router = APIRouter()


@router.get("/dashboard")
def dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Main dashboard KPIs and summary statistics."""
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)

    # Projects
    total_projects = db.query(Project).count()
    active_projects = db.query(Project).filter(Project.status == ProjectStatus.active).count()
    projects_this_month = db.query(Project).filter(Project.created_at >= thirty_days_ago).count()

    # Pipeline
    pipeline_deals = db.query(PipelineDeal).all()
    total_pipeline_value = sum(d.deal_size or 0 for d in pipeline_deals if d.stage not in (DealStage.closed_lost,))
    closed_won = db.query(PipelineDeal).filter(PipelineDeal.stage == DealStage.closed_won).count()
    closed_lost = db.query(PipelineDeal).filter(PipelineDeal.stage == DealStage.closed_lost).count()

    # Investors
    total_investors = db.query(Investor).count()
    active_investors = db.query(Investor).filter(Investor.status == InvestorStatus.active).count()

    # IC
    pending_ic = db.query(ICSession).filter(ICSession.decision == ICDecision.pending).count()
    approved_ic = db.query(ICSession).filter(ICSession.decision == ICDecision.approved).count()

    # Total committed
    total_committed = sum(
        d.deal_size or 0 for d in pipeline_deals if d.stage == DealStage.closed_won
    )

    return {
        "projects": {
            "total": total_projects,
            "active": active_projects,
            "new_this_month": projects_this_month,
            "by_status": {s.value: db.query(Project).filter(Project.status == s).count() for s in ProjectStatus},
        },
        "pipeline": {
            "total_deals": len(pipeline_deals),
            "total_value": total_pipeline_value,
            "closed_won": closed_won,
            "closed_lost": closed_lost,
            "win_rate": round(closed_won / (closed_won + closed_lost) * 100, 1) if (closed_won + closed_lost) > 0 else 0,
        },
        "investors": {
            "total": total_investors,
            "active": active_investors,
        },
        "ic": {
            "pending": pending_ic,
            "approved": approved_ic,
        },
        "financials": {
            "total_committed_usd": total_committed,
            "total_pipeline_value_usd": total_pipeline_value,
        },
    }


@router.get("/projects/trends")
def project_trends(
    days: int = Query(90, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=days)
    projects = db.query(Project).filter(Project.created_at >= since).all()
    by_type = {t.value: 0 for t in ProjectType}
    for p in projects:
        by_type[p.project_type.value] += 1
    by_sector: dict = {}
    for p in projects:
        sector = p.sector or "Unknown"
        by_sector[sector] = by_sector.get(sector, 0) + 1
    by_country: dict = {}
    for p in projects:
        country = p.country or "Unknown"
        by_country[country] = by_country.get(country, 0) + 1
    return {
        "period_days": days,
        "total": len(projects),
        "by_type": by_type,
        "by_sector": by_sector,
        "by_country": by_country,
    }


@router.get("/pipeline/funnel")
def pipeline_funnel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    funnel = []
    for stage in DealStage:
        deals = db.query(PipelineDeal).filter(PipelineDeal.stage == stage).all()
        funnel.append({
            "stage": stage.value,
            "count": len(deals),
            "total_value": sum(d.deal_size or 0 for d in deals),
            "avg_probability": sum(d.probability for d in deals) / len(deals) if deals else 0,
        })
    return funnel


@router.get("/investors/breakdown")
def investor_breakdown(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    investors = db.query(Investor).all()
    by_type: dict = {}
    by_country: dict = {}
    total_aum = 0.0
    for inv in investors:
        t = inv.investor_type.value
        by_type[t] = by_type.get(t, 0) + 1
        c = inv.country or "Unknown"
        by_country[c] = by_country.get(c, 0) + 1
        if inv.aum:
            total_aum += inv.aum
    return {
        "total": len(investors),
        "by_type": by_type,
        "by_country": by_country,
        "total_aum": total_aum,
    }
