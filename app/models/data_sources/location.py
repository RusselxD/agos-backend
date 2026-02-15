from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship
from ..base import Base


class Location(Base):
    __tablename__ = 'locations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    weather_conditions = relationship("Weather", back_populates="location", cascade="all, delete-orphan")
    sensor_device = relationship("SensorDevice", back_populates="location", uselist=False, cascade="all, delete-orphan")
    camera_device = relationship("CameraDevice", back_populates="location", uselist=False, cascade="all, delete-orphan")
    daily_summaries = relationship("DailySummary", back_populates="location", cascade="all, delete-orphan")