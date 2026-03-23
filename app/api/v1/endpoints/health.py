from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter(tags=["health"])


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
