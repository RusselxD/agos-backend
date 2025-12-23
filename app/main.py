from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager

from app.api.v1.router import api_router
from app.core.config import settings
from app.api.v1.endpoints.websocket import router as ws_router
from app.services.stream import stream_processor
from prometheus_fastapi_instrumentator import Instrumentator
from app.services.ml_service import ml_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup services"""
    # Startup
    print("🚀 Starting application...")
    await stream_processor.start()
    print("✅ Stream processor started")
    await ml_service.start()
    
    yield  # Application runs here
    
    # Shutdown
    print("🛑 Shutting down application...")
    await stream_processor.stop()
    print("✅ Stream processor stopped")
    await ml_service.stop()


# Create FastAPI app with lifespan
app = FastAPI(
    title="AGOS API",
    version="1.0.0",
    lifespan=lifespan  # Pass lifespan here
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ws_router)
app.include_router(api_router, prefix="/api/v1")

# Serve static HLS files
hls_path = Path(settings.HLS_OUTPUT_DIR)
hls_path.mkdir(parents=True, exist_ok=True)
app.mount("/hls", StaticFiles(directory=str(hls_path)), name="hls")

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