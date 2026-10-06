"""Immutable monitoring data plus the analysis generated from that snapshot."""
import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, UUID
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base


class ReadingReport(Base):
    __tablename__ = "reading_reports"
    __table_args__ = (UniqueConstraint("created_by", "request_id", name="uq_reading_report_request"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    snapshot = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    analysis_text = Column(Text, nullable=False, default="")
    analysis_error = Column(Text, nullable=True)
    analysis_started_at = Column(DateTime(timezone=True), nullable=True)
    analysis_completed_at = Column(DateTime(timezone=True), nullable=True)
    analysis_model = Column(String(100), nullable=True)
    prompt_version = Column(String(20), nullable=False, default="1")
    template_version = Column(String(20), nullable=False, default="1")
    pdf_content = Column(LargeBinary, nullable=True)
    pdf_created_at = Column(DateTime(timezone=True), nullable=True)
