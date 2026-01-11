from sqlalchemy import Column, ForeignKey, String, Integer
from sqlalchemy.orm import relationship

from ..base import Base

class CameraDevice(Base):
    __tablename__ = "camera_devices"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, unique=True)
    device_name = Column(String(100), nullable=False)

    location = relationship("Location", back_populates="camera_device")
    model_readings = relationship("ModelReadings", back_populates="camera_device", cascade="all, delete-orphan")