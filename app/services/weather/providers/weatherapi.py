"""WeatherAPI.com provider (F2).

No-credit-card alternative to OpenWeatherMap (~15-min refresh). Maps WeatherAPI
condition codes to WMO so downstream display + scoring stay unchanged.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

from .base import WeatherReading, WeatherFetchError, WeatherRateLimitedError

logger = logging.getLogger(__name__)

CURRENT_URL = "https://api.weatherapi.com/v1/current.json"
TIMEOUT = httpx.Timeout(20.0, connect=10.0)

# WeatherAPI condition code -> WMO code (nearest equivalent).
_WEATHERAPI_TO_WMO = {
    1000: 0,   # Sunny/Clear
    1003: 2,   # Partly cloudy
    1006: 3,   # Cloudy
    1009: 3,   # Overcast
    1030: 45,  # Mist
    1135: 45,  # Fog
    1147: 48,  # Freezing fog
    1063: 61, 1150: 51, 1153: 53, 1180: 61, 1183: 61, 1186: 63, 1189: 63,
    1192: 65, 1195: 65, 1240: 80, 1243: 81, 1246: 82,
    1066: 71, 1210: 71, 1213: 71, 1216: 73, 1219: 73, 1222: 75, 1225: 75,
    1273: 95, 1276: 95, 1279: 95, 1282: 96,
}


def weatherapi_code_to_wmo(code: int) -> int:
    wmo = _WEATHERAPI_TO_WMO.get(code)
    if wmo is None:
        logger.warning("Unmapped WeatherAPI code %s; defaulting to overcast (WMO 3)", code)
        return 3
    return wmo


class WeatherApiProvider:
    name = "weatherapi"

    async def fetch(self, lat: float, lon: float) -> WeatherReading:
        if not settings.WEATHERAPI_API_KEY:
            raise WeatherFetchError("WEATHERAPI_API_KEY is not configured")

        params = {"key": settings.WEATHERAPI_API_KEY, "q": f"{lat},{lon}", "aqi": "no"}

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                response = await client.get(CURRENT_URL, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise WeatherRateLimitedError("WeatherAPI rate limited") from e
                raise WeatherFetchError(f"WeatherAPI returned {e.response.status_code}") from e
            except httpx.HTTPError as e:
                raise WeatherFetchError(f"WeatherAPI request failed: {type(e).__name__}") from e

        current = response.json().get("current", {})
        condition_code = int((current.get("condition") or {}).get("code", 1000))

        return WeatherReading(
            precipitation_mm=float(current.get("precip_mm", 0.0)),
            weather_code=weatherapi_code_to_wmo(condition_code),
            temperature_2m=float(current.get("temp_c", 0.0)),
            relative_humidity_2m=float(current.get("humidity", 0.0)),
            wind_speed_10m=float(current.get("wind_kph", 0.0)),
            wind_direction_10m=float(current.get("wind_degree", 0.0)),
            cloud_cover=float(current.get("cloud", 0.0)),
        )
