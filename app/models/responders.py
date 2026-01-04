import uuid
from sqlalchemy import Column, String, UUID, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base

class Responders(Base):
    __tablename__ = "responders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(Enum('pending', 'approved', name='responder_status'), nullable=False, default='pending')
    id_photo_path = Column(String(255), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True)

    admin_user = relationship("AdminUser", back_populates="responders_approved")