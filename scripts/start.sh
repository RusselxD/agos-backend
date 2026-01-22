#!/bin/bash
set -e

# Auto migrate db on startup
alembic upgrade head

# Start app
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
