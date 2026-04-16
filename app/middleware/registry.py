from fastapi import FastAPI

from .cors import add_cors_middleware
from .gzip import add_gzip_middleware
from .security_headers import add_security_headers_middleware


def register_middleware(app: FastAPI) -> None:
    add_cors_middleware(app)
    add_security_headers_middleware(app)
    add_gzip_middleware(app)
