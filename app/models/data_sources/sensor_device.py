from sqlalchemy import Column, ForeignKey, String, Integer, JSON
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship
from ..base import Base
from pydantic import BaseModel


class SensorConfig(BaseModel):
    installation_height: int
    warning_threshold: int
    critical_threshold: int


class SensorConfigType(TypeDecorator):
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, _):
        if isinstance(value, SensorConfig):
            return value.model_dump()
        return value

    def process_result_value(self, value, _):
        if value is not None:
            return SensorConfig(**value)
        return value


class SensorDevice(Base):
    __tablename__ = "sensor_devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, unique=True)
    device_name = Column(String(100), nullable=False)
    sensor_config = Column(SensorConfigType, nullable=False)

    location = relationship("Location", back_populates="sensor_device")
    sensor_readings = relationship("SensorReading", back_populates="sensor_device", cascade="all, delete-orphan")