"""Tests for AI interpretation repository reasoning persistence."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import repository as ai_repository
from app.ai.models import AiMemory


def _reasoning_payload() -> dict[str, object]:
    return {
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


@pytest.mark.asyncio
async def test_upsert_stores_reasoning_json(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user, _ = await make_user(email="ai_repo_reasoning@example.com")
    document = await make_document(user=user, status="completed")
    reasoning = _reasoning_payload()

    await ai_repository.upsert_ai_interpretation(
        async_db_session,
        user_id=user.id,
        document_id=document.id,
        interpretation_text="Your glucose is normal.",
        model_version="claude-sonnet-4-6",
        reasoning_json=reasoning,
    )

    result = await ai_repository.get_interpretation_and_metadata(
        async_db_session,
        user_id=user.id,
        document_id=document.id,
    )

    assert result is not None
    interpretation, stored_reasoning, memory = result
    assert interpretation == "Your glucose is normal."
    assert stored_reasoning == reasoning
    assert memory.document_id == document.id


@pytest.mark.asyncio
async def test_upsert_stores_no_reasoning_when_none(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user, _ = await make_user(email="ai_repo_no_reasoning@example.com")
    document = await make_document(user=user, status="completed")

    await ai_repository.upsert_ai_interpretation(
        async_db_session,
        user_id=user.id,
        document_id=document.id,
        interpretation_text="Your glucose is normal.",
        model_version="claude-sonnet-4-6",
        reasoning_json=None,
    )

    result = await ai_repository.get_interpretation_and_metadata(
        async_db_session,
        user_id=user.id,
        document_id=document.id,
    )

    assert result is not None
    _, stored_reasoning, _ = result
    assert stored_reasoning is None


@pytest.mark.asyncio
async def test_reasoning_roundtrip_encrypted(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user, _ = await make_user(email="ai_repo_encrypted@example.com")
    document = await make_document(user=user, status="completed")
    reasoning = _reasoning_payload()

    memory = await ai_repository.upsert_ai_interpretation(
        async_db_session,
        user_id=user.id,
        document_id=document.id,
        interpretation_text="Your glucose is normal.",
        model_version="claude-sonnet-4-6",
        reasoning_json=reasoning,
    )

    result = await async_db_session.execute(
        select(AiMemory).where(AiMemory.id == memory.id)
    )
    stored_memory = result.scalar_one()

    assert isinstance(stored_memory.context_json_encrypted, bytes)
    assert stored_memory.context_json_encrypted != b""
    assert b'"values_referenced"' not in stored_memory.context_json_encrypted


@pytest.mark.asyncio
async def test_list_user_ai_context_returns_active_document_first(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user, _ = await make_user(email="ai_context_order@example.com")
    doc1 = await make_document(user=user, status="completed")
    doc2 = await make_document(user=user, status="completed")

    await ai_repository.upsert_ai_interpretation(
        async_db_session,
        user_id=user.id,
        document_id=doc1.id,
        interpretation_text="Interpretation for doc1.",
        model_version="claude-sonnet-4-6",
    )
    await ai_repository.upsert_ai_interpretation(
        async_db_session,
        user_id=user.id,
        document_id=doc2.id,
        interpretation_text="Interpretation for doc2.",
        model_version="claude-sonnet-4-6",
    )

    context = await ai_repository.list_user_ai_context(
        async_db_session,
        user_id=user.id,
        active_document_id=doc2.id,
    )

    assert len(context) == 2
    # Active document must come first
    assert context[0]["document_id"] == str(doc2.id)
    assert context[0]["interpretation"] == "Interpretation for doc2."
    assert context[1]["document_id"] == str(doc1.id)


@pytest.mark.asyncio
async def test_list_user_ai_context_skips_corrupt_rows(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user, _ = await make_user(email="ai_context_corrupt@example.com")
    doc_good = await make_document(user=user, status="completed")
    doc_bad = await make_document(user=user, status="completed")

    # Good row via normal upsert
    await ai_repository.upsert_ai_interpretation(
        async_db_session,
        user_id=user.id,
        document_id=doc_good.id,
        interpretation_text="Valid interpretation.",
        model_version="claude-sonnet-4-6",
    )

    # Bad row: corrupt interpretation bytes, should be skipped
    corrupt_memory = AiMemory(
        user_id=user.id,
        document_id=doc_bad.id,
        interpretation_encrypted=b"not-valid-encrypted",
        model_version="claude-sonnet-4-6",
        safety_validated=True,
    )
    async_db_session.add(corrupt_memory)
    await async_db_session.flush()

    context = await ai_repository.list_user_ai_context(
        async_db_session,
        user_id=user.id,
    )

    # Only the valid row is returned; corrupt row is skipped gracefully
    assert len(context) == 1
    assert context[0]["interpretation"] == "Valid interpretation."


# ──────────────────────────────────────────────────────────────────────────────
# Story 15.3 — document_kind filter on list_user_ai_context
# ──────────────────────────────────────────────────────────────────────────────


async def _seed_three_kinds(
    db: AsyncSession, make_user, make_document, *, email: str
):
    from app.core.encryption import encrypt_bytes as _enc

    user, _ = await make_user(email=email)

    a_doc = await make_document(user=user, status="completed")
    a_doc.document_kind = "analysis"
    d_doc = await make_document(user=user, status="completed")
    d_doc.document_kind = "document"
    u_doc = await make_document(user=user, status="failed")
    u_doc.document_kind = "unknown"
    await db.flush()

    for doc, label in [(a_doc, "A"), (d_doc, "D"), (u_doc, "U")]:
        db.add(
            AiMemory(
                user_id=user.id,
                document_id=doc.id,
                interpretation_encrypted=__import__("app.core.encryption", fromlist=["encrypt_bytes"]).encrypt_bytes(label.encode()),
                model_version="claude-sonnet-4-6",
                safety_validated=True,
            )
        )
    await db.flush()

    return user, a_doc, d_doc, u_doc


@pytest.mark.asyncio
async def test_list_user_ai_context_no_filter_returns_every_kind(
    async_db_session: AsyncSession, make_user, make_document
):
    user, *_ = await _seed_three_kinds(
        async_db_session, make_user, make_document, email="repo_ctx_none@example.com"
    )

    rows = await ai_repository.list_user_ai_context(async_db_session, user_id=user.id)

    assert len(rows) == 3
    texts = {r["interpretation"] for r in rows}
    assert texts == {"A", "D", "U"}


@pytest.mark.asyncio
async def test_list_user_ai_context_all_excludes_unknown(
    async_db_session: AsyncSession, make_user, make_document
):
    user, *_ = await _seed_three_kinds(
        async_db_session, make_user, make_document, email="repo_ctx_all@example.com"
    )

    rows = await ai_repository.list_user_ai_context(
        async_db_session, user_id=user.id, document_kind="all"
    )

    texts = {r["interpretation"] for r in rows}
    assert texts == {"A", "D"}
    assert "U" not in texts


@pytest.mark.asyncio
async def test_list_user_ai_context_analysis_only(
    async_db_session: AsyncSession, make_user, make_document
):
    user, *_ = await _seed_three_kinds(
        async_db_session, make_user, make_document, email="repo_ctx_analysis@example.com"
    )

    rows = await ai_repository.list_user_ai_context(
        async_db_session, user_id=user.id, document_kind="analysis"
    )

    assert len(rows) == 1
    assert rows[0]["interpretation"] == "A"


@pytest.mark.asyncio
async def test_list_user_ai_context_document_only(
    async_db_session: AsyncSession, make_user, make_document
):
    user, *_ = await _seed_three_kinds(
        async_db_session, make_user, make_document, email="repo_ctx_document@example.com"
    )

    rows = await ai_repository.list_user_ai_context(
        async_db_session, user_id=user.id, document_kind="document"
    )

    assert len(rows) == 1
    assert rows[0]["interpretation"] == "D"


@pytest.mark.asyncio
async def test_list_user_ai_context_ownership_scoped_via_join(
    async_db_session: AsyncSession, make_user, make_document
):
    """JOIN now pins Document.user_id as defense-in-depth; a cross-user FK
    inconsistency cannot leak rows even if AiMemory.user_id is bypassed."""
    user_a, *_ = await _seed_three_kinds(
        async_db_session, make_user, make_document, email="repo_ctx_own_a@example.com"
    )
    user_b, *_ = await _seed_three_kinds(
        async_db_session, make_user, make_document, email="repo_ctx_own_b@example.com"
    )

    rows = await ai_repository.list_user_ai_context(
        async_db_session, user_id=user_a.id, document_kind="all"
    )
    assert len(rows) == 2
