from pydantic import BaseModel

class WeatherConditionResponse(BaseModel):
    precipitation: float
    weather_code: int