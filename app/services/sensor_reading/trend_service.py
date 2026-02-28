from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.crud import sensor_reading_crud
from app.schemas.sensor_reading import SensorReadingTrendResponse


DURATION_DELTAS = {
    "1_hour": timedelta(hours=1),
    "6_hours": timedelta(hours=6),
    "12_hours": timedelta(hours=12),
    "1_day": timedelta(days=1),
    "1_week": timedelta(weeks=1),
    "1_month": timedelta(days=30),
}

AGGREGATION_INTERVALS = {
    "1_hour": timedelta(minutes=1),
    "6_hours": timedelta(minutes=5),
    "12_hours": timedelta(minutes=10),
    "1_day": timedelta(minutes=30),
    "1_week": timedelta(hours=2),
    "1_month": timedelta(days=1),
}


def _format_trend_label(dt: datetime, interval: timedelta) -> str:

    local_dt = dt.astimezone(timezone(timedelta(hours=settings.UTC_OFFSET_HOURS)))
    if interval >= timedelta(days=1):
        return local_dt.strftime("%d %b")
    elif interval >= timedelta(hours=2):
        return local_dt.strftime("%d %b %H:%M")
    else:
        return local_dt.strftime("%H:%M")


def _process_trend_data(
    items: list, 
    interval: timedelta, 
    start_time: datetime) -> SensorReadingTrendResponse:
    
    grouped_data: dict[float, list[float]] = {}
    interval_seconds = interval.total_seconds()

    for item in items:
        ts_seconds = item.timestamp.timestamp()
        bucket_ts = ts_seconds - (ts_seconds % interval_seconds)
        if bucket_ts not in grouped_data:
            grouped_data[bucket_ts] = []
        grouped_data[bucket_ts].append(item.water_level_cm)

    start_ts = start_time.timestamp()
    current_bucket_ts = start_ts - (start_ts % interval_seconds)
    end_ts = datetime.now(timezone.utc).timestamp()

    labels: list[str] = []
    levels: list[float] = []

    while current_bucket_ts <= end_ts:
        if current_bucket_ts in grouped_data:
            avg_level = sum(grouped_data[current_bucket_ts]) / len(grouped_data[current_bucket_ts])
            levels.append(round(avg_level, 2))
        else:
            levels.append(0.0)

        dt = datetime.fromtimestamp(current_bucket_ts, tz=timezone.utc)
        labels.append(_format_trend_label(dt, interval))
        current_bucket_ts += interval_seconds

    return SensorReadingTrendResponse(labels=labels, levels=levels)


async def get_readings_trend(
    db: AsyncSession,
    duration: str,
    sensor_device_id: int) -> SensorReadingTrendResponse:
    
    delta = DURATION_DELTAS.get(duration)
    if delta is None:
        raise ValueError(f"Invalid duration: {duration}")

    range_start = datetime.now(timezone.utc) - delta
    db_items = await sensor_reading_crud.get_readings_since(
        db=db,
        since_datetime=range_start,
        sensor_device_id=sensor_device_id,
    )
    interval = AGGREGATION_INTERVALS.get(duration, timedelta(minutes=1))
    return _process_trend_data(db_items, interval, range_start)
