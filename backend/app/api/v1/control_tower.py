"""
Control Tower Routes - Unified operational visibility and dashboard
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.shipment import Shipment, ShipmentException
from app.models.vessel import Vessel
from app.models.asset import Asset
from app.models.port import Port
from app.models.corridor import Corridor
from app.models.freight import DemurrageRecord
from app.models.user import User
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/overview")
async def get_control_tower_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive control tower overview - the main dashboard endpoint"""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Shipment stats
    active_shipments = db.query(Shipment).filter(
        Shipment.status.notin_(["completed", "cancelled"])
    ).all()
    total_active = len(active_shipments)
    high_risk = sum(1 for s in active_shipments if (s.demurrage_risk_score or 0) >= 70)
    total_demurrage_exposure = sum(s.demurrage_exposure_usd or 0 for s in active_shipments)

    # Vessel stats
    active_vessels = db.query(Vessel).filter(Vessel.status == "active").count()
    idle_vessels = db.query(Vessel).filter(Vessel.status == "idle").count()

    # Asset stats
    total_assets = db.query(Asset).count()
    assets_in_transit = db.query(Asset).filter(Asset.status == "in_transit").count()
    assets_available = db.query(Asset).filter(Asset.status == "available").count()
    assets_maintenance = db.query(Asset).filter(Asset.status == "maintenance").count()

    # Port stats
    ports = db.query(Port).filter(Port.status != "closed").all()
    congested_ports = sum(1 for p in ports if p.status == "congested")

    # Open exceptions
    open_exceptions = db.query(ShipmentException).filter(
        ShipmentException.status.in_(["open", "acknowledged"])
    ).count()
    critical_exceptions = db.query(ShipmentException).filter(
        ShipmentException.status.in_(["open", "acknowledged"]),
        ShipmentException.severity == "critical"
    ).count()

    # Corridor stats
    active_corridors = db.query(Corridor).filter(Corridor.status == "active").count()

    # Shipments by status
    status_counts = db.query(
        Shipment.status, func.count(Shipment.id)
    ).group_by(Shipment.status).all()

    # Shipments by mode
    mode_counts = db.query(
        Shipment.current_mode, func.count(Shipment.id)
    ).filter(Shipment.status.notin_(["completed", "cancelled"])).group_by(
        Shipment.current_mode
    ).all()

    # Recent exceptions
    recent_exceptions = db.query(ShipmentException).filter(
        ShipmentException.created_at >= week_ago
    ).order_by(ShipmentException.created_at.desc()).limit(10).all()

    return {
        "generated_at": now.isoformat(),
        "shipments": {
            "active": total_active,
            "high_risk": high_risk,
            "total_demurrage_exposure_usd": round(total_demurrage_exposure, 2),
            "by_status": {s: c for s, c in status_counts},
            "by_mode": {m or "unassigned": c for m, c in mode_counts},
        },
        "vessels": {
            "active": active_vessels,
            "idle": idle_vessels,
            "total": active_vessels + idle_vessels,
        },
        "fleet": {
            "total": total_assets,
            "in_transit": assets_in_transit,
            "available": assets_available,
            "maintenance": assets_maintenance,
        },
        "ports": {
            "total": len(ports),
            "congested": congested_ports,
            "operational": len(ports) - congested_ports,
        },
        "corridors": {
            "active": active_corridors,
        },
        "exceptions": {
            "open": open_exceptions,
            "critical": critical_exceptions,
            "recent": [{
                "id": e.id,
                "shipment_id": e.shipment_id,
                "type": e.exception_type,
                "severity": e.severity,
                "description": e.description,
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            } for e in recent_exceptions],
        },
    }


@router.get("/map-data")
async def get_map_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all geo-positioned entities for the control tower map view"""

    # Vessels with positions
    vessels = db.query(Vessel).filter(
        Vessel.current_lat.isnot(None),
        Vessel.current_lng.isnot(None)
    ).all()

    # Assets with positions
    assets = db.query(Asset).filter(
        Asset.current_lat.isnot(None),
        Asset.current_lng.isnot(None)
    ).all()

    # Ports
    ports = db.query(Port).all()

    # Corridors with waypoints
    corridors = db.query(Corridor).filter(Corridor.status == "active").all()

    return {
        "vessels": [{
            "id": v.id,
            "name": v.name,
            "type": v.vessel_type,
            "lat": v.current_lat,
            "lng": v.current_lng,
            "speed": v.current_speed,
            "heading": v.current_heading,
            "status": v.status,
            "destination": v.current_destination,
            "updated_at": v.position_updated_at.isoformat() if v.position_updated_at else None,
        } for v in vessels],
        "assets": [{
            "id": a.id,
            "code": a.asset_code,
            "name": a.name,
            "type": a.asset_type,
            "lat": a.current_lat,
            "lng": a.current_lng,
            "speed": a.current_speed,
            "status": a.status,
        } for a in assets],
        "ports": [{
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "lat": p.latitude,
            "lng": p.longitude,
            "status": p.status,
            "queue": p.current_queue,
        } for p in ports],
        "corridors": [{
            "id": c.id,
            "name": c.name,
            "code": c.code,
            "waypoints": c.waypoints,
            "status": c.status,
        } for c in corridors],
    }


@router.get("/kpis")
async def get_operational_kpis(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get operational KPIs for the specified period"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Completed shipments in period
    completed = db.query(Shipment).filter(
        Shipment.status == "completed",
        Shipment.updated_at >= cutoff
    ).all()

    # Demurrage KPIs
    demurrage_records = db.query(DemurrageRecord).filter(
        DemurrageRecord.created_at >= cutoff
    ).all()
    total_demurrage_cost = sum(d.demurrage_amount_usd or 0 for d in demurrage_records)
    total_demurrage_days = sum(d.demurrage_days or 0 for d in demurrage_records)

    # Asset utilization
    all_assets = db.query(Asset).all()
    avg_utilization = sum(a.utilization_pct or 0 for a in all_assets) / max(len(all_assets), 1)

    # ETA accuracy (for completed shipments with ETAs)
    eta_variances = []
    for s in completed:
        if s.eta_destination and s.arrived_destination:
            variance = abs((s.arrived_destination - s.eta_destination).total_seconds() / 3600)
            eta_variances.append(variance)

    return {
        "period_days": days,
        "shipments_completed": len(completed),
        "demurrage": {
            "total_cost_usd": round(total_demurrage_cost, 2),
            "total_days": round(total_demurrage_days, 1),
            "avg_cost_per_shipment": round(total_demurrage_cost / max(len(demurrage_records), 1), 2),
        },
        "fleet": {
            "avg_utilization_pct": round(avg_utilization, 1),
            "total_assets": len(all_assets),
        },
        "eta_accuracy": {
            "sample_size": len(eta_variances),
            "avg_variance_hours": round(sum(eta_variances) / max(len(eta_variances), 1), 1),
            "within_8_hours_pct": round(
                sum(1 for v in eta_variances if v <= 8) / max(len(eta_variances), 1) * 100, 1
            ) if eta_variances else 0,
        },
    }
