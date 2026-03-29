"""
Health Check Endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone
import time
import logging

from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

_START_TIME = time.time()


@router.get("")
@router.get("/")
async def health_check(db: Session = Depends(get_db)):
    """Public health check endpoint."""
    db_status = "healthy"
    db_latency_ms = 0
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - start) * 1000, 2)
    except Exception as e:
        db_status = "unhealthy"
        logger.warning(f"DB health check failed: {e}")

    uptime = int(time.time() - _START_TIME)

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
        "environment": "debug" if settings.DEBUG else "production",
        "uptime_seconds": uptime,
        "checks": {
            "database": {
                "status": db_status,
                "latency_ms": db_latency_ms,
            }
        },
    }


@router.get("/ready")
async def readiness_probe(db: Session = Depends(get_db)):
    """Readiness probe — returns 200 if ready to serve traffic."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Not ready")


@router.get("/live")
async def liveness_probe():
    """Liveness probe — returns 200 if process is alive."""
    return {"status": "alive"}
