from pydantic import BaseModel


class CitizenSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class CitizenSubscriptionCreate(BaseModel):
    """F4/F6 — anonymous citizen Web Push subscription (no PII)."""
    location_id: int
    endpoint: str
    keys: CitizenSubscriptionKeys


class CitizenSubscriptionDelete(BaseModel):
    location_id: int
    endpoint: str
