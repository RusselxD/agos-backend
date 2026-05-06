"""Fusion analysis scoring: blockage, water level, weather."""

from app.schemas import (
    FusionData,
    BlockageStatus,
    WaterLevelStatus,
    WeatherStatus,
    AlertThresholdsResponse,
)
from app.schemas.fusion_analysis import AnomalyType


def calculate_fusion_data(
    blockage_status: BlockageStatus | None,
    water_level_status: WaterLevelStatus | None,
    weather_status: WeatherStatus | None,
    alert_thresholds: AlertThresholdsResponse,
) -> FusionData:
    """Compute combined risk score and conditions from component statuses."""
    score = 0
    conditions: list[str] = []
    unavailable: list[str] = []
    anomalies: list[AnomalyType] = []

    # Track unavailable data sources
    if not blockage_status:
        unavailable.append("Blockage detection")
    if not water_level_status:
        unavailable.append("Water level sensor")
    if not weather_status:
        unavailable.append("Weather data")

    # If all sources are unavailable, report degraded state
    if len(unavailable) == 3:
        return FusionData(
            alert_name="Unavailable",
            combined_risk_score=0,
            triggered_conditions=["All data sources are currently unavailable"],
            anomalies=[],
        )

    # --- Anomaly Detection Engine ---
    is_water_critical = water_level_status and water_level_status.critical_percentage >= 90
    is_water_stable_or_low = water_level_status and water_level_status.critical_percentage < 50
    is_blockage_clear = blockage_status and blockage_status.status == "clear"
    is_blockage_severe = blockage_status and blockage_status.status == "blocked"
    is_weather_clear = weather_status and weather_status.precipitation_mm < 1.0
    is_weather_heavy = weather_status and weather_status.precipitation_mm >= 7.5
    is_water_rising_fast = water_level_status and water_level_status.change_rate >= 2
    is_water_dead_flat = water_level_status and water_level_status.change_rate == 0

    # 1. OBSTRUCTED_SENSOR (False High Water)
    # Water is CRITICAL, Blockage is CLEAR, Weather is NO RAIN
    if is_water_critical and is_blockage_clear and is_weather_clear:
        anomalies.append(AnomalyType.OBSTRUCTED_SENSOR)
        conditions.append("⚠️ ANOMALY: Water reads critical but no rain or blockage detected. Suspect sensor obstruction.")

    # 2. BLIND_CAMERA (False Positive Blockage)
    # Blockage is SEVERE, Water is LOW, Weather is HEAVY RAIN
    if is_blockage_severe and is_water_stable_or_low and is_weather_heavy:
        anomalies.append(AnomalyType.BLIND_CAMERA)
        conditions.append("⚠️ ANOMALY: Severe blockage detected but water is low despite heavy rain. Suspect camera lens issue.")

    # 3. STALE_SENSOR (Frozen Sensor)
    # Water is EXACTLY STATIC, Weather is CHANGING/HEAVY
    if is_water_dead_flat and is_weather_heavy:
        # Note: In a real system, you'd check historical variance. For now, dead flat during heavy rain is suspect.
        anomalies.append(AnomalyType.STALE_SENSOR)
        conditions.append("⚠️ ANOMALY: Water level mathematically static during heavy rain. Suspect dead sensor.")

    # 4. GHOST_FLOOD
    # Water RISING RAPIDLY, Blockage CLEAR, Weather API CLEAR
    if is_water_rising_fast and is_blockage_clear and is_weather_clear:
        anomalies.append(AnomalyType.GHOST_FLOOD)
        conditions.append("⚠️ ANOMALY: Rapid water rise without rain or blockage. Potential upstream discharge or localized flash flood.")

    # --- Standard Scoring Logic (with Circuit Breakers) ---

    # Blockage Score (0-30)
    if blockage_status:
        if blockage_status.status == "blocked":
            if AnomalyType.BLIND_CAMERA in anomalies:
                 conditions.append("Ignoring Blockage status due to BLIND_CAMERA anomaly.")
            else:
                score += 30
                conditions.append("Waterway is BLOCKED - Immediate action required.")
        elif blockage_status.status == "partial":
            score += 20
            conditions.append("Partial blockage detected in waterway.")

    # Water Level Score (0-45)
    if water_level_status:
        if AnomalyType.OBSTRUCTED_SENSOR in anomalies or AnomalyType.STALE_SENSOR in anomalies:
             conditions.append("Ignoring Water Level status due to sensor anomaly.")
        else:
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
        and not anomalies  # Don't trigger critical combo if data is suspect
    ):
        conditions.append("MULTIPLE CRITICAL FACTORS")

    alert_name = "Normal"
    if alert_thresholds.tier_2_min <= score <= alert_thresholds.tier_2_max:
        alert_name = "Warning"
    elif alert_thresholds.tier_3_min <= score:
        alert_name = "Critical"

    # Append unavailable sources so operators know the score is incomplete
    if unavailable:
        conditions.append(f"Data unavailable: {', '.join(unavailable)}")

    if alert_name == "Normal":
        if not unavailable and not conditions and not anomalies:
            conditions = [
                "All systems operating within normal parameters",
                "Drainage system clear and functioning",
                "Water levels within safe range",
            ]
        elif not unavailable and not anomalies:
            conditions = ["Conditions normal - Continue routine monitoring"] + conditions

    return FusionData(
        alert_name=alert_name,
        combined_risk_score=score,
        triggered_conditions=conditions,
        anomalies=anomalies,
    )
