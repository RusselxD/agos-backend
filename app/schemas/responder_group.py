from pydantic import BaseModel
from uuid import UUID

class ResponderGroupItem(BaseModel):
    group_name: str
    member_ids: list[UUID]

    class Config:
        from_attributes = True