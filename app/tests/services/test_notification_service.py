from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.crud import notification_template_crud
from app.models.notification_template import NotificationType
from app.schemas.subscription import SendNotificationSchema
from app.services.notification_service import notification_service


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "notification_type",
    [
        NotificationType.WARNING,
        NotificationType.CRITICAL,
        NotificationType.BLOCKAGE,
    ],
)
async def test_system_notifications_accept_system_templates(
    monkeypatch: pytest.MonkeyPatch,
    notification_type: NotificationType,
):
    template = SimpleNamespace(
        id=1,
        type=notification_type,
        title="System alert",
        message="System-generated alert message",
    )
    monkeypatch.setattr(
        notification_template_crud,
        "get",
        AsyncMock(return_value=template),
    )
    payload = SendNotificationSchema(
        responder_ids=[uuid4()],
        template_id=template.id,
    )

    result = await notification_service._resolve_notification_content(
        payload=payload,
        db=AsyncMock(),
        system_initiated=True,
    )

    assert result == (template.title, template.message, notification_type)


@pytest.mark.asyncio
async def test_manual_notifications_still_reject_system_templates(
    monkeypatch: pytest.MonkeyPatch,
):
    template = SimpleNamespace(
        id=1,
        type=NotificationType.CRITICAL,
        title="Critical alert",
        message="Critical system-generated alert message",
    )
    monkeypatch.setattr(
        notification_template_crud,
        "get",
        AsyncMock(return_value=template),
    )
    payload = SendNotificationSchema.model_validate(
        {
            "responder_ids": [uuid4()],
            "template_id": template.id,
            # A client-provided bypass must be ignored; only the internal service
            # call argument can mark a send as automatic.
            "system_initiated": True,
        }
    )

    with pytest.raises(HTTPException, match="Manual notifications") as exc_info:
        await notification_service._resolve_notification_content(
            payload=payload,
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 400
