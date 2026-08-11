"""Weather fetch orchestration (F2).

Provider selection is delegated to ``providers.get_provider(settings.WEATHER_PROVIDER)``;
this module only loops over coordinates and normalizes provider readings into
``WeatherCreate`` rows. Error types are re-exported for backward compatibility.
"""

import logging

from app.core.config import settings
from app.schemas import WeatherCreate, LocationCoordinate

from .providers import get_provider
from .providers.base import (  # re-exported for existing imports
    WeatherFetchError,
    WeatherRateLimitedError,
)

logger = logging.getLogger(__name__)

__all__ = [
    "fetch_weather_for_coordinates",
    "WeatherFetchError",
    "WeatherRateLimitedError",
]


async def fetch_weather_for_coordinates(
    coordinates: list[LocationCoordinate],
) -> list[WeatherCreate]:
    """Fetch current weather for each coordinate via the configured provider.

    Skips locations that fail; raises ``WeatherRateLimitedError`` if every
    location was rate-limited, or ``WeatherFetchError`` if all failed.
    """
    if not coordinates:
        raise RuntimeError("No location coordinates provided")

    provider = get_provider(settings.WEATHER_PROVIDER)
    weather_conditions: list[WeatherCreate] = []
    rate_limited_location_ids: set[int] = set()

    for coord in coordinates:
        try:
            reading = await provider.fetch(coord.latitude, coord.longitude)
        except WeatherRateLimitedError:
            rate_limited_location_ids.add(coord.id)
            logger.warning(
                "%s rate-limited weather fetch for location_id=%s",
                provider.name,
                coord.id,
            )
            continue
        except WeatherFetchError as e:
            logger.warning(
                "Skipping weather fetch for location_id=%s via %s: %s",
                coord.id,
                provider.name,
                e,
            )
            continue

        weather_conditions.append(
            WeatherCreate(
                location_id=coord.id,
                precipitation_mm=reading.precipitation_mm,
                weather_code=reading.weather_code,
                temperature_2m=reading.temperature_2m,
                relative_humidity_2m=reading.relative_humidity_2m,
                wind_speed_10m=reading.wind_speed_10m,
                wind_direction_10m=reading.wind_direction_10m,
                cloud_cover=reading.cloud_cover,
            )
        )

    if not weather_conditions:
        if rate_limited_location_ids and len(rate_limited_location_ids) == len(coordinates):
            raise WeatherRateLimitedError("Weather API rate limited all locations")
        raise WeatherFetchError("Weather fetch failed for all locations")

    return weather_conditions
