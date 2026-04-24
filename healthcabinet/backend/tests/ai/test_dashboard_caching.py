"""Tests for the persisted (cached) dashboard/overall AI clinical note.

Covers all three filter scopes (all / analysis / document):
- Cache miss → LLM called once, row persisted under the correct scope.
- Cache hit → no LLM call.
- Locale mismatch per scope → regenerate with the requested locale.
- POST /regenerate invalidates only the requested filter's scope.
- Broad invalidation via invalidate_all_overall_interpretations.
- Cache isolation between scopes.
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


async def _seed_user_with_doc(
    db: AsyncSession,
    make_user,
    make_document,
    *,
    email: str,
    document_kind: str = "analysis",
) -> User:
    user, _ = await make_user(email=email)
    doc = await make_document(user=user, status="completed")
    doc.document_kind = document_kind
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
    user = await _seed_user_with_doc(
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
    user = await _seed_user_with_doc(
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
    user = await _seed_user_with_doc(
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
    user = await _seed_user_with_doc(
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


# ---------------------------------------------------------------------------
# Per-filter caching (analysis / document)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_get_writes_cache_for_analysis_filter(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user = await _seed_user_with_doc(
        async_db_session,
        make_user,
        make_document,
        email="cache_analysis@example.com",
        document_kind="analysis",
    )

    call_mock = AsyncMock(return_value="Analysis-only body. ")
    with patch("app.ai.service.call_model_text", call_mock):
        response = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    assert call_mock.await_count == 1

    analysis_row = await ai_repository.get_overall_interpretation(
        async_db_session, user_id=user.id, scope=ai_repository.OVERALL_SCOPE_ANALYSIS
    )
    assert analysis_row is not None
    assert analysis_row.scope == "overall_analysis"
    assert analysis_row.safety_validated is True


@pytest.mark.asyncio
async def test_dashboard_get_serves_cache_for_analysis_filter(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user = await _seed_user_with_doc(
        async_db_session,
        make_user,
        make_document,
        email="cachehit_analysis@example.com",
        document_kind="analysis",
    )

    await ai_repository.upsert_overall_interpretation(
        async_db_session,
        user_id=user.id,
        interpretation_text="Cached analysis body.",
        model_version="claude-sonnet-4-6",
        reasoning_json={"source_document_ids": [], "locale": "en"},
        scope=ai_repository.OVERALL_SCOPE_ANALYSIS,
    )
    await async_db_session.flush()

    call_mock = AsyncMock(return_value="SHOULD_NOT_BE_CALLED")
    with patch("app.ai.service.call_model_text", call_mock):
        response = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    assert call_mock.await_count == 0
    assert "Cached analysis body." in response.json()["interpretation"]


@pytest.mark.asyncio
async def test_cache_isolation_between_scopes(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Generating overall_analysis must not overwrite or flip overall_all."""
    user = await _seed_user_with_doc(
        async_db_session,
        make_user,
        make_document,
        email="iso@example.com",
        document_kind="analysis",
    )

    await ai_repository.upsert_overall_interpretation(
        async_db_session,
        user_id=user.id,
        interpretation_text="All-scope body.",
        model_version="claude-sonnet-4-6",
        reasoning_json={"source_document_ids": [], "locale": "en"},
        scope=ai_repository.OVERALL_SCOPE_ALL,
    )
    await async_db_session.flush()

    call_mock = AsyncMock(return_value="Analysis body. ")
    with patch("app.ai.service.call_model_text", call_mock):
        response = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    assert call_mock.await_count == 1

    all_row = await ai_repository.get_overall_interpretation(
        async_db_session, user_id=user.id, scope=ai_repository.OVERALL_SCOPE_ALL
    )
    analysis_row = await ai_repository.get_overall_interpretation(
        async_db_session, user_id=user.id, scope=ai_repository.OVERALL_SCOPE_ANALYSIS
    )
    assert all_row is not None and all_row.safety_validated is True
    assert analysis_row is not None and analysis_row.safety_validated is True
    # Different rows.
    assert all_row.id != analysis_row.id


