from sqlalchemy import Column, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from ..base import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    __table_args__ = (UniqueConstraint("responder_id", "endpoint", name="uq_push_subscription_responder_endpoint"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    responder_id = Column(UUID(as_uuid=True), ForeignKey("responders.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(Text, nullable=False)
    p256dh = Column(Text, nullable=False)
    auth = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.timezone("UTC", func.now()), nullable=False)

    responder = relationship("Responder", back_populates="push_subscriptions")
    deliveries = relationship("NotificationDelivery", back_populates="subscription", cascade="all, delete-orphan")