from pydantic import BaseModel
from uuid import UUID

class ResponderGroupCreate(BaseModel):
    group_name: str
    member_ids: list[UUID]

class ResponderGroupItem(BaseModel):
    id: int
    group_name: str
    member_ids: list[UUID]

    class Config:
        from_attributes = True