import asyncio
import logging
import httpx
from app.core.config import settings
from app.core.exceptions import SMSGatewayUnavailableError, SMSDeliveryError

logger = logging.getLogger(__name__)


class SMSService():

    def _get_client(self) -> httpx.AsyncClient:
        username, password = settings.SMS_GATEWAY_API_KEY.split(":", 1)
        return httpx.AsyncClient(
            base_url=settings.SMS_GATEWAY_URL,
            timeout=settings.SMS_GATEWAY_TIMEOUT_SECONDS,
            auth=httpx.BasicAuth(username, password),
        )

    async def send_one_sms(self, phone_number: str, message: str) -> None:
        if not settings.SMS_GATEWAY_URL:
            logger.warning(f"SMS gateway not configured. Would send to {phone_number}: {message}")
            return

        async with self._get_client() as client:
            try:
                is_cloud = "sms-gate.app" in settings.SMS_GATEWAY_URL
                endpoint = "/3rdparty/v1/message" if is_cloud else "/message"

                response = await client.post(
                    endpoint,
                    json={
                        "phoneNumbers": [phone_number],
                        "message": message,
                    },
                )
            except httpx.ConnectError:
                raise SMSGatewayUnavailableError(
                    "SMS gateway is unreachable. Ensure the Android phone is online and the SMS Gateway app is running."
                )
            except httpx.TimeoutException:
                raise SMSGatewayUnavailableError(
                    "SMS gateway timed out. The Android phone may be unresponsive."
                )

            if response.status_code >= 500:
                raise SMSDeliveryError(
                    f"SMS gateway error (HTTP {response.status_code}). The phone may have no load or SIM issues."
                )

            if response.status_code >= 400:
                detail = response.text
                raise SMSDeliveryError(f"SMS delivery failed: {detail}")

            logger.info(f"SMS sent to {phone_number}")

    async def send_bulk_sms(self, phone_numbers: list[str], message: str) -> dict:
        """Returns {"succeeded": [...], "failed": [...]} for partial failure reporting."""
        succeeded = []
        failed = []

        for phone_number in phone_numbers:
            try:
                await self.send_one_sms(phone_number=phone_number, message=message)
                succeeded.append(phone_number)
            except (SMSGatewayUnavailableError, SMSDeliveryError) as e:
                logger.error(f"SMS to {phone_number} failed: {e}")
                failed.append({"phone_number": phone_number, "error": str(e)})

            if len(phone_numbers) > 1:
                await asyncio.sleep(settings.SMS_BULK_DELAY_SECONDS)

        return {"succeeded": succeeded, "failed": failed}


sms_service = SMSService()
