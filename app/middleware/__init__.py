"""Middleware modules."""

from .cors import add_cors_middleware
from .gzip import add_gzip_middleware
from .registry import register_middleware

__all__ = ["add_cors_middleware", "add_gzip_middleware", "register_middleware"]
