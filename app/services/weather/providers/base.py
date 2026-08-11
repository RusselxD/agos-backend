"""Weather provider abstraction (F2).

A ``WeatherProvider`` fetches the current conditions for a single coordinate and
returns a normalized ``WeatherReading``. The only field the fusion scorer uses is
``precipitation_mm``; ``weather_code`` is WMO (providers map their own codes to
WMO) and the remaining fields are display-only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class WeatherFetchError(RuntimeError):
    """Raised when a provider cannot provide data for a coordinate."""


class WeatherRateLimitedError(WeatherFetchError):
    """Raised when a provider rate-limits the request (HTTP 429)."""


class WeatherReading(BaseModel):
    """Normalized, provider-neutral weather reading."""

    precipitation_mm: float  # REQUIRED — the only field the scorer consumes
    weather_code: int        # WMO code; providers map their own codes to WMO
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Optional display-only fields (kept non-null so WeatherCreate stays satisfied)
    temperature_2m: float = 0.0
    relative_humidity_2m: float = 0.0
    wind_speed_10m: float = 0.0
    wind_direction_10m: float = 0.0
    cloud_cover: float = 0.0


@runtime_checkable
class WeatherProvider(Protocol):
    """Fetch current weather for a coordinate. Implementations are stateless."""

    name: str

    async def fetch(self, lat: float, lon: float) -> WeatherReading:
        ...
