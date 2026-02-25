from fastapi import FastAPI

from .cors import add_cors_middleware
from .gzip import add_gzip_middleware


def register_middleware(app: FastAPI) -> None:
    add_cors_middleware(app)
    add_gzip_middleware(app)
