from pydantic import BaseModel
from datetime import datetime


class CameraStatus(BaseModel):
    is_online: bool
    last_seen: datetime | None
