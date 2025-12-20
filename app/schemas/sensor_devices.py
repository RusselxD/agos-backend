from pydantic import BaseModel

class SensorDeviceBase(BaseModel):
    device_name: str
    location: str

class SensorDeviceResponse(SensorDeviceBase):
    connection: str
    last_updated: str
    signal: str | None

    class Config:
        from_attributes = True