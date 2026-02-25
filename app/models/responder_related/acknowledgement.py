import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..base import Base


class Acknowledgement(Base):
    __tablename__ = "acknowledgements"
    __table_args__ = (UniqueConstraint("responder_id", "notification_id", name="uq_acknowledgement_responder_notification"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(Integer, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False)
    responder_id = Column(UUID(as_uuid=True), ForeignKey("responders.id", ondelete="CASCADE"), nullable=False)
    message = Column(String, nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), server_default=func.timezone("UTC", func.now()), nullable=False)

    notification = relationship("Notification", back_populates="acknowledgements")
    responder = relationship("Responder", back_populates="acknowledgements")