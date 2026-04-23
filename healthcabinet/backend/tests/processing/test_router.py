"""HTTP-level tests for the SSE document-status endpoint."""

import json
import uuid
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from redis.exceptions import RedisError

from app.main import app
from app.processing.dependencies import get_db as processing_get_db
from app.processing.schemas import STAGE_MESSAGES


def _sse_lines(body: str) -> list[dict]:
    """Parse `data: {...}` lines from an SSE body string."""
    events = []
    for line in body.splitlines():
        if line.startswith("data:"):
            events.append(json.loads(line[5:].strip()))
    return events


def _stub_user(user_id: uuid.UUID | None = None) -> SimpleNamespace:
    """Minimal User stand-in for SSE auth mocks.

    The SSE endpoint only reads `.id` off the resolved user; providing a full ORM
    User would force the test to manage attached-to-session state. account_status
    and tokens_invalid_before are included so accidental attribute access during
    future refactors surfaces as a clear test failure instead of AttributeError.
    """
    return SimpleNamespace(
        id=user_id or uuid.uuid4(),
        account_status="active",
        tokens_invalid_before=None,
    )


def _patch_auth(user_id: uuid.UUID | None = None, **kwargs: object) -> object:
    """Wrap patch() for the SSE auth boundary — always async, always a User."""
    if "side_effect" in kwargs:
        return patch("app.processing.router.resolve_access_token", **kwargs)
    return patch(
        "app.processing.router.resolve_access_token",
        new=AsyncMock(return_value=_stub_user(user_id)),
    )


def _make_fake_pubsub(messages: list[dict] | None = None) -> MagicMock:
    queue = list(messages or [])
    fake_pubsub = MagicMock()
    fake_pubsub.subscribe = AsyncMock()
    fake_pubsub.unsubscribe = AsyncMock()
    fake_pubsub.aclose = AsyncMock()

    async def _get_message(**_: object) -> dict | None:
        if queue:
            return queue.pop(0)
        return None

    fake_pubsub.get_message = AsyncMock(side_effect=_get_message)
    return fake_pubsub


