from ..base import Base
from sqlalchemy import Boolean, Column, Index, Integer, String, Text


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(100), unique=True, nullable=False)
    template_content = Column(Text, nullable=False)
    auto_send_on_warning = Column(Boolean, default=False)
    auto_send_on_critical = Column(Boolean, default=False)
    auto_send_on_blocked = Column(Boolean, default=False)

    # contraints to ensure only one template can have auto_send_on_[type] set to True
    __table_args__ = (
        Index(
            "uq_message_templates_auto_send_warning_true",
            auto_send_on_warning,
            unique=True,
            postgresql_where=auto_send_on_warning.is_(True),
        ),
        Index(
            "uq_message_templates_auto_send_critical_true",
            auto_send_on_critical,
            unique=True,
            postgresql_where=auto_send_on_critical.is_(True),
        ),
        Index(
            "uq_message_templates_auto_send_blocked_true",
            auto_send_on_blocked,
            unique=True,
            postgresql_where=auto_send_on_blocked.is_(True),
        ),
    )
