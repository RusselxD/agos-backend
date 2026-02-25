from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import sensor_reading_crud, sensor_device_crud
from app.schemas import (
    SensorReadingForExport,
    SensorReadingForExportResponse,
)
from app.utils.sensor_utils import (
    get_status_and_change_rate,
    format_datetime_for_excel,
    get_signal_quality,
)


async def get_readings_for_export(
    db: AsyncSession,
    start_datetime: datetime,
    end_datetime: datetime,
    sensor_device_id: int,
) -> SensorReadingForExportResponse:
    sensor_device_name = await sensor_device_crud.get_sensor_device_name(
        db=db, sensor_device_id=sensor_device_id
    )
    records = await sensor_reading_crud.get_readings_for_export(
        db=db,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        sensor_device_id=sensor_device_id,
    )

    readings = []
    for record in records:
        status, change_rate = get_status_and_change_rate(
            record.water_level_cm, record.prev_water_level
        )
        readings.append(
            SensorReadingForExport(
                timestamp=format_datetime_for_excel(record.timestamp),
                water_level_cm=record.water_level_cm,
                status=status,
                change_rate=change_rate,
                signal_strength=record.signal_strength,
                signal_quality=get_signal_quality(record.signal_strength),
            )
        )

    return SensorReadingForExportResponse(
        readings=readings,
        sensor_device_name=sensor_device_name,
    )
