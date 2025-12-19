from sqlalchemy import Column, String,  DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.sql import func

from .base import Base

class SensorDevice(Base):
    __tablename__ = "sensor_devices"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    device_name = Column(String(100), nullable=False)
    location = Column(String(100), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=True) # for connection status (online/offline)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
