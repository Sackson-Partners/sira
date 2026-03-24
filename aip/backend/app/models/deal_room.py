from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base


class DealRoom(Base):
    __tablename__ = "deal_rooms"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    participants = Column(JSON, default=list)  # list of user_ids
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    messages = relationship("DealRoomMessage", back_populates="deal_room", cascade="all, delete-orphan")


class DealRoomMessage(Base):
    __tablename__ = "deal_room_messages"

    id = Column(Integer, primary_key=True, index=True)
    deal_room_id = Column(Integer, ForeignKey("deal_rooms.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text")  # text/file/system
    file_path = Column(String(1000), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    deal_room = relationship("DealRoom", back_populates="messages")
