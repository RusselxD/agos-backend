from .reading_summary_response import ReadingSummaryResponse
from app.schemas.weather import WeatherConditionResponse

class WeatherWebSocketResponse(ReadingSummaryResponse):
    weather_condition: WeatherConditionResponse | None