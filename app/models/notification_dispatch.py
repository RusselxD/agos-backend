from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base
from .notification_template import NotificationType


class NotificationDispatch(Base):
    __tablename__ = "notification_dispatches"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("notification_templates.id", ondelete="SET NULL"), nullable=True)
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.timezone("UTC", func.now()), nullable=False)

    template = relationship("NotificationTemplate", back_populates="dispatches")
    deliveries = relationship("NotificationDelivery", back_populates="dispatch", cascade="all, delete-orphan")
