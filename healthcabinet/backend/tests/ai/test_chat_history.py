"""Tests for persistent AI chat history (ai_chat_messages table).

Covers:
- append + list roundtrip (encryption transparent to callers)
- Thread isolation between (user, thread_id)
- Pagination via `before` cursor
- Clear-thread only wipes one thread
- `thread_id_for_document` / `thread_id_for_dashboard` helpers are pure
- Streaming chat persists user message before streaming and assistant
  message after successful completion
- Stream abort / safety block → no assistant row written
- Router endpoints return RFC 7807-shaped errors on ownership violations
- Filter switch on dashboard chat picks up a different thread
"""

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import repository as ai_repository
from app.ai.models import AiChatMessage, AiMemory
from app.auth.models import User
from app.core.database import get_db
from app.core.encryption import decrypt_bytes, encrypt_bytes
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


# ---------------------------------------------------------------------------
# Repository layer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_append_then_list_roundtrip(
    async_db_session: AsyncSession,
    make_user,
):
    user, _ = await make_user(email="chatroundtrip@example.com")
    thread_id = ai_repository.thread_id_for_dashboard(user.id, "all")

    u = await ai_repository.append_chat_message(
        async_db_session, user_id=user.id, thread_id=thread_id, role="user", text="hi"
    )
    a = await ai_repository.append_chat_message(
        async_db_session, user_id=user.id, thread_id=thread_id, role="assistant", text="hello"
    )
    await async_db_session.flush()

    # Verify ciphertext is stored, not plaintext.
    row = (await async_db_session.execute(select(AiChatMessage).where(AiChatMessage.id == u.id))).scalar_one()
    assert row.text_encrypted != b"hi"
    assert decrypt_bytes(row.text_encrypted).decode() == "hi"

    records = await ai_repository.list_chat_messages(
        async_db_session, user_id=user.id, thread_id=thread_id
    )
    assert [(r.role, r.text) for r in records] == [("user", "hi"), ("assistant", "hello")]
    # created_at ordering is ASC (oldest first).
    assert records[0].created_at <= records[1].created_at
    assert records[0].id == u.id
    assert records[1].id == a.id


