"""Weather provider factory (F2)."""

from __future__ import annotations

from .base import (
    WeatherProvider,
    WeatherReading,
    WeatherFetchError,
    WeatherRateLimitedError,
)
from .openmeteo import OpenMeteoProvider
from .openweathermap import OpenWeatherMapProvider
from .weatherapi import WeatherApiProvider

_PROVIDERS: dict[str, type] = {
    "openmeteo": OpenMeteoProvider,
    "openweathermap": OpenWeatherMapProvider,
    "weatherapi": WeatherApiProvider,
}


def get_provider(name: str) -> WeatherProvider:
    """Return the configured provider singleton. Falls back to Open-Meteo."""
    provider_cls = _PROVIDERS.get((name or "").lower())
    if provider_cls is None:
        raise WeatherFetchError(
            f"Unknown WEATHER_PROVIDER '{name}'. "
            f"Choose one of: {', '.join(_PROVIDERS)}"
        )
    return provider_cls()


__all__ = [
    "get_provider",
    "WeatherProvider",
    "WeatherReading",
    "WeatherFetchError",
    "WeatherRateLimitedError",
]
