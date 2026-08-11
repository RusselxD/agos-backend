import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class CitizenSubscription(Base):
    """F4/F6 — anonymous, location-scoped Web Push subscription for a citizen.

    Deliberately separate from ``push_subscriptions`` (which has a NOT NULL
    responder FK). No PII, no responder link. Fire-and-forget: citizens get no
    per-device delivery rows or acknowledgements.
    """

    __tablename__ = "citizen_subscriptions"
    __table_args__ = (
        UniqueConstraint("location_id", "endpoint", name="uq_citizen_subscription_location_endpoint"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location_id = Column(
        Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    endpoint = Column(Text, nullable=False)
    p256dh = Column(Text, nullable=False)
    auth = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.timezone("UTC", func.now()), nullable=False
    )

    location = relationship("Location")
