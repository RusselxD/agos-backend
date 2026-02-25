BLOCKAGE_SEVERITY = {"clear": 0, "partial": 1, "blocked": 2}

def calc_water_score(water_level_cm: float, critical_level: float) -> int:
    """Calculate water level contribution to risk score."""
    critical_pct = (water_level_cm / critical_level) * 100
    if critical_pct < 50:
        return 10
    elif critical_pct < 75:
        return 20
    elif critical_pct < 90:
        return 30
    return 45


def calc_blockage_score(self, status: str) -> int:
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