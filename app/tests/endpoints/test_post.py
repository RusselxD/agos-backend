import pytest
from httpx import AsyncClient


async def create_post(async_client: AsyncClient, body: str):
    response = await async_client.post("/post", json={"body": body})
    return response.json()


@pytest.fixture
async def created_post(async_client: AsyncClient):
    return await create_post(async_client, body="Test post content")


@pytest.mark.asyncio
async def test_create_post(async_client: AsyncClient):
    body = "Hello, world!"

    response = await async_client.post("/post", json={"body": body})

    assert response.status_code == 201
    assert {"id": 0, "body": body}.items() <= response.json().items()


@pytest.mark.asyncio
async def test_post_no_body(async_client: AsyncClient):
    response = await async_client.post("/post", json={})

    assert response.status_code == 422
