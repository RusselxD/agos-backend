from pydantic import BaseModel
from app.models.notification_template import NotificationType

class NotificationTemplateResponse(BaseModel):
    id: int
    type: NotificationType
    title: str
    message: str


class CreateNotificationTemplateRequest(BaseModel):
    type: NotificationType
    title: str
    message: str