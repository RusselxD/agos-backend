from sqlalchemy import Column, Float, DateTime, ForeignKey, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..base import Base


class Weather(Base):
    __tablename__ = "weather"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    precipitation_mm = Column(Float, nullable=False)
    weather_code = Column(Integer, nullable=False) # WMO weather code
    temperature_2m = Column(Float, nullable=False)
    relative_humidity_2m = Column(Float, nullable=False)
    wind_speed_10m = Column(Float, nullable=False)
    wind_direction_10m = Column(Float, nullable=False)
    cloud_cover = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.now()), nullable=False)
    
    location = relationship("Location", back_populates="weather_conditions")