"""GZip compression middleware."""

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware


# Default: compress responses larger than 1000 bytes (~70% reduction for JSON)
DEFAULT_MINIMUM_SIZE = 1000


def add_gzip_middleware(
    app: FastAPI,
    minimum_size: int = DEFAULT_MINIMUM_SIZE,
) -> None:
    """Add GZip compression middleware to the FastAPI app."""
    app.add_middleware(GZipMiddleware, minimum_size=minimum_size)
