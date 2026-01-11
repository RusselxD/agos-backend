from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import SensorDeviceResponse, SensorDeviceStatusResponse
from app.crud.sensor_device import sensor_device as sensor_device_crud
from app.crud.sensor_reading import sensor_reading as sensor_reading_crud
from datetime import datetime, timedelta
from fastapi import HTTPException
from app.core.config import settings

class SensorDeviceService:
    
    async def get_device_status(self, db: AsyncSession, sensor_device_id: int) -> SensorDeviceStatusResponse:
        sensor_device: SensorDeviceResponse = await sensor_device_crud.get(db=db, id=sensor_device_id)

        if not sensor_device:
            raise HTTPException(status_code=404, detail="Sensor device not found")

        latest_reading = await sensor_reading_crud.get_latest_reading(db=db, sensor_device_id=sensor_device_id)

        # Default values if no readings yet
        if not latest_reading:
            return SensorDeviceStatusResponse(
                device_name=sensor_device.device_name,
                                location_name=sensor_device.location_name,
                connection="Offline",
                last_updated=None,
                signal=None
            )

        # Calculate connection status
        now = datetime.now(latest_reading.timestamp.tzinfo)
        time_since = now - latest_reading.timestamp

        if time_since <= timedelta(minutes=settings.SENSOR_GRACE_PERIOD_MINUTES):
            connection = "Online"
        elif time_since <= timedelta(minutes=settings.SENSOR_WARNING_PERIOD_MINUTES):
            connection = "Warning"
        else:
            connection = "Offline"

        # Response if the last reading is way off the grace period
        if connection == "Offline":
            return SensorDeviceStatusResponse(
            device_name=sensor_device.device_name,
                            location_name=sensor_device.location_name,
            connection=connection,
            last_updated=latest_reading.timestamp.isoformat(),
            signal=None
        )

        # Normal response with signal quality
        return SensorDeviceStatusResponse(
            device_name=sensor_device.device_name,
                            location_name=sensor_device.location_name,
            connection=connection,
            last_updated=latest_reading.timestamp.isoformat(),
            signal=latest_reading.signal_quality
        )

sensor_device_service = SensorDeviceService()