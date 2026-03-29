"""
AIS API - MarineTraffic vessel tracking endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.marinetraffic_service import marinetraffic_service

router = APIRouter()


@router.get("/status")
async def ais_status(current_user=Depends(get_current_user)):
    """Check MarineTraffic AIS integration status."""
    return {
        "configured": marinetraffic_service.is_configured,
        "provider": "MarineTraffic",
    }


@router.get("/vessel/{mmsi}")
async def get_vessel_position(
    mmsi: str, current_user=Depends(get_current_user)
):
    """Get current position for a vessel by MMSI."""
    if not marinetraffic_service.is_configured:
        raise HTTPException(
            status_code=503, detail="MarineTraffic integration not configured"
        )
    position = await marinetraffic_service.get_vessel_position(mmsi)
    if not position:
        raise HTTPException(status_code=404, detail=f"No position found for MMSI {mmsi}")
    return {"position": position}


@router.get("/fleet")
async def get_fleet_positions(current_user=Depends(get_current_user)):
    """Get positions for all tracked vessels."""
    if not marinetraffic_service.is_configured:
        raise HTTPException(
            status_code=503, detail="MarineTraffic integration not configured"
        )
    positions = await marinetraffic_service.get_fleet_positions()
    return {"positions": positions, "count": len(positions)}


@router.get("/vessel/{imo}/details")
async def get_vessel_details(
    imo: str, current_user=Depends(get_current_user)
):
    """Get detailed vessel information by IMO number."""
    if not marinetraffic_service.is_configured:
        raise HTTPException(
            status_code=503, detail="MarineTraffic integration not configured"
        )
    details = await marinetraffic_service.get_vessel_details(imo)
    if not details:
        raise HTTPException(status_code=404, detail=f"No details found for IMO {imo}")
    return {"vessel": details}


@router.post("/sync-positions")
async def sync_vessel_positions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Sync vessel positions from MarineTraffic into the database."""
    if not marinetraffic_service.is_configured:
        raise HTTPException(
            status_code=503, detail="MarineTraffic integration not configured"
        )
    count = await marinetraffic_service.sync_vessel_positions(db)
    return {"updated": count, "message": f"Updated {count} vessel positions"}
