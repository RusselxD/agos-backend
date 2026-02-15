from pydantic import BaseModel

class MessageTemplateBase(BaseModel):
    template_name: str
    template_content: str
    auto_send_on_critical: bool | None = None
    auto_send_on_warning: bool | None = None
    auto_send_on_blocked: bool | None = None

class MessageTemplateCreate(MessageTemplateBase):
    pass

class MessageTemplateResponse(MessageTemplateBase):
    id: int

    class Config:
        from_attributes = True
