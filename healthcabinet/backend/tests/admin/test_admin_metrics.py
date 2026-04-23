"""
Tests for GET /api/v1/admin/metrics endpoint.

Uses real database — no DB mocking per project rules.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import AiMemory
from app.auth.models import User
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def admin_client(async_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test client with DB override."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield async_db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def admin_headers(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


def user_headers(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_admin_gets_metrics(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
):
    """Test 1: Admin with role=admin JWT gets 200 with all metric fields."""
    admin_user, _ = await make_user(email="admin@example.com")
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    await async_db_session.flush()

    response = await admin_client.get(
        "/api/v1/admin/metrics", headers=admin_headers(admin_user)
    )

    assert response.status_code == 200
    data = response.json()
    assert "total_signups" in data
    assert "total_uploads" in data
    assert "upload_success_rate" in data
    assert "documents_error_or_partial" in data
    assert "ai_interpretation_completion_rate" in data


async def test_regular_user_gets_403(
    admin_client: AsyncClient,
    make_user,
):
    """Test 2: User with role=user JWT gets 403."""
    regular_user, _ = await make_user(email="regular@example.com")

    response = await admin_client.get(
        "/api/v1/admin/metrics", headers=user_headers(regular_user)
    )

    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "Admin access required"


async def test_no_jwt_gets_401(admin_client: AsyncClient):
    """Test 3: No JWT gets 401."""
    response = await admin_client.get("/api/v1/admin/metrics")

    assert response.status_code == 401  # HTTPBearer returns 401 when no credentials provided


async def test_metrics_correct_with_fixture_data(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Test 4: Metrics are correct with known fixture data.
    Setup: 2 users, 3 docs: 1 completed, 1 partial, 1 failed.
    """
    admin_user, _ = await make_user(email="admin2@example.com")
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    await async_db_session.flush()

    _user2, _ = await make_user(email="user2@example.com")

    doc_completed = await make_document(user=admin_user, status="completed")
    _doc_partial = await make_document(user=admin_user, status="partial")
    _doc_failed = await make_document(user=admin_user, status="failed")

    # Add an ai_memory for the completed doc (interpreted + safety validated)
    ai_mem = AiMemory(
        user_id=admin_user.id,
        document_id=doc_completed.id,
        interpretation_encrypted=b"encrypted-data",
        safety_validated=True,
    )
    async_db_session.add(ai_mem)
    await async_db_session.flush()

    response = await admin_client.get(
        "/api/v1/admin/metrics", headers=admin_headers(admin_user)
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total_signups"] == 2
    assert data["total_uploads"] == 3
    assert data["upload_success_rate"] == pytest.approx(1 / 3)
    assert data["documents_error_or_partial"] == 2
    assert data["ai_interpretation_completion_rate"] == pytest.approx(1 / 3)


async def test_null_rates_when_no_documents(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
):
    """Test 5: upload_success_rate and ai_interpretation_completion_rate are None when no documents.

    Session is function-scoped and rolled back after each test, so no documents exist
    at the start of this test. Creating only an admin user (no documents) guarantees
    total_uploads=0 and both rates return null.
    """
    admin_user, _ = await make_user(email="admin_nodata@example.com")
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    await async_db_session.flush()

    response = await admin_client.get(
        "/api/v1/admin/metrics", headers=admin_headers(admin_user)
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total_uploads"] == 0
    assert data["upload_success_rate"] is None
    assert data["ai_interpretation_completion_rate"] is None
