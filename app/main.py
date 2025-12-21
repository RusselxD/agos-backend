from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.api.v1.endpoints.websocket import router as ws_router
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="AGOS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)
app.include_router(api_router, prefix="/api/v1")

# Add Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Migration commands:
# alembic revision --autogenerate -m "Initial migration"
# alembic upgrade head

# Start Prometheus and Grafana
# docker-compose up

# To check database size, run the following SQL command in PostgreSQL:
# SELECT pg_size_pretty(pg_database_size('agos_db'));