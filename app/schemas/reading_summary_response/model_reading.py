from .reading_summary_response import ReadingSummaryResponse
from app.schemas.fusion_analysis import ObstructionConfidence

class ModelWebSocketResponse(ReadingSummaryResponse):
    blockage_status: str | None  # "clear", "partial", "blocked"
    confidence: ObstructionConfidence | None = None  # F1 (additive)