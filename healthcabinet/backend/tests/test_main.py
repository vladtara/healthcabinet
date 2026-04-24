import uuid
from collections.abc import Callable, Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import _serialize_validation_errors, app


@pytest.fixture
def add_test_route() -> Iterator[Callable[[str, Callable], None]]:
    added_routes = []

    def _add_test_route(path: str, endpoint: Callable) -> None:
        app.add_api_route(path, endpoint, methods=["GET"])
        added_routes.append(app.router.routes[-1])

    yield _add_test_route

    for route in added_routes:
        if route in app.router.routes:
            app.router.routes.remove(route)


def test_serialize_validation_errors_stringifies_non_primitive_ctx_values():
    sentinel = ValueError("not JSON serializable")
    errors = [
        {
            "type": "value_error",
            "loc": ("body", "field"),
            "msg": "Invalid field",
            "input": "bad",
            "ctx": {
                "error": sentinel,
                "attempts": 2,
                "allowed": ["a", "b"],
                "metadata": {"source": "validator"},
                "optional": None,
            },
        }
    ]

    serialized = _serialize_validation_errors(errors)

    assert serialized == [
        {
            "type": "value_error",
            "loc": ("body", "field"),
            "msg": "Invalid field",
            "input": "bad",
            "ctx": {
                "error": str(sentinel),
                "attempts": 2,
                "allowed": ["a", "b"],
                "metadata": {"source": "validator"},
                "optional": None,
            },
        }
    ]


async def test_global_exception_handler_redacts_detail_and_keeps_request_id(
    add_test_route, monkeypatch
):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    path = f"/__tests__/boom-{uuid.uuid4()}"

    async def boom() -> None:
        raise RuntimeError("database credentials leaked")

    add_test_route(path, boom)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path)

    assert response.status_code == 500
    assert response.headers.get("x-request-id") is not None
    assert str(uuid.UUID(response.headers["x-request-id"])) == response.headers["x-request-id"]
    assert response.json() == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "An error occurred",
        "instance": f"http://test{path}",
    }
