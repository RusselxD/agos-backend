from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def add_cors_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.FRONTEND_URLS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
