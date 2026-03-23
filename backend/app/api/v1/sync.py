"""
Sync API — Offline-first batch sync endpoint
POST /api/v1/sync/batch
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.sync import BatchSyncRequest, BatchSyncResponse
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/batch", response_model=BatchSyncResponse)
def batch_sync(
    payload: BatchSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Core offline-first batch sync endpoint.

    Accepts a queue of events generated while the mobile client was offline.
    Handles deduplication, causal ordering, and conflict resolution.
    Returns per-event results plus any server-side updates since last sync.
    """
    if not payload.events:
        return BatchSyncResponse(
            processed=0,
            success_count=0,
            failed_count=0,
            results=[],
            server_updates=[],
        )

    # Resolve organization from user
    organization_id = getattr(current_user, "organization_id", None)
    if not organization_id:
        # Fall back: use a default org derived from user id (single-tenant compat)
        organization_id = 1

    logger.info(
        f"Batch sync: user={current_user.id}, device={payload.device_id}, "
        f"events={len(payload.events)}"
    )

    service = SyncService(db)
    try:
        result = service.process_batch(
            request=payload,
            user_id=current_user.id,
            organization_id=organization_id,
        )
    except Exception as exc:
        logger.error(f"Batch sync failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sync processing failed",
        )

    return result


@router.get("/status")
def sync_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return sync statistics for the current user."""
    from app.models.sync_log import SyncLog

    logs = (
        db.query(SyncLog)
        .filter(SyncLog.user_id == current_user.id)
        .order_by(SyncLog.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "user_id": current_user.id,
        "recent_syncs": [
            {
                "id": log.id,
                "device_id": log.device_id,
                "events_count": log.events_count,
                "success_count": log.success_count,
                "failed_count": log.failed_count,
                "status": log.status,
                "duration_ms": log.duration_ms,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }
