class SMSError(Exception):
    """Base exception for SMS-related errors."""
    pass


class SMSGatewayUnavailableError(SMSError):
    """Raised when the Android SMS gateway is unreachable (phone off, network issue)."""
    pass


class SMSDeliveryError(SMSError):
    """Raised when the gateway accepted the request but SMS delivery failed."""
    pass
