from pydantic import BaseModel

class MessageTemplateBase(BaseModel):
    template_name: str
    template_content: str
    auto_send_on_critical: bool = False

class MessageTemplateCreate(MessageTemplateBase):
    pass

class MessageTemplateResponse(MessageTemplateBase):
    id: int

    class Config:
        from_attributes = True