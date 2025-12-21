from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sensor_devices import SensorDevice
from app.crud.base import CRUDBase
from sqlalchemy import select

class CRUDSensorDevice(CRUDBase[SensorDevice, None, None]):

    async def get_device(self, db: AsyncSession, id: int = 1) -> SensorDevice:
        result = await db.execute(
            select(SensorDevice).filter(SensorDevice.id == id)
        )
        return result.scalars().first()

sensor_device = CRUDSensorDevice(SensorDevice)