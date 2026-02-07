import uuid
from sqlalchemy import Column, Table, String, UUID, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..base import Base

responder_groups = Table(
    'responder_groups',
    Base.metadata,
    Column('responder_id',  UUID(as_uuid=True), ForeignKey('responders.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True)
)

class Responders(Base):
    __tablename__ = "responders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), unique=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    status = Column(Enum('pending', 'approved', name='responder_status'), nullable=False, default='pending')
    id_photo_path = Column(String(255), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.now()))
    approved_at = Column(DateTime(timezone=True), nullable=True)

    admin_user = relationship("AdminUser", back_populates="responders_approved")
    groups = relationship("Group", secondary=responder_groups, back_populates="responders")