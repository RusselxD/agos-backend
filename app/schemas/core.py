from pydantic import BaseModel

class LocationDetails(BaseModel):
    location_id: int
    location_name: str

class DeviceDetails(BaseModel):
    sensor_device_id: int
    sensor_device_name: str
    camera_device_id: int
    camera_device_name: str