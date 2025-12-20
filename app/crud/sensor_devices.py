from sqlalchemy.orm import Session
from app.schemas.sensor_devices import SensorDeviceResponse
from app.models.sensor_devices import SensorDevice
from app.models.sensor_readings import SensorReading
from app.crud.base import CRUDBase
from datetime import datetime, timedelta
from fastapi import HTTPException

class CRUDSensorDevice(CRUDBase[SensorDevice, None, None]):

    def get(self, db: Session, id: int = 1) -> SensorDeviceResponse | None:
        sensor_device = db.query(SensorDevice).filter(SensorDevice.id == id).first()

        if not sensor_device:
            raise HTTPException(status_code=404, detail="Sensor device not found")

        # Get latest reading
        latest_reading = (
            db.query(SensorReading)
            .filter(SensorReading.sensor_id == id)
            .order_by(SensorReading.timestamp.desc())
            .first()
        )

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