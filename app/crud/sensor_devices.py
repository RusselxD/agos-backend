from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.sensor_devices import SensorDeviceResponse
from app.models.sensor_devices import SensorDevice
from app.models.sensor_readings import SensorReading
from app.crud.base import CRUDBase
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import select

class CRUDSensorDevice(CRUDBase[SensorDevice, None, None]):

    async def get(self, db: AsyncSession, id: int = 1) -> SensorDeviceResponse | None:
        result = await db.execute(
            select(SensorDevice).filter(SensorDevice.id == id)
        )
        sensor_device = result.scalars().first()

        if not sensor_device:
            raise HTTPException(status_code=404, detail="Sensor device not found")

        # Get latest reading
        result = await db.execute(
            select(SensorReading).filter(SensorReading.sensor_id == id).order_by(SensorReading.timestamp.desc())
        )
        latest_reading = result.scalars().first()

        # Default values if no readings
        if not latest_reading:
            return SensorDeviceResponse(
                device_name=sensor_device.device_name,
                location=sensor_device.location,
                connection="Offline",
                last_updated=None,
                signal=None
            )
        
        # Calculate connection status
        now = datetime.now(latest_reading.timestamp.tzinfo)
        time_since = now - latest_reading.timestamp
        
        if time_since <= timedelta(minutes=6):
            connection = "Online"
        elif time_since <= timedelta(minutes=10):
            connection = "Warning"  # or "Unstable"
        else:
            connection = "Offline"
        
        if connection == "Offline":
            return SensorDeviceResponse(
            device_name=sensor_device.device_name,
            location=sensor_device.location,
            connection=connection,
            last_updated=latest_reading.timestamp.isoformat(),
            signal=None
        )

        return SensorDeviceResponse(
            device_name=sensor_device.device_name,
            location=sensor_device.location,
            connection=connection,
            last_updated=latest_reading.timestamp.isoformat(),
            signal=latest_reading.signal_quality
        )

sensor_device = CRUDSensorDevice(SensorDevice)