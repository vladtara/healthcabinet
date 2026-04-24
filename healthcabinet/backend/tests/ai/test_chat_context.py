"""Tests for injecting the overall/main clinical note into AI-assistant chat.

The prompt assembled for `stream_follow_up_answer` and `_build_follow_up_prompt`
should carry a `[Main health summary]` section when the user has a persisted
overall note (ai_memories with scope='overall_all'), and should omit that
section cleanly when no overall note exists.
"""

from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import repository as ai_repository
from app.ai.models import AiMemory
from app.ai.service import (
    _build_follow_up_prompt,
    stream_dashboard_follow_up,
    stream_follow_up_answer,
)
from app.core.encryption import encrypt_bytes


def test_build_follow_up_prompt_without_main_summary_has_no_anchor_block():
    prompt = _build_follow_up_prompt(
        context_rows=[
            {
                "document_id": "11111111-1111-1111-1111-111111111111",
                "interpretation": "Doc A text.",
            }
        ],
        question="How am I doing?",
        output_language="en",
        main_summary=None,
    )
    assert "Main health summary" not in prompt
    assert "Doc A text." in prompt


def test_build_follow_up_prompt_with_main_summary_emits_anchor_block():
    prompt = _build_follow_up_prompt(
        context_rows=[
            {
                "document_id": "11111111-1111-1111-1111-111111111111",
                "interpretation": "Doc A text.",
            }
        ],
        question="How am I doing?",
        output_language="en",
        main_summary=("Your cholesterol has drifted up over 6 months.", None),
    )
    assert "Main health summary" in prompt
    assert "Your cholesterol has drifted up" in prompt
    # The anchor block should come before the per-document context so the
    # model treats it as the overarching frame.
    anchor_idx = prompt.index("Main health summary")
    doc_idx = prompt.index("Doc A text.")
    assert anchor_idx < doc_idx


