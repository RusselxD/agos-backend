from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import importlib

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.schemas.system_settings import AlertThresholdsResponse
from app.services.daily_summary.summary_generator import (
    calculate_risk_scores, smooth_model_readings, extract_model_readings_summary,
)

service_module = importlib.import_module("app.services.daily_summary.service")
START = datetime(2026, 10, 5, 16, tzinfo=timezone.utc)  # Oct 6 midnight in Manila
THRESHOLDS = AlertThresholdsResponse(tier_1_max=39, tier_2_min=40, tier_2_max=69, tier_3_min=70)


def sensor(minutes, level):
    return SimpleNamespace(timestamp=START + timedelta(minutes=minutes), water_level_cm=level)


def camera(minutes, status, percentage=80):
    return SimpleNamespace(timestamp=START + timedelta(minutes=minutes), blockage_status=status, blockage_percentage=percentage)


def weather(minutes, precipitation):
    return SimpleNamespace(created_at=START + timedelta(minutes=minutes), precipitation_mm=precipitation, weather_code=65)


def scores(sensors=(), models=(), weather_readings=()):
    return calculate_risk_scores(list(sensors), list(models), list(weather_readings), 100, THRESHOLDS, START)


def test_rising_water_bonus_uses_previous_day_reading():
    result = scores([sensor(-1, 55), sensor(0, 60)])
    assert result["min_risk_score"] == result["max_risk_score"] == 25
    assert result["min_risk_timestamp"] == START


@pytest.mark.parametrize(
    "previous_level, level, status, precipitation, expected",
    [
        (93, 95, "clear", 0, 0),      # suspect critical sensor: suppress water and rising bonus
        (95, 95, "clear", 10, 20),    # frozen sensor during heavy rain: weather only
        (20, 22, "blocked", 10, 35),  # blind camera: water + rising + weather, suppress camera
        (55, 60, "partial", 1, 53),   # normal contributions + rising bonus
    ],
)
def test_historical_risk_uses_live_anomaly_and_scoring_rules(
    previous_level, level, status, precipitation, expected,
):
    result = scores(
        [sensor(-2, previous_level), sensor(0, level)],
        [camera(-1, status)], [weather(-1, precipitation)],
    )
    assert result["max_risk_score"] == expected
    assert result["min_risk_score"] == expected


def test_future_weather_is_not_used_and_weather_updates_can_set_peak_risk():
    result = scores([sensor(-1, 55), sensor(0, 60)], weather_readings=[weather(1, 10)])
    assert result["min_risk_score"] == 25
    assert result["max_risk_score"] == 45
    assert result["max_risk_timestamp"] == START + timedelta(minutes=1)


def test_stale_sources_are_excluded_from_risk():
    result = scores([sensor(0, 60)], [camera(-30, "blocked")], [weather(-180, 10)])
    assert result["max_risk_score"] == 20


def test_no_daily_events_leaves_risk_missing():
    assert scores() == {}
    assert scores([sensor(-1, 60)], [camera(-1, "blocked")], [weather(-1, 10)]) == {}


def test_camera_smoothing_cold_start_and_midnight_context(monkeypatch):
    monkeypatch.setattr(settings, "OBSTRUCTION_WINDOW_K", 5)
    monkeypatch.setattr(settings, "OBSTRUCTION_TIER_LIKELY", 0.6)
    monkeypatch.setattr(settings, "OBSTRUCTION_TIER_CONFIRMED", 0.8)
    lone = smooth_model_readings([camera(0, "blocked")])
    assert lone[0].blockage_status == "partial"
    readings = [camera(i, "blocked") for i in range(-4, 1)]
    smoothed = smooth_model_readings(readings)
    assert smoothed[-1].blockage_status == "blocked"
    assert readings[-1].blockage_status == "blocked"  # raw evidence remains intact
    assert extract_model_readings_summary(lone)["most_severe_blockage"] == "partial"


@pytest.fixture
def backfill_setup(monkeypatch):
    service = service_module.DailySummaryService()
    db = SimpleNamespace(rollback=AsyncMock())
    monkeypatch.setattr(service_module.cache_service, "get_all_location_ids", AsyncMock(return_value=[1]))
    lookup = AsyncMock(return_value=None)
    create = AsyncMock()
    monkeypatch.setattr(service_module.daily_summary_crud, "get_by_location_and_date", lookup)
    monkeypatch.setattr(service_module.daily_summary_crud, "create_daily_summary", create)
    generate = AsyncMock(return_value={"max_risk_score": 25})
    monkeypatch.setattr(service, "generate_summary_for_location", generate)
    return service, db, lookup, create, generate


