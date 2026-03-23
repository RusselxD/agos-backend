from pydantic import BaseModel


class TypeBreakdown(BaseModel):
    type: str
    total: int
    acknowledged: int
    avg_response_time_seconds: float | None = None


class ResponderRanking(BaseModel):
    responder_id: str
    first_name: str
    last_name: str
    avg_response_time_seconds: float
    total_acknowledged: int


class NotificationAnalyticsResponse(BaseModel):
    total_sent: int
    total_acknowledged: int
    acknowledgement_rate: float
    avg_response_time_seconds: float | None = None
    per_type_breakdown: list[TypeBreakdown]
    top_responders: list[ResponderRanking]
