from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sensor_devices import SensorDevice
from app.crud.base import CRUDBase
from sqlalchemy import select

class CRUDSensorDevice(CRUDBase[SensorDevice, None, None]):

    async def get_coordinates(self, db: AsyncSession, id: int = 1) -> tuple[float, float] | None:
        result = await db.execute(
            select(SensorDevice.latitude, SensorDevice.longitude).filter(SensorDevice.id == id)
        )
        row = result.first()
        if row:
            return row[0], row[1]  # Access by index when selecting specific columns
        return None

sensor_device = CRUDSensorDevice(SensorDevice)