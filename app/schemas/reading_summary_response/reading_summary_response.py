from pydantic import BaseModel

class ReadingSummaryResponse(BaseModel):
    status: str # either "success" or "error"
    message: str # detailed message (for success, it's just "Retrieved successfully")