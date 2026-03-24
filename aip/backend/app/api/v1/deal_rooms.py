from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.deal_room import DealRoom, DealRoomMessage
from ...models.user import User

router = APIRouter()


class DealRoomCreate(BaseModel):
    project_id: int
    name: str
    description: Optional[str] = None
    participants: Optional[List[int]] = []


class DealRoomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    participants: Optional[List[int]] = None
    is_active: Optional[bool] = None


class MessageCreate(BaseModel):
    content: str
    message_type: str = "text"


@router.get("/")
def list_deal_rooms(
    skip: int = 0,
    limit: int = Query(50, le=200),
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(DealRoom)
    if project_id:
        q = q.filter(DealRoom.project_id == project_id)
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return {"total": total, "items": items}


@router.post("/", status_code=201)
def create_deal_room(
    req: DealRoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst")),
):
    dr = DealRoom(**req.model_dump(), created_by_id=current_user.id)
    db.add(dr)
    db.commit()
    db.refresh(dr)
    return dr


@router.get("/{room_id}")
def get_deal_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dr = db.query(DealRoom).filter(DealRoom.id == room_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Deal Room not found")
    return dr


@router.put("/{room_id}")
def update_deal_room(
    room_id: int,
    req: DealRoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst")),
):
    dr = db.query(DealRoom).filter(DealRoom.id == room_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Deal Room not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(dr, field, value)
    db.commit()
    db.refresh(dr)
    return dr


@router.delete("/{room_id}", status_code=204)
def delete_deal_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    dr = db.query(DealRoom).filter(DealRoom.id == room_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Deal Room not found")
    db.delete(dr)
    db.commit()


@router.get("/{room_id}/messages")
def get_messages(
    room_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dr = db.query(DealRoom).filter(DealRoom.id == room_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Deal Room not found")
    messages = (
        db.query(DealRoomMessage)
        .filter(DealRoomMessage.deal_room_id == room_id)
        .order_by(DealRoomMessage.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return messages


@router.post("/{room_id}/messages", status_code=201)
def send_message(
    room_id: int,
    req: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dr = db.query(DealRoom).filter(DealRoom.id == room_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Deal Room not found")
    msg = DealRoomMessage(
        deal_room_id=room_id,
        sender_id=current_user.id,
        content=req.content,
        message_type=req.message_type,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
