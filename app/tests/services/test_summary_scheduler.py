import importlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.config import settings

scheduler_module = importlib.import_module("app.core.scheduler")
services = importlib.import_module("app.services")


def test_backfill_runs_at_local_half_past_midnight_before_cleanup(monkeypatch):
    scheduler = Mock()
    monkeypatch.setattr(scheduler_module, "scheduler", scheduler)
    scheduler_module.start_scheduler()
    jobs = {call.kwargs["id"]: call for call in scheduler.add_job.call_args_list}
    after_midnight = datetime(2026, 10, 6, 0, 1, tzinfo=settings.APP_TIMEZONE)
    backfill = jobs["daily_summary_backfill_job"]
    assert backfill.args[0] is scheduler_module.daily_summary_backfill_job
    trigger = backfill.args[1]
    next_run = trigger.get_next_fire_time(None, after_midnight)
    assert next_run == datetime(2026, 10, 6, 0, 30, tzinfo=settings.APP_TIMEZONE)
    assert next_run.astimezone(timezone.utc) < jobs["data_cleanup_job"].args[1].get_next_fire_time(None, after_midnight)
    assert backfill.kwargs["max_instances"] == 1
    scheduler.start.assert_called_once()


@pytest.mark.parametrize("failure", [False, True])
async def test_scheduled_backfill_uses_retention_and_logs_failure(monkeypatch, caplog, failure):
    db = object()

    @asynccontextmanager
    async def session():
        yield db

    monkeypatch.setattr(scheduler_module, "AsyncSessionLocal", session)
    backfill = AsyncMock(return_value=2, side_effect=RuntimeError("offline") if failure else None)
    monkeypatch.setattr(services.daily_summary_service, "backfill_missing_summaries", backfill)
    await scheduler_module.daily_summary_backfill_job()
    backfill.assert_awaited_once_with(db)
    if failure:
        assert "Daily summary backfill failed" in caplog.text
