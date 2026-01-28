from pydantic import BaseModel
from datetime import datetime

class WeatherCreate(BaseModel):
    location_id: int
    precipitation_mm: float
    weather_code: int
    temperature_2m: float
    relative_humidity_2m: float
    wind_speed_10m: float
    wind_direction_10m: float
    cloud_cover: float

class WeatherConditionResponse(BaseModel):
    precipitation_mm: float
    weather_code: int
    timestamp: datetime
    condition: str
    description: str

class WeatherComprehensiveResponse(BaseModel):
    # Timestamp
    timestamp: datetime
    
    # Raw values (pass-through for display/charts)
    precipitation_mm: float
    weather_code: int
    temperature_c: float
    humidity_percent: float
    wind_speed_kmh: float
    wind_direction_degrees: float
    cloud_cover_percent: float
    
    # Derived/dynamic values
    condition: str                    # from weather_code
    precipitation_description: str    # from precipitation_mm
    temperature_description: str      # from temperature_c
    humidity_level: str               # from humidity_percent
    wind_category: str                # from wind_speed_kmh
    wind_direction_label: str         # from wind_direction_degrees
    cloudiness: str                   # from cloud_cover_percent
    comfort_level: str                # from temperature + humidity
    storm_risk_level: str             # from weather_code + precipitation + wind