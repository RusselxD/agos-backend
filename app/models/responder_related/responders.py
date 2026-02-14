import uuid
from sqlalchemy import Column, Table, String, UUID, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from ..base import Base


class ResponderStatus(enum.Enum):
    PENDING = 'pending'
    ACTIVE = 'active'


responder_groups = Table(
    'responder_groups',
    Base.metadata,
    Column('responder_id', UUID(as_uuid=True), ForeignKey('responders.id', ondelete='CASCADE'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True)
)


class Responder(Base):
    __tablename__ = "responders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), unique=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    status = Column(Enum(ResponderStatus), nullable=False, default=ResponderStatus.PENDING)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.now()))
    created_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=False)

    admin_user = relationship("AdminUser", back_populates="responders_created")
    groups = relationship("Group", secondary=responder_groups, back_populates="responders", passive_deletes=True)
    otp_verification = relationship("RespondersOTPVerification", back_populates="responder", uselist=False)
