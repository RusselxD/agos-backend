from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import app, get_session


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# This fixture provides a TestClient for testing the FastAPI.
@pytest.fixture()
def client(db) -> Generator:
    with TestClient(app) as c:
        yield c


# This fixture sets up an in-memory SQLite database for testing
# and overrides the get_session dependency to use this test database.
@pytest.fixture(autouse=True)
async def db() -> AsyncGenerator:

    # Create an in-memory SQLite database for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create a session factory
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Override the get_session dependency to use the test database
    async def override_get_session() -> AsyncGenerator:
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    yield

    # Cleanup: Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# This fixture provides an AsyncClient for testing the FastAPI.
@pytest.fixture()
async def async_client() -> AsyncGenerator:
    async with AsyncClient(app=app, base_url=client.base_url) as ac:
        yield ac
