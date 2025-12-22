from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UUID
from datetime import datetime, timezone
from .base import Base
from sqlalchemy.orm import relationship

class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(225), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)

    admin_user = relationship("AdminUser", back_populates="admin_audit_logs")