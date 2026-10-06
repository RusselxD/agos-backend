import asyncio
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
import pytest

from app.core.config import settings
from app.schemas.daily_summary import DailySummaryResponse
from app.schemas.reading_report import ReadingReportCreate
from app.services.reading_report.snapshot import make_snapshot
from app.services.reading_report.pdf import PDFRenderer, build_html, one_decimal

module = importlib.import_module("app.services.reading_report.service")


def summary(day="2026-09-01", **values):
    defaults = {name: None for name in DailySummaryResponse.model_fields}
    return DailySummaryResponse(**{**defaults, "summary_date": day, **values})


def request(**values):
    return ReadingReportCreate(request_id=uuid4(), location_id=1, start_date="2026-09-01", end_date=values.pop("end_date", "2026-09-03"), **values)


def report(rows=None, **values):
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    req = request()
    rows = rows or [summary(max_risk_score=0, max_water_level_cm=0, max_precipitation_mm=0, most_severe_blockage="clear")]
    return SimpleNamespace(id=uuid4(), created_by=uuid4(), request_id=req.request_id,
        location_id=1, start_date=req.start_date, end_date=req.end_date, created_at=now,
        expires_at=now+timedelta(days=30),
        snapshot=make_snapshot(SimpleNamespace(name="River <script>alert(1)</script>"), req, rows, 8),
        status=values.pop("status", "pending"), analysis_text=values.pop("analysis_text", ""),
        analysis_error=None, analysis_completed_at=now, analysis_started_at=now,
        analysis_model="test-model", prompt_version="1", template_version="1", pdf_content=values.pop("pdf_content", None), **values)


def result(value):
    return SimpleNamespace(scalar_one_or_none=lambda: value)


def test_snapshot_covers_gaps_zero_missing_values_and_immutable_order():
    req = request()
    rows = [summary("2026-09-03", max_risk_score=4, max_precipitation_mm=8, most_severe_blockage="blocked"), summary(max_risk_score=0, max_water_level_cm=0, max_precipitation_mm=0, most_severe_blockage="clear")]
    snapshot = make_snapshot(SimpleNamespace(name="River"), req, rows, 8)
    assert snapshot["missing_dates"] == ["2026-09-02"]
    assert snapshot["stats"]["avgDailyPeakPrecipitation"] == 4
    assert snapshot["stats"]["precipDays"] == 2
    assert snapshot["stats"]["highestRisk"] == {"value":4, "date":"2026-09-03"}
    assert snapshot["stats"]["peakWaterLevel"] == {"value":0, "date":"2026-09-01"}
    assert snapshot["stats"]["blockedDays"] == 1
    assert make_snapshot(SimpleNamespace(name="River"), req, list(reversed(rows)), 8)["data_hash"] == snapshot["data_hash"]
    rows[0].max_risk_score = 99
    assert snapshot["summaries"][1]["max_risk_score"] == 4
    assert make_snapshot(SimpleNamespace(name="River"), req, [summary()], 8)["stats"]["highestRisk"] is None


@pytest.mark.parametrize("end", ["2026-08-30", "2028-09-01", "2099-01-01"])
def test_range_limits(end):
    with pytest.raises(ValidationError):
        request(end_date=end)


def test_client_cannot_supply_authoritative_data():
    with pytest.raises(ValidationError):
        request(summaries=[])


async def test_create_loads_backend_data_and_reuses_request_id(monkeypatch):
    req = request()
    existing = report()
    db = SimpleNamespace(execute=AsyncMock(side_effect=[result(None),result(existing),result(existing)]), get=AsyncMock(return_value=SimpleNamespace(name="River")), add=Mock(), commit=AsyncMock(), refresh=AsyncMock())
    fetch = AsyncMock(return_value=[summary()])
    monkeypatch.setattr(module.daily_summary_service,"get_daily_summaries",fetch)
    created = await module.reading_report_service.create(db,req,existing.created_by)
    fetch.assert_awaited_once_with(db,1,req.start_date,req.end_date)
    assert created.snapshot["summaries"][0]["summary_date"] == "2026-09-01"
    assert created.created_by == existing.created_by
    existing.request_id = req.request_id
    reused = await module.reading_report_service.create(db,req,existing.created_by)
    assert reused is existing
    assert fetch.await_count == 1


async def test_idempotency_conflicts_do_not_read_new_data():
    existing = report()
    existing.location_id = 2
    db = SimpleNamespace(execute=AsyncMock(return_value=result(existing)))
    with pytest.raises(HTTPException) as exc:
        await module.reading_report_service.create(db,request(),existing.created_by)
    assert exc.value.status_code == 409


