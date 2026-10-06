from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
import importlib

import pytest
from httpx import ASGITransport, AsyncClient

from fastapi import FastAPI
from app.api.v1.dependencies import require_auth
from app.core.database import get_db

endpoint = importlib.import_module("app.api.v1.endpoints.daily_summary")
app = FastAPI()
app.include_router(endpoint.router, prefix="/api/v1")


@pytest.fixture
def summary_api(monkeypatch):
    async def db():
        yield object()

    async def auth():
        return SimpleNamespace(id="admin")

    app.dependency_overrides[require_auth] = auth
    app.dependency_overrides[get_db] = db
    fetch = AsyncMock(return_value=[])
    monkeypatch.setattr(endpoint.daily_summary_service, "get_daily_summaries", fetch)
    monkeypatch.setattr(endpoint.daily_summary_service, "get_available_summary_days", AsyncMock(return_value=[date(2026, 10, 5)]))
    yield fetch
    app.dependency_overrides.pop(require_auth, None)
    app.dependency_overrides.pop(get_db, None)


async def test_date_contract_and_reversed_range(summary_api):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        days = await client.get("/api/v1/daily-summaries/available-days/1")
        assert days.json() == ["2026-10-05"]
        response = await client.get("/api/v1/daily-summaries", params={
            "location_id": 1, "start_date": "2026-10-01", "end_date": "2026-10-05",
        })
        assert response.status_code == 200
        assert summary_api.await_args.kwargs["start_date"] == date(2026, 10, 1)
        bad = await client.get("/api/v1/daily-summaries", params={
            "location_id": 1, "start_date": "2026-10-05", "end_date": "2026-10-01",
        })
        assert bad.status_code == 422
        assert summary_api.await_count == 1