@pytest.mark.asyncio
async def test_stream_follow_up_injects_main_summary_when_present(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user, _ = await make_user(email="chat_ctx_with_main@example.com")
    doc = await make_document(user=user, status="completed")
    async_db_session.add(
        AiMemory(
            user_id=user.id,
            document_id=doc.id,
            interpretation_encrypted=encrypt_bytes(b"Per-doc interpretation text."),
            model_version="claude-sonnet-4-6",
            safety_validated=True,
        )
    )
    await async_db_session.flush()

    await ai_repository.upsert_overall_interpretation(
        async_db_session,
        user_id=user.id,
        interpretation_text="Anchor: trending upward across labs.",
        model_version="claude-sonnet-4-6",
        reasoning_json={"source_document_ids": [str(doc.id)], "locale": "en"},
    )
    await async_db_session.flush()

    captured_prompts: list[str] = []

    async def _fake_stream(prompt: str):
        captured_prompts.append(prompt)
        yield "ok"

    with patch("app.ai.service.stream_model_text", _fake_stream):
        stream = await stream_follow_up_answer(
            async_db_session,
            user_id=user.id,
            document_id=doc.id,
            question="What patterns do you see?",
        )
        # Drain the stream so the prompt is actually captured.
        async for _ in stream:
            pass

    assert captured_prompts, "stream_model_text was not called"
    prompt = captured_prompts[0]
    assert "Main health summary" in prompt
    assert "Anchor: trending upward across labs." in prompt
    assert "Per-doc interpretation text." in prompt


@pytest.mark.asyncio
async def test_stream_follow_up_omits_main_summary_when_absent(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user, _ = await make_user(email="chat_ctx_no_main@example.com")
    doc = await make_document(user=user, status="completed")
    async_db_session.add(
        AiMemory(
            user_id=user.id,
            document_id=doc.id,
            interpretation_encrypted=encrypt_bytes(b"Only per-doc text."),
            model_version="claude-sonnet-4-6",
            safety_validated=True,
        )
    )
    await async_db_session.flush()

    captured_prompts: list[str] = []

    async def _fake_stream(prompt: str):
        captured_prompts.append(prompt)
        yield "ok"

    with patch("app.ai.service.stream_model_text", _fake_stream):
        stream = await stream_follow_up_answer(
            async_db_session,
            user_id=user.id,
            document_id=doc.id,
            question="What do my labs say?",
        )
        async for _ in stream:
            pass

    assert captured_prompts
    assert "Main health summary" not in captured_prompts[0]
    assert "Only per-doc text." in captured_prompts[0]


def test_build_follow_up_prompt_with_filter_summary_emits_filter_block():
    prompt = _build_follow_up_prompt(
        context_rows=[
            {
                "document_id": "11111111-1111-1111-1111-111111111111",
                "interpretation": "Doc A text.",
            }
        ],
        question="Any trend in my analyses?",
        output_language="en",
        main_summary=("Overall anchor summary.", None),
        filter_summary=("analysis", "Filter-specific analysis narrative.", None),
    )
    assert "Main health summary" in prompt
    assert "Filter view: analysis" in prompt
    assert "Filter-specific analysis narrative." in prompt
    # Main summary must still come before the filter-specific view so the
    # model treats "all" as the overarching anchor.
    assert prompt.index("Main health summary") < prompt.index("Filter view: analysis")


@pytest.mark.asyncio
async def test_stream_dashboard_follow_up_injects_filter_summary(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Dashboard chat scoped to `analysis` should inject BOTH the overall_all
    anchor and the cached overall_analysis filter view into the prompt."""
    user, _ = await make_user(email="dash_chat_filter@example.com")
    doc = await make_document(user=user, status="completed")
    doc.document_kind = "analysis"
    async_db_session.add(
        AiMemory(
            user_id=user.id,
            document_id=doc.id,
            interpretation_encrypted=encrypt_bytes(b"Per-doc analysis interpretation."),
            model_version="claude-sonnet-4-6",
            safety_validated=True,
        )
    )
    await async_db_session.flush()

    await ai_repository.upsert_overall_interpretation(
        async_db_session,
        user_id=user.id,
        interpretation_text="Anchor overall narrative.",
        model_version="claude-sonnet-4-6",
        reasoning_json={"source_document_ids": [str(doc.id)], "locale": "en"},
        scope=ai_repository.OVERALL_SCOPE_ALL,
    )
    await ai_repository.upsert_overall_interpretation(
        async_db_session,
        user_id=user.id,
        interpretation_text="Analysis-only narrative body.",
        model_version="claude-sonnet-4-6",
        reasoning_json={"source_document_ids": [str(doc.id)], "locale": "en"},
        scope=ai_repository.OVERALL_SCOPE_ANALYSIS,
    )
    await async_db_session.flush()

    captured_prompts: list[str] = []

    async def _fake_stream(prompt: str):
        captured_prompts.append(prompt)
        yield "ok"

    with patch("app.ai.service.stream_model_text", _fake_stream):
        stream = await stream_dashboard_follow_up(
            async_db_session,
            user_id=user.id,
            document_kind="analysis",
            question="What's going on?",
        )
        async for _ in stream:
            pass

    assert captured_prompts
    prompt = captured_prompts[0]
    assert "Main health summary" in prompt
    assert "Anchor overall narrative." in prompt
    assert "Filter view: analysis" in prompt
    assert "Analysis-only narrative body." in prompt


@pytest.mark.asyncio
async def test_stream_dashboard_follow_up_anchor_only_when_no_filter_cache(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Dashboard chat scoped to `analysis` with NO overall_analysis cache row
    should still inject the overall_all anchor but omit the filter view."""
    user, _ = await make_user(email="dash_chat_anchor_only@example.com")
    doc = await make_document(user=user, status="completed")
    doc.document_kind = "analysis"
    async_db_session.add(
        AiMemory(
            user_id=user.id,
            document_id=doc.id,
            interpretation_encrypted=encrypt_bytes(b"Per-doc analysis interpretation."),
            model_version="claude-sonnet-4-6",
            safety_validated=True,
        )
    )
    await async_db_session.flush()

    await ai_repository.upsert_overall_interpretation(
        async_db_session,
        user_id=user.id,
        interpretation_text="Anchor-only narrative.",
        model_version="claude-sonnet-4-6",
        reasoning_json={"source_document_ids": [str(doc.id)], "locale": "en"},
        scope=ai_repository.OVERALL_SCOPE_ALL,
    )
    await async_db_session.flush()

    captured_prompts: list[str] = []

    async def _fake_stream(prompt: str):
        captured_prompts.append(prompt)
        yield "ok"

    with patch("app.ai.service.stream_model_text", _fake_stream):
        stream = await stream_dashboard_follow_up(
            async_db_session,
            user_id=user.id,
            document_kind="analysis",
            question="What's going on?",
        )
        async for _ in stream:
            pass

    assert captured_prompts
    prompt = captured_prompts[0]
    assert "Main health summary" in prompt
    assert "Anchor-only narrative." in prompt
    assert "Filter view:" not in prompt
