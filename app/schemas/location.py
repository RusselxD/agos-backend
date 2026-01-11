from pydantic import BaseModel

class LocationCoordinate(BaseModel):
    id: int
    latitude: float
    longitude: float

class DevicePerLocation(BaseModel):
    sensor_device_id: int
    camera_device_id: int