import logging

import sentry_sdk
from sentry_sdk.integrations.logging import ignore_logger

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.cloudinary import init_cloudinary
from app.core.database import AsyncSessionLocal, engine

from app.core.rate_limiter import limiter
from app.middleware.registry import register_middleware

from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import api_router
from app.api.v1.endpoints.websocket import router as ws_router

from app.services import weather_service
# from app.services import database_cleanup_service
from app.core.state import fusion_state_manager
from app.core.scheduler import start_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting application...")
    init_cloudinary()
    await weather_service.start()
    # await database_cleanup_service.start()
    # Initialize Fusion Analysis State with latest data
    print("📊 Loading initial fusion analysis state...")
    await fusion_state_manager.start_all_states()
    print("✅ Fusion analysis state loaded.")

    # Start scheduler for daily summary jobs
    start_scheduler()

    # Backfill missing daily summaries for the past 7 days
    try:
        from app.services import daily_summary_service
        async with AsyncSessionLocal() as db:
            count = await daily_summary_service.backfill_missing_summaries(db)
            if count > 0:
                print(f"📋 Backfilled {count} missing daily summaries")
    except Exception as e:
        print(f"⚠️ Daily summary backfill failed (non-blocking): {e}")

    yield  # Application runs here

    # Shutdown
    print("🛑 Shutting down application...")
    shutdown_scheduler()
    await weather_service.stop()
    # await database_cleanup_service.stop()
    await engine.dispose()
    print("✅ Database engine disposed.")

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENVIRONMENT,
    traces_sample_rate=0.2,
    send_default_pii=False,
)

# Suppress noisy, non-actionable SQLAlchemy pool cleanup warnings that happen
# when Render hibernates or Supabase's pooler drops idle connections.
ignore_logger("sqlalchemy.pool.impl.AsyncAdaptedQueuePool")

# Create FastAPI app with lifespan
app = FastAPI(
    title="AGOS API",
    version="1.0.0",
    lifespan=lifespan  # Pass lifespan here
)

# Attach rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

register_middleware(app)

# Include routers
app.include_router(ws_router)
app.include_router(api_router)

# Add Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Root endpoints
@app.get("/")
async def root():
    return {"message": "AGOS API is running"}

# Migration commands:
# alembic revision --autogenerate -m "Initial migration"
# alembic upgrade head

# Start Prometheus and Grafana
# docker-compose up

# Visit localhost:3000 to access Grafana dashboard

# To check database size, run the following SQL command in PostgreSQL:
# SELECT pg_size_pretty(pg_database_size('agos_db'));

# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000