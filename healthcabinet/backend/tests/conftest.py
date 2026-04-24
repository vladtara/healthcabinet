import os
import redis.asyncio as aioredis
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path

import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force production-safe cookie flags for the test process, overriding any
# local-dev bleed-through (compose sets COOKIE_SECURE=false for HTTP dev).
# Tests assert the hardened shape (Secure, SameSite=Strict) — if dev overrides
# leak in via `docker compose exec backend uv run pytest`, the asserts trip.
os.environ["COOKIE_SECURE"] = "true"
os.environ["COOKIE_SAMESITE"] = "strict"

# Load test env vars before app imports resolve Settings — must precede all app.* imports
load_dotenv(Path(__file__).parent.parent / ".env.test", override=False)

from app.auth.models import User  # noqa: E402
from app.auth.repository import create_user  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.documents.models import Document  # noqa: E402
from app.health_data.models import HealthValue  # noqa: E402
from app.health_data.repository import _encrypt_numeric_value  # noqa: E402
from app.main import app  # noqa: E402

# NOTE: Login rate limiting (app/core/rate_limit.py) is NOT integration-tested here.
# The rate limiter uses Redis and is designed to fail-open on connection errors.
# In the test suite, Redis is absent so all rate-limit calls silently pass through —
# this means the 429 threshold, Retry-After header, IP key, and 60s window are not
# exercised via the /auth/login endpoint. Unit tests in tests/core/test_rate_limit.py
# cover that logic using an injected mock Redis client.

# Test database — reads DATABASE_URL from env (set to test DB in CI)
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://healthcabinet:healthcabinet@localhost:5432/healthcabinet_test",
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _flush_redis() -> AsyncGenerator[None, None]:
    """Flush Redis at session start to prevent rate-limit state bleed across tests.

    When Redis is present (CI environment with REDIS_URL set), rate-limit counters
    could accumulate across test runs and cause legitimate tests to receive 429s.
    Flushing once per session ensures a clean slate without per-test overhead.

    Guards: only flushes when ENVIRONMENT=test to protect non-test Redis instances
    in shared environments. Silently skips when Redis is unavailable.
    """
    if os.getenv("ENVIRONMENT") != "test":
        yield
        return

    client: aioredis.Redis | None = None
    try:
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        client = aioredis.from_url(url, decode_responses=True, socket_connect_timeout=2)
        await client.flushdb()
    except Exception:
        pass  # Fail-open: Redis is optional for the test suite
    yield
    if client is not None:
        try:
            await client.aclose()
        except Exception:
            pass


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Async DB session fixture. Rolls back after each test."""
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_client(async_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX async test client with DB session override."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield async_db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def make_user(async_db_session: AsyncSession):
    """Factory fixture for creating persisted User instances.

    Returns a tuple of (User, plaintext_password) so callers can use the
    password directly in login tests without duplicating the hardcoded default.
    """

    async def _make_user(
        email: str = "test@example.com",
        password: str = "testpassword123",
    ) -> tuple[User, str]:
        hashed = hash_password(password)
        user = await create_user(async_db_session, email, hashed)
        return user, password

    return _make_user


@pytest_asyncio.fixture
async def make_document(async_db_session: AsyncSession, make_user):
    """Factory fixture for creating persisted Document instances."""

    async def _make_document(
        user: User | None = None,
        status: str = "pending",
        filename: str = "test_lab.pdf",
        file_size_bytes: int = 1024,
        file_type: str = "application/pdf",
        created_at: datetime | None = None,
    ) -> Document:
        if user is None:
            user, _ = await make_user()
        doc = Document(
            user_id=user.id,
            status=status,
            filename=filename,
            file_size_bytes=file_size_bytes,
            file_type=file_type,
        )
        if created_at is not None:
            doc.created_at = created_at
        async_db_session.add(doc)
        await async_db_session.flush()
        await async_db_session.refresh(doc)
        return doc

    return _make_document


@pytest_asyncio.fixture
async def make_health_value(async_db_session: AsyncSession, make_user, make_document):
    """Factory fixture for creating persisted HealthValue instances with encrypted values."""

    async def _make_health_value(
        user: User | None = None,
        document: Document | None = None,
        biomarker_name: str = "Cholesterol",
        canonical_biomarker_name: str = "cholesterol_total",
        value: float = 5.0,
        unit: str | None = "mmol/L",
        confidence: float = 0.95,
        needs_review: bool = False,
        is_flagged: bool = False,
    ) -> HealthValue:
        if user is None:
            user, _ = await make_user()
        if document is None:
            document = await make_document(user=user)
        hv = HealthValue(
            user_id=user.id,
            document_id=document.id,
            biomarker_name=biomarker_name,
            canonical_biomarker_name=canonical_biomarker_name,
            value_encrypted=_encrypt_numeric_value(value),
            unit=unit,
            confidence=confidence,
            needs_review=needs_review,
            is_flagged=is_flagged,
        )
        async_db_session.add(hv)
        await async_db_session.flush()
        await async_db_session.refresh(hv)
        return hv

    return _make_health_value
