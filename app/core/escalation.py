"""Automated escalation for unacknowledged critical notifications."""

from app.core.database import AsyncSessionLocal
from app.core.config import settings


async def escalation_check_job():
    """Re-notify responders with unacknowledged critical alerts past the timeout."""
    from app.crud.system_settings import system_settings_crud
    from app.crud.notification_delivery import notification_delivery_crud
    from app.services import notification_service
    from app.schemas.subscription import SendNotificationSchema, CustomNotificationPayload
    from app.models.notification_template import NotificationType

    try:
        async with AsyncSessionLocal() as db:
            timeout = await system_settings_crud.get_value(db, "escalation_timeout_minutes")
            max_escalation = await system_settings_crud.get_value(db, "max_escalation_count")

            if not timeout or not max_escalation:
                return

            timeout = int(timeout)
            max_escalation = int(max_escalation)

            overdue = await notification_delivery_crud.get_unacknowledged_critical_past_threshold(
                db=db,
                timeout_minutes=timeout,
                max_escalation=max_escalation,
            )

            if not overdue:
                return

            # Group by responder to avoid duplicate notifications
            responder_ids_seen = set()
            deliveries_to_escalate = []

            for delivery in overdue:
                if delivery.responder_id not in responder_ids_seen:
                    responder_ids_seen.add(delivery.responder_id)
                    deliveries_to_escalate.append(delivery)

            if not deliveries_to_escalate:
                return

            responder_ids = list(responder_ids_seen)

            payload = SendNotificationSchema(
                responder_ids=responder_ids,
                template_id=None,
                custom_notification=CustomNotificationPayload(
                    type=NotificationType.CRITICAL,
                    title="Critical Alert - Escalation",
                    message="You have unacknowledged critical alerts. Please review and respond immediately.",
                ),
                system_initiated=True,
            )
            await notification_service.send_notification_to_subscribers(payload=payload, db=db)

            # Increment escalation count for all overdue deliveries
            for delivery in overdue:
                await notification_delivery_crud.increment_escalation_count(db=db, delivery_id=delivery.id)

            print(f"⚡ Escalated critical alerts to {len(responder_ids)} responder(s), {len(overdue)} delivery(ies) escalated")

    except Exception as e:
        print(f"⚠️ Escalation check failed: {e}")
