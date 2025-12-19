from sqlalchemy import Column,  DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.sql import func

from .base import Base

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensor_devices.id"), nullable=False)
    water_level_cm = Column(Numeric(5, 2), nullable=False)
    raw_distance_cm = Column(Numeric(5, 2), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False) # when the reading was taken
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False) # when the record was created in the DB