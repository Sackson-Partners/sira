from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base
import enum


class AccessLevel(str, enum.Enum):
    view = "view"
    download = "download"
    manage = "manage"


class DataRoom(Base):
    __tablename__ = "data_rooms"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    watermark_enabled = Column(Boolean, default=True)
    nda_required = Column(Boolean, default=False)
    nda_document_path = Column(String(1000), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    documents = relationship("DataRoomDocument", back_populates="data_room", cascade="all, delete-orphan")
    access_list = relationship("DataRoomAccess", back_populates="data_room", cascade="all, delete-orphan")


class DataRoomDocument(Base):
    __tablename__ = "data_room_documents"

    id = Column(Integer, primary_key=True, index=True)
    data_room_id = Column(Integer, ForeignKey("data_rooms.id"), nullable=False)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    folder_path = Column(String(1000), default="/")
    file_type = Column(String(50), nullable=True)
    file_size = Column(Integer, nullable=True)
    storage_path = Column(String(1000), nullable=False)
    version = Column(Integer, default=1)
    description = Column(Text, nullable=True)
    is_visible = Column(Boolean, default=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    download_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    data_room = relationship("DataRoom", back_populates="documents")


class DataRoomAccess(Base):
    __tablename__ = "data_room_access"

    id = Column(Integer, primary_key=True, index=True)
    data_room_id = Column(Integer, ForeignKey("data_rooms.id"), nullable=False)
    investor_id = Column(Integer, ForeignKey("investors.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    access_level = Column(SAEnum(AccessLevel), default=AccessLevel.view)
    granted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    nda_signed = Column(Boolean, default=False)
    nda_signed_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    data_room = relationship("DataRoom", back_populates="access_list")
