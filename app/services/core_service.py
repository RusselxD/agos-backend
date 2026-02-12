from app.crud import location_crud
from app.crud import sensor_device_crud
from app.crud import camera_device_crud
from app.schemas import LocationDetails, DeviceDetails
from fastapi import HTTPException

class CoreService:
    
    async def get_default_location(self, db) -> LocationDetails:
        default_location = await location_crud.get_default_location(db=db)
        print(default_location)
        if not default_location:
            raise HTTPException(status_code=404, detail="Default location not found")
        
        return LocationDetails(
            location_id=default_location["id"],
            location_name=default_location["name"]
        )


    async def get_device_details(self, db, location_id: int) -> DeviceDetails:

        default_camera = await camera_device_crud.get_default_camera_by_location(db=db, location_id=location_id)
        default_sensor = await sensor_device_crud.get_default_sensor_by_location(db=db, location_id=location_id)

        if not default_camera or not default_sensor:
            raise HTTPException(status_code=404, detail="Default devices not found for the given location")
        
        return DeviceDetails(
            sensor_device_id=default_sensor["id"],
            sensor_device_name=default_sensor["device_name"],
            camera_device_id=default_camera["id"],
            camera_device_name=default_camera["device_name"]
        )


core_service = CoreService()