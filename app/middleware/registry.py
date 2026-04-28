from fastapi import FastAPI

from .cors import add_cors_middleware
from .gzip import add_gzip_middleware
from .security_headers import add_security_headers_middleware


def register_middleware(app: FastAPI) -> None:
    # Order matters: Starlette's add_middleware inserts at index 0, so the
    # last call becomes the outermost. CORS must be outermost so preflight
    # OPTIONS requests are handled before any other middleware can alter
    # the response (e.g., BaseHTTPMiddleware can drop headers).
    add_security_headers_middleware(app)
    add_gzip_middleware(app)
    add_cors_middleware(app)
