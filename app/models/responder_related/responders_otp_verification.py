from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.sql import func
from ..base import Base


class RespondersOTPVerification(Base):
    __tablename__ = "responders_otp_verification"

    phone_number = Column(String(20), primary_key=True, index=True)
    otp_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.now()), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Valid for 10 minutes
    attempt_count = Column(Integer, default=0, nullable=False)