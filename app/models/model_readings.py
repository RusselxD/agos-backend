from sqlalchemy import Column, String, DateTime, Integer, Float
from .base import Base
from sqlalchemy.sql import func

class ModelReadings(Base):
    __tablename__ = "model_readings"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False)  # "clear", "partial", "blocked"
    confidence = Column(Float, nullable=False)
    image_path = Column(String)  # Path to the stored image
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)