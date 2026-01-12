import uuid
from sqlalchemy import Column, Boolean, String, UUID, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base

class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    hashed_password = Column(String, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    force_password_change = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    deactivated_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True)
    deactivation_reason = Column(Text, nullable=True)

    admin_creator = relationship("AdminUser", remote_side=[id], foreign_keys=[created_by])
    admin_deactivator = relationship("AdminUser", remote_side=[id], foreign_keys=[deactivated_by])
    admin_audit_logs = relationship("AdminAuditLog", back_populates="admin_user", cascade="all, delete-orphan")
    responders_approved = relationship("Responders", back_populates="admin_user")