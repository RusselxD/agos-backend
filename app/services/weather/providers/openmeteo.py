"""Open-Meteo provider (F2) — the original hardcoded behavior, now behind the
``WeatherProvider`` interface so it remains available as a free, no-key fallback.
"""

from __future__ import annotations

import logging

import httpx

from .base import WeatherProvider, WeatherReading, WeatherFetchError, WeatherRateLimitedError

logger = logging.getLogger(__name__)

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast?"
    "latitude={lat}&longitude={lon}&"
    "current=precipitation,weather_code,temperature_2m,relative_humidity_2m,"
    "wind_speed_10m,wind_direction_10m,cloud_cover"
)
TIMEOUT = httpx.Timeout(20.0, connect=10.0)
MAX_ATTEMPTS = 2


class OpenMeteoProvider:
    name = "openmeteo"

    async def fetch(self, lat: float, lon: float) -> WeatherReading:
        api_url = OPEN_METEO_URL.format(lat=lat, lon=lon)
        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    response = await client.get(api_url)
                    response.raise_for_status()
                    current = response.json()["current"]
                    return WeatherReading(
                        precipitation_mm=current["precipitation"],
                        weather_code=current["weather_code"],
                        temperature_2m=current["temperature_2m"],
                        relative_humidity_2m=current["relative_humidity_2m"],
                        wind_speed_10m=current["wind_speed_10m"],
                        wind_direction_10m=current["wind_direction_10m"],
                        cloud_cover=current["cloud_cover"],
                    )
                except httpx.TimeoutException as e:
                    last_error = e
                    logger.warning("Open-Meteo timeout (attempt %s/%s)", attempt, MAX_ATTEMPTS)
                except httpx.HTTPStatusError as e:
                    last_error = e
                    if e.response.status_code == 429:
                        raise WeatherRateLimitedError("Open-Meteo rate limited") from e
                    if e.response.status_code < 500:
                        break
                except httpx.HTTPError as e:
                    last_error = e
                    break

        raise WeatherFetchError(
            f"Open-Meteo fetch failed: {type(last_error).__name__ if last_error else 'unknown'}"
        )


_provider: WeatherProvider = OpenMeteoProvider()
