from datetime import datetime
from pydantic import BaseModel


class ModelReadingListItem(BaseModel):
    id: int
    blockage_status: str
    blockage_percentage: float
    total_debris_count: int
    timestamp: datetime

    class Config:
        from_attributes = True


class ModelReadingPaginatedResponse(BaseModel):
    items: list[ModelReadingListItem]
    has_more: bool


class ModelReadingDetailResponse(BaseModel):
    id: int
    camera_device_id: int
    image_path: str
    blockage_status: str
    blockage_percentage: float
    total_debris_count: int
    timestamp: datetime
    created_at: datetime

    class Config:
        from_attributes = True
