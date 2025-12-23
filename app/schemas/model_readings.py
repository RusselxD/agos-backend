from pydantic import BaseModel
from datetime import datetime

class ModelReadingBase(BaseModel):
    timestamp: datetime
    status: str  # "clear", "partial", "blocked"
    confidence: float
    image_path: str

class ModelReadingCreate(ModelReadingBase):
    pass

class ModelReadingResponse(ModelReadingBase):
    id: int

    class Config:
        from_attributes = True