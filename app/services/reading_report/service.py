"""Persist snapshots, stream their analysis, and export only completed reports."""
import asyncio
import json
import logging
from contextlib import aclosing
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import defer

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.data_sources.location import Location
from app.models.reading_report import ReadingReport
from app.schemas.daily_summary import DailySummaryAnalysisRequest, DailySummaryResponse
from app.schemas.reading_report import ReadingReportResponse
from app.services.analysis_service import analysis_service
from app.services.daily_summary.service import daily_summary_service
from .snapshot import make_snapshot

logger = logging.getLogger(__name__)


def utcnow():
    return datetime.now(timezone.utc)


def event(payload):
    return f"data: {json.dumps(payload)}\n\n"


def as_response(report):
    snapshot = report.snapshot
    return ReadingReportResponse(
        id=report.id, location_id=report.location_id, location_name=snapshot["location_name"],
        start_date=report.start_date, end_date=report.end_date, created_at=report.created_at,
        expires_at=report.expires_at, timezone=snapshot["timezone"], utc_offset_hours=snapshot["utc_offset_hours"],
        summaries=snapshot["summaries"], missing_dates=snapshot["missing_dates"], status=report.status,
        analysis_text=report.analysis_text, analysis_error=report.analysis_error,
        analysis_completed_at=report.analysis_completed_at, analysis_model=report.analysis_model,
        data_hash=snapshot["data_hash"], stats=snapshot["stats"],
    )


