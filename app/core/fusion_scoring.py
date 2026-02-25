"""Fusion analysis scoring: blockage, water level, weather."""

from app.schemas import (
    FusionData,
    BlockageStatus,
    WaterLevelStatus,
    WeatherStatus,
    AlertThresholdsResponse,
)


def calculate_fusion_data(
    blockage_status: BlockageStatus | None,
    water_level_status: WaterLevelStatus | None,
    weather_status: WeatherStatus | None,
    alert_thresholds: AlertThresholdsResponse,
) -> FusionData:
    """Compute combined risk score and conditions from component statuses."""
    score = 0
    conditions: list[str] = []

    # Blockage Score (0-30)
    if blockage_status:
        if blockage_status.status == "blocked":
            score += 30
            conditions.append("Waterway is BLOCKED - Immediate action required.")
        elif blockage_status.status == "partial":
            score += 20
            conditions.append("Partial blockage detected in waterway.")

    # Water Level Score (0-45)
    if water_level_status:
        if water_level_status.critical_percentage < 50:
            score += 10
            conditions.append("Water level is within normal range.")
        elif 50 <= water_level_status.critical_percentage < 75:
            score += 20
            conditions.append("Water level is elevated.")
        elif 75 <= water_level_status.critical_percentage < 90:
            score += 30
            conditions.append("Water level is high.")
        elif 90 <= water_level_status.critical_percentage < 100:
            score += 45
            conditions.append("Water level nearing critical threshold.")
        elif water_level_status.critical_percentage == 100:
            score += 45
            conditions.append("Water level at CRITICAL threshold!")
        else:
            score += 45
            conditions.append("Water level above CRITICAL threshold!")

        if water_level_status.trend == "rising":
            score += 5
        if water_level_status.change_rate >= 2:
            conditions.append("Water level rising quickly.")
        elif water_level_status.change_rate >= 1.5:
            conditions.append("Water level rising.")

    # Weather Score (0-20)
    if weather_status:
        if 1 <= weather_status.precipitation_mm < 2.55:
            score += 8
            conditions.append("Light rainfall detected.")
        elif 2.55 <= weather_status.precipitation_mm < 7.5:
            score += 15
            conditions.append("Moderate rainfall detected.")
        elif weather_status.precipitation_mm >= 7.5:
            score += 20
            conditions.append("Heavy rainfall detected.")

    # Critical combination
    if (
        blockage_status
        and blockage_status.status == "blocked"
        and water_level_status
        and water_level_status.critical_percentage >= 90
        and weather_status
        and weather_status.precipitation_mm >= 7.5
    ):
        conditions.append("MULTIPLE CRITICAL FACTORS")

    alert_name = "Normal"
    if alert_thresholds.tier_2_min <= score <= alert_thresholds.tier_2_max:
        alert_name = "Warning"
    elif alert_thresholds.tier_3_min <= score:
        alert_name = "Critical"

    if alert_name == "Normal":
        if not conditions:
            conditions = [
                "All systems operating within normal parameters",
                "Drainage system clear and functioning",
                "Water levels within safe range",
            ]
        else:
            conditions = ["Conditions normal - Continue routine monitoring"] + conditions

    return FusionData(
        alert_name=alert_name,
        combined_risk_score=score,
        triggered_conditions=conditions,
    )
