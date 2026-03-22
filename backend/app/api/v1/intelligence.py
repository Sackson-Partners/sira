"""
AI Intelligence API - SIRA AI endpoints
Provides AI-powered analytics, chat, and predictions.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.ai_engine import ai_engine

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    history: Optional[List[Dict[str, str]]] = None


class ETARequest(BaseModel):
    origin: str
    destination: str
    departure_time: str
    vessel_speed: Optional[float] = None
    weather_conditions: Optional[str] = None


class RiskAnalysisRequest(BaseModel):
    shipment_id: Optional[int] = None
    shipment_data: Optional[Dict[str, Any]] = None


class DemurrageRequest(BaseModel):
    vessel_data: Dict[str, Any]
    port_data: Dict[str, Any]


@router.get("/status")
async def ai_status(current_user=Depends(get_current_user)):
    """Check AI engine status and available providers."""
    from app.core.config import settings

    return {
        "configured": ai_engine.is_configured,
        "providers": {
            "anthropic": bool(settings.ANTHROPIC_API_KEY),
            "openai": bool(settings.OPENAI_API_KEY),
        },
        "model": settings.AI_MODEL,
    }


@router.post("/chat")
async def ai_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Chat with SIRA AI for natural language queries about operations."""
    response = await ai_engine.chat(
        message=request.message,
        context=request.context,
        history=request.history,
    )
    return {"response": response}


@router.post("/predict-eta")
async def predict_eta(
    request: ETARequest,
    current_user=Depends(get_current_user),
):
    """AI-powered ETA prediction for a voyage."""
    result = await ai_engine.predict_eta(
        origin=request.origin,
        destination=request.destination,
        departure_time=request.departure_time,
        vessel_speed=request.vessel_speed,
        weather_conditions=request.weather_conditions,
    )
    return result


@router.post("/analyze-risk")
async def analyze_risk(
    request: RiskAnalysisRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Analyze shipment risk using AI."""
    shipment_data = request.shipment_data
    if request.shipment_id and not shipment_data:
        from app.models.shipment import Shipment

        shipment = db.query(Shipment).filter(Shipment.id == request.shipment_id).first()
        if not shipment:
            raise HTTPException(status_code=404, detail="Shipment not found")
        shipment_data = {
            "id": shipment.id,
            "reference": shipment.reference_number,
            "status": shipment.status,
            "origin": shipment.origin_port,
            "destination": shipment.destination_port,
            "cargo_type": shipment.cargo_type,
            "cargo_volume": shipment.cargo_volume_mt,
        }

    if not shipment_data:
        raise HTTPException(status_code=400, detail="Provide shipment_id or shipment_data")

    result = await ai_engine.analyze_shipment_risk(shipment_data)
    return result


@router.post("/demurrage-risk")
async def demurrage_risk(
    request: DemurrageRequest,
    current_user=Depends(get_current_user),
):
    """Analyze demurrage risk for a vessel at a port."""
    result = await ai_engine.analyze_demurrage_risk(
        vessel_data=request.vessel_data,
        port_data=request.port_data,
    )
    return result
