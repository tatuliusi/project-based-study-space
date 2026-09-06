import pytest
from httpx import AsyncClient, ASGITransport
from src.api.main import app


@pytest.mark.asyncio
async def test_empty_question_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/debates", json={"question": "   "})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_missing_question_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/debates", json={"domain": "philosophy"})
    assert resp.status_code == 422
