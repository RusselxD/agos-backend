class SMSService():

    async def send_one_sms(self, phone_number: str, message: str) -> bool:
        # Placeholder for actual SMS sending logic
        print(f"Sending SMS to {phone_number}: {message}")
        return True


sms_service = SMSService()