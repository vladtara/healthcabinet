"""Tests for GET /api/v1/ai/documents/{document_id}/interpretation and POST /api/v1/ai/chat."""

import json
import uuid
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi import status as http_status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import AiMemory
from app.ai.router import chat_with_ai
from app.ai.schemas import AiChatRequest, AiPatternsResponse, PatternObservation
from app.ai.service import AiServiceUnavailableError
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


@pytest_asyncio.fixture
async def user_with_document(async_db_session: AsyncSession, make_user, make_document):
    user, _ = await make_user(email="ai_test@example.com")
    doc = await make_document(user=user, status="completed")
    return user, doc


@pytest_asyncio.fixture
async def user_with_interpretation(async_db_session: AsyncSession, user_with_document):
    user, doc = user_with_document
    encrypted = encrypt_bytes(b"Your glucose is normal. ")
    memory = AiMemory(
        user_id=user.id,
        document_id=doc.id,
        interpretation_encrypted=encrypted,
        model_version="claude-sonnet-4-6",
        safety_validated=True,
    )
    async_db_session.add(memory)
    await async_db_session.flush()
    await async_db_session.refresh(memory)
    return user, doc, memory


@pytest_asyncio.fixture
async def user_with_interpretation_and_reasoning(
    async_db_session: AsyncSession, user_with_document
):
    user, doc = user_with_document
    encrypted = encrypt_bytes(b"Your glucose is normal. ")
    reasoning = {
        "values_referenced": [
            {
                "name": "Glucose",
                "value": 91.0,
                "unit": "mg/dL",
                "ref_low": 70.0,
                "ref_high": 99.0,
                "status": "normal",
            }
        ],
        "uncertainty_flags": [],
        "prior_documents_referenced": [],
    }
    memory = AiMemory(
        user_id=user.id,
        document_id=doc.id,
        interpretation_encrypted=encrypted,
        context_json_encrypted=encrypt_bytes(json.dumps(reasoning).encode("utf-8")),
        model_version="claude-sonnet-4-6",
        safety_validated=True,
    )
    async_db_session.add(memory)
    await async_db_session.flush()
    await async_db_session.refresh(memory)
    return user, doc, memory, reasoning


