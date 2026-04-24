"""
Tests for admin extraction error queue and manual value correction endpoints.

Uses real database — no DB mocking per project rules.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AuditLog
from app.auth.models import User
from app.core.database import get_db
from app.core.security import create_access_token
from app.health_data.models import HealthValue
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
# Tests: GET /admin/queue
# ---------------------------------------------------------------------------


async def test_queue_returns_only_problematic_documents(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
):
    """Test 1: Queue returns exactly 4 documents from setup of 5 docs.

    Setup: 1 failed doc, 1 partial doc, 1 completed doc with low-confidence value,
    1 completed doc with flagged value, 1 completed doc with all OK values.
    Expected queue: first 4 docs only.
    """
    admin_user, _ = await make_user(email="queue_admin@example.com")
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    await async_db_session.flush()

    regular_user, _ = await make_user(email="queue_user@example.com")

    # 1. Failed document
    doc_failed = await make_document(user=regular_user, status="failed", filename="failed_lab.pdf")

    # 2. Partial document
    doc_partial = await make_document(
        user=regular_user, status="partial", filename="partial_lab.pdf"
    )

    # 3. Completed doc with a low-confidence value
    doc_low_conf = await make_document(
        user=regular_user, status="completed", filename="low_conf_lab.pdf"
    )
    await make_health_value(
        user=regular_user, document=doc_low_conf, value=4.5, confidence=0.5, needs_review=True
    )
    # OK value on same doc
    await make_health_value(
        user=regular_user,
        document=doc_low_conf,
        value=120.0,
        confidence=0.95,
        biomarker_name="Heart Rate",
        canonical_biomarker_name="heart_rate",
        unit="bpm",
    )

    # 4. Completed doc with a flagged value
    doc_flagged = await make_document(
        user=regular_user, status="completed", filename="flagged_lab.pdf"
    )
    await make_health_value(
        user=regular_user, document=doc_flagged, value=5.5, confidence=0.9, is_flagged=True
    )

    # 5. Completed doc with all OK values — should NOT appear in queue
    doc_ok = await make_document(user=regular_user, status="completed", filename="ok_lab.pdf")
    await make_health_value(user=regular_user, document=doc_ok, value=5.0, confidence=0.95)

    response = await admin_client.get("/api/v1/admin/queue", headers=admin_headers(admin_user))

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4
    assert len(data["items"]) == 4

    # Verify the 4 problematic docs are present
    doc_ids = {item["document_id"] for item in data["items"]}
    assert str(doc_failed.id) in doc_ids
    assert str(doc_partial.id) in doc_ids
    assert str(doc_low_conf.id) in doc_ids
    assert str(doc_flagged.id) in doc_ids
    assert str(doc_ok.id) not in doc_ids


async def test_queue_items_have_correct_aggregate_counts(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
):
    """Test 2: Queue items have correct value_count, low_confidence_count, flagged_count."""
    admin_user, _ = await make_user(email="counts_admin@example.com")
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    await async_db_session.flush()

    regular_user, _ = await make_user(email="counts_user@example.com")

    # Document with: 3 values total, 1 low confidence, 1 flagged
    doc = await make_document(user=regular_user, status="completed", filename="multi_lab.pdf")
    await make_health_value(
        user=regular_user, document=doc, value=5.5, confidence=0.5, is_flagged=True
    )
    await make_health_value(user=regular_user, document=doc, value=4.2, confidence=0.6)
    await make_health_value(user=regular_user, document=doc, value=120.0, confidence=0.95)

    response = await admin_client.get("/api/v1/admin/queue", headers=admin_headers(admin_user))

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["value_count"] == 3
    assert item["low_confidence_count"] == 2  # 0.5 and 0.6
    assert item["flagged_count"] == 1
    assert item["failed"] is False


async def test_queue_ordering(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Test: Queue orders by failed first, then partial, then by created_at DESC."""
    admin_user, _ = await make_user(email="order_admin@example.com")
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    await async_db_session.flush()

    regular_user, _ = await make_user(email="order_user@example.com")

    doc_partial = await make_document(
        user=regular_user, status="partial", filename="partial_first.pdf"
    )
    doc_failed = await make_document(
        user=regular_user, status="failed", filename="failed_second.pdf"
    )

    response = await admin_client.get("/api/v1/admin/queue", headers=admin_headers(admin_user))

    assert response.status_code == 200
    data = response.json()
    # failed should come before partial (status ordering)
    # Within same status, DESC created_at — partial was created after failed
    ids = [item["document_id"] for item in data["items"]]
    # failed should be first (0), partial second (1)
    assert ids.index(str(doc_failed.id)) < ids.index(str(doc_partial.id))


