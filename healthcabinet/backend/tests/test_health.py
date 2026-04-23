"""Tests for /health endpoint (AC #2, #4)."""

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_returns_200():
    """GET /health returns 200 with status ok. Does not require a live database."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