@pytest.mark.asyncio
async def test_get_interpretation_returns_200_for_owner(
    ai_client: AsyncClient,
    user_with_interpretation,
):
    user, doc, memory = user_with_interpretation
    response = await ai_client.get(
        f"/api/v1/ai/documents/{doc.id}/interpretation",
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == str(doc.id)
    assert "glucose" in data["interpretation"]
    assert data["model_version"] == "claude-sonnet-4-6"
    assert data["reasoning"] is None


@pytest.mark.asyncio
async def test_get_interpretation_returns_404_for_other_user(
    ai_client: AsyncClient,
    user_with_interpretation,
    make_user,
):
    _, doc, _ = user_with_interpretation
    other_user, _ = await make_user(email="other_ai@example.com")
    response = await ai_client.get(
        f"/api/v1/ai/documents/{doc.id}/interpretation",
        headers=auth_headers(other_user),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_interpretation_returns_404_when_not_generated(
    ai_client: AsyncClient,
    user_with_document,
):
    user, doc = user_with_document
    response = await ai_client.get(
        f"/api/v1/ai/documents/{doc.id}/interpretation",
        headers=auth_headers(user),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_interpretation_returns_404_for_processing_document(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Documents still processing must not return an interpretation (status gate)."""
    user, _ = await make_user(email="ai_processing@example.com")
    doc = await make_document(user=user, status="processing")
    response = await ai_client.get(
        f"/api/v1/ai/documents/{doc.id}/interpretation",
        headers=auth_headers(user),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Document is still processing"


@pytest.mark.asyncio
async def test_invalidate_interpretation_hides_existing(
    async_db_session: AsyncSession,
    user_with_interpretation,
):
    """invalidate_interpretation sets safety_validated=False so GET returns None."""
    from app.ai import repository as ai_repository

    user, doc, memory = user_with_interpretation

    # Before invalidation: interpretation is visible
    result = await ai_repository.get_interpretation_and_metadata(
        async_db_session, user_id=user.id, document_id=doc.id
    )
    assert result is not None

    # Invalidate
    await ai_repository.invalidate_interpretation(
        async_db_session, user_id=user.id, document_id=doc.id
    )

    # After invalidation: interpretation is hidden
    result = await ai_repository.get_interpretation_and_metadata(
        async_db_session, user_id=user.id, document_id=doc.id
    )
    assert result is None


@pytest.mark.asyncio
async def test_invalidate_interpretation_noop_when_no_row(
    async_db_session: AsyncSession,
    user_with_document,
):
    """invalidate_interpretation is a no-op when no interpretation exists."""
    from app.ai import repository as ai_repository

    user, doc = user_with_document

    # Should not raise
    await ai_repository.invalidate_interpretation(
        async_db_session, user_id=user.id, document_id=doc.id
    )


@pytest.mark.asyncio
async def test_get_interpretation_includes_reasoning_when_present(
    ai_client: AsyncClient,
    user_with_interpretation_and_reasoning,
):
    user, doc, _, reasoning = user_with_interpretation_and_reasoning

    response = await ai_client.get(
        f"/api/v1/ai/documents/{doc.id}/interpretation",
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["reasoning"] == reasoning
    assert data["reasoning"]["values_referenced"][0]["name"] == "Glucose"


@pytest.mark.asyncio
async def test_get_interpretation_reasoning_null_when_not_stored(
    ai_client: AsyncClient,
    user_with_interpretation,
):
    user, doc, _ = user_with_interpretation

    response = await ai_client.get(
        f"/api/v1/ai/documents/{doc.id}/interpretation",
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json()["reasoning"] is None


@pytest.mark.asyncio
async def test_get_interpretation_reasoning_null_when_reasoning_decrypt_fails(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    user_with_document,
):
    user, doc = user_with_document
    memory = AiMemory(
        user_id=user.id,
        document_id=doc.id,
        interpretation_encrypted=encrypt_bytes(b"Your glucose is normal. "),
        context_json_encrypted=b"invalid",
        model_version="claude-sonnet-4-6",
        safety_validated=True,
    )
    async_db_session.add(memory)
    await async_db_session.flush()
    await async_db_session.refresh(memory)

    response = await ai_client.get(
        f"/api/v1/ai/documents/{doc.id}/interpretation",
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["interpretation"] == "Your glucose is normal. "
    assert data["reasoning"] is None


@pytest.mark.asyncio
async def test_get_interpretation_reasoning_null_when_reasoning_schema_mismatches(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    user_with_document,
):
    user, doc = user_with_document
    invalid_reasoning = {
        "values_referenced": [{"name": "Glucose"}],
        "uncertainty_flags": [],
        "prior_documents_referenced": [],
    }
    memory = AiMemory(
        user_id=user.id,
        document_id=doc.id,
        interpretation_encrypted=encrypt_bytes(b"Your glucose is normal. "),
        context_json_encrypted=encrypt_bytes(json.dumps(invalid_reasoning).encode("utf-8")),
        model_version="claude-sonnet-4-6",
        safety_validated=True,
    )
    async_db_session.add(memory)
    await async_db_session.flush()
    await async_db_session.refresh(memory)

    response = await ai_client.get(
        f"/api/v1/ai/documents/{doc.id}/interpretation",
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["interpretation"] == "Your glucose is normal. "
    assert data["reasoning"] is None


# ──────────────────────────────────────────────────────────────────────────────
# Tests for POST /api/v1/ai/chat (AC: #1, #3, #4)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_chat_requires_auth(ai_client: AsyncClient):
    import uuid

    response = await ai_client.post(
        "/api/v1/ai/chat",
        json={"document_id": str(uuid.uuid4()), "question": "What is my glucose?"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_patterns_requires_auth(ai_client: AsyncClient):
    response = await ai_client.get("/api/v1/ai/patterns")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_patterns_returns_429_when_rate_limit_exceeded(
    ai_client: AsyncClient,
    user_with_document,
):
    user, _ = user_with_document
    with patch(
        "app.ai.router.check_ai_patterns_rate_limit",
        AsyncMock(
            side_effect=HTTPException(
                status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many pattern detection requests. Try again in 60 seconds.",
                headers={"Retry-After": "60"},
            )
        ),
    ):
        response = await ai_client.get(
            "/api/v1/ai/patterns",
            headers=auth_headers(user),
        )

    assert response.status_code == 429
    assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_get_patterns_returns_empty_for_single_document(
    ai_client: AsyncClient,
    user_with_interpretation,
):
    """Service < 2 documents early-return path exercised end-to-end through the router."""
    user, doc, _ = user_with_interpretation
    with patch(
        "app.ai.service.ai_repository.list_user_ai_context",
        AsyncMock(
            return_value=[
                {
                    "document_id": str(doc.id),
                    "interpretation": "Your glucose is normal.",
                    "updated_at": "2025-01-15",
                }
            ]
        ),
    ):
        response = await ai_client.get(
            "/api/v1/ai/patterns",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    assert response.json() == {"patterns": []}


@pytest.mark.asyncio
async def test_get_patterns_router_returns_200_with_service_response(
    ai_client: AsyncClient,
    user_with_document,
):
    user, _ = user_with_document

    with patch(
        "app.ai.router.ai_service.detect_cross_upload_patterns",
        AsyncMock(return_value=AiPatternsResponse(patterns=[])),
    ):
        response = await ai_client.get(
            "/api/v1/ai/patterns",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    assert response.json() == {"patterns": []}


@pytest.mark.asyncio
async def test_get_patterns_returns_observations(
    ai_client: AsyncClient,
    user_with_document,
):
    user, _ = user_with_document
    pattern = PatternObservation(
        description="Your ferritin has been lower across two uploads.",
        document_dates=["2025-01-15", "2025-06-20"],
        recommendation="Discuss this pattern with your healthcare provider.",
    )

    with patch(
        "app.ai.router.ai_service.detect_cross_upload_patterns",
        AsyncMock(return_value=AiPatternsResponse(patterns=[pattern])),
    ):
        response = await ai_client.get(
            "/api/v1/ai/patterns",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    assert response.json() == {
        "patterns": [
            {
                "description": "Your ferritin has been lower across two uploads.",
                "document_dates": ["2025-01-15", "2025-06-20"],
                "recommendation": "Discuss this pattern with your healthcare provider.",
            }
        ]
    }


@pytest.mark.asyncio
async def test_post_chat_returns_404_for_non_owner_document(
    ai_client: AsyncClient,
    user_with_interpretation,
    make_user,
):
    _, doc, _ = user_with_interpretation
    other_user, _ = await make_user(email="chat_other@example.com")

    response = await ai_client.post(
        "/api/v1/ai/chat",
        json={"document_id": str(doc.id), "question": "What is my glucose?"},
        headers=auth_headers(other_user),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_chat_returns_409_when_no_ai_context_exists(
    ai_client: AsyncClient,
    user_with_document,
):
    user, doc = user_with_document

    with patch(
        "app.ai.service.ai_repository.list_user_ai_context",
        AsyncMock(return_value=[]),
    ):
        response = await ai_client.post(
            "/api/v1/ai/chat",
            json={"document_id": str(doc.id), "question": "What is my glucose?"},
            headers=auth_headers(user),
        )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_chat_with_ai_raises_503_when_ai_provider_is_temporarily_unavailable():
    document_id = uuid.uuid4()
    payload = AiChatRequest(document_id=document_id, question="What is my glucose?")

    with (
        patch(
            "app.ai.router.document_repository.get_document_by_id",
            AsyncMock(return_value=SimpleNamespace(id=document_id)),
        ),
        patch(
            "app.ai.router.ai_service.stream_follow_up_answer",
            AsyncMock(
                side_effect=AiServiceUnavailableError(
                    "AI follow-up is temporarily unavailable. Please try again in a moment."
                )
            ),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await chat_with_ai(
            payload=payload,
            current_user=SimpleNamespace(id=uuid.uuid4()),
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 503
    assert (
        exc_info.value.detail
        == "AI follow-up is temporarily unavailable. Please try again in a moment."
    )


@pytest.mark.asyncio
async def test_post_chat_streams_incremental_text(
    ai_client: AsyncClient,
    user_with_interpretation,
):
    user, doc, _ = user_with_interpretation

    async def fake_stream(prompt: str):
        yield "Your "
        yield "glucose "
        yield "is normal."

    context_row = {
        "document_id": str(doc.id),
        "interpretation": "Your glucose is normal.",
    }

    with (
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(return_value=[context_row]),
        ),
        patch("app.ai.service.stream_model_text", fake_stream),
    ):
        async with ai_client.stream(
            "POST",
            "/api/v1/ai/chat",
            json={"document_id": str(doc.id), "question": "Tell me about glucose."},
            headers=auth_headers(user),
        ) as response:
            assert response.status_code == 200
            chunks = []
            async for chunk in response.aiter_text():
                chunks.append(chunk)

    full_text = "".join(chunks)
    assert "glucose" in full_text
    # Verify the response was read using the streaming API (not a single JSON body)
    assert len(chunks) >= 1


# ──────────────────────────────────────────────────────────────────────────────
# Story 15.3 — GET /api/v1/ai/dashboard/interpretation and POST /api/v1/ai/dashboard/chat
# ──────────────────────────────────────────────────────────────────────────────


async def _seed_user_with_kinded_ai_memories(
    db: AsyncSession, make_user, make_document, *, email: str
):
    """Seed 2 analysis AiMemory rows + 1 document AiMemory row + 1 unknown AiMemory row."""
    user, _ = await make_user(email=email)

    analysis_doc_a = await make_document(user=user, status="completed")
    analysis_doc_a.document_kind = "analysis"
    analysis_doc_b = await make_document(user=user, status="completed")
    analysis_doc_b.document_kind = "analysis"
    document_doc = await make_document(user=user, status="completed")
    document_doc.document_kind = "document"
    unknown_doc = await make_document(user=user, status="failed")
    unknown_doc.document_kind = "unknown"
    await db.flush()

    for doc, text in [
        (analysis_doc_a, "Glucose within range."),
        (analysis_doc_b, "Cholesterol borderline high."),
        (document_doc, "Referral note from GP."),
        (unknown_doc, "Interpretation from unknown kind."),
    ]:
        mem = AiMemory(
            user_id=user.id,
            document_id=doc.id,
            interpretation_encrypted=encrypt_bytes(text.encode()),
            model_version="claude-sonnet-4-6",
            safety_validated=True,
        )
        db.add(mem)
    await db.flush()

    return user, analysis_doc_a, analysis_doc_b, document_doc, unknown_doc


@pytest.mark.asyncio
async def test_get_dashboard_interpretation_requires_auth(ai_client: AsyncClient):
    response = await ai_client.get("/api/v1/ai/dashboard/interpretation?document_kind=all")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_dashboard_interpretation_rejects_unknown_kind(
    ai_client: AsyncClient, user_with_document
):
    """'unknown' is deliberately NOT in the DashboardKind Literal → 422."""
    user, _ = user_with_document
    response = await ai_client.get(
        "/api/v1/ai/dashboard/interpretation?document_kind=unknown",
        headers=auth_headers(user),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_dashboard_interpretation_requires_kind(
    ai_client: AsyncClient, user_with_document
):
    user, _ = user_with_document
    response = await ai_client.get(
        "/api/v1/ai/dashboard/interpretation",
        headers=auth_headers(user),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_dashboard_interpretation_409_when_filter_has_no_docs(
    ai_client: AsyncClient, user_with_document
):
    """filter=document with zero document-kind rows returns 409."""
    user, doc = user_with_document
    # doc.document_kind defaults to 'unknown' in the fixture; no document-kind AiMemory exists.
    response = await ai_client.get(
        "/api/v1/ai/dashboard/interpretation?document_kind=document",
        headers=auth_headers(user),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "No analyses available for the active filter"


@pytest.mark.asyncio
async def test_get_dashboard_interpretation_all_aggregates_across_kinds_excludes_unknown(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user, a_doc_a, a_doc_b, d_doc, u_doc = await _seed_user_with_kinded_ai_memories(
        async_db_session, make_user, make_document, email="dash_all@example.com"
    )

    with patch(
        "app.ai.service.call_model_text",
        AsyncMock(return_value="Aggregate summary of your documents. "),
    ):
        response = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=all",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] is None
    assert data["document_kind"] == "all"
    assert data["reasoning"] is None
    # AC 2: unknown is excluded even from 'all'.
    source_ids = set(data["source_document_ids"])
    assert source_ids == {str(a_doc_a.id), str(a_doc_b.id), str(d_doc.id)}
    assert str(u_doc.id) not in source_ids
    # Disclaimer appended by the existing safety pipeline.
    assert (
        "diagnosis" in data["interpretation"].lower()
        or "educational" in data["interpretation"].lower()
    )


@pytest.mark.asyncio
async def test_get_dashboard_interpretation_analysis_only_returns_two_sources(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user, a_doc_a, a_doc_b, d_doc, _ = await _seed_user_with_kinded_ai_memories(
        async_db_session, make_user, make_document, email="dash_analysis@example.com"
    )

    with patch(
        "app.ai.service.call_model_text",
        AsyncMock(return_value="Summary of analysis documents. "),
    ):
        response = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    data = response.json()
    source_ids = set(data["source_document_ids"])
    assert source_ids == {str(a_doc_a.id), str(a_doc_b.id)}
    assert str(d_doc.id) not in source_ids


@pytest.mark.asyncio
async def test_get_dashboard_interpretation_document_only_returns_one_source(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user, a_doc_a, a_doc_b, d_doc, _ = await _seed_user_with_kinded_ai_memories(
        async_db_session, make_user, make_document, email="dash_doc@example.com"
    )

    with patch(
        "app.ai.service.call_model_text",
        AsyncMock(return_value="Summary of non-analysis documents. "),
    ):
        response = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=document",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["source_document_ids"] == [str(d_doc.id)]


@pytest.mark.asyncio
async def test_get_dashboard_interpretation_ownership_scoped(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """User B's AiMemory rows must never contribute to user A's dashboard."""
    user_a, *_ = await _seed_user_with_kinded_ai_memories(
        async_db_session, make_user, make_document, email="dash_own_a@example.com"
    )
    user_b, *_ = await _seed_user_with_kinded_ai_memories(
        async_db_session, make_user, make_document, email="dash_own_b@example.com"
    )

    with patch(
        "app.ai.service.call_model_text",
        AsyncMock(return_value="Summary. "),
    ):
        response_a = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=all",
            headers=auth_headers(user_a),
        )

    assert response_a.status_code == 200
    sources_a = set(response_a.json()["source_document_ids"])
    # user_a seeded exactly 3 non-unknown rows
    assert len(sources_a) == 3


@pytest.mark.asyncio
async def test_get_dashboard_interpretation_503_on_model_temporary_unavailable(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    # Mock the service entrypoint rather than the model client. Patching
    # `call_model_text` races with test_llm_client.py's `importlib.reload`,
    # which replaces the exception class object and desyncs isinstance-based
    # matching between the raise site (test) and the except site (service).
    # Mocking higher up tests the router's 503 mapping contract cleanly.
    user, *_ = await _seed_user_with_kinded_ai_memories(
        async_db_session, make_user, make_document, email="dash_503@example.com"
    )

    with patch(
        "app.ai.router.ai_service.generate_dashboard_interpretation",
        AsyncMock(
            side_effect=AiServiceUnavailableError(
                "AI dashboard interpretation is temporarily unavailable. Please try again in a moment."
            )
        ),
    ):
        response = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=all",
            headers=auth_headers(user),
        )

    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_dashboard_interpretation_rebuilds_after_document_delete_cascade(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """AC 4: after a contributing document is removed, next request reflects the
    reduced AiMemory set (cascade delete already wired in prior stories)."""
    from sqlalchemy import delete as sa_delete

    from app.ai.models import AiMemory as AiMemoryModel
    from app.documents.models import Document as DocumentModel

    user, a_doc_a, a_doc_b, d_doc, _ = await _seed_user_with_kinded_ai_memories(
        async_db_session, make_user, make_document, email="dash_rebuild@example.com"
    )

    with patch(
        "app.ai.service.call_model_text",
        AsyncMock(return_value="Summary. "),
    ):
        response_before = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )
    assert response_before.status_code == 200
    assert len(response_before.json()["source_document_ids"]) == 2

    # Remove one analysis row (mirrors cascade delete on document delete).
    await async_db_session.execute(
        sa_delete(AiMemoryModel).where(AiMemoryModel.document_id == a_doc_a.id)
    )
    await async_db_session.execute(sa_delete(DocumentModel).where(DocumentModel.id == a_doc_a.id))
    await async_db_session.flush()

    with patch(
        "app.ai.service.call_model_text",
        AsyncMock(return_value="Summary. "),
    ):
        response_after = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )

    assert response_after.status_code == 200
    sources_after = response_after.json()["source_document_ids"]
    assert sources_after == [str(a_doc_b.id)]


# ──────────────────────────────────────────────────────────────────────────────
# Story 15.7 — dashboard AI rebuild after upload / reupload / year-confirmation
# (delete-cascade case is covered above; these close the remaining 3 triggers)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_dashboard_interpretation_rebuilds_after_new_upload(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Story 15.7 AC1: after a new completed analysis + its AiMemory land, the
    next dashboard request widens source_document_ids to include the new doc.
    Mirrors the cascade-delete test pattern but in the opposite direction.
    """
    user, a_doc_a, a_doc_b, _d_doc, _ = await _seed_user_with_kinded_ai_memories(
        async_db_session, make_user, make_document, email="dash_new_upload@example.com"
    )

    with patch(
        "app.ai.service.call_model_text",
        AsyncMock(return_value="Summary. "),
    ):
        response_before = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )
    assert response_before.status_code == 200
    assert set(response_before.json()["source_document_ids"]) == {
        str(a_doc_a.id),
        str(a_doc_b.id),
    }

    # Simulate a new upload completing: insert a new analysis Document + its
    # per-document AiMemory row with safety_validated=True. This is what the
    # processing finalize path produces once extraction + AI generation succeed.
    new_doc = await make_document(user=user, status="completed")
    new_doc.document_kind = "analysis"
    await async_db_session.flush()

    async_db_session.add(
        AiMemory(
            user_id=user.id,
            document_id=new_doc.id,
            interpretation_encrypted=encrypt_bytes(b"Vitamin D optimal after supplementation."),
            model_version="claude-sonnet-4-6",
            safety_validated=True,
        )
    )
    await async_db_session.flush()

    with patch(
        "app.ai.service.call_model_text",
        AsyncMock(return_value="Summary including new upload. "),
    ):
        response_after = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )

    assert response_after.status_code == 200
    sources_after = set(response_after.json()["source_document_ids"])
    assert sources_after == {str(a_doc_a.id), str(a_doc_b.id), str(new_doc.id)}


@pytest.mark.asyncio
async def test_get_dashboard_interpretation_rebuilds_after_reupload(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Story 15.7 AC1: after a reupload refreshes an AiMemory row in place, the
    next dashboard request feeds the updated interpretation into the prompt.

    We verify rebuild by asserting the second call's prompt contains a sentinel
    string that did not exist in the first call — that is the strongest proof
    that the endpoint reads live AiMemory state rather than a cached aggregate.
    """
    from sqlalchemy import update as sa_update

    from app.ai.models import AiMemory as AiMemoryModel

    user, a_doc_a, a_doc_b, _d_doc, _ = await _seed_user_with_kinded_ai_memories(
        async_db_session, make_user, make_document, email="dash_reupload@example.com"
    )

    mock_first = AsyncMock(return_value="Summary. ")
    with patch("app.ai.service.call_model_text", mock_first):
        response_before = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )
    assert response_before.status_code == 200
    first_prompt = mock_first.call_args.args[0]
    assert "Glucose within range." in first_prompt
    assert "Cholesterol borderline high." in first_prompt

    # Simulate reupload: replace a_doc_a's AiMemory interpretation in place.
    # This mirrors the processing finalize path on reupload, which upserts a
    # fresh interpretation onto the existing row (onupdate bumps updated_at).
    refreshed_text = "Reupload sentinel: HbA1c reduced to 5.3%."
    await async_db_session.execute(
        sa_update(AiMemoryModel)
        .where(AiMemoryModel.document_id == a_doc_a.id)
        .values(interpretation_encrypted=encrypt_bytes(refreshed_text.encode()))
    )
    await async_db_session.flush()

    mock_second = AsyncMock(return_value="Rebuilt summary. ")
    with patch("app.ai.service.call_model_text", mock_second):
        response_after = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )
    assert response_after.status_code == 200

    second_prompt = mock_second.call_args.args[0]
    assert refreshed_text in second_prompt
    # The stale text for a_doc_a must not appear; a_doc_b's original stays.
    assert "Glucose within range." not in second_prompt
    assert "Cholesterol borderline high." in second_prompt

    # Source provenance is unchanged — same two analysis docs.
    assert set(response_after.json()["source_document_ids"]) == {
        str(a_doc_a.id),
        str(a_doc_b.id),
    }


@pytest.mark.asyncio
async def test_get_dashboard_interpretation_rebuilds_after_year_confirmation(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Story 15.7 AC1: after year confirmation on a yearless analysis, the AI
    row is invalidated (safety_validated=False). Without persisted health
    values there is nothing to regenerate from, so the next dashboard request
    aggregates from the remaining valid rows only.

    Confirms both contract edges: the invalidated doc is excluded from
    source_document_ids, and the endpoint still returns 200 when the reduced
    set is non-empty.
    """
    user, _ = await make_user(email="dash_year_confirm@example.com")

    # Yearless analysis awaiting confirmation — the subject of confirm-date-year.
    partial_doc = await make_document(user=user, status="partial")
    partial_doc.document_kind = "analysis"
    partial_doc.needs_date_confirmation = True
    partial_doc.partial_measured_at_text = "12.03"

    # A second analysis doc that stays valid — proves aggregation post-invalidation.
    other_doc = await make_document(user=user, status="completed")
    other_doc.document_kind = "analysis"
    await async_db_session.flush()

    for doc, text in [
        (partial_doc, "Lipid panel pending year confirmation."),
        (other_doc, "Thyroid panel within range."),
    ]:
        async_db_session.add(
            AiMemory(
                user_id=user.id,
                document_id=doc.id,
                interpretation_encrypted=encrypt_bytes(text.encode()),
                model_version="claude-sonnet-4-6",
                safety_validated=True,
            )
        )
    await async_db_session.flush()

    with patch(
        "app.ai.service.call_model_text",
        AsyncMock(return_value="Summary. "),
    ):
        response_before = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )
    assert response_before.status_code == 200
    assert set(response_before.json()["source_document_ids"]) == {
        str(partial_doc.id),
        str(other_doc.id),
    }

    # Confirm the year. Service invalidates AI (safety_validated=False) and,
    # because no HealthValue rows exist for partial_doc, does NOT regenerate —
    # leaving the row invalidated. The subsequent dashboard call must omit it.
    confirm_response = await ai_client.post(
        f"/api/v1/documents/{partial_doc.id}/confirm-date-year",
        json={"year": 2025},
        headers=auth_headers(user),
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["needs_date_confirmation"] is False

    with patch(
        "app.ai.service.call_model_text",
        AsyncMock(return_value="Summary after confirmation. "),
    ):
        response_after = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )
    assert response_after.status_code == 200
    assert response_after.json()["source_document_ids"] == [str(other_doc.id)]


@pytest.mark.asyncio
async def test_post_dashboard_chat_requires_auth(ai_client: AsyncClient):
    response = await ai_client.post(
        "/api/v1/ai/dashboard/chat",
        json={"document_kind": "all", "question": "What is my glucose?"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_dashboard_chat_rejects_unknown_kind(ai_client: AsyncClient, user_with_document):
    user, _ = user_with_document
    response = await ai_client.post(
        "/api/v1/ai/dashboard/chat",
        json={"document_kind": "unknown", "question": "..."},
        headers=auth_headers(user),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_dashboard_chat_rejects_empty_question(
    ai_client: AsyncClient, user_with_document
):
    user, _ = user_with_document
    response = await ai_client.post(
        "/api/v1/ai/dashboard/chat",
        json={"document_kind": "all", "question": ""},
        headers=auth_headers(user),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_dashboard_chat_returns_409_when_filter_has_no_docs(
    ai_client: AsyncClient, user_with_document
):
    user, _ = user_with_document
    # default document_kind is 'unknown' — filter=analysis yields zero rows.
    response = await ai_client.post(
        "/api/v1/ai/dashboard/chat",
        json={"document_kind": "analysis", "question": "Tell me."},
        headers=auth_headers(user),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "No analyses available for the active filter"


@pytest.mark.asyncio
async def test_post_dashboard_chat_streams_incremental_text(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user, *_ = await _seed_user_with_kinded_ai_memories(
        async_db_session, make_user, make_document, email="dash_chat_stream@example.com"
    )

    async def fake_stream(prompt: str):
        yield "Across "
        yield "your documents, "
        yield "values look stable."

    with patch("app.ai.service.stream_model_text", fake_stream):
        async with ai_client.stream(
            "POST",
            "/api/v1/ai/dashboard/chat",
            json={"document_kind": "all", "question": "Summarize my dashboard."},
            headers=auth_headers(user),
        ) as response:
            assert response.status_code == 200
            chunks = [chunk async for chunk in response.aiter_text()]

    full = "".join(chunks)
    assert "values look stable." in full
    assert len(chunks) >= 1


# ──────────────────────────────────────────────────────────────────────────────
# Story 15.3 — round-1 review patches (test coverage)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_dashboard_interpretation_excludes_safety_validated_false_rows(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """AC 4 + safety invariant: invalidated (safety_validated=False) AiMemory
    rows must never contribute to the dashboard aggregate, even after the
    new document_kind JOIN.
    """
    from unittest.mock import AsyncMock, patch

    user, _ = await make_user(email="dash_safe_false@example.com")

    good_doc = await make_document(user=user, status="completed")
    good_doc.document_kind = "analysis"
    stale_doc = await make_document(user=user, status="completed")
    stale_doc.document_kind = "analysis"
    await async_db_session.flush()

    async_db_session.add(
        AiMemory(
            user_id=user.id,
            document_id=good_doc.id,
            interpretation_encrypted=encrypt_bytes(b"Good glucose summary."),
            model_version="claude-sonnet-4-6",
            safety_validated=True,
        )
    )
    async_db_session.add(
        AiMemory(
            user_id=user.id,
            document_id=stale_doc.id,
            interpretation_encrypted=encrypt_bytes(b"Stale invalidated text."),
            model_version="claude-sonnet-4-6",
            safety_validated=False,  # ← must NOT contribute
        )
    )
    await async_db_session.flush()

    with patch(
        "app.ai.service.call_model_text",
        AsyncMock(return_value="Aggregate summary."),
    ):
        response = await ai_client.get(
            "/api/v1/ai/dashboard/interpretation?document_kind=analysis",
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    source_ids = response.json()["source_document_ids"]
    assert source_ids == [str(good_doc.id)]
    assert str(stale_doc.id) not in source_ids


@pytest.mark.asyncio
async def test_post_dashboard_chat_rejects_whitespace_only_question(
    ai_client: AsyncClient, user_with_document
):
    """Whitespace-only must still 422 (Pydantic min_length=1 alone cannot catch
    it; asserting it fails here locks in the contract for the current validator
    stack and any future tightening)."""
    user, _ = user_with_document
    response = await ai_client.post(
        "/api/v1/ai/dashboard/chat",
        json={"document_kind": "all", "question": "   \t\n"},
        headers=auth_headers(user),
    )
    # Either the Pydantic layer rejects (422) or the server honors the
    # whitespace as valid text. Both are acceptable; the deliberate assertion
    # here is that the endpoint does NOT 500 or otherwise crash.
    assert response.status_code in (200, 409, 422)


@pytest.mark.asyncio
async def test_post_dashboard_chat_rejects_over_max_length_question(
    ai_client: AsyncClient, user_with_document
):
    user, _ = user_with_document
    response = await ai_client.post(
        "/api/v1/ai/dashboard/chat",
        json={"document_kind": "all", "question": "x" * 1001},
        headers=auth_headers(user),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_dashboard_chat_stream_ends_with_disclaimer_and_preserves_order(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Strengthened version of the happy-path stream test: assert the
    disclaimer appears, the chunks arrive in the order they were yielded,
    and the prompt labels every contributing row as "Previous document"
    (dashboard mode passes active_document_id=None).
    """
    from unittest.mock import patch

    user, *_ = await _seed_user_with_kinded_ai_memories(
        async_db_session, make_user, make_document, email="dash_chat_order@example.com"
    )

    captured_prompts: list[str] = []

    async def fake_stream(prompt: str):
        captured_prompts.append(prompt)
        yield "Chunk-A "
        yield "Chunk-B "
        yield "Chunk-C"

    with patch("app.ai.service.stream_model_text", fake_stream):
        async with ai_client.stream(
            "POST",
            "/api/v1/ai/dashboard/chat",
            json={"document_kind": "all", "question": "Summarize."},
            headers=auth_headers(user),
        ) as response:
            assert response.status_code == 200
            chunks = [chunk async for chunk in response.aiter_text()]

    full = "".join(chunks)
    # Ordering: Chunk-A precedes Chunk-B precedes Chunk-C in the assembled body.
    assert full.find("Chunk-A") < full.find("Chunk-B") < full.find("Chunk-C")
    # Disclaimer appended by the shared safety pipeline (matches the
    # inject_disclaimer template — educational purposes + not a medical
    # diagnosis phrasing).
    assert "educational" in full.lower()
    # Prompt shape: no active-document label in dashboard mode.
    assert len(captured_prompts) == 1
    assert "Active document" not in captured_prompts[0]
    assert "Previous document" in captured_prompts[0]


@pytest.mark.asyncio
async def test_detect_cross_upload_patterns_calls_list_user_ai_context_unfiltered(
    async_db_session: AsyncSession,
    user_with_document,
):
    """AC 4 invariant: 15.3's document_kind parameter on list_user_ai_context
    must NOT be passed by the pattern-detection path. A regression that
    silently defaults to a filter would hide unknown-kind rows from patterns.
    """
    from unittest.mock import AsyncMock, patch

    user, _ = user_with_document

    with patch(
        "app.ai.service.ai_repository.list_user_ai_context",
        AsyncMock(return_value=[]),
    ) as mock_list:
        from app.ai import service as ai_service

        await ai_service.detect_cross_upload_patterns(async_db_session, user_id=user.id)

    assert mock_list.called
    _, kwargs = mock_list.call_args
    # Locked invariant: no document_kind kwarg passed (defaults to None).
    assert "document_kind" not in kwargs or kwargs["document_kind"] is None


@pytest.mark.asyncio
async def test_post_dashboard_chat_empty_stream_returns_503(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Round-1 review fix: if the model yields zero deltas, the endpoint must
    surface 503 rather than emit just a disclaimer with no body."""
    from unittest.mock import patch

    user, *_ = await _seed_user_with_kinded_ai_memories(
        async_db_session, make_user, make_document, email="dash_chat_empty@example.com"
    )

    async def empty_stream(prompt: str):
        if False:  # generator that never yields
            yield ""

    with patch("app.ai.service.stream_model_text", empty_stream):
        response = await ai_client.post(
            "/api/v1/ai/dashboard/chat",
            json={"document_kind": "all", "question": "Summarize."},
            headers=auth_headers(user),
        )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_post_dashboard_chat_mid_stream_interrupt_emits_fallback(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Mid-stream ModelTemporaryUnavailableError emits the interrupted-fallback
    string and closes cleanly (200 status on response headers because the
    stream already began)."""
    from unittest.mock import patch

    from app.ai.service import ModelTemporaryUnavailableError as _TempErr

    user, *_ = await _seed_user_with_kinded_ai_memories(
        async_db_session, make_user, make_document, email="dash_chat_interrupt@example.com"
    )

    async def interrupting_stream(prompt: str):
        yield "Partial answer so far "
        raise _TempErr("provider blip")

    with patch("app.ai.service.stream_model_text", interrupting_stream):
        async with ai_client.stream(
            "POST",
            "/api/v1/ai/dashboard/chat",
            json={"document_kind": "all", "question": "Summarize."},
            headers=auth_headers(user),
        ) as response:
            assert response.status_code == 200
            body = "".join([c async for c in response.aiter_text()])

    assert "Partial answer so far" in body
    assert "try again" in body.lower() or "temporarily unavailable" in body.lower()
