from pydantic import BaseModel
from datetime import datetime

class WeatherBase(BaseModel):
    precipitation_mm: float

class WeatherCreate(WeatherBase):
    sensor_id: int
    weather_code: int

class WeatherConditionResponse(BaseModel):
    precipitation_mm: float
    weather_code: int
    timestamp: datetime
    condition: str
    description: str