from ..base import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship


DEFAULT_APPROVED_RESPONDERS_GROUP_NAME = "All Approved Responders"

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)

    responders = relationship("Responders", secondary="responder_groups", back_populates="groups")
