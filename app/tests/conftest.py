from typing import AsyncGenerator, Generator
import os
import pytest
from httpx import ASGITransport, AsyncClient
from fastapi.testclient import TestClient

os.environ["ENV_STATE"] = "test"

from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# This fixture provides a TestClient for testing the FastAPI.
@pytest.fixture()
def client(db) -> Generator:
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def db() -> Generator:
    """Database fixture - app uses get_db for actual DB access."""
    yield


# This fixture provides an AsyncClient for testing the FastAPI.
@pytest.fixture()
async def async_client(db) -> AsyncGenerator:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
