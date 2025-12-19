from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base

class SystemSettings(Base):
    __tablename__ = "system_settings"

    key = Column(Text, primary_key=True)
    json_value = Column(JSONB, nullable=False)