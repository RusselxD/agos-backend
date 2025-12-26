from .reading_summary_response import ReadingSummaryResponse

class ModelWebSocketResponse(ReadingSummaryResponse):
    blockage_status: str | None  # "clear", "partial", "blocked"