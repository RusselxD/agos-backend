from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.schemas import DailySummaryAnalysisRequest, FollowUpRequest
from app.api.v1.dependencies import require_auth
from app.services import analysis_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/daily-summaries", dependencies=[Depends(require_auth)])
async def analyze_daily_summaries(
    payload: DailySummaryAnalysisRequest
):
    return StreamingResponse(
        analysis_service.stream_analysis(payload=payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/follow-up")
async def follow_up(
    payload: FollowUpRequest,
    _: None = Depends(require_auth),
):
    return StreamingResponse(
        analysis_service.stream_follow_up(payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )