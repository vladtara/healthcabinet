"""Tests for the persisted (cached) dashboard/overall AI clinical note.

Covers:
- Cache miss → LLM called once, row persisted to ai_memories(scope='overall_all').
- Cache hit → no LLM call; response served from the cached row.
- Invalidation → next GET regenerates.
- POST /regenerate → always calls LLM even with a valid cache.
- Non-'all' filter variants intentionally skip the cache.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import repository as ai_repository
from app.ai.models import AiMemory
from app.auth.models import User
from app.core.database import get_db
from app.core.encryption import encrypt_bytes
from app.core.security import create_access_token
from app.main import app


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def ai_client(
    async_db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield async_db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def _seed_user_with_analysis_doc(
    db: AsyncSession, make_user, make_document, *, email: str
) -> User:
    user, _ = await make_user(email=email)
    doc = await make_document(user=user, status="completed")
    doc.document_kind = "analysis"
    await db.flush()
    mem = AiMemory(
        user_id=user.id,
        document_id=doc.id,
        interpretation_encrypted=encrypt_bytes(b"Glucose within range."),
        model_version="claude-sonnet-4-6",
        safety_validated=True,
    )
    db.add(mem)
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_dashboard_get_writes_cache_on_first_call(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user = await _seed_user_with_analysis_doc(
        async_db_session, make_user, make_document, email="cache_first@example.com"
    )

    call_mock = AsyncMock(return_value="Aggregate summary. ")
    with patch("app.ai.service.call_model_text", call_mock):
        response = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=all",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    assert call_mock.await_count == 1

    overall = await ai_repository.get_overall_interpretation(async_db_session, user_id=user.id)
    assert overall is not None
    assert overall.scope == "overall_all"
    assert overall.safety_validated is True
    assert overall.document_id is None


@pytest.mark.asyncio
async def test_dashboard_get_serves_cache_without_llm(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user = await _seed_user_with_analysis_doc(
        async_db_session, make_user, make_document, email="cache_hit@example.com"
    )

    # Seed a valid cached overall row directly — locale 'en' to match the request.
    await ai_repository.upsert_overall_interpretation(
        async_db_session,
        user_id=user.id,
        interpretation_text="Cached summary body.",
        model_version="claude-sonnet-4-6",
        reasoning_json={"source_document_ids": [], "locale": "en"},
    )
    await async_db_session.flush()

    call_mock = AsyncMock(return_value="SHOULD_NOT_BE_CALLED")
    with patch("app.ai.service.call_model_text", call_mock):
        response = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=all",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    data = response.json()
    assert "Cached summary body." in data["interpretation"]
    assert call_mock.await_count == 0


@pytest.mark.asyncio
async def test_dashboard_get_regenerates_after_invalidation(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user = await _seed_user_with_analysis_doc(
        async_db_session, make_user, make_document, email="cache_stale@example.com"
    )

    await ai_repository.upsert_overall_interpretation(
        async_db_session,
        user_id=user.id,
        interpretation_text="Old body.",
        model_version="claude-sonnet-4-6",
        reasoning_json={"source_document_ids": [], "locale": "en"},
    )
    await ai_repository.invalidate_overall_interpretation(async_db_session, user_id=user.id)
    await async_db_session.flush()

    call_mock = AsyncMock(return_value="Fresh aggregate body. ")
    with patch("app.ai.service.call_model_text", call_mock):
        response = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=all",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    assert call_mock.await_count == 1
    refreshed = await ai_repository.get_overall_interpretation(
        async_db_session, user_id=user.id
    )
    assert refreshed is not None
    assert refreshed.safety_validated is True


@pytest.mark.asyncio
async def test_dashboard_regenerate_post_always_calls_llm(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user = await _seed_user_with_analysis_doc(
        async_db_session, make_user, make_document, email="force_regen@example.com"
    )

    await ai_repository.upsert_overall_interpretation(
        async_db_session,
        user_id=user.id,
        interpretation_text="Old body.",
        model_version="claude-sonnet-4-6",
        reasoning_json={"source_document_ids": [], "locale": "en"},
    )
    await async_db_session.flush()

    call_mock = AsyncMock(return_value="Regenerated body. ")
    with patch("app.ai.service.call_model_text", call_mock):
        response = await ai_client.post(
            "/api/v1/ai/dashboard/interpretation/regenerate?document_kind=all",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    assert call_mock.await_count == 1


@pytest.mark.asyncio
async def test_dashboard_non_all_filter_does_not_cache(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user = await _seed_user_with_analysis_doc(
        async_db_session, make_user, make_document, email="filter_nocache@example.com"
    )

    call_mock = AsyncMock(return_value="Analysis-only summary. ")
    with patch("app.ai.service.call_model_text", call_mock):
        response = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )

    assert response.status_code == 200

    rows = await async_db_session.execute(
        select(AiMemory).where(AiMemory.user_id == user.id, AiMemory.scope.is_not(None))
    )
    assert rows.scalars().first() is None
