"""
Telemetry API - Flespi telematics integration endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.flespi_service import flespi_service

router = APIRouter()


@router.get("/status")
async def telemetry_status(current_user=Depends(get_current_user)):
    """Check Flespi integration status."""
    return {
        "configured": flespi_service.is_configured,
        "mqtt_host": flespi_service.rest_url if flespi_service.is_configured else None,
    }


@router.get("/devices")
async def list_flespi_devices(current_user=Depends(get_current_user)):
    """List all devices from Flespi platform."""
    if not flespi_service.is_configured:
        raise HTTPException(status_code=503, detail="Flespi integration not configured")
    devices = await flespi_service.get_devices()
    return {"devices": devices, "count": len(devices)}


@router.get("/devices/{device_id}/telemetry")
async def get_device_telemetry(
    device_id: int, current_user=Depends(get_current_user)
):
    """Get latest telemetry for a specific Flespi device."""
    if not flespi_service.is_configured:
        raise HTTPException(status_code=503, detail="Flespi integration not configured")
    telemetry = await flespi_service.get_device_telemetry(device_id)
    return {"telemetry": telemetry}


@router.get("/devices/{device_id}/messages")
async def get_device_messages(
    device_id: int,
    limit: int = 100,
    current_user=Depends(get_current_user),
):
    """Get recent messages from a Flespi device."""
    if not flespi_service.is_configured:
        raise HTTPException(status_code=503, detail="Flespi integration not configured")
    messages = await flespi_service.get_device_messages(device_id, limit)
    parsed = [flespi_service.parse_telemetry_message(m) for m in messages]
    return {"messages": parsed, "count": len(parsed)}


@router.post("/sync-devices")
async def sync_flespi_devices(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Sync Flespi devices into the local IoTDevice table."""
    if not flespi_service.is_configured:
        raise HTTPException(status_code=503, detail="Flespi integration not configured")
    count = await flespi_service.sync_devices_to_db(db)
    return {"synced": count, "message": f"Synced {count} new devices from Flespi"}
