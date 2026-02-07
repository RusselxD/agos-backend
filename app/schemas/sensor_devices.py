from pydantic import BaseModel

class SensorDeviceBase(BaseModel):
    device_name: str
    location_id: int
class SensorDeviceResponse(BaseModel):
    device_name: str
    location_name: str

    class Config:
        from_attributes = True

class SensorDeviceStatusResponse(BaseModel):
    device_name: str
    location_name: str
    connection: str
    last_updated: str | None
    signal: str | None

    class Config:
        from_attributes = True