@pytest.mark.asyncio
async def test_list_chat_messages_thread_isolation(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user, _ = await make_user(email="threadsep@example.com")
    doc = await make_document(user=user, status="completed")

    dash_thread = ai_repository.thread_id_for_dashboard(user.id, "all")
    doc_thread = ai_repository.thread_id_for_document(user.id, doc.id)

    await ai_repository.append_chat_message(
        async_db_session, user_id=user.id, thread_id=dash_thread, role="user", text="dash"
    )
    await ai_repository.append_chat_message(
        async_db_session, user_id=user.id, thread_id=doc_thread, role="user", text="doc"
    )
    await async_db_session.flush()

    dash_msgs = await ai_repository.list_chat_messages(
        async_db_session, user_id=user.id, thread_id=dash_thread
    )
    doc_msgs = await ai_repository.list_chat_messages(
        async_db_session, user_id=user.id, thread_id=doc_thread
    )
    assert [m.text for m in dash_msgs] == ["dash"]
    assert [m.text for m in doc_msgs] == ["doc"]


@pytest.mark.asyncio
async def test_list_chat_messages_pagination_via_before_cursor(
    async_db_session: AsyncSession,
    make_user,
):
    """Inserts with explicit created_at timestamps so ordering is
    deterministic. Within a single Postgres transaction `now()` returns the
    transaction start time, which would otherwise tie every row's created_at
    and force the test to rely on UUID ordering (non-deterministic).
    """
    import datetime as _dt

    user, _ = await make_user(email="pagination@example.com")
    thread_id = ai_repository.thread_id_for_dashboard(user.id, "all")

    base = _dt.datetime(2026, 4, 24, 10, 0, tzinfo=_dt.UTC)
    created_ids: list[uuid.UUID] = []
    for idx in range(5):
        row = AiChatMessage(
            user_id=user.id,
            thread_id=thread_id,
            role="user",
            text_encrypted=encrypt_bytes(f"msg {idx}".encode()),
            created_at=base + _dt.timedelta(seconds=idx),
        )
        async_db_session.add(row)
        await async_db_session.flush()
        created_ids.append(row.id)

    # Get newest 3 first.
    newest = await ai_repository.list_chat_messages(
        async_db_session, user_id=user.id, thread_id=thread_id, limit=3
    )
    assert [m.text for m in newest] == ["msg 2", "msg 3", "msg 4"]

    # Page back using `before` = id of the oldest in the returned page.
    older = await ai_repository.list_chat_messages(
        async_db_session,
        user_id=user.id,
        thread_id=thread_id,
        limit=3,
        before=newest[0].id,
    )
    assert [m.text for m in older] == ["msg 0", "msg 1"]


@pytest.mark.asyncio
async def test_clear_chat_thread_only_wipes_target(
    async_db_session: AsyncSession,
    make_user,
):
    user, _ = await make_user(email="clearthread@example.com")
    thread_a = ai_repository.thread_id_for_dashboard(user.id, "all")
    thread_b = ai_repository.thread_id_for_dashboard(user.id, "analysis")

    await ai_repository.append_chat_message(
        async_db_session, user_id=user.id, thread_id=thread_a, role="user", text="a"
    )
    await ai_repository.append_chat_message(
        async_db_session, user_id=user.id, thread_id=thread_b, role="user", text="b"
    )
    await async_db_session.flush()

    deleted = await ai_repository.clear_chat_thread(
        async_db_session, user_id=user.id, thread_id=thread_a
    )
    assert deleted == 1
    await async_db_session.flush()

    assert (
        await ai_repository.list_chat_messages(
            async_db_session, user_id=user.id, thread_id=thread_a
        )
        == []
    )
    b_msgs = await ai_repository.list_chat_messages(
        async_db_session, user_id=user.id, thread_id=thread_b
    )
    assert [m.text for m in b_msgs] == ["b"]


@pytest.mark.asyncio
async def test_thread_id_helpers_are_pure():
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    doc_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    assert (
        ai_repository.thread_id_for_document(user_id, doc_id)
        == f"doc:{user_id}:{doc_id}"
    )
    assert ai_repository.thread_id_for_dashboard(user_id, "analysis") == (
        f"dash:{user_id}:analysis"
    )


# ---------------------------------------------------------------------------
# Streaming handlers persist the right rows.
# ---------------------------------------------------------------------------


async def _seed_doc_with_interpretation(
    db: AsyncSession,
    make_user,
    make_document,
    *,
    email: str,
) -> tuple[User, uuid.UUID]:
    user, _ = await make_user(email=email)
    doc = await make_document(user=user, status="completed")
    db.add(
        AiMemory(
            user_id=user.id,
            document_id=doc.id,
            interpretation_encrypted=encrypt_bytes(b"Per-doc interpretation text."),
            model_version="claude-sonnet-4-6",
            safety_validated=True,
        )
    )
    await db.flush()
    return user, doc.id


@pytest.mark.asyncio
async def test_stream_follow_up_persists_user_and_assistant(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    from app.ai.service import stream_follow_up_answer

    user, doc_id = await _seed_doc_with_interpretation(
        async_db_session, make_user, make_document, email="persist_both@example.com"
    )

    async def _fake_stream(prompt: str):
        yield "Sure, "
        yield "here's the answer."

    with patch("app.ai.service.stream_model_text", _fake_stream):
        stream = await stream_follow_up_answer(
            async_db_session,
            user_id=user.id,
            document_id=doc_id,
            question="What does this mean?",
        )
        async for _ in stream:
            pass

    thread_id = ai_repository.thread_id_for_document(user.id, doc_id)
    records = await ai_repository.list_chat_messages(
        async_db_session, user_id=user.id, thread_id=thread_id
    )
    assert [(r.role, r.text) for r in records] == [
        ("user", "What does this mean?"),
        ("assistant", "Sure, here's the answer."),
    ]


@pytest.mark.asyncio
async def test_stream_follow_up_does_not_persist_assistant_on_empty_reply(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """A cumulative-empty stream must not leave an orphan assistant row."""
    from app.ai.service import stream_follow_up_answer

    user, doc_id = await _seed_doc_with_interpretation(
        async_db_session, make_user, make_document, email="empty_reply@example.com"
    )

    async def _empty_stream(prompt: str):
        if False:
            yield "unreachable"
        return

    with patch("app.ai.service.stream_model_text", _empty_stream):
        stream = await stream_follow_up_answer(
            async_db_session,
            user_id=user.id,
            document_id=doc_id,
            question="?",
        )
        async for _ in stream:
            pass

    thread_id = ai_repository.thread_id_for_document(user.id, doc_id)
    records = await ai_repository.list_chat_messages(
        async_db_session, user_id=user.id, thread_id=thread_id
    )
    # Only the user row should be there.
    assert [(r.role, r.text) for r in records] == [("user", "?")]


@pytest.mark.asyncio
async def test_stream_follow_up_does_not_persist_assistant_on_safety_block(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Safety-blocked replies emit a fallback chunk to the client but must not
    be stored as an assistant row in the audit table."""
    from app.ai.safety import SafetyValidationError
    from app.ai.service import stream_follow_up_answer

    user, doc_id = await _seed_doc_with_interpretation(
        async_db_session, make_user, make_document, email="safety_block@example.com"
    )

    async def _stream(prompt: str):
        yield "This looks like "
        yield "a diagnosis statement."

    async def _validate(text: str) -> str:
        if "diagnosis" in text:
            raise SafetyValidationError("simulated diagnostic")
        return text

    with (
        patch("app.ai.service.stream_model_text", _stream),
        patch("app.ai.service.validate_no_diagnostic", _validate),
    ):
        stream = await stream_follow_up_answer(
            async_db_session,
            user_id=user.id,
            document_id=doc_id,
            question="What is this?",
        )
        async for _ in stream:
            pass

    thread_id = ai_repository.thread_id_for_document(user.id, doc_id)
    records = await ai_repository.list_chat_messages(
        async_db_session, user_id=user.id, thread_id=thread_id
    )
    assert [(r.role, r.text) for r in records] == [("user", "What is this?")]


@pytest.mark.asyncio
async def test_dashboard_chat_thread_is_scoped_per_filter(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Switching filter from `all` to `analysis` picks up a different thread —
    previous messages in the `all` thread are not returned for `analysis`."""
    from app.ai.service import stream_dashboard_follow_up

    user, _ = await make_user(email="filter_split@example.com")
    doc = await make_document(user=user, status="completed")
    doc.document_kind = "analysis"
    async_db_session.add(
        AiMemory(
            user_id=user.id,
            document_id=doc.id,
            interpretation_encrypted=encrypt_bytes(b"Analysis doc interpretation."),
            model_version="claude-sonnet-4-6",
            safety_validated=True,
        )
    )
    await async_db_session.flush()

    async def _fake_stream(prompt: str):
        yield "ok"

    with patch("app.ai.service.stream_model_text", _fake_stream):
        stream = await stream_dashboard_follow_up(
            async_db_session,
            user_id=user.id,
            document_kind="all",
            question="Q on all",
        )
        async for _ in stream:
            pass
        stream2 = await stream_dashboard_follow_up(
            async_db_session,
            user_id=user.id,
            document_kind="analysis",
            question="Q on analysis",
        )
        async for _ in stream2:
            pass

    all_msgs = await ai_repository.list_chat_messages(
        async_db_session,
        user_id=user.id,
        thread_id=ai_repository.thread_id_for_dashboard(user.id, "all"),
    )
    analysis_msgs = await ai_repository.list_chat_messages(
        async_db_session,
        user_id=user.id,
        thread_id=ai_repository.thread_id_for_dashboard(user.id, "analysis"),
    )
    assert any("Q on all" in m.text for m in all_msgs)
    assert not any("Q on analysis" in m.text for m in all_msgs)
    assert any("Q on analysis" in m.text for m in analysis_msgs)
    assert not any("Q on all" in m.text for m in analysis_msgs)


# ---------------------------------------------------------------------------
# Router endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_document_chat_messages_endpoint(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user, doc_id = await _seed_doc_with_interpretation(
        async_db_session, make_user, make_document, email="list_ep@example.com"
    )
    thread_id = ai_repository.thread_id_for_document(user.id, doc_id)
    await ai_repository.append_chat_message(
        async_db_session, user_id=user.id, thread_id=thread_id, role="user", text="q1"
    )
    await ai_repository.append_chat_message(
        async_db_session,
        user_id=user.id,
        thread_id=thread_id,
        role="assistant",
        text="a1",
    )
    await async_db_session.flush()

    response = await ai_client.get(
        f"/api/v1/ai/chat/{doc_id}/messages",
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    body = response.json()
    assert [m["role"] for m in body["messages"]] == ["user", "assistant"]
    assert [m["text"] for m in body["messages"]] == ["q1", "a1"]
    assert body["has_more"] is False


@pytest.mark.asyncio
async def test_list_document_chat_messages_404_on_other_user_doc(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user_a, _ = await make_user(email="uaiso@example.com")
    user_b, _ = await make_user(email="ubiso@example.com")
    doc_b = await make_document(user=user_b, status="completed")
    await async_db_session.flush()

    response = await ai_client.get(
        f"/api/v1/ai/chat/{doc_b.id}/messages",
        headers=auth_headers(user_a),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_clear_document_chat_messages_endpoint(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    user, doc_id = await _seed_doc_with_interpretation(
        async_db_session, make_user, make_document, email="clear_ep@example.com"
    )
    thread_id = ai_repository.thread_id_for_document(user.id, doc_id)
    await ai_repository.append_chat_message(
        async_db_session, user_id=user.id, thread_id=thread_id, role="user", text="q"
    )
    await async_db_session.flush()

    response = await ai_client.delete(
        f"/api/v1/ai/chat/{doc_id}/messages",
        headers=auth_headers(user),
    )
    assert response.status_code == 204
    assert (
        await ai_repository.list_chat_messages(
            async_db_session, user_id=user.id, thread_id=thread_id
        )
        == []
    )


@pytest.mark.asyncio
async def test_list_dashboard_chat_messages_endpoint_filter_scoped(
    ai_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
):
    user, _ = await make_user(email="dash_list@example.com")
    dash_all = ai_repository.thread_id_for_dashboard(user.id, "all")
    dash_analysis = ai_repository.thread_id_for_dashboard(user.id, "analysis")
    await ai_repository.append_chat_message(
        async_db_session, user_id=user.id, thread_id=dash_all, role="user", text="all q"
    )
    await ai_repository.append_chat_message(
        async_db_session,
        user_id=user.id,
        thread_id=dash_analysis,
        role="user",
        text="analysis q",
    )
    await async_db_session.flush()

    r_all = await ai_client.get(
        "/api/v1/ai/dashboard/chat/messages?document_kind=all",
        headers=auth_headers(user),
    )
    r_an = await ai_client.get(
        "/api/v1/ai/dashboard/chat/messages?document_kind=analysis",
        headers=auth_headers(user),
    )
    assert r_all.status_code == 200 and r_an.status_code == 200
    assert [m["text"] for m in r_all.json()["messages"]] == ["all q"]
    assert [m["text"] for m in r_an.json()["messages"]] == ["analysis q"]


@pytest.mark.asyncio
async def test_cascade_delete_drops_chat_rows(
    async_db_session: AsyncSession,
    make_user,
):
    """Deleting a user cascades to ai_chat_messages via the existing FK."""
    from sqlalchemy import delete

    user, _ = await make_user(email="cascadechat@example.com")
    thread_id = ai_repository.thread_id_for_dashboard(user.id, "all")
    await ai_repository.append_chat_message(
        async_db_session, user_id=user.id, thread_id=thread_id, role="user", text="x"
    )
    await async_db_session.flush()

    await async_db_session.execute(delete(User).where(User.id == user.id))
    await async_db_session.flush()

    result = await async_db_session.execute(
        select(AiChatMessage).where(AiChatMessage.user_id == user.id)
    )
    assert result.scalars().all() == []
