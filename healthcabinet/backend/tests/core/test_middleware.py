import uuid
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient
from structlog.contextvars import clear_contextvars, get_contextvars

import app.core.middleware as middleware_module
from app.core.middleware import RequestIDMiddleware
from app.main import app


async def test_request_id_header_added_and_unique_per_request():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first_response = await client.get("/health")
        second_response = await client.get("/health")

    first_request_id = first_response.headers.get("x-request-id")
    second_request_id = second_response.headers.get("x-request-id")

    assert first_request_id is not None
    assert second_request_id is not None
    assert first_request_id != second_request_id
    assert str(uuid.UUID(first_request_id)) == first_request_id
    assert str(uuid.UUID(second_request_id)) == second_request_id


async def test_request_started_log_binds_request_metadata(monkeypatch):
    fixed_request_id = uuid.UUID("11111111-1111-4111-8111-111111111111")
    captured_log: dict[str, object] = {}

    class DummyLogger:
        def info(self, event: str) -> None:
            captured_log["event"] = event
            captured_log["context"] = get_contextvars()

    clear_contextvars()
    monkeypatch.setattr(middleware_module, "logger", DummyLogger())
    monkeypatch.setattr(middleware_module.uuid, "uuid4", lambda: fixed_request_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.headers["x-request-id"] == str(fixed_request_id)
    assert captured_log == {
        "event": "request.started",
        "context": {
            "request_id": str(fixed_request_id),
            "method": "GET",
            "path": "/health",
        },
    }
    assert get_contextvars() == {}


async def test_validation_error_responses_keep_request_id_header(test_client):
    response = await test_client.post("/api/v1/auth/register", json={"email": "invalid"})

    request_id = response.headers.get("x-request-id")

    assert response.status_code == 422
    assert request_id is not None
    assert str(uuid.UUID(request_id)) == request_id


async def test_non_http_scopes_bypass_request_id_handling():
    async def downstream_app(scope, receive, send):
        assert scope["type"] == "websocket"
        assert "request_id" not in scope
        await send({"type": "websocket.accept"})
        await send({"type": "websocket.close"})

    middleware = RequestIDMiddleware(downstream_app)
    receive = AsyncMock(return_value={"type": "websocket.disconnect"})
    send = AsyncMock()
    scope = {"type": "websocket", "path": "/ws"}

    await middleware(scope, receive, send)

    assert "request_id" not in scope
    assert send.await_count == 2
