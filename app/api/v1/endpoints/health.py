from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.post("/simulate-anomaly")
async def simulate_anomaly():
    from app.core.state import fusion_state_manager
    from app.schemas.fusion_analysis import BlockageStatus, WeatherStatus, WaterLevelStatus
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    
    # 1. Clear weather (No rain)
    weather_status = WeatherStatus(
        timestamp=now,
        precipitation_mm=0.0,
        weather_condition="Clear"
    )
    
    # 2. Clear Blockage
    blockage_status = BlockageStatus(
        timestamp=now,
        status="clear"
    )
    
    # 3. Critical Water Level
    water_level_status = WaterLevelStatus(
        timestamp=now,
        water_level_cm=190.0,
        change_rate=0.5,
        critical_percentage=95.0,
        trend="rising"
    )

    location_id = 1
    await fusion_state_manager.recalculate_weather_score(weather_status, location_id)
    await fusion_state_manager.recalculate_visual_status_score(blockage_status, location_id)
    await fusion_state_manager.recalculate_water_level_score(water_level_status, location_id)

    return {"status": "anomaly triggered"}

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    components = {}
    overall_healthy = True

    # Database
    try:
        await db.execute(text("SELECT 1"))
        components["database"] = "healthy"
    except Exception:
        components["database"] = "unhealthy"
        overall_healthy = False

    # Scheduler
    try:
        from app.core.scheduler import scheduler
        components["scheduler"] = "running" if scheduler.running else "stopped"
        if not scheduler.running:
            overall_healthy = False
    except Exception:
        components["scheduler"] = "unknown"

    # WebSocket connections
    try:
        from app.core.ws_manager import ws_manager
        total = sum(len(clients) for clients in ws_manager.connections.values())
        components["websocket_connections"] = total
    except Exception:
        components["websocket_connections"] = 0

    status_code = 200 if overall_healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if overall_healthy else "degraded",
            "components": components,
        },
    )