async def test_backfill_skips_existing_and_empty_days(backfill_setup):
    service, db, lookup, create, generate = backfill_setup
    lookup.side_effect = [object(), None, None]
    generate.side_effect = [{}, {"max_risk_score": 25}]
    assert await service.backfill_missing_summaries(db, days=3) == 1
    assert lookup.await_count == 3
    assert generate.await_count == 2
    create.assert_awaited_once()
    target_dates = [call.args[2] for call in lookup.await_args_list]
    today = datetime.now(settings.APP_TIMEZONE).date()
    assert target_dates == [today - timedelta(days=i) for i in (1, 2, 3)]


async def test_backfill_reads_retention_on_every_run(backfill_setup, monkeypatch):
    service, db, lookup, create, generate = backfill_setup
    retention = AsyncMock(side_effect=[30, 2])
    monkeypatch.setattr(service_module.system_settings_crud, "get_value", retention)
    lookup.return_value = object()  # Existing summaries must never be rewritten.
    today = datetime.now(settings.APP_TIMEZONE).date()

    assert await service.backfill_missing_summaries(db) == 0
    assert lookup.await_count == 30
    assert lookup.await_args_list[-1].args[2] == today - timedelta(days=30)
    lookup.reset_mock()

    assert await service.backfill_missing_summaries(db) == 0
    assert lookup.await_count == 2
    assert lookup.await_args_list[-1].args[2] == today - timedelta(days=2)
    assert retention.await_count == 2
    retention.assert_awaited_with(db, "data_retention_days")
    generate.assert_not_awaited()
    create.assert_not_awaited()


@pytest.mark.parametrize("error", [RuntimeError("query failed"), IntegrityError("insert", {}, Exception("duplicate"))])
async def test_backfill_rolls_back_and_continues_after_failure(backfill_setup, error):
    service, db, lookup, create, generate = backfill_setup
    create.side_effect = [error, None]
    assert await service.backfill_missing_summaries(db, days=2) == 1
    db.rollback.assert_awaited_once()
    assert create.await_count == 2


async def test_empty_source_day_does_not_create_summary(monkeypatch):
    service = service_module.DailySummaryService()
    result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))
    db = SimpleNamespace(execute=AsyncMock(return_value=result))
    monkeypatch.setattr(service_module.cache_service, "get_device_ids_per_location", AsyncMock(return_value=SimpleNamespace(sensor_device_id=None, camera_device_id=None)))
    monkeypatch.setattr(service_module.cache_service, "get_sensor_config", AsyncMock(return_value=SimpleNamespace(critical_threshold=100)))
    assert await service.generate_summary_for_location(db, 1, START.date()) == {}


async def test_summary_queries_local_day_and_carries_pre_midnight_context(monkeypatch):
    service = service_module.DailySummaryService()
    # Descending context queries return newest first.
    results = [
        [sensor(0, 60)], [sensor(-1, 55), sensor(-2, 54)],
        [camera(0, "blocked")], [camera(i, "blocked") for i in range(-1, -6, -1)],
        [weather(1, 1)], [weather(-1, 0)],
    ]
    db = SimpleNamespace(execute=AsyncMock(side_effect=[
        SimpleNamespace(scalars=lambda rows=rows: SimpleNamespace(all=lambda: rows)) for rows in results
    ]))
    monkeypatch.setattr(service_module.cache_service, "get_device_ids_per_location", AsyncMock(return_value=SimpleNamespace(sensor_device_id=1, camera_device_id=1)))
    monkeypatch.setattr(service_module.cache_service, "get_sensor_config", AsyncMock(return_value=SimpleNamespace(critical_threshold=100)))
    monkeypatch.setattr(service_module.cache_service, "get_alert_thresholds", AsyncMock(return_value=THRESHOLDS))
    monkeypatch.setattr(settings, "OBSTRUCTION_WINDOW_K", 5)
    result = await service.generate_summary_for_location(db, 1, datetime(2026, 10, 6).date())
    assert result["min_water_level_cm"] == 60  # exclude preceding day's 54 and 55
    assert result["most_severe_blockage"] == "blocked"
    assert result["min_risk_timestamp"] >= START
    first_query = db.execute.await_args_list[0].args[0].compile().params
    assert START in first_query.values()
    assert START + timedelta(days=1) in first_query.values()