async def test_owner_and_expiry_are_required_by_lookup():
    owner, report_id = uuid4(),uuid4()
    db = SimpleNamespace(execute=AsyncMock(return_value=result(None)))
    with pytest.raises(HTTPException) as exc:
        await module.reading_report_service.get(db,report_id,owner)
    assert exc.value.status_code == 404
    query = db.execute.await_args.args[0]
    assert "created_by" in str(query) and "expires_at >" in str(query)
    assert owner in query.compile().params.values()
    assert report_id in query.compile().params.values()


async def test_generation_is_claimed_once_and_stale_slots_can_recover():
    item=report()
    db=SimpleNamespace(execute=AsyncMock(return_value=result(None)),commit=AsyncMock())
    with pytest.raises(HTTPException) as exc:
        await module.reading_report_service.claim_analysis(db,item)
    assert exc.value.status_code == 409
    query=db.execute.await_args.args[0]
    assert "analysis_started_at <" in str(query) and "expires_at >" in str(query)
    item.status="complete"
    assert await module.reading_report_service.claim_analysis(db,item) is None
    assert db.execute.await_count == 1


@pytest.mark.parametrize("terminal", ["complete","error","truncated"])
async def test_stream_saves_exact_text_before_terminal_and_blocks_partial_export(monkeypatch,terminal):
    item=report()
    service=module.ReadingReportService()
    saved=[]
    async def save(id,claim,**values):
        saved.append(values)
        for key,value in values.items(): setattr(item,key,value)
    service.save_analysis=save
    text="**Risk**\n- Water ↑ remains stable.\n"
    async def stream(payload):
        assert payload.summaries[0].max_risk_score == 0
        yield module.event({"text":text})
        if terminal=="complete": yield module.event({"done":True,"model":"test-model"})
        elif terminal=="error": yield module.event({"error":"provider failed","done":True})
    monkeypatch.setattr(module.analysis_service,"stream_analysis",stream)
    events=[]
    async for event in service.stream(item,item.analysis_started_at):
        parsed=json.loads(event[6:])
        if parsed.get("done"): assert saved
        events.append(parsed)
    assert saved[-1]["analysis_text"] == text
    if terminal=="complete":
        assert item.status == "complete"
        assert events[-1]=={"done":True,"report_id":str(item.id)}
        item.pdf_content=b"%PDF-cached"
        assert await service.pdf(item)==b"%PDF-cached"
    else:
        assert item.status == "error"
        assert events[-1]["error"]
        with pytest.raises(HTTPException) as exc: await service.pdf(item)
        assert exc.value.status_code == 409


async def test_cached_analysis_never_calls_provider(monkeypatch):
    item=report(status="complete",analysis_text="Saved exact result")
    provider=Mock(side_effect=AssertionError("should not be called"))
    monkeypatch.setattr(module.analysis_service,"stream_analysis",provider)
    events=[json.loads(event[6:]) async for event in module.reading_report_service.stream(item,None)]
    assert events[0]["text"]==item.analysis_text
    provider.assert_not_called()


async def test_cancel_marks_generation_retryable(monkeypatch):
    service=module.ReadingReportService()
    save=AsyncMock()
    service.save_analysis=save
    async def stream(payload):
        yield module.event({"text":"Partial"})
        await asyncio.sleep(10)
    monkeypatch.setattr(module.analysis_service,"stream_analysis",stream)
    item=report()
    generator=service.stream(item,item.analysis_started_at)
    await anext(generator)
    await generator.aclose()
    save.assert_awaited_once()
    assert save.await_args.kwargs["status"] == "error"


async def test_expiry_cleanup_removes_saved_pdfs_and_snapshots():
    db=SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(rowcount=2)),commit=AsyncMock())
    assert await module.reading_report_service.cleanup(db)==2
    assert "DELETE FROM reading_reports" in str(db.execute.await_args.args[0])
    assert "expires_at <=" in str(db.execute.await_args.args[0])
    db.commit.assert_awaited_once()


def test_print_document_is_escaped_and_contains_data_dates_and_timezone():
    item=report(status="complete",analysis_text="**Overview**\n- <img src='https://bad.test/a'> **steady**")
    document=build_html(item,item.created_at)
    assert "<script>alert(1)</script>" not in document
    assert "<img src=" not in document
    assert "&lt;script&gt;" in document and "&lt;img" in document
    assert "2026-09-01 to 2026-09-03" in document
    assert "2026-10-01 08:00:00" in document and "Asia/Manila" in document
    assert "2026-09-02, 2026-09-03" in document
    assert "Snapshot SHA-256" in document
    assert document.count('<svg ') == 4
    assert "counter(pages)" in document
    assert "<strong>steady</strong>" in document


