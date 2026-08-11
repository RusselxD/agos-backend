import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class EvacuationEventKind(str, enum.Enum):
    EVACUATE = "evacuate"
    ALL_CLEAR = "all_clear"


class EvacuationEvent(Base):
    """F4 — audit row for one admin-authorized public evacuation (or all-clear).

    Records who authorized it, the basis (risk score + fusion snapshot), and the
    message that was blasted. One row per authorization."""

    __tablename__ = "evacuation_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location_id = Column(
        Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dispatch_id = Column(
        Integer, ForeignKey("notification_dispatches.id", ondelete="SET NULL"), nullable=True
    )
    kind = Column(
        Enum(
            EvacuationEventKind,
            name="evacuationeventkind",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    authorized_by = Column(
        UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=False
    )
    basis_risk_score = Column(Integer, nullable=True)
    basis_snapshot = Column(JSONB, nullable=True)
    message = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.timezone("UTC", func.now()), nullable=False
    )

    location = relationship("Location")
    authorizer = relationship("AdminUser")
