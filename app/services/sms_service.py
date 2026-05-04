import asyncio
import logging
import httpx
from app.core.config import settings

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
        logger.info(f"SMS to {phone_number}: {message}")

        if not settings.SMS_GATEWAY_URL:
            return

        try:
            async with self._get_client() as client:
                is_cloud = "sms-gate.app" in settings.SMS_GATEWAY_URL
                endpoint = "/3rdparty/v1/message" if is_cloud else "/message"
                response = await client.post(
                    endpoint,
                    json={"phoneNumbers": [phone_number], "message": message},
                )
                if response.status_code >= 400:
                    logger.warning(
                        f"SMS gateway returned HTTP {response.status_code} ({response.text}) for {phone_number}"
                    )
        except Exception as e:
            logger.warning(f"SMS gateway error for {phone_number}: {e}")

    async def send_bulk_sms(self, phone_numbers: list[str], message: str) -> dict:
        """Returns {"succeeded": [...], "failed": []} — failures are logged, not surfaced."""
        for phone_number in phone_numbers:
            await self.send_one_sms(phone_number=phone_number, message=message)
            if len(phone_numbers) > 1:
                await asyncio.sleep(settings.SMS_BULK_DELAY_SECONDS)

        return {"succeeded": list(phone_numbers), "failed": []}


sms_service = SMSService()
