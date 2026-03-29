"""
Notification Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.notification import NotificationPreference
from app.models.user import User
from app.schemas.notification import NotificationResponse, NotificationPreferenceUpdate, NotificationPreferenceResponse
from app.services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List notifications for current user"""
    notification_service = NotificationService(db)
    notifications = notification_service.get_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=skip
    )
    return notifications


@router.get("/unread-count")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get count of unread notifications"""
    notification_service = NotificationService(db)
    count = notification_service.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a notification as read"""
    notification_service = NotificationService(db)
    success = notification_service.mark_notification_read(
        notification_id=notification_id,
        user_id=current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    return {"message": "Notification marked as read"}


@router.post("/read-all")
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all notifications as read"""
    notification_service = NotificationService(db)
    count = notification_service.mark_all_read(current_user.id)
    return {"message": f"Marked {count} notifications as read"}


@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's notification preferences"""
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()

    if not prefs:
        # Create default preferences
        prefs = NotificationPreference(user_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    return prefs


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    pref_data: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update notification preferences"""
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()

    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id)
        db.add(prefs)

    update_data = pref_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prefs, field, value)

    db.commit()
    db.refresh(prefs)

    logger.info(f"Notification preferences updated for user {current_user.username}")
    return prefs
