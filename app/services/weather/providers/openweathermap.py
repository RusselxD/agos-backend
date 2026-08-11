"""OpenWeatherMap One Call 3.0 provider (F2).

Chosen for its high refresh frequency (~10-min current + minute nowcast). Maps
OWM condition ids to WMO ``weather_code`` so the display layer + WS payload stay
byte-compatible with the Open-Meteo behavior.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

from .base import WeatherReading, WeatherFetchError, WeatherRateLimitedError

logger = logging.getLogger(__name__)

ONE_CALL_URL = "https://api.openweathermap.org/data/3.0/onecall"
TIMEOUT = httpx.Timeout(20.0, connect=10.0)


def owm_id_to_wmo(owm_id: int) -> int:
    """Map an OpenWeatherMap condition id to the nearest WMO code."""
    if owm_id == 800:
        return 0  # clear sky
    if owm_id == 801:
        return 1  # few clouds -> mainly clear
    if owm_id in (802, 803, 804):
        return 3  # clouds -> overcast
    if 200 <= owm_id < 300:
        return 95  # thunderstorm
    if 300 <= owm_id < 400:
        return 53  # drizzle
    if 500 <= owm_id < 600:
        # 520-531 are shower rain
        return 81 if owm_id >= 520 else 63  # rain / rain showers
    if 600 <= owm_id < 700:
        return 73  # snow
    if 700 <= owm_id < 800:
        return 45  # atmosphere (fog/mist/haze)
    logger.warning("Unmapped OWM condition id %s; defaulting to overcast (WMO 3)", owm_id)
    return 3


class OpenWeatherMapProvider:
    name = "openweathermap"

    async def fetch(self, lat: float, lon: float) -> WeatherReading:
        if not settings.OPENWEATHERMAP_API_KEY:
            raise WeatherFetchError("OPENWEATHERMAP_API_KEY is not configured")

        params = {
            "lat": lat,
            "lon": lon,
            "appid": settings.OPENWEATHERMAP_API_KEY,
            "units": "metric",
            "exclude": "minutely,hourly,daily,alerts",
        }

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                response = await client.get(ONE_CALL_URL, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise WeatherRateLimitedError("OpenWeatherMap rate limited") from e
                raise WeatherFetchError(
                    f"OpenWeatherMap returned {e.response.status_code}"
                ) from e
            except httpx.HTTPError as e:
                raise WeatherFetchError(f"OpenWeatherMap request failed: {type(e).__name__}") from e

        current = response.json().get("current", {})
        weather = (current.get("weather") or [{}])[0]
        # Precipitation reported under rain["1h"] (mm over the last hour).
        precipitation_mm = float((current.get("rain") or {}).get("1h", 0.0))
        wind_speed_ms = float(current.get("wind_speed", 0.0))

        return WeatherReading(
            precipitation_mm=precipitation_mm,
            weather_code=owm_id_to_wmo(int(weather.get("id", 800))),
            temperature_2m=float(current.get("temp", 0.0)),
            relative_humidity_2m=float(current.get("humidity", 0.0)),
            wind_speed_10m=round(wind_speed_ms * 3.6, 2),  # m/s -> km/h (Open-Meteo scale)
            wind_direction_10m=float(current.get("wind_deg", 0.0)),
            cloud_cover=float(current.get("clouds", 0.0)),
        )
