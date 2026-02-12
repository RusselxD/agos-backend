from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..base import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    sensor_device_id = Column(Integer, ForeignKey("sensor_devices.id", ondelete="CASCADE"), nullable=False)
    water_level_cm = Column(Numeric(5, 2), nullable=False)
    raw_distance_cm = Column(Numeric(5, 2), nullable=False)

    # Signal strength metrics
    signal_strength = Column(Integer, nullable=False)  # RSSI in dBm (e.g., -40 to -80)

    timestamp = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.now()), nullable=False, index=True) # when the reading was taken
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.now()), nullable=False) # when the record was created in the DB

    sensor_device = relationship("SensorDevice", back_populates="sensor_readings")