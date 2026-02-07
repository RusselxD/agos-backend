from ..base import Base
from sqlalchemy import Column, Integer, String, Text, Boolean

class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(100), unique=True, nullable=False)
    template_content = Column(Text, nullable=False)
    auto_send_on_critical = Column(Boolean, default=False, nullable=False)