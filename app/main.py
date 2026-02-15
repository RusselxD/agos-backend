from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from pathlib import Path
from contextlib import asynccontextmanager
from app.core.cloudinary import init_cloudinary

from app.core.config import settings
from app.core.rate_limiter import limiter

from app.services.stream import stream_processor
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import api_router
from app.api.v1.endpoints.websocket import router as ws_router

from app.services import ml_service
from app.services import weather_service
# from app.services import database_cleanup_service
from app.core.state import fusion_state_manager
from app.core.scheduler import start_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting application...")
    init_cloudinary()
    await stream_processor.start()
    await ml_service.start()
    await weather_service.start()
    # await database_cleanup_service.start()
    # Initialize Fusion Analysis State with latest data
    print("📊 Loading initial fusion analysis state...")
    await fusion_state_manager.start_all_states()
    print("✅ Fusion analysis state loaded.")
    
    # Start scheduler for daily summary jobs
    start_scheduler()

    yield  # Application runs here

    # Shutdown
    print("🛑 Shutting down application...")
    shutdown_scheduler()
    await stream_processor.stop()
    await ml_service.stop()
    await weather_service.stop()
    # await database_cleanup_service.stop()

# Create FastAPI app with lifespan
app = FastAPI(
    title="AGOS API",
    version="1.0.0",
    lifespan=lifespan  # Pass lifespan here
)

# Attach rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip Compression Middleware
# Compresses responses larger than 1000 bytes (reduces JSON payload size by ~70%)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(ws_router)
app.include_router(api_router, prefix="/api/v1")

# Serve static HLS files
hls_path = Path(settings.HLS_OUTPUT_DIR)
hls_path.mkdir(parents=True, exist_ok=True)
app.mount("/hls", StaticFiles(directory=str(hls_path)), name="hls")

# Serve other static storage files (e.g., responder IDs)
storage_path = Path("app/storage")
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/app/storage", StaticFiles(directory=str(storage_path)), name="storage")

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