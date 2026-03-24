from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.event import Event, EventType
from ...models.user import User

router = APIRouter()


class EventCreate(BaseModel):
    title: str
    event_type: EventType = EventType.other
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    location: Optional[str] = None
    virtual_link: Optional[str] = None
    is_virtual: bool = False
    project_id: Optional[int] = None
    max_attendees: Optional[int] = None
    is_public: bool = False
    notes: Optional[str] = None


class EventUpdate(EventCreate):
    title: Optional[str] = None
    start_date: Optional[datetime] = None


class RSVPRequest(BaseModel):
    status: str = "confirmed"  # confirmed/declined/maybe


@router.get("/")
def list_events(
    skip: int = 0,
    limit: int = Query(50, le=200),
    event_type: Optional[EventType] = None,
    project_id: Optional[int] = None,
    upcoming: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Event)
    if event_type:
        q = q.filter(Event.event_type == event_type)
    if project_id:
        q = q.filter(Event.project_id == project_id)
    if upcoming:
        q = q.filter(Event.start_date >= datetime.utcnow())
    total = q.count()
    items = q.order_by(Event.start_date.asc()).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


@router.post("/", status_code=201)
def create_event(
    req: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = Event(**req.model_dump(), organizer_id=current_user.id)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/{event_id}")
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/{event_id}")
def update_event(
    event_id: int,
    req: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.organizer_id != current_user.id and current_user.role not in ("admin", "analyst"):
        raise HTTPException(status_code=403, detail="Not authorized to edit this event")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.organizer_id != current_user.id and current_user.role not in ("admin",):
        raise HTTPException(status_code=403, detail="Not authorized")
    db.delete(event)
    db.commit()


@router.post("/{event_id}/rsvp")
def rsvp(
    event_id: int,
    req: RSVPRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    attendees = list(event.attendees or [])
    existing = next((a for a in attendees if a.get("user_id") == current_user.id), None)
    if existing:
        existing["status"] = req.status
    else:
        attendees.append({
            "user_id": current_user.id,
            "name": current_user.full_name,
            "status": req.status,
        })
    event.attendees = attendees
    db.commit()
    return {"message": f"RSVP recorded: {req.status}"}
