"""Extract summaries and calculate risk scores from sensor/model/weather data."""

from datetime import datetime, timedelta

from app.utils.summary_utils import (
    BLOCKAGE_SEVERITY,
    calc_water_score,
    calc_blockage_score,
    calc_weather_score,
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
    most_severe_code = max(r.weather_code for r in readings)
    return {
        "min_precipitation_mm": min_precip.precipitation_mm,
        "min_precip_timestamp": min_precip.created_at,
        "max_precipitation_mm": max_precip.precipitation_mm,
        "max_precip_timestamp": max_precip.created_at,
        "most_severe_weather_code": most_severe_code,
    }


def _find_closest(
    readings: list,
    target_time: datetime,
    time_attr: str,
    max_gap_minutes: int = 15,
):
    """Find reading closest to target_time within max_gap_minutes."""
    if not readings:
        return None
    max_gap = timedelta(minutes=max_gap_minutes)
    closest = None
    min_diff = max_gap
    for r in readings:
        diff = abs(getattr(r, time_attr) - target_time)
        if diff < min_diff:
            min_diff = diff
            closest = r
    return closest


def _find_and_calc_blockage_score(
    model_readings: list,
    target_time: datetime,
    max_gap_minutes: int = 15,
) -> int:
    closest = _find_closest(model_readings, target_time, "timestamp", max_gap_minutes)
    return calc_blockage_score(closest.blockage_status) if closest else 0


def _find_and_calc_weather_score(
    weather_readings: list,
    target_time: datetime,
    max_gap_minutes: int = 15,
) -> int:
    closest = _find_closest(weather_readings, target_time, "created_at", max_gap_minutes)
    return calc_weather_score(closest.precipitation_mm) if closest else 0


def calculate_risk_scores(
    sensor_readings: list,
    model_readings: list,
    weather_readings: list,
    critical_level: float,
) -> dict:
    """Calculate min/max risk scores from pre-fetched data."""
    if not sensor_readings and not model_readings and not weather_readings:
        return {}

    min_score = float("inf")
    max_score = float("-inf")
    min_timestamp = None
    max_timestamp = None

    if sensor_readings:
        for sensor in sensor_readings:
            score = calc_water_score(float(sensor.water_level_cm), critical_level)
            score += _find_and_calc_blockage_score(model_readings, sensor.timestamp)
            score += _find_and_calc_weather_score(weather_readings, sensor.timestamp)
            if score < min_score:
                min_score, min_timestamp = score, sensor.timestamp
            if score > max_score:
                max_score, max_timestamp = score, sensor.timestamp
    elif model_readings:
        for model in model_readings:
            score = calc_blockage_score(model.blockage_status)
            score += _find_and_calc_weather_score(weather_readings, model.timestamp)
            if score < min_score:
                min_score, min_timestamp = score, model.timestamp
            if score > max_score:
                max_score, max_timestamp = score, model.timestamp
    elif weather_readings:
        for weather in weather_readings:
            score = calc_weather_score(weather.precipitation_mm)
            if score < min_score:
                min_score, min_timestamp = score, weather.created_at
            if score > max_score:
                max_score, max_timestamp = score, weather.created_at

    if min_score == float("inf"):
        return {}

    return {
        "min_risk_score": min_score,
        "max_risk_score": max_score,
        "min_risk_timestamp": min_timestamp,
        "max_risk_timestamp": max_timestamp,
    }
