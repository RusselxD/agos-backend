from sqlalchemy import Column, ForeignKey, String, DateTime, Integer, Float
from ..base import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class ModelReadings(Base):
    __tablename__ = "model_readings"

    id = Column(Integer, primary_key=True)
    camera_device_id = Column(Integer, ForeignKey("camera_devices.id", ondelete="CASCADE"), nullable=False)
    
    # Image info
    image_path = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.now()), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.now()), nullable=False)
    
    # Blockage measurement
    blockage_percentage = Column(Float, nullable=False)  # 0-100
    blockage_status = Column(String, nullable=False)  # 'clear', 'partial', 'blocked'
    
    # Detection summary
    total_debris_count = Column(Integer, default=0)
    
    camera_device = relationship("CameraDevice", back_populates="model_readings")