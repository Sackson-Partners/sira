from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import os, shutil, uuid

from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...core.config import settings
from ...models.data_room import DataRoom, DataRoomDocument, DataRoomAccess, AccessLevel
from ...models.user import User

router = APIRouter()


class DataRoomCreate(BaseModel):
    project_id: int
    name: str
    description: Optional[str] = None
    watermark_enabled: bool = True
    nda_required: bool = False


class DataRoomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    watermark_enabled: Optional[bool] = None
    nda_required: Optional[bool] = None


class GrantAccessRequest(BaseModel):
    investor_id: Optional[int] = None
    user_id: Optional[int] = None
    access_level: AccessLevel = AccessLevel.view
    expires_at: Optional[datetime] = None


@router.get("/")
def list_data_rooms(
    skip: int = 0,
    limit: int = Query(50, le=200),
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(DataRoom)
    if project_id:
        q = q.filter(DataRoom.project_id == project_id)
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return {"total": total, "items": items}


@router.post("/", status_code=201)
def create_data_room(
    req: DataRoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst")),
):
    dr = DataRoom(**req.model_dump(), created_by_id=current_user.id)
    db.add(dr)
    db.commit()
    db.refresh(dr)
    return dr


@router.get("/{room_id}")
def get_data_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dr = db.query(DataRoom).filter(DataRoom.id == room_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Data Room not found")
    return dr


@router.put("/{room_id}")
def update_data_room(
    room_id: int,
    req: DataRoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst")),
):
    dr = db.query(DataRoom).filter(DataRoom.id == room_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Data Room not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(dr, field, value)
    db.commit()
    db.refresh(dr)
    return dr


@router.delete("/{room_id}", status_code=204)
def delete_data_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    dr = db.query(DataRoom).filter(DataRoom.id == room_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Data Room not found")
    db.delete(dr)
    db.commit()


@router.post("/{room_id}/documents", status_code=201)
async def upload_document(
    room_id: int,
    file: UploadFile = File(...),
    folder_path: str = Form("/"),
    description: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst")),
):
    dr = db.query(DataRoom).filter(DataRoom.id == room_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Data Room not found")

    upload_dir = os.path.join(settings.UPLOAD_DIR, "data_rooms", str(room_id), folder_path.lstrip("/"))
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    stored_name = f"{uuid.uuid4()}{ext}"
    storage_path = os.path.join(upload_dir, stored_name)

    content = await file.read()
    file_size = len(content)
    with open(storage_path, "wb") as f:
        f.write(content)

    doc = DataRoomDocument(
        data_room_id=room_id,
        filename=stored_name,
        original_filename=file.filename,
        folder_path=folder_path,
        file_type=file.content_type,
        file_size=file_size,
        storage_path=storage_path,
        description=description,
        uploaded_by_id=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{room_id}/documents")
def list_documents(
    room_id: int,
    folder_path: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(DataRoomDocument).filter(DataRoomDocument.data_room_id == room_id)
    if folder_path:
        q = q.filter(DataRoomDocument.folder_path == folder_path)
    return q.all()


@router.post("/{room_id}/access")
def grant_access(
    room_id: int,
    req: GrantAccessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst")),
):
    dr = db.query(DataRoom).filter(DataRoom.id == room_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Data Room not found")
    access = DataRoomAccess(
        data_room_id=room_id,
        **req.model_dump(),
        granted_by_id=current_user.id,
    )
    db.add(access)
    db.commit()
    db.refresh(access)
    return access


@router.get("/{room_id}/access")
def list_access(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst")),
):
    return db.query(DataRoomAccess).filter(DataRoomAccess.data_room_id == room_id).all()


@router.delete("/{room_id}/access/{access_id}", status_code=204)
def revoke_access(
    room_id: int,
    access_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst")),
):
    access = db.query(DataRoomAccess).filter(
        DataRoomAccess.id == access_id,
        DataRoomAccess.data_room_id == room_id
    ).first()
    if not access:
        raise HTTPException(status_code=404, detail="Access record not found")
    db.delete(access)
    db.commit()
