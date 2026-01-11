from pydantic import BaseModel
from datetime import datetime

class WeatherCreate(BaseModel):
    location_id: int
    precipitation_mm: float
    weather_code: int

class WeatherConditionResponse(BaseModel):
    precipitation_mm: float
    weather_code: int
    timestamp: datetime
    condition: str
    description: str