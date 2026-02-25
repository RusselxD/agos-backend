import logging
import httpx

from app.schemas import WeatherCreate, LocationCoordinate


logger = logging.getLogger(__name__)

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast?"
    "latitude={lat}&longitude={lon}&"
    "current=precipitation,weather_code,temperature_2m,relative_humidity_2m,"
    "wind_speed_10m,wind_direction_10m,cloud_cover"
)
TIMEOUT = httpx.Timeout(20.0, connect=10.0)
MAX_ATTEMPTS = 2


async def fetch_weather_for_coordinates(coordinates: list[LocationCoordinate]) -> list[WeatherCreate]:
    """
    Fetch current weather from Open-Meteo API for each location coordinate.
    Skips locations that fail after retries; raises RuntimeError if all fail.
    """
    if not coordinates:
        raise RuntimeError("No location coordinates provided")

    weather_conditions: list[WeatherCreate] = []

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for coord in coordinates:
            api_url = OPEN_METEO_URL.format(lat=coord.latitude, lon=coord.longitude)
            last_error: Exception | None = None

            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    response = await client.get(api_url)
                    response.raise_for_status()
                    data = response.json()
                    current = data["current"]

                    weather_conditions.append(
                        WeatherCreate(
                            location_id=coord.id,
                            precipitation_mm=current["precipitation"],
                            weather_code=current["weather_code"],
                            temperature_2m=current["temperature_2m"],
                            relative_humidity_2m=current["relative_humidity_2m"],
                            wind_speed_10m=current["wind_speed_10m"],
                            wind_direction_10m=current["wind_direction_10m"],
                            cloud_cover=current["cloud_cover"],
                        )
                    )
                    last_error = None
                    break

                except httpx.TimeoutException as e:
                    last_error = e
                    logger.warning(
                        "Weather API timeout for location_id=%s (attempt %s/%s)",
                        coord.id,
                        attempt,
                        MAX_ATTEMPTS,
                    )
                except httpx.HTTPStatusError as e:
                    last_error = e
                    logger.warning(
                        "Weather API returned %s for location_id=%s (attempt %s/%s)",
                        e.response.status_code,
                        coord.id,
                        attempt,
                        MAX_ATTEMPTS,
                    )
                    if e.response.status_code < 500:
                        break
                except httpx.HTTPError as e:
                    last_error = e
                    logger.warning(
                        "Weather API request failed for location_id=%s: %s",
                        coord.id,
                        type(e).__name__,
                    )
                    break

            if last_error is not None:
                logger.error(
                    "Skipping weather fetch for location_id=%s after failure: %s",
                    coord.id,
                    type(last_error).__name__,
                )


    if not weather_conditions:
        raise RuntimeError("Weather fetch failed for all locations")


    return weather_conditions
