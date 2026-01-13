from sqlalchemy.ext.asyncio import AsyncSession
from app.models import SensorDevice
from app.schemas import SensorDeviceResponse
from app.crud.base import CRUDBase
from sqlalchemy import select
from sqlalchemy.orm import joinedload

class CRUDSensorDevice(CRUDBase[SensorDevice, None, None]):

    async def get_sensor_device_name(self, db: AsyncSession, sensor_device_id: int) -> str:
        result = await db.execute(
            select(self.model.device_name)
            .filter(self.model.id == sensor_device_id)
            .limit(1)
        )
        sensor_device_name = result.scalars().first()
        return sensor_device_name

    async def get(self, db: AsyncSession, id: int) ->  SensorDeviceResponse | None:
        sensor_devices = await db.execute(
            select(self.model)
            .filter(self.model.id == id)
            .options(joinedload(self.model.location))        
            .execution_options(populate_existing=False)
        )
        sensor_device = sensor_devices.scalars().first()

        if sensor_device:
            return SensorDeviceResponse(
                device_name=sensor_device.device_name,
                location_name=sensor_device.location.name
            )
        
        return None

    async def get_id_by_location(self, db: AsyncSession, location_id: int) -> int | None:
        result = await db.execute(
            select(self.model.id)
            .filter(self.model.location_id == location_id)
            .limit(1)
        )
        sensor_device = result.scalars().first()
        return sensor_device

sensor_device = CRUDSensorDevice(SensorDevice)