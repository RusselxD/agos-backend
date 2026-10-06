import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
import pytest

from app.api.v1.dependencies import require_auth
from app.core.database import get_db
from app.core.rate_limiter import limiter
from app.tests.services.test_reading_report import report

endpoint=importlib.import_module("app.api.v1.endpoints.analysis")


@pytest.fixture
def report_api(monkeypatch):
    app=FastAPI()
    app.state.limiter=limiter
    app.include_router(endpoint.router,prefix="/api/v1")
    owner=uuid4()
    db=SimpleNamespace(commit=AsyncMock())
    async def database(): yield db
    async def auth(): return SimpleNamespace(id=str(owner))
    app.dependency_overrides[get_db]=database
    app.dependency_overrides[require_auth]=auth
    service=SimpleNamespace(create=AsyncMock(return_value=report()),get=AsyncMock(return_value=report(status="complete",analysis_text="Complete")),claim_analysis=AsyncMock(return_value=None),pdf=AsyncMock(return_value=b"%PDF-test"))
    async def stream(item,claim):
        yield 'data: {"text":"Complete"}\n\n'
        yield 'data: {"done":true}\n\n'
    service.stream=stream
    monkeypatch.setattr(endpoint,"reading_report_service",service)
    yield app,service,owner,db


async def test_create_pdf_and_stream_contract(report_api):
    app,service,owner,db=report_api
    async with AsyncClient(transport=ASGITransport(app=app),base_url="http://test") as client:
        body={"request_id":str(uuid4()),"location_id":1,"start_date":"2026-09-01","end_date":"2026-09-03"}
        created=await client.post("/api/v1/analysis/reports",json=body)
        assert created.status_code==201, created.text
        assert created.json()["stats"]["peakWaterLevel"]["value"]==0
        assert service.create.await_args.args[2]==str(owner)
        path=f'/api/v1/analysis/reports/{created.json()["id"]}'
        streamed=await client.post(path+"/stream")
        assert streamed.status_code==200 and '"done":true' in streamed.text
        assert streamed.headers["cache-control"]=="private, no-store"
        pdf=await client.get(path+"/pdf")
        assert pdf.content==b"%PDF-test"
        assert pdf.headers["content-type"]=="application/pdf"
        assert "2026-09-01_to_2026-09-03.pdf" in pdf.headers["content-disposition"]
        assert pdf.headers["cache-control"]=="private, no-store"
        assert db.commit.await_count==2
        bad=await client.post("/api/v1/analysis/reports",json={**body,"summaries":[]})
        assert bad.status_code==422


async def test_non_owner_cannot_get_stream_or_download(report_api):
    app,service,owner,_=report_api
    service.get.side_effect=HTTPException(404,"Report not found or expired")
    async with AsyncClient(transport=ASGITransport(app=app),base_url="http://test") as client:
        path=f"/api/v1/analysis/reports/{uuid4()}"
        for method,suffix in ((client.get,""),(client.post,"/stream"),(client.get,"/pdf")):
            response=await method(path+suffix)
            assert response.status_code==404
            assert service.get.await_args.args[2]==str(owner)
    service.claim_analysis.assert_not_awaited()
    service.pdf.assert_not_awaited()


async def test_routes_require_authentication(report_api):
    app,service,_,_=report_api
    app.dependency_overrides.pop(require_auth)
    async with AsyncClient(transport=ASGITransport(app=app),base_url="http://test") as client:
        response=await client.get(f"/api/v1/analysis/reports/{uuid4()}/pdf")
        assert response.status_code in (401,403)
    service.get.assert_not_awaited()
