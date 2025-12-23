from .reading_summary_response import ReadingSummaryResponse

class ModelReadingSummary(ReadingSummaryResponse):
    blockage_status: str | None  # "clear", "partial", "blocked"