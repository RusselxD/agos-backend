
from pydantic import BaseModel

class UploadResponse(BaseModel):
    file_path: str