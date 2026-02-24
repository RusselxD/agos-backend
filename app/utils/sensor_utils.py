from datetime import datetime, timedelta, timezone
from app.core.config import settings

def get_signal_quality(self, signal_strength: int) -> str:
    if signal_strength >= -50:
        quality = 'excellent'
    elif signal_strength >= -60:
        quality = 'good'
    elif signal_strength >= -70:
        quality = 'fair'
    else:
        quality = 'poor'
    return quality


def get_status_and_change_rate(self, current_cm: float, prev_cm: float | None) -> tuple[str, float]:
    if prev_cm is None:
        return "stable", 0.0
    change_rate = round(current_cm - prev_cm, 2)
    if change_rate > 1:
        status = 'rising'
    elif change_rate < -1:
        status = 'falling'
    else:
        status = 'stable'
    return status, change_rate


def format_datetime_for_excel(self, dt: datetime) -> str:
    # Convert UTC to UTC+8 for display
    local_dt = dt.astimezone(timezone(timedelta(hours=settings.UTC_OFFSET_HOURS)))
    return local_dt.strftime("%Y-%m-%d %H:%M")