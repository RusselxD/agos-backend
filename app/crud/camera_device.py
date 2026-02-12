from app.crud.base import CRUDBase
from app.models import CameraDevice
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class CRUDCameraDevice(CRUDBase[CameraDevice, None, None]):

    async def get_default_camera_by_location(self, db: AsyncSession, location_id: int) -> CameraDevice | None:
        result = await db.execute(
            select(self.model.id, self.model.device_name)
            .filter(self.model.location_id == location_id)
            .limit(1)
        )
        return result.mappings().first()

    async def get_id_by_location(self, db: AsyncSession, location_id: int) -> int | None:
        result = await db.execute(
            select(self.model.id)
            .filter(self.model.location_id == location_id)
            .limit(1)
        )
        camera_device = result.scalars().first()
        return camera_device
    
camera_device_crud = CRUDCameraDevice(CameraDevice)