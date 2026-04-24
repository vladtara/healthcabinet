"""Infrastructure smoke tests: verify the DB and Redis services are reachable in CI.

These tests run against live service containers (Postgres and Redis) and confirm
that the environment is correctly wired before the main test suite executes.
"""

import os

import pytest
import redis.asyncio as aioredis
from sqlalchemy import text


async def test_db_is_reachable(test_engine) -> None:
    """SELECT 1 confirms the async engine can reach the test database."""
    async with test_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


async def test_redis_is_reachable() -> None:
    """PING confirms Redis is reachable and responding from the test process."""
    url = os.getenv("REDIS_URL")
    if not url:
        pytest.skip("REDIS_URL not set — skipping Redis connectivity test")

    client = aioredis.from_url(url, decode_responses=True, socket_connect_timeout=5)
    try:
        result = await client.ping()
        assert result is True
    finally:
        await client.aclose()
