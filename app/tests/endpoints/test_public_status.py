from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.core.state import fusion_state_manager
from app.services.camera_status_service import camera_status_service
from app.schemas import (
    FusionAnalysisData,
    FusionData,
    WaterLevelStatus,
    WeatherStatus,
)


@pytest.mark.asyncio
async def test_public_status_maps_critical_to_high_risk(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    older = datetime.now(timezone.utc) - timedelta(minutes=5)
    newest = older + timedelta(minutes=3)
    snapshot = FusionAnalysisData(
        fusion_data=FusionData(
            alert_name="Critical",
            combined_risk_score=75,
            triggered_conditions=["Water level is high."],
        ),
        blockage_status=None,
        water_level_status=WaterLevelStatus(
            timestamp=older,
            water_level_cm=176,
            change_rate=2,
            critical_percentage=92,
            trend="rising",
        ),
        weather_status=WeatherStatus(
            timestamp=newest,
            precipitation_mm=8,
            weather_condition="Heavy rain",
        ),
    )
    monkeypatch.setattr(
        fusion_state_manager,
        "get_fusion_analysis_state",
        lambda location_id: snapshot,
    )

    response = await async_client.get(
        "/api/v1/public/status", params={"location_id": 1}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["level"] == "high_risk"
    assert body["updated_at"] == newest.isoformat().replace("+00:00", "Z")
    assert body["fusion_analysis"]["fusion_data"]["alert_name"] == "Critical"


@pytest.mark.asyncio
async def test_public_status_returns_unknown_before_state_is_ready(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    def missing_state(location_id: int):
        raise ValueError(f"No state for {location_id}")

    monkeypatch.setattr(
        fusion_state_manager,
        "get_fusion_analysis_state",
        missing_state,
    )

    response = await async_client.get(
        "/api/v1/public/status", params={"location_id": 999}
    )

    assert response.status_code == 200
    assert response.json() == {
        "location_id": 999,
        "level": "unknown",
        "updated_at": None,
        "fusion_analysis": None,
    }


@pytest.mark.asyncio
async def test_latest_camera_frame_returns_retained_snapshot(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    captured_at = datetime.now(timezone.utc)
    monkeypatch.setattr(
        camera_status_service,
        "get_latest_frame",
        lambda location_id: {
            "image": "aGVsbG8=",
            "timestamp": captured_at,
        },
    )

    response = await async_client.get(
        "/api/v1/stream/latest-frame", params={"location_id": 1}
    )

    assert response.status_code == 200
    assert response.json() == {
        "image": "aGVsbG8=",
        "timestamp": captured_at.isoformat().replace("+00:00", "Z"),
    }


@pytest.mark.asyncio
async def test_latest_camera_frame_returns_404_when_unavailable(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        camera_status_service,
        "get_latest_frame",
        lambda location_id: None,
    )

    response = await async_client.get(
        "/api/v1/stream/latest-frame", params={"location_id": 1}
    )

    assert response.status_code == 404