@pytest.mark.asyncio
async def test_locale_mismatch_per_scope_regenerates(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Cached overall_document with locale=uk; request locale=en → regenerate."""
    user = await _seed_user_with_doc(
        async_db_session,
        make_user,
        make_document,
        email="locale_doc@example.com",
        document_kind="document",
    )

    await ai_repository.upsert_overall_interpretation(
        async_db_session,
        user_id=user.id,
        interpretation_text="Ukrainian body.",
        model_version="claude-sonnet-4-6",
        reasoning_json={"source_document_ids": [], "locale": "uk"},
        scope=ai_repository.OVERALL_SCOPE_DOCUMENT,
    )
    await async_db_session.flush()

    call_mock = AsyncMock(return_value="English body. ")
    with patch("app.ai.service.call_model_text", call_mock):
        response = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=document&locale=en",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    assert call_mock.await_count == 1


@pytest.mark.asyncio
async def test_force_regenerate_is_scope_specific(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """POST /regenerate?document_kind=analysis invalidates only analysis scope."""
    user = await _seed_user_with_doc(
        async_db_session,
        make_user,
        make_document,
        email="scoped_regen@example.com",
        document_kind="analysis",
    )

    await ai_repository.upsert_overall_interpretation(
        async_db_session,
        user_id=user.id,
        interpretation_text="All body.",
        model_version="claude-sonnet-4-6",
        reasoning_json={"source_document_ids": [], "locale": "en"},
        scope=ai_repository.OVERALL_SCOPE_ALL,
    )
    await ai_repository.upsert_overall_interpretation(
        async_db_session,
        user_id=user.id,
        interpretation_text="Analysis body.",
        model_version="claude-sonnet-4-6",
        reasoning_json={"source_document_ids": [], "locale": "en"},
        scope=ai_repository.OVERALL_SCOPE_ANALYSIS,
    )
    await async_db_session.flush()

    call_mock = AsyncMock(return_value="Regenerated analysis body. ")
    with patch("app.ai.service.call_model_text", call_mock):
        response = await ai_client.post(
            "/api/v1/ai/dashboard/interpretation/regenerate?document_kind=analysis",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    assert call_mock.await_count == 1

    all_row = await ai_repository.get_overall_interpretation(
        async_db_session, user_id=user.id, scope=ai_repository.OVERALL_SCOPE_ALL
    )
    analysis_row = await ai_repository.get_overall_interpretation(
        async_db_session, user_id=user.id, scope=ai_repository.OVERALL_SCOPE_ANALYSIS
    )
    # all scope untouched, analysis scope replaced (still validated after regen).
    assert all_row is not None and all_row.safety_validated is True
    assert analysis_row is not None and analysis_row.safety_validated is True


@pytest.mark.asyncio
async def test_invalidate_all_overall_interpretations_flips_all_scopes(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Broad-invalidation helper flips safety_validated=False on every scope row."""
    user = await _seed_user_with_doc(
        async_db_session,
        make_user,
        make_document,
        email="broadinv@example.com",
    )

    for scope in (
        ai_repository.OVERALL_SCOPE_ALL,
        ai_repository.OVERALL_SCOPE_ANALYSIS,
        ai_repository.OVERALL_SCOPE_DOCUMENT,
    ):
        await ai_repository.upsert_overall_interpretation(
            async_db_session,
            user_id=user.id,
            interpretation_text=f"Body for {scope}.",
            model_version="claude-sonnet-4-6",
            reasoning_json={"source_document_ids": [], "locale": "en"},
            scope=scope,
        )
    await async_db_session.flush()

    await ai_repository.invalidate_all_overall_interpretations(
        async_db_session, user_id=user.id
    )
    await async_db_session.flush()

    result = await async_db_session.execute(
        select(AiMemory).where(
            AiMemory.user_id == user.id,
            AiMemory.scope.is_not(None),
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 3
    for row in rows:
        assert row.safety_validated is False


@pytest.mark.asyncio
async def test_empty_filter_after_delete_raises_409_not_stale_cache(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """After the last contributing doc is gone, the filter must 409, not
    serve an orphan cached row."""
    user, _ = await make_user(email="empty_transition@example.com")
    # No documents of any kind — purely synthetic cached row.
    await ai_repository.upsert_overall_interpretation(
        async_db_session,
        user_id=user.id,
        interpretation_text="Stale body for a deleted doc.",
        model_version="claude-sonnet-4-6",
        reasoning_json={"source_document_ids": [], "locale": "en"},
        scope=ai_repository.OVERALL_SCOPE_ANALYSIS,
    )
    # Simulate broad invalidation (what the upload/delete hooks do).
    await ai_repository.invalidate_all_overall_interpretations(
        async_db_session, user_id=user.id
    )
    await async_db_session.flush()

    call_mock = AsyncMock(return_value="SHOULD_NOT_BE_CALLED")
    with patch("app.ai.service.call_model_text", call_mock):
        response = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )

    # No per-document context rows → service raises NoDashboardAiContextError → 409.
    assert response.status_code == 409
    assert call_mock.await_count == 0
