from uuid import UUID
from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.rate_limiter import limiter
from app.schemas.reading_report import ReadingReportCreate, ReadingReportResponse
from app.services.reading_report.service import reading_report_service, as_response


from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.schemas import DailySummaryAnalysisRequest
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


@router.post("/reports", response_model=ReadingReportResponse, status_code=201)
@limiter.limit("6/minute")
async def create_reading_report(
    request: Request, payload: ReadingReportCreate,
    db: AsyncSession = Depends(get_db), current_user=Depends(require_auth),
):
    return as_response(await reading_report_service.create(db, payload, current_user.id))


@router.get("/reports/{report_id}", response_model=ReadingReportResponse)
async def get_reading_report(
    report_id: UUID, db: AsyncSession = Depends(get_db), current_user=Depends(require_auth),
):
    return as_response(await reading_report_service.get(db, report_id, current_user.id))


@router.post("/reports/{report_id}/stream")
@limiter.limit("6/minute")
async def analyze_reading_report(
    request: Request, report_id: UUID,
    db: AsyncSession = Depends(get_db), current_user=Depends(require_auth),
):
    report = await reading_report_service.get(db, report_id, current_user.id)
    claim = await reading_report_service.claim_analysis(db, report)
    # Release the request's DB connection before waiting on the provider.
    await db.commit()
    return StreamingResponse(
        reading_report_service.stream(report, claim), media_type="text/event-stream",
        headers={"Cache-Control": "private, no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/reports/{report_id}/pdf")
@limiter.limit("10/minute")
async def download_reading_report(
    request: Request, report_id: UUID,
    db: AsyncSession = Depends(get_db), current_user=Depends(require_auth),
):
    report = await reading_report_service.get(db, report_id, current_user.id, include_pdf=True)
    await db.commit()
    content = await reading_report_service.pdf(report)
    filename = f"AGOS_Reading_Report_{report.start_date}_to_{report.end_date}.pdf"
    return Response(content, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
    })