@pytest_asyncio.fixture
async def sse_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTPX client with a stub DB dependency override."""

    async def override_get_db() -> AsyncGenerator[MagicMock, None]:
        yield MagicMock()

    app.dependency_overrides[processing_get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sse_requires_valid_token(sse_client: AsyncClient):
    """Missing both header and query param → 401."""
    doc_id = uuid.uuid4()

    resp = await sse_client.get(f"/api/v1/documents/{doc_id}/status")
    assert resp.status_code == 401

    with _patch_auth(side_effect=HTTPException(status_code=401, detail="Invalid")):
        resp = await sse_client.get(f"/api/v1/documents/{doc_id}/status?token=not-a-valid-jwt")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sse_requires_document_ownership(sse_client: AsyncClient):
    """Valid token but wrong user → 404."""
    doc_id = uuid.uuid4()

    with (
        _patch_auth(),
        patch(
            "app.processing.router.get_document_by_id",
            side_effect=HTTPException(status_code=404, detail="Not found"),
        ),
    ):
        resp = await sse_client.get(f"/api/v1/documents/{doc_id}/status?token=valid-token")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sse_already_completed_returns_terminal_event(sse_client: AsyncClient):
    """Document already completed → immediate terminal event emitted, stream closes."""
    doc_id = uuid.uuid4()
    doc = SimpleNamespace(id=doc_id, status="completed")

    with (
        _patch_auth(),
        patch("app.processing.router.get_document_by_id", new=AsyncMock(return_value=doc)),
    ):
        resp = await sse_client.get(f"/api/v1/documents/{doc_id}/status?token=valid-token")

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert _sse_lines(resp.text) == [
        {
            "event": "document.completed",
            "document_id": str(doc_id),
            "progress": 1.0,
            "message": "Processing complete",
        }
    ]


@pytest.mark.asyncio
async def test_sse_already_failed_returns_terminal_event(sse_client: AsyncClient):
    """Document already failed → immediate terminal event emitted."""
    doc_id = uuid.uuid4()
    doc = SimpleNamespace(id=doc_id, status="failed")

    with (
        _patch_auth(),
        patch("app.processing.router.get_document_by_id", new=AsyncMock(return_value=doc)),
    ):
        resp = await sse_client.get(f"/api/v1/documents/{doc_id}/status?token=valid-token")

    assert resp.status_code == 200
    assert _sse_lines(resp.text)[0]["event"] == "document.failed"


@pytest.mark.asyncio
async def test_sse_already_partial_returns_terminal_event(sse_client: AsyncClient):
    """Document already partial → immediate terminal event emitted."""
    doc_id = uuid.uuid4()
    doc = SimpleNamespace(id=doc_id, status="partial")

    with (
        _patch_auth(),
        patch("app.processing.router.get_document_by_id", new=AsyncMock(return_value=doc)),
    ):
        resp = await sse_client.get(f"/api/v1/documents/{doc_id}/status?token=valid-token")

    assert resp.status_code == 200
    assert _sse_lines(resp.text)[0]["event"] == "document.partial"


@pytest.mark.asyncio
async def test_sse_event_sequence(sse_client: AsyncClient):
    """SSE stream yields stage events in the expected order."""
    doc_id = uuid.uuid4()
    doc = SimpleNamespace(id=doc_id, status="pending")
    stage_events = [
        "document.upload_started",
        "document.reading",
        "document.extracting",
        "document.generating",
        "document.completed",
    ]
    messages = []
    for evt_type in stage_events:
        msg, progress = STAGE_MESSAGES[evt_type]
        payload = json.dumps(
            {
                "event": evt_type,
                "document_id": str(doc_id),
                "progress": progress,
                "message": msg,
            }
        )
        messages.append({"type": "message", "data": payload})

    fake_pubsub = _make_fake_pubsub(messages)
    fake_redis_instance = MagicMock()
    fake_redis_instance.pubsub = MagicMock(return_value=fake_pubsub)
    fake_redis_instance.aclose = AsyncMock()

    with (
        _patch_auth(),
        patch("app.processing.router.get_document_by_id", new=AsyncMock(return_value=doc)),
        patch("app.processing.router.aioredis.from_url", return_value=fake_redis_instance),
        patch("app.processing.router.get_latest_event", new=AsyncMock(return_value=None)),
    ):
        resp = await sse_client.get(f"/api/v1/documents/{doc_id}/status?token=valid-token")

    assert resp.status_code == 200
    assert [event["event"] for event in _sse_lines(resp.text)] == stage_events


@pytest.mark.asyncio
async def test_sse_latest_event_replayed_on_connect(sse_client: AsyncClient):
    """A cached latest event is replayed immediately to late subscribers."""
    doc_id = uuid.uuid4()
    doc = SimpleNamespace(id=doc_id, status="pending")
    latest = {
        "event": "document.reading",
        "document_id": str(doc_id),
        "progress": 0.25,
        "message": "Reading document…",
    }
    fake_pubsub = _make_fake_pubsub()
    fake_redis_instance = MagicMock()
    fake_redis_instance.pubsub = MagicMock(return_value=fake_pubsub)
    fake_redis_instance.aclose = AsyncMock()

    with (
        _patch_auth(),
        patch("app.processing.router.get_document_by_id", new=AsyncMock(return_value=doc)),
        patch("app.processing.router.aioredis.from_url", return_value=fake_redis_instance),
        patch("app.processing.router.get_latest_event", new=AsyncMock(return_value=latest)),
        patch("app.processing.router._MAX_STREAM_SECONDS", 0),
    ):
        resp = await sse_client.get(f"/api/v1/documents/{doc_id}/status?token=valid-token")

    assert resp.status_code == 200
    assert [event["event"] for event in _sse_lines(resp.text)] == ["document.reading"]


@pytest.mark.asyncio
async def test_sse_latest_event_is_terminal_skips_pubsub(sse_client: AsyncClient):
    """Terminal cached events are returned once and the stream closes without waiting."""
    doc_id = uuid.uuid4()
    doc = SimpleNamespace(id=doc_id, status="pending")
    latest = {
        "event": "document.completed",
        "document_id": str(doc_id),
        "progress": 1.0,
        "message": "Processing complete",
    }
    fake_pubsub = _make_fake_pubsub()
    fake_redis_instance = MagicMock()
    fake_redis_instance.pubsub = MagicMock(return_value=fake_pubsub)
    fake_redis_instance.aclose = AsyncMock()

    with (
        _patch_auth(),
        patch("app.processing.router.get_document_by_id", new=AsyncMock(return_value=doc)),
        patch("app.processing.router.aioredis.from_url", return_value=fake_redis_instance),
        patch("app.processing.router.get_latest_event", new=AsyncMock(return_value=latest)),
    ):
        resp = await sse_client.get(f"/api/v1/documents/{doc_id}/status?token=valid-token")

    assert resp.status_code == 200
    assert [event["event"] for event in _sse_lines(resp.text)] == ["document.completed"]
    fake_pubsub.get_message.assert_not_called()


@pytest.mark.asyncio
async def test_sse_refresh_token_rejected(sse_client: AsyncClient):
    """Refresh JWTs are not accepted by the SSE endpoint."""
    doc_id = uuid.uuid4()

    with _patch_auth(
        side_effect=HTTPException(status_code=401, detail="Expected access token")
    ):
        resp = await sse_client.get(f"/api/v1/documents/{doc_id}/status?token=refresh-token")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sse_expired_token_returns_401(sse_client: AsyncClient):
    """Expired access JWTs fail authentication before the stream starts."""
    doc_id = uuid.uuid4()

    with _patch_auth(side_effect=HTTPException(status_code=401, detail="Expired token")):
        resp = await sse_client.get(f"/api/v1/documents/{doc_id}/status?token=expired-token")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sse_stream_closes_after_120s_timeout(sse_client: AsyncClient):
    """Idle streams eventually terminate instead of hanging forever."""
    doc_id = uuid.uuid4()
    doc = SimpleNamespace(id=doc_id, status="pending")
    fake_pubsub = _make_fake_pubsub()
    fake_redis_instance = MagicMock()
    fake_redis_instance.pubsub = MagicMock(return_value=fake_pubsub)
    fake_redis_instance.aclose = AsyncMock()

    with (
        _patch_auth(),
        patch("app.processing.router.get_document_by_id", new=AsyncMock(return_value=doc)),
        patch("app.processing.router.aioredis.from_url", return_value=fake_redis_instance),
        patch("app.processing.router.get_latest_event", new=AsyncMock(return_value=None)),
        patch("app.processing.router._MAX_STREAM_SECONDS", 0.01),
        patch("app.processing.router._HEARTBEAT_INTERVAL_SECONDS", 0.005),
    ):
        resp = await sse_client.get(f"/api/v1/documents/{doc_id}/status?token=valid-token")

    assert resp.status_code == 200
    assert ":\n\n" in resp.text


@pytest.mark.asyncio
async def test_sse_redis_error_emits_failed_event(sse_client: AsyncClient):
    """RedisError during pub/sub yields document.failed event before closing."""
    doc_id = uuid.uuid4()
    doc = SimpleNamespace(id=doc_id, status="pending")
    fake_pubsub = MagicMock()
    fake_pubsub.subscribe = AsyncMock()
    fake_pubsub.unsubscribe = AsyncMock()
    fake_pubsub.aclose = AsyncMock()
    fake_pubsub.get_message = AsyncMock(side_effect=RedisError("connection lost"))
    fake_redis_instance = MagicMock()
    fake_redis_instance.pubsub = MagicMock(return_value=fake_pubsub)
    fake_redis_instance.aclose = AsyncMock()

    with (
        _patch_auth(),
        patch("app.processing.router.get_document_by_id", new=AsyncMock(return_value=doc)),
        patch("app.processing.router.aioredis.from_url", return_value=fake_redis_instance),
        patch("app.processing.router.get_latest_event", new=AsyncMock(return_value=None)),
    ):
        resp = await sse_client.get(f"/api/v1/documents/{doc_id}/status?token=valid-token")

    assert resp.status_code == 200
    events = _sse_lines(resp.text)
    assert len(events) == 1
    assert events[0]["event"] == "document.failed"
    assert events[0]["document_id"] == str(doc_id)


# --- Header-based auth tests (Story 14-1) ---


@pytest.mark.asyncio
async def test_sse_header_auth_success(sse_client: AsyncClient):
    """Authorization: Bearer header authenticates and streams events."""
    doc_id = uuid.uuid4()
    doc = SimpleNamespace(id=doc_id, status="completed")

    with (
        _patch_auth(),
        patch("app.processing.router.get_document_by_id", new=AsyncMock(return_value=doc)),
    ):
        resp = await sse_client.get(
            f"/api/v1/documents/{doc_id}/status",
            headers={"Authorization": "Bearer valid-access-token"},
        )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    events = _sse_lines(resp.text)
    assert len(events) == 1
    assert events[0]["event"] == "document.completed"


@pytest.mark.asyncio
async def test_sse_header_auth_expired_token_returns_401(sse_client: AsyncClient):
    """Expired token in Authorization header → 401."""
    doc_id = uuid.uuid4()

    with _patch_auth(side_effect=HTTPException(status_code=401, detail="Expired token")):
        resp = await sse_client.get(
            f"/api/v1/documents/{doc_id}/status",
            headers={"Authorization": "Bearer expired-token"},
        )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sse_missing_both_auth_methods_returns_401(sse_client: AsyncClient):
    """No Authorization header and no ?token= query param → 401."""
    doc_id = uuid.uuid4()

    resp = await sse_client.get(f"/api/v1/documents/{doc_id}/status")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sse_header_preferred_over_query_param(sse_client: AsyncClient):
    """When both Authorization header and ?token= are present, header takes precedence."""
    doc_id = uuid.uuid4()
    header_user_id = uuid.uuid4()
    doc = SimpleNamespace(id=doc_id, status="completed")

    call_args: list[str] = []

    async def tracking_resolve(t: str, _db: object) -> SimpleNamespace:
        call_args.append(t)
        return _stub_user(header_user_id)

    with (
        patch("app.processing.router.resolve_access_token", side_effect=tracking_resolve),
        patch("app.processing.router.get_document_by_id", new=AsyncMock(return_value=doc)),
    ):
        resp = await sse_client.get(
            f"/api/v1/documents/{doc_id}/status?token=query-param-token",
            headers={"Authorization": "Bearer header-token"},
        )

    assert resp.status_code == 200
    # resolve_access_token was called once with the header token, not the query param
    assert len(call_args) == 1
    assert call_args[0] == "header-token"


@pytest.mark.asyncio
async def test_sse_malformed_authorization_header_returns_401_even_with_query_token(
    sse_client: AsyncClient,
):
    """Malformed Authorization header fails closed instead of falling back to ?token=."""
    doc_id = uuid.uuid4()

    with patch("app.processing.router.resolve_access_token") as resolve_token:
        resp = await sse_client.get(
            f"/api/v1/documents/{doc_id}/status?token=fallback-token",
            headers={"Authorization": "Basic some-other-auth"},
        )

    assert resp.status_code == 401
    resolve_token.assert_not_called()


@pytest.mark.asyncio
async def test_sse_lowercase_bearer_scheme_is_accepted(sse_client: AsyncClient):
    """Bearer auth scheme comparison is case-insensitive."""
    doc_id = uuid.uuid4()
    doc = SimpleNamespace(id=doc_id, status="completed")

    with (
        _patch_auth(),
        patch("app.processing.router.get_document_by_id", new=AsyncMock(return_value=doc)),
    ):
        resp = await sse_client.get(
            f"/api/v1/documents/{doc_id}/status",
            headers={"Authorization": "bearer valid-access-token"},
        )

    assert resp.status_code == 200
    assert _sse_lines(resp.text)[0]["event"] == "document.completed"


@pytest.mark.asyncio
async def test_sse_header_auth_event_sequence(sse_client: AsyncClient):
    """Full event sequence works with header auth (not just terminal fast-path)."""
    doc_id = uuid.uuid4()
    doc = SimpleNamespace(id=doc_id, status="pending")
    stage_events = [
        "document.upload_started",
        "document.reading",
        "document.extracting",
        "document.generating",
        "document.completed",
    ]
    messages = []
    for evt_type in stage_events:
        msg, progress = STAGE_MESSAGES[evt_type]
        payload = json.dumps(
            {
                "event": evt_type,
                "document_id": str(doc_id),
                "progress": progress,
                "message": msg,
            }
        )
        messages.append({"type": "message", "data": payload})

    fake_pubsub = _make_fake_pubsub(messages)
    fake_redis_instance = MagicMock()
    fake_redis_instance.pubsub = MagicMock(return_value=fake_pubsub)
    fake_redis_instance.aclose = AsyncMock()

    with (
        _patch_auth(),
        patch("app.processing.router.get_document_by_id", new=AsyncMock(return_value=doc)),
        patch("app.processing.router.aioredis.from_url", return_value=fake_redis_instance),
        patch("app.processing.router.get_latest_event", new=AsyncMock(return_value=None)),
    ):
        resp = await sse_client.get(
            f"/api/v1/documents/{doc_id}/status",
            headers={"Authorization": "Bearer valid-access-token"},
        )

    assert resp.status_code == 200
    assert [event["event"] for event in _sse_lines(resp.text)] == stage_events
