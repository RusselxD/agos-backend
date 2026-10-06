import importlib
from unittest.mock import AsyncMock, Mock
from types import SimpleNamespace

main = importlib.import_module("app.main")
services = importlib.import_module("app.services")


async def test_startup_starts_scheduler_without_running_backfill(monkeypatch):
    monkeypatch.setattr(main, "init_cloudinary", Mock())
    monkeypatch.setattr(main.weather_service, "start", AsyncMock())
    monkeypatch.setattr(main.weather_service, "stop", AsyncMock())
    monkeypatch.setattr(main.fusion_state_manager, "start_all_states", AsyncMock())
    backfill = AsyncMock()
    monkeypatch.setattr(services.daily_summary_service, "backfill_missing_summaries", backfill)
    start = Mock()
    stop = Mock()
    monkeypatch.setattr(main, "start_scheduler", start)
    monkeypatch.setattr(main, "shutdown_scheduler", stop)
    monkeypatch.setattr(main, "engine", SimpleNamespace(dispose=AsyncMock()))
    async with main.lifespan(main.app):
        backfill.assert_not_awaited()
        start.assert_called_once()
    stop.assert_called_once()
