from typing import AsyncGenerator, Generator
import os
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

os.environ["ENV_STATE"] = "test"

from app.core.database import database
from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# This fixture provides a TestClient for testing the FastAPI.
@pytest.fixture()
def client(db) -> Generator:
    with TestClient(app) as c:
        yield c


#
@pytest.fixture(autouse=True)
async def db() -> AsyncGenerator:
    await database.connect()
    yield
    await database.disconnect()


# This fixture provides an AsyncClient for testing the FastAPI.
@pytest.fixture()
async def async_client(db) -> AsyncGenerator:
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
