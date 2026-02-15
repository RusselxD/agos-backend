from sqlalchemy import Column, Integer, String, Float, Numeric, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..base import Base


class DailySummary(Base):
    __tablename__ = "daily_summaries"
    __table_args__ = (
        UniqueConstraint('location_id', 'summary_date', name='uq_location_date'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    summary_date = Column(Date, nullable=False, index=True)

    # Risk Score (calculated from raw data at end of day)
    min_risk_score = Column(Integer, nullable=True)
    max_risk_score = Column(Integer, nullable=True)
    min_risk_timestamp = Column(DateTime(timezone=True), nullable=True)
    max_risk_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Model Readings (Debris/Blockage)
    min_debris_count = Column(Integer, nullable=True)
    max_debris_count = Column(Integer, nullable=True)
    min_debris_timestamp = Column(DateTime(timezone=True), nullable=True)
    max_debris_timestamp = Column(DateTime(timezone=True), nullable=True)
    least_severe_blockage = Column(String, nullable=True)  # clear/partial/blocked
    most_severe_blockage = Column(String, nullable=True)

    # Sensor Readings (Water Level)
    min_water_level_cm = Column(Numeric(5, 2), nullable=True)
    max_water_level_cm = Column(Numeric(5, 2), nullable=True)
    min_water_timestamp = Column(DateTime(timezone=True), nullable=True)
    max_water_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Weather
    min_precipitation_mm = Column(Float, nullable=True)
    max_precipitation_mm = Column(Float, nullable=True)
    min_precip_timestamp = Column(DateTime(timezone=True), nullable=True)
    max_precip_timestamp = Column(DateTime(timezone=True), nullable=True)
    most_severe_weather_code = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.now()), nullable=False)

    location = relationship("Location", back_populates="daily_summaries")