async def test_missing_renderer_and_busy_renderer_return_retryable_errors(monkeypatch):
    renderer=PDFRenderer()
    monkeypatch.setattr(settings,"REPORT_CHROMIUM_EXECUTABLE_PATH","/nonexistent/chromium")
    with pytest.raises(HTTPException) as exc: await renderer.render(report(),datetime.now(timezone.utc))
    assert exc.value.status_code==503
    async with renderer._lock:
        with pytest.raises(HTTPException) as exc: await renderer.render(report(),datetime.now(timezone.utc))
        assert exc.value.headers["Retry-After"]=="10"


@pytest.mark.skipif(not os.environ.get("REPORT_TEST_CHROMIUM"),reason="Set REPORT_TEST_CHROMIUM for native PDF integration")
@pytest.mark.parametrize("days", [1, 31, 366])
async def test_native_pdf_render(monkeypatch,tmp_path,days):
    monkeypatch.setattr(settings,"REPORT_CHROMIUM_EXECUTABLE_PATH",os.environ["REPORT_TEST_CHROMIUM"])
    monkeypatch.setattr(settings,"REPORT_CHROMIUM_NO_SANDBOX",True)
    item=report(status="complete",analysis_text="**AI Overview**\n- All data included.\n"*70)
    item.start_date = date(2025, 1, 1)
    item.end_date = item.start_date + timedelta(days=days-1)
    rows = [summary((item.start_date+timedelta(days=i)).isoformat(),
                    max_risk_score=i%110 if i%2==0 else None, max_water_level_cm=i%40,
                    max_precipitation_mm=i%10, most_severe_blockage="clear",
                    min_risk_timestamp="2025-01-01T00:00:00Z") for i in range(days)]
    item.snapshot=make_snapshot(SimpleNamespace(name="Native test"), item, rows, 8)
    content=await PDFRenderer().render(item,item.created_at)
    assert content.startswith(b"%PDF-")
    path=tmp_path / "report.pdf"
    path.write_bytes(content)
    process=await asyncio.create_subprocess_exec("pdftotext",str(path),"-",stdout=asyncio.subprocess.PIPE)
    text=(await process.communicate())[0].decode()
    assert "All data included." in text
    assert item.start_date.isoformat() in text and item.end_date.isoformat() in text
    assert "Daily readings" in text and "Observation times" in text
    assert "2025-01-01 08:00:00" in text
    assert text.count("Risk score") >= days
    assert "Page 1 of" in text and "Asia/Manila" in text


async def test_export_returns_first_saved_artifact_and_expires_during_render(monkeypatch):
    item=report(status="complete",analysis_text="Saved exact overview")
    renderer_module=importlib.import_module("app.services.reading_report.pdf")
    render=AsyncMock(return_value=b"%PDF-new")
    monkeypatch.setattr(renderer_module.pdf_renderer,"render",render)
    db=SimpleNamespace(execute=AsyncMock(side_effect=[result(None),result(b"%PDF-first-render")]),commit=AsyncMock())
    @asynccontextmanager
    async def session(): yield db
    monkeypatch.setattr(module,"AsyncSessionLocal",session)
    assert await module.reading_report_service.pdf(item)==b"%PDF-first-render"
    update=db.execute.await_args_list[0].args[0]
    assert "pdf_content IS NULL" in str(update) and "expires_at >" in str(update)
    db.execute.side_effect=[result(None),result(None)]
    with pytest.raises(HTTPException) as exc: await module.reading_report_service.pdf(item)
    assert exc.value.status_code==410


async def test_renderer_timeout_kills_children_and_cleans_temporary_files(monkeypatch):
    renderer=PDFRenderer()
    monkeypatch.setattr(settings,"REPORT_CHROMIUM_EXECUTABLE_PATH","/bin/true")
    monkeypatch.setattr(settings,"REPORT_PDF_TIMEOUT_SECONDS",.01)
    process=SimpleNamespace(pid=99999999,wait=AsyncMock(return_value=0))
    monkeypatch.setattr(asyncio,"create_subprocess_exec",AsyncMock(return_value=process))
    killed=Mock()
    renderer_module=importlib.import_module("app.services.reading_report.pdf")
    monkeypatch.setattr(renderer_module.os,"killpg",killed)
    directories=[]
    async def wait_for_renderer(proc,root,document):
        directories.append(root)
        await asyncio.sleep(1)
    monkeypatch.setattr(renderer,"_print",wait_for_renderer)
    with pytest.raises(HTTPException) as exc: await renderer.render(report(),datetime.now(timezone.utc))
    assert exc.value.status_code==504
    killed.assert_called_once()
    process.wait.assert_awaited_once()
    assert not directories[0].exists()


def test_card_rounding_matches_admin_number_to_fixed():
    assert one_decimal(2.25) == "2.3"
    assert one_decimal(2.55) == "2.5"
    assert one_decimal(0) == "0.0"
