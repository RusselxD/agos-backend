from app.schemas.fusion_analysis import FusionAnalysisData
from .reading_summary_response import ReadingSummaryResponse

class FusionWebSocketResponse(ReadingSummaryResponse):
    fusion_analysis: FusionAnalysisData | None = None