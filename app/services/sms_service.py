class SMSService():

    async def send_one_sms(self, phone_number: str, message: str) -> bool:
        # Placeholder for actual SMS sending logic
        print(f"Sending SMS to {phone_number}: {message}")
        return True


    async def send_bulk_sms(self, phone_numbers: list[str], message: str) -> bool:
        # Placeholder for actual bulk SMS sending logic
        # In production, this would batch send to an SMS provider
        for phone_number in phone_numbers:
            print(f"Sending SMS to {phone_number}: {message}")
        return True


sms_service = SMSService()