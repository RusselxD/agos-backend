BLOCKAGE_SEVERITY = {"clear": 0, "partial": 1, "blocked": 2}

# WMO weather-code severity ranking for flood monitoring (higher = worse).
# Numeric WMO codes are only loosely ordered by severity, so rank explicitly
# rather than relying on max(weather_code).
WMO_SEVERITY_RANK = {
    0: 0, 1: 0, 2: 0, 3: 0,        # clear / cloudy
    45: 1, 48: 1,                  # fog
    51: 2, 53: 3, 55: 4,           # drizzle: light / moderate / dense
    56: 3, 57: 4,                  # freezing drizzle
    71: 2, 73: 3, 75: 4, 77: 2,    # snow (low flood relevance)
    85: 3, 86: 4,                  # snow showers
    61: 5, 63: 6, 65: 8,           # rain: slight / moderate / heavy
    66: 5, 67: 8,                  # freezing rain
    80: 5, 81: 7, 82: 9,           # rain showers: slight / moderate / violent
    95: 9,                         # thunderstorm
    96: 10, 99: 11,                # thunderstorm with hail
}


def wmo_severity(weather_code: int) -> int:
    """Flood-severity rank for a WMO weather code (higher = more severe)."""
    return WMO_SEVERITY_RANK.get(weather_code, 0)


def calc_water_score_from_pct(critical_pct: float) -> int:
    """Water level contribution to the risk score, from a precomputed critical %.

    Single source of truth for the water-level scoring tiers, shared by the
    nightly daily-summary aggregation and the live fusion score.
    """
    if critical_pct < 50:
        return 10
    elif critical_pct < 75:
        return 20
    elif critical_pct < 90:
        return 30
    return 45


def calc_water_score(water_level_cm: float, critical_level: float) -> int:
    """Calculate water level contribution to risk score."""
    return calc_water_score_from_pct((water_level_cm / critical_level) * 100)


def calc_blockage_score(status: str) -> int:
    """Calculate blockage contribution to risk score."""
    if status == "blocked":
        return 30
    elif status == "partial":
        return 20
    return 0


def calc_weather_score(precipitation_mm: float) -> int:
    """Calculate weather contribution to risk score."""
    if precipitation_mm >= 7.5:
        return 20
    elif precipitation_mm >= 2.55:
        return 15
    elif precipitation_mm >= 1:
        return 8
    return 0