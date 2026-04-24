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


# ---------------------------------------------------------------------------
# User profile injection + recent-messages injection
# ---------------------------------------------------------------------------


def test_build_profile_block_empty_returns_none():
    from app.ai.service import _build_profile_block
    from app.users.repository import ProfileContext

    assert _build_profile_block(None) is None
    empty = ProfileContext(
        age=None, sex=None, known_conditions=[], medications=[], family_history=None
    )
    assert _build_profile_block(empty) is None


def test_build_profile_block_renders_only_filled_fields():
    from app.ai.service import _build_profile_block
    from app.users.repository import ProfileContext

    partial = ProfileContext(
        age=42,
        sex=None,
        known_conditions=["hypothyroidism"],
        medications=[],
        family_history=None,
    )
    block = _build_profile_block(partial)
    assert block is not None
    assert "Age: 42" in block
    assert "Known conditions: hypothyroidism" in block
    # Missing fields are omitted, never printed as "Unknown".
    assert "Sex:" not in block
    assert "Current medications:" not in block
    assert "Family history:" not in block


def test_build_follow_up_prompt_profile_block_precedes_main_summary():
    from app.ai.service import _build_follow_up_prompt

    prompt = _build_follow_up_prompt(
        context_rows=[{"document_id": "11111111-1111-1111-1111-111111111111", "interpretation": "Doc A"}],
        question="q?",
        output_language="en",
        main_summary=("Anchor body.", None),
        profile_block="[User profile]\nAge: 34\nSex: female",
    )
    assert "[User profile]" in prompt
    assert "Age: 34" in prompt
    assert prompt.index("[User profile]") < prompt.index("Main health summary")


def test_build_follow_up_prompt_recent_messages_precede_user_question():
    import datetime as _dt
    import uuid as _uuid

    from app.ai.repository import ChatMessageRecord
    from app.ai.service import _build_follow_up_prompt

    recent = [
        ChatMessageRecord(
            id=_uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            thread_id="t",
            role="user",
            text="earlier question",
            created_at=_dt.datetime(2026, 4, 24, 10, 0, tzinfo=_dt.UTC),
        ),
        ChatMessageRecord(
            id=_uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            thread_id="t",
            role="assistant",
            text="earlier answer",
            created_at=_dt.datetime(2026, 4, 24, 10, 1, tzinfo=_dt.UTC),
        ),
    ]
    prompt = _build_follow_up_prompt(
        context_rows=[{"document_id": "11111111-1111-1111-1111-111111111111", "interpretation": "Doc A"}],
        question="the new question",
        output_language="en",
        recent_messages=recent,
    )
    assert "[Recent conversation]" in prompt
    assert "User: earlier question" in prompt
    assert "Assistant: earlier answer" in prompt
    assert prompt.index("[Recent conversation]") < prompt.index("the new question")


@pytest.mark.asyncio
async def test_stream_follow_up_injects_profile_block_when_present(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """stream_follow_up_answer reads the user's profile context (decrypted)
    and injects it into the prompt."""
    from app.ai.service import stream_follow_up_answer
    from app.users.repository import upsert_user_profile

    user, _ = await make_user(email="prof_inj@example.com")
    doc = await make_document(user=user, status="completed")
    async_db_session.add(
        AiMemory(
            user_id=user.id,
            document_id=doc.id,
            interpretation_encrypted=encrypt_bytes(b"Per-doc interpretation."),
            model_version="claude-sonnet-4-6",
            safety_validated=True,
        )
    )
    await upsert_user_profile(
        async_db_session,
        user.id,
        age=55,
        sex="male",
        known_conditions=["type 2 diabetes"],
        medications=["metformin 500mg"],
    )
    await async_db_session.flush()

    captured: list[str] = []

    async def _fake_stream(prompt: str):
        captured.append(prompt)
        yield "ok"

    with patch("app.ai.service.stream_model_text", _fake_stream):
        stream = await stream_follow_up_answer(
            async_db_session,
            user_id=user.id,
            document_id=doc.id,
            question="How about my HbA1c?",
        )
        async for _ in stream:
            pass

    assert captured
    p = captured[0]
    assert "[User profile]" in p
    assert "Age: 55" in p
    assert "Sex: male" in p
    assert "type 2 diabetes" in p
    assert "metformin 500mg" in p


@pytest.mark.asyncio
async def test_stream_follow_up_omits_profile_block_when_empty(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    from app.ai.service import stream_follow_up_answer

    user, _ = await make_user(email="prof_empty@example.com")
    doc = await make_document(user=user, status="completed")
    async_db_session.add(
        AiMemory(
            user_id=user.id,
            document_id=doc.id,
            interpretation_encrypted=encrypt_bytes(b"Per-doc."),
            model_version="claude-sonnet-4-6",
            safety_validated=True,
        )
    )
    await async_db_session.flush()

    captured: list[str] = []

    async def _fake_stream(prompt: str):
        captured.append(prompt)
        yield "ok"

    with patch("app.ai.service.stream_model_text", _fake_stream):
        stream = await stream_follow_up_answer(
            async_db_session,
            user_id=user.id,
            document_id=doc.id,
            question="q",
        )
        async for _ in stream:
            pass

    assert captured
    assert "[User profile]" not in captured[0]


@pytest.mark.asyncio
async def test_stream_follow_up_injects_prior_messages_as_recent_conversation(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    from app.ai.service import stream_follow_up_answer

    user, _ = await make_user(email="recent_msgs@example.com")
    doc = await make_document(user=user, status="completed")
    async_db_session.add(
        AiMemory(
            user_id=user.id,
            document_id=doc.id,
            interpretation_encrypted=encrypt_bytes(b"Per-doc."),
            model_version="claude-sonnet-4-6",
            safety_validated=True,
        )
    )
    await async_db_session.flush()

    thread_id = ai_repository.thread_id_for_document(user.id, doc.id)
    await ai_repository.append_chat_message(
        async_db_session, user_id=user.id, thread_id=thread_id, role="user", text="earlier q"
    )
    await ai_repository.append_chat_message(
        async_db_session,
        user_id=user.id,
        thread_id=thread_id,
        role="assistant",
        text="earlier a",
    )
    await async_db_session.flush()

    captured: list[str] = []

    async def _fake_stream(prompt: str):
        captured.append(prompt)
        yield "ok"

    with patch("app.ai.service.stream_model_text", _fake_stream):
        stream = await stream_follow_up_answer(
            async_db_session,
            user_id=user.id,
            document_id=doc.id,
            question="new question",
        )
        async for _ in stream:
            pass

    assert captured
    p = captured[0]
    assert "[Recent conversation]" in p
    assert "User: earlier q" in p
    assert "Assistant: earlier a" in p
