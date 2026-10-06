"""Extract summaries and calculate risk scores from sensor/model/weather data."""

from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass

from app.core.config import settings
from app.core.fusion_scoring import calculate_fusion_data
from app.schemas.fusion_analysis import BlockageStatus, WaterLevelStatus, WeatherStatus
from app.schemas.system_settings import AlertThresholdsResponse
from app.utils.obstruction_utils import calculate_obstruction_confidence, obstruction_status_from_tier
from app.utils.sensor_utils import get_status_and_change_rate

from app.utils.summary_utils import (
    BLOCKAGE_SEVERITY,
    wmo_severity,
)


def extract_water_level_summary(readings: list) -> dict:
    """Extract min/max water levels from pre-fetched readings."""
    min_reading = min(readings, key=lambda r: r.water_level_cm)
    max_reading = max(readings, key=lambda r: r.water_level_cm)
    return {
        "min_water_level_cm": float(min_reading.water_level_cm),
        "min_water_timestamp": min_reading.timestamp,
        "max_water_level_cm": float(max_reading.water_level_cm),
        "max_water_timestamp": max_reading.timestamp,
    }


def extract_model_readings_summary(readings: list) -> dict:
    """Extract blockage stats from pre-fetched readings."""
    least_severe = min(readings, key=lambda r: BLOCKAGE_SEVERITY.get(r.blockage_status, 0))
    most_severe = max(readings, key=lambda r: BLOCKAGE_SEVERITY.get(r.blockage_status, 0))
    return {
        "least_severe_blockage": least_severe.blockage_status,
        "most_severe_blockage": most_severe.blockage_status,
    }


def extract_weather_summary(readings: list) -> dict:
    """Extract precipitation stats from pre-fetched readings."""
    min_precip = min(readings, key=lambda r: r.precipitation_mm)
    max_precip = max(readings, key=lambda r: r.precipitation_mm)
    most_severe = max(readings, key=lambda r: wmo_severity(r.weather_code))
    return {
        "min_precipitation_mm": min_precip.precipitation_mm,
        "min_precip_timestamp": min_precip.created_at,
        "max_precipitation_mm": max_precip.precipitation_mm,
        "max_precip_timestamp": max_precip.created_at,
        "most_severe_weather_code": most_severe.weather_code,
    }


@dataclass(frozen=True)
class SmoothedModelReading:
    timestamp: datetime
    blockage_status: str


def smooth_model_readings(readings: list) -> list[SmoothedModelReading]:
    """Replay raw detections through the same rolling window as live inference."""
    window = deque(maxlen=max(1, settings.OBSTRUCTION_WINDOW_K))
    smoothed = []
    for reading in sorted(readings, key=lambda item: item.timestamp):
        window.append(reading.blockage_status)
        confidence = calculate_obstruction_confidence(list(window), reading.blockage_percentage)
        smoothed.append(SmoothedModelReading(
            timestamp=reading.timestamp,
            blockage_status=obstruction_status_from_tier(confidence.tier),
        ))
    return smoothed


def calculate_risk_scores(
    sensor_readings: list,
    model_readings: list,
    weather_readings: list,
    critical_level: float,
    alert_thresholds: AlertThresholdsResponse,
    start_of_day: datetime,
) -> dict:
    """Replay source updates causally using the live scoring and anomaly rules.

    Input may include context from before midnight; only events in the target
    day contribute extrema. Camera readings must already be smoothed.
    """
    events = [(r.timestamp, 0, r) for r in sensor_readings]
    events += [(r.timestamp, 1, r) for r in model_readings]
    events += [(r.created_at, 2, r) for r in weather_readings]
    events.sort(key=lambda event: (event[0], event[1]))
    water = blockage = weather = None
    previous_water_cm = None
    min_score = max_score = None
    min_timestamp = max_timestamp = None

    def current(status, timestamp, max_age_minutes):
        if status is None or timestamp - status.timestamp > timedelta(minutes=max_age_minutes):
            return None
        return status

    for timestamp, source, reading in events:
        if source == 0:
            level = float(reading.water_level_cm)
            trend, change_rate = get_status_and_change_rate(level, previous_water_cm)
            water = WaterLevelStatus(
                timestamp=timestamp, water_level_cm=level, trend=trend,
                change_rate=change_rate,
                critical_percentage=round(level / critical_level * 100, 1) if critical_level else 0.0,
            )
            previous_water_cm = level
        elif source == 1:
            blockage = BlockageStatus(timestamp=timestamp, status=reading.blockage_status)
        else:
            weather = WeatherStatus(
                timestamp=timestamp, precipitation_mm=reading.precipitation_mm,
                weather_condition=str(reading.weather_code),
            )
        if timestamp < start_of_day:
            continue
        score = calculate_fusion_data(
            blockage_status=current(blockage, timestamp, settings.DETECTION_WARNING_PERIOD_MINUTES),
            water_level_status=current(water, timestamp, settings.SENSOR_WARNING_PERIOD_MINUTES),
            weather_status=current(weather, timestamp, settings.WEATHER_CONDITION_WARNING_PERIOD_MINUTES),
            alert_thresholds=alert_thresholds,
        ).combined_risk_score
        if min_score is None or score < min_score:
            min_score, min_timestamp = score, timestamp
        if max_score is None or score > max_score:
            max_score, max_timestamp = score, timestamp

    if min_score is None:
        return {}
    return {
        "min_risk_score": min_score,
        "max_risk_score": max_score,
        "min_risk_timestamp": min_timestamp,
        "max_risk_timestamp": max_timestamp,
    }
