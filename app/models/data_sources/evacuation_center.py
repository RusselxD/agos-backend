import enum

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..base import Base


class EvacuationCenterStatus(str, enum.Enum):
    OPEN = "open"
    FULL = "full"
    CLOSED = "closed"


class EvacuationCenter(Base):
    """F5 — an evacuation center residents can be routed to. Mirrors the simple
    ResponderGroup CRUD pattern; per-location scoped."""

    __tablename__ = "evacuation_centers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    location_id = Column(
        Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(120), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    capacity = Column(Integer, nullable=True)
    contact = Column(String, nullable=True)
    status = Column(
        Enum(
            EvacuationCenterStatus,
            name="evacuationcenterstatus",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=EvacuationCenterStatus.OPEN,
        server_default=EvacuationCenterStatus.OPEN.value,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.timezone("UTC", func.now()), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.timezone("UTC", func.now()),
        onupdate=func.timezone("UTC", func.now()),
        nullable=False,
    )

    location = relationship("Location")