class ReadingReportService:
    async def get(self, db, report_id, owner_id, *, include_pdf=False):
        query = select(ReadingReport)
        if not include_pdf:
            query = query.options(defer(ReadingReport.pdf_content))
        report = (await db.execute(query.where(
            ReadingReport.id == report_id, ReadingReport.created_by == UUID(str(owner_id)),
            ReadingReport.expires_at > utcnow(),
        ))).scalar_one_or_none()
        if not report:
            raise HTTPException(404, "Report not found or expired")
        return report

    async def create(self, db, request, owner_id):
        owner = UUID(str(owner_id))
        existing = (await db.execute(select(ReadingReport).options(defer(ReadingReport.pdf_content)).where(
            ReadingReport.created_by == owner, ReadingReport.request_id == request.request_id,
        ))).scalar_one_or_none()
        if existing:
            if (existing.location_id, existing.start_date, existing.end_date) != (request.location_id, request.start_date, request.end_date):
                raise HTTPException(409, "Request ID already used for a different report")
            return await self.get(db, existing.id, owner)
        location = await db.get(Location, request.location_id)
        if not location:
            raise HTTPException(404, "Location not found")
        summaries = await daily_summary_service.get_daily_summaries(db, request.location_id, request.start_date, request.end_date)
        if not summaries:
            raise HTTPException(422, "No daily summaries are available for this period")
        now = utcnow()
        report = ReadingReport(
            request_id=request.request_id, created_by=owner, location_id=request.location_id,
            start_date=request.start_date, end_date=request.end_date, created_at=now,
            expires_at=now + timedelta(days=settings.REPORT_RETENTION_DAYS),
            snapshot=make_snapshot(location, request, summaries, settings.UTC_OFFSET_HOURS),
            status="pending", analysis_text="", prompt_version="1", template_version="1",
        )
        db.add(report)
        try:
            await db.commit()
            await db.refresh(report)
        except IntegrityError:
            await db.rollback()
            existing = (await db.execute(select(ReadingReport).options(defer(ReadingReport.pdf_content)).where(
                ReadingReport.created_by == owner, ReadingReport.request_id == request.request_id,
            ))).scalar_one_or_none()
            if not existing:
                raise
            if (existing.location_id, existing.start_date, existing.end_date) != (request.location_id, request.start_date, request.end_date):
                raise HTTPException(409, "Request ID already used for a different report")
            report = await self.get(db, existing.id, owner)
        return report

    async def claim_analysis(self, db, report):
        if report.status == "complete":
            return None
        now = utcnow()
        stale = now - timedelta(seconds=settings.REPORT_ANALYSIS_TIMEOUT_SECONDS + 30)
        result = await db.execute(update(ReadingReport).where(
            ReadingReport.id == report.id, ReadingReport.expires_at > now,
            or_(ReadingReport.status.in_(["pending", "error"]),
                (ReadingReport.status == "streaming") & (ReadingReport.analysis_started_at < stale)),
        ).values(status="streaming", analysis_started_at=now, analysis_error=None, analysis_text="").returning(ReadingReport.id))
        claimed = result.scalar_one_or_none()
        await db.commit()
        if not claimed:
            raise HTTPException(409, "This report is already being analyzed. Please retry shortly.")
        return now

    async def save_analysis(self, report_id, claim, **values):
        async with AsyncSessionLocal() as db:
            result = await db.execute(update(ReadingReport).where(
                ReadingReport.id == report_id, ReadingReport.analysis_started_at == claim,
                ReadingReport.status == "streaming",
            ).values(**values).returning(ReadingReport.id))
            saved = result.scalar_one_or_none()
            await db.commit()
            if not saved:
                raise RuntimeError("Report analysis no longer owns its generation slot")

    async def stream(self, report, claim):
        if claim is None:
            yield event({"text": report.analysis_text})
            yield event({"done": True, "report_id": str(report.id)})
            return
        chunks = []
        completed = False
        error_message = "AI analysis was interrupted. Please try again."
        try:
            payload = DailySummaryAnalysisRequest(
                start_date=report.start_date, end_date=report.end_date,
                summaries=[DailySummaryResponse.model_validate(row) for row in report.snapshot["summaries"]],
            )
            async with asyncio.timeout(settings.REPORT_ANALYSIS_TIMEOUT_SECONDS), aclosing(analysis_service.stream_analysis(payload)) as source:
                async for chunk in source:
                    data = json.loads(chunk.removeprefix("data: ").strip())
                    if data.get("error"):
                        error_message = data["error"]
                        break
                    if data.get("text"):
                        chunks.append(data["text"])
                        yield event({"text": data["text"]})
                    if data.get("done"):
                        text = "".join(chunks)
                        if not text.strip():
                            break
                        await self.save_analysis(report.id, claim, status="complete", analysis_text=text,
                            analysis_model=data.get("model"), analysis_completed_at=utcnow(), analysis_error=None)
                        completed = True
                        yield event({"done": True, "report_id": str(report.id)})
                        return
        except (asyncio.CancelledError, GeneratorExit):
            raise
        except Exception:
            logger.exception("Report analysis failed for report %s", report.id)
        finally:
            if not completed:
                try:
                    await asyncio.shield(self.save_analysis(report.id, claim, status="error",
                        analysis_text="".join(chunks), analysis_error=error_message))
                except Exception:
                    logger.exception("Could not save report analysis failure for %s", report.id)
        yield event({"error": error_message, "done": True})

    async def pdf(self, report):
        if report.status != "complete" or not report.analysis_text.strip():
            raise HTTPException(409, "Finish the AI analysis before downloading the report")
        if report.pdf_content:
            return report.pdf_content
        from .pdf import pdf_renderer
        generated_at = utcnow()
        content = await pdf_renderer.render(report, generated_at)
        async with AsyncSessionLocal() as db:
            # The first successful export becomes the stable downloadable artifact.
            await db.execute(update(ReadingReport).where(
                ReadingReport.id == report.id, ReadingReport.pdf_content.is_(None),
                ReadingReport.expires_at > utcnow(),
            ).values(pdf_content=content, pdf_created_at=generated_at))
            await db.commit()
            saved = (await db.execute(select(ReadingReport.pdf_content).where(ReadingReport.id == report.id, ReadingReport.expires_at > utcnow()))).scalar_one_or_none()
            if not saved:
                raise HTTPException(410, "Report expired while the PDF was being generated")
            return saved

    async def cleanup(self, db):
        result = await db.execute(delete(ReadingReport).where(ReadingReport.expires_at <= utcnow()))
        await db.commit()
        return result.rowcount


reading_report_service = ReadingReportService()