async def test_empty_queue_returns_zero_items(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
):
    """Test 9: Empty queue returns { items: [], total: 0 } when no problematic docs exist."""
    admin_user, _ = await make_user(email="empty_admin@example.com")
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    await async_db_session.flush()

    response = await admin_client.get("/api/v1/admin/queue", headers=admin_headers(admin_user))

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# Tests: GET /admin/queue/{document_id}
# ---------------------------------------------------------------------------


async def test_queue_detail_returns_decrypted_values(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
):
    """Test 3: Document detail returns decrypted health values."""
    admin_user, _ = await make_user(email="detail_admin@example.com")
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    await async_db_session.flush()

    regular_user, _ = await make_user(email="detail_user@example.com")
    doc = await make_document(user=regular_user, status="partial", filename="detail_lab.pdf")

    original_value = 5.4
    await make_health_value(
        user=regular_user,
        document=doc,
        biomarker_name="Cholesterol",
        canonical_biomarker_name="cholesterol_total",
        value=original_value,
        unit="mmol/L",
        confidence=0.85,
        needs_review=False,
        is_flagged=False,
    )

    response = await admin_client.get(
        f"/api/v1/admin/queue/{doc.id}", headers=admin_headers(admin_user)
    )

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == str(doc.id)
    assert data["user_id"] == str(regular_user.id)
    assert data["filename"] == "detail_lab.pdf"
    assert data["status"] == "partial"
    assert len(data["values"]) == 1
    # Value should be decrypted
    assert data["values"][0]["value"] == original_value
    assert data["values"][0]["biomarker_name"] == "Cholesterol"
    assert data["values"][0]["confidence"] == 0.85


