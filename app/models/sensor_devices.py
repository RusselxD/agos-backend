from sqlalchemy import Column, String,  DateTime, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base

class SensorDevice(Base):
    __tablename__ = "sensor_devices"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    device_name = Column(String(100), nullable=False)
    location = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sensor_readings = relationship("SensorReading", back_populates="sensor_device", cascade="all, delete-orphan")