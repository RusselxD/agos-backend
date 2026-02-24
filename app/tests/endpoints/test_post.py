import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_login_no_body(async_client: AsyncClient):
    """Missing required fields returns 422."""
    response = await async_client.post("/api/v1/auth/login", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_auth_login_missing_fields(async_client: AsyncClient):
    """Partial body returns 422."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"phone_number": "09001234567"},
    )
    assert response.status_code == 422
