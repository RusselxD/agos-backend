from pydantic import BaseModel
from datetime import datetime

class ModelReadingBase(BaseModel):
    camera_device_id: int
    image_path: str
    timestamp: datetime
    blockage_percentage: float
    blockage_status: str
    total_debris_count: int

class ModelReadingCreate(ModelReadingBase):
    pass

# class ModelReadingResponse(ModelReadingBase):
#     id: int

#     class Config:
#         from_attributes = True