async def test_queue_detail_nonexistent_document_returns_404(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
):
    """Test: GET queue detail for non-existent document returns 404."""
    import uuid

    admin_user, _ = await make_user(email="notfound_admin@example.com")
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    await async_db_session.flush()

    fake_id = uuid.uuid4()
    response = await admin_client.get(
        f"/api/v1/admin/queue/{fake_id}", headers=admin_headers(admin_user)
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


# ---------------------------------------------------------------------------
# Tests: POST /admin/queue/{document_id}/values/{health_value_id}/correct
# ---------------------------------------------------------------------------


async def test_correction_creates_audit_log_and_updates_value(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
):
    """Test 4: Correction creates audit_log row and updates health_value with new encrypted value."""
    admin_user, _ = await make_user(email="correct_admin@example.com")
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    await async_db_session.flush()

    regular_user, _ = await make_user(email="correct_user@example.com")
    doc = await make_document(user=regular_user, status="completed", filename="correct_lab.pdf")

    original_value = 5.4
    hv = await make_health_value(
        user=regular_user,
        document=doc,
        biomarker_name="Cholesterol",
        canonical_biomarker_name="cholesterol_total",
        value=original_value,
        unit="mmol/L",
        confidence=0.85,
    )

    new_value = 5.8
    reason = "Decimal misread by OCR — original lab shows 5.8 not 5.4"
    response = await admin_client.post(
        f"/api/v1/admin/queue/{doc.id}/values/{hv.id}/correct",
        headers=admin_headers(admin_user),
        json={"new_value": new_value, "reason": reason},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["health_value_id"] == str(hv.id)
    assert data["value_name"] == "cholesterol_total"
    assert data["original_value"] == original_value
    assert data["new_value"] == new_value
    assert "audit_log_id" in data
    assert "corrected_at" in data

    # Verify audit log row was created
    audit_result = await async_db_session.execute(
        select(AuditLog).where(AuditLog.id == data["audit_log_id"])
    )
    audit_row = audit_result.scalar_one()
    assert audit_row.admin_id == admin_user.id
    assert audit_row.user_id == regular_user.id
    assert audit_row.document_id == doc.id
    assert audit_row.health_value_id == hv.id
    assert audit_row.value_name == "cholesterol_total"
    assert audit_row.original_value == str(original_value)
    assert audit_row.new_value == str(new_value)
    assert audit_row.reason == reason

    # Verify health_value was updated with new encrypted value
    hv_result = await async_db_session.execute(select(HealthValue).where(HealthValue.id == hv.id))
    updated_hv = hv_result.scalar_one()
    # Decrypt and check value
    from app.health_data.repository import _decrypt_numeric_value

    decrypted = _decrypt_numeric_value(updated_hv.value_encrypted)
    assert decrypted == new_value


@pytest.mark.parametrize("invalid_reason", ["", "   "])
async def test_correction_without_reason_returns_422(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
    invalid_reason: str,
):
    """Test 5: Correction without reason → 422 validation error."""
    admin_user, _ = await make_user(email="noreason_admin@example.com")
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    await async_db_session.flush()

    regular_user, _ = await make_user(email="noreason_user@example.com")
    doc = await make_document(user=regular_user, status="completed")
    hv = await make_health_value(user=regular_user, document=doc, value=5.0)

    response = await admin_client.post(
        f"/api/v1/admin/queue/{doc.id}/values/{hv.id}/correct",
        headers=admin_headers(admin_user),
        json={"new_value": 5.5, "reason": invalid_reason},
    )

    assert response.status_code == 422


async def test_correction_mismatched_document_and_health_value_returns_404(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
):
    """Correction route enforces that the health value belongs to the document in the URL."""
    admin_user, _ = await make_user(email="mismatch_admin@example.com")
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    await async_db_session.flush()

    regular_user, _ = await make_user(email="mismatch_user@example.com")
    source_doc = await make_document(user=regular_user, status="completed")
    other_doc = await make_document(user=regular_user, status="completed")
    hv = await make_health_value(user=regular_user, document=source_doc, value=5.0)

    response = await admin_client.post(
        f"/api/v1/admin/queue/{other_doc.id}/values/{hv.id}/correct",
        headers=admin_headers(admin_user),
        json={"new_value": 5.5, "reason": "Corrected from source report"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Health value not found"


async def test_correction_nonexistent_health_value_returns_404(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
):
    """Test 6: Correction for non-existent health_value_id → 404."""
    import uuid

    admin_user, _ = await make_user(email="notfound_hv_admin@example.com")
    admin_user.role = "admin"
    async_db_session.add(admin_user)
    await async_db_session.flush()

    regular_user, _ = await make_user(email="notfound_hv_user@example.com")
    doc = await make_document(user=regular_user, status="completed")
    await make_health_value(user=regular_user, document=doc, value=5.0)

    fake_hv_id = uuid.uuid4()
    response = await admin_client.post(
        f"/api/v1/admin/queue/{doc.id}/values/{fake_hv_id}/correct",
        headers=admin_headers(admin_user),
        json={"new_value": 5.5, "reason": "Test reason"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Health value not found"


# ---------------------------------------------------------------------------
# Tests: Auth — non-admin and unauthenticated
# ---------------------------------------------------------------------------


async def test_non_admin_gets_403_on_queue_list(
    admin_client: AsyncClient,
    make_user,
):
    """Test 7: Non-admin user gets 403 on queue list endpoint."""
    regular_user, _ = await make_user(email="regular_queue@example.com")

    response = await admin_client.get("/api/v1/admin/queue", headers=user_headers(regular_user))

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


async def test_non_admin_gets_403_on_queue_detail(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
):
    """Test 7: Non-admin user gets 403 on queue detail endpoint."""
    regular_user, _ = await make_user(email="regular_detail@example.com")
    doc = await make_document(user=regular_user, status="failed")
    await make_health_value(user=regular_user, document=doc, value=5.0)

    another_user, _ = await make_user(email="another_regular@example.com")

    response = await admin_client.get(
        f"/api/v1/admin/queue/{doc.id}", headers=user_headers(another_user)
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


async def test_non_admin_gets_403_on_correction(
    admin_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
):
    """Test 7: Non-admin user gets 403 on correction endpoint."""
    regular_user, _ = await make_user(email="regular_correct@example.com")
    doc = await make_document(user=regular_user, status="completed")
    hv = await make_health_value(user=regular_user, document=doc, value=5.0)

    another_user, _ = await make_user(email="another_regular_correct@example.com")

    response = await admin_client.post(
        f"/api/v1/admin/queue/{doc.id}/values/{hv.id}/correct",
        headers=user_headers(another_user),
        json={"new_value": 5.5, "reason": "Test reason"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


async def test_no_jwt_gets_401_on_queue_list(admin_client: AsyncClient):
    """Test 8: No JWT gets 401 on queue list."""
    response = await admin_client.get("/api/v1/admin/queue")
    assert response.status_code == 401


async def test_no_jwt_gets_401_on_queue_detail(admin_client: AsyncClient):
    """Test 8: No JWT gets 401 on queue detail."""
    import uuid

    fake_id = uuid.uuid4()
    response = await admin_client.get(f"/api/v1/admin/queue/{fake_id}")
    assert response.status_code == 401


async def test_no_jwt_gets_401_on_correction(admin_client: AsyncClient):
    """Test 8: No JWT gets 401 on correction."""
    import uuid

    fake_doc_id = uuid.uuid4()
    fake_hv_id = uuid.uuid4()
    response = await admin_client.post(
        f"/api/v1/admin/queue/{fake_doc_id}/values/{fake_hv_id}/correct",
        json={"new_value": 5.5, "reason": "Test"},
    )
    assert response.status_code == 401
