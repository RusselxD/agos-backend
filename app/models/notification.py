import enum

from sqlalchemy import Column, DateTime, Enum, Integer, String, UUID, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class NotificationType(enum.Enum):
    WARNING = "warning"
    CRITICAL = "critical"
    BLOCKAGE = "blockage"
    ANNOUNCEMENT = "announcement"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.timezone("UTC", func.now()), nullable=False)

    creator = relationship("AdminUser", back_populates="notifications")
    acknowledgements = relationship("Acknowledgement", back_populates="notification", cascade="all, delete-orphan")
    deliveries = relationship("NotificationDelivery", back_populates="notification", cascade="all, delete-orphan")