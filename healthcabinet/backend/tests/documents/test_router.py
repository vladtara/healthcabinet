"""
Tests for /api/v1/documents endpoints.

Rate limiting and ARQ are dependency-overridden so tests don't require Redis or an ARQ worker.
boto3 presigned URL generation is patched to avoid needing a live MinIO instance.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.database import get_db
from app.core.security import create_access_token
from app.documents.dependencies import get_arq_redis, rate_limit_upload
from app.documents.exceptions import UploadLimitExceededError
from app.main import app

def make_upload_file(
    filename: str = "lab_results.pdf",
    content: bytes = b"fake-pdf-content",
    content_type: str = "application/pdf",
) -> dict:
    """Return a files dict suitable for httpx multipart POST."""
    return {"file": (filename, content, content_type)}


class MockArqRedis:
    def __init__(self) -> None:
        self.enqueued: list[dict] = []

    async def enqueue_job(self, func_name: str, **kwargs: object) -> MagicMock:
        mock_job = MagicMock()
        mock_job.job_id = str(uuid.uuid4())
        self.enqueued.append({"func": func_name, "kwargs": kwargs, "job": mock_job})
        return mock_job


@pytest_asyncio.fixture
async def doc_client(
    async_db_session: AsyncSession,
) -> AsyncGenerator[tuple[AsyncClient, MockArqRedis], None]:
    """Test client with documents-specific dependency overrides."""
    mock_arq = MockArqRedis()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield async_db_session

    async def override_rate_limit() -> None:
        pass  # allow all uploads unless overridden per-test

    async def override_get_arq() -> MockArqRedis:
        return mock_arq

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[rate_limit_upload] = override_rate_limit
    app.dependency_overrides[get_arq_redis] = override_get_arq

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, mock_arq

    app.dependency_overrides.clear()


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /api/v1/documents/upload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_requires_auth(doc_client: tuple[AsyncClient, MockArqRedis]):
    client, _ = doc_client
    response = await client.post(
        "/api/v1/documents/upload",
        files=make_upload_file(),
    )
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == 401
    assert data["type"] == "about:blank"


@pytest.mark.asyncio
async def test_upload_success_creates_document_and_enqueues_job(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user
):
    """Successful upload returns 202, a server-generated document id, and enqueues an ARQ job."""
    client, mock_arq = doc_client
    user, _ = await make_user(email="uploader@test.com")

    with (
        patch("app.documents.service.upload_object"),
        patch("app.documents.service.get_s3_client", return_value=MagicMock()),
    ):
        response = await client.post(
            "/api/v1/documents/upload",
            files=make_upload_file(),
            headers=auth_headers(user),
        )

    assert response.status_code == 202
    data = response.json()
    assert uuid.UUID(data["id"])  # server-generated UUID
    assert data["status"] == "pending"
    assert data["arq_job_id"] is not None

    assert len(mock_arq.enqueued) == 1
    assert mock_arq.enqueued[0]["func"] == "process_document"
    assert mock_arq.enqueued[0]["kwargs"]["document_id"] == data["id"]


@pytest.mark.asyncio
async def test_upload_rate_limit_429(async_db_session: AsyncSession, make_user):
    """Free tier returns 429 when rate_limit_upload raises UploadLimitExceededError."""
    user, _ = await make_user(email="ratelimited@test.com")

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield async_db_session

    async def override_rate_limit_exceeded() -> None:
        raise UploadLimitExceededError()

    async def override_get_arq() -> MockArqRedis:
        return MockArqRedis()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[rate_limit_upload] = override_rate_limit_exceeded
    app.dependency_overrides[get_arq_redis] = override_get_arq

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents/upload",
            files=make_upload_file(),
            headers=auth_headers(user),
        )

    app.dependency_overrides.clear()

    assert response.status_code == 429
    data = response.json()
    assert data["status"] == 429
    assert data["type"] == "about:blank"
    assert "try again tomorrow" in data["detail"].lower()
    assert response.headers.get("Retry-After") == "86400"


# ---------------------------------------------------------------------------
# GET /api/v1/documents (list)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_documents_requires_auth(doc_client: tuple[AsyncClient, MockArqRedis]):
    client, _ = doc_client
    response = await client.get("/api/v1/documents")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_documents_returns_user_documents_newest_first(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    client, _ = doc_client
    user, _ = await make_user(email="list-docs@test.com")
    now = datetime.now(UTC)
    await make_document(
        user=user, filename="first.pdf", status="completed", created_at=now - timedelta(minutes=1)
    )
    await make_document(user=user, filename="second.pdf", status="pending", created_at=now)

    response = await client.get("/api/v1/documents", headers=auth_headers(user))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Verify newest-first ordering: second.pdf was created most recently
    assert data[0]["filename"] == "second.pdf"
    assert data[1]["filename"] == "first.pdf"


@pytest.mark.asyncio
async def test_list_documents_user_isolation(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    """User A cannot see User B's documents."""
    client, _ = doc_client
    user_a, _ = await make_user(email="list-a@test.com")
    user_b, _ = await make_user(email="list-b@test.com")
    await make_document(user=user_a, filename="a-doc.pdf")
    await make_document(user=user_b, filename="b-doc.pdf")

    response = await client.get("/api/v1/documents", headers=auth_headers(user_a))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["filename"] == "a-doc.pdf"


@pytest.mark.asyncio
async def test_list_documents_empty_returns_empty_list(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user
):
    client, _ = doc_client
    user, _ = await make_user(email="list-empty@test.com")

    response = await client.get("/api/v1/documents", headers=auth_headers(user))
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /api/v1/documents/{document_id} (detail)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_document_detail_requires_auth(doc_client: tuple[AsyncClient, MockArqRedis]):
    client, _ = doc_client
    response = await client.get(f"/api/v1/documents/{uuid.uuid4()}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_document_detail_returns_document_with_health_values(
    doc_client: tuple[AsyncClient, MockArqRedis],
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    from app.health_data.repository import replace_document_health_values
    from app.processing.schemas import NormalizedHealthValue

    client, _ = doc_client
    user, _ = await make_user(email="detail-doc@test.com")
    doc = await make_document(user=user, status="completed")

    await replace_document_health_values(
        async_db_session,
        document_id=doc.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )

    response = await client.get(f"/api/v1/documents/{doc.id}", headers=auth_headers(user))
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(doc.id)
    assert data["filename"] == doc.filename
    assert len(data["health_values"]) == 1
    hv = data["health_values"][0]
    assert hv["canonical_biomarker_name"] == "glucose"
    assert hv["value"] == 91.0
    assert hv["confidence"] == 0.95


@pytest.mark.asyncio
async def test_get_document_detail_wrong_user_returns_404(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    client, _ = doc_client
    user_a, _ = await make_user(email="detail-a@test.com")
    user_b, _ = await make_user(email="detail-b@test.com")
    doc = await make_document(user=user_a)

    response = await client.get(f"/api/v1/documents/{doc.id}", headers=auth_headers(user_b))
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_document_detail_nonexistent_returns_404(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user
):
    client, _ = doc_client
    user, _ = await make_user(email="detail-nonexist@test.com")
    response = await client.get(f"/api/v1/documents/{uuid.uuid4()}", headers=auth_headers(user))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/documents/{document_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_document_requires_auth(doc_client: tuple[AsyncClient, MockArqRedis]):
    client, _ = doc_client
    response = await client.delete(f"/api/v1/documents/{uuid.uuid4()}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_document_success(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    """Successful delete removes document and returns deleted: true."""
    client, _ = doc_client
    user, _ = await make_user(email="delete-doc@test.com")
    doc = await make_document(user=user, status="completed")

    with (
        patch("app.documents.service.get_s3_client", return_value=MagicMock()),
        patch("app.documents.service.delete_object"),
    ):
        response = await client.delete(
            f"/api/v1/documents/{doc.id}", headers=auth_headers(user)
        )

    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] is True

    # Verify document is gone
    list_response = await client.get("/api/v1/documents", headers=auth_headers(user))
    assert list_response.status_code == 200
    assert list_response.json() == []


@pytest.mark.asyncio
async def test_delete_document_wrong_user_returns_404(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    client, _ = doc_client
    user_a, _ = await make_user(email="delete-a@test.com")
    user_b, _ = await make_user(email="delete-b@test.com")
    doc = await make_document(user=user_a, status="completed")

    with (
        patch("app.documents.service.get_s3_client", return_value=MagicMock()),
        patch("app.documents.service.delete_object"),
    ):
        response = await client.delete(
            f"/api/v1/documents/{doc.id}", headers=auth_headers(user_b)
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_minio_failure_logs_and_document_stays_deleted(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Storage cleanup failure is logged after the DB commit and does not resurrect the row."""
    from app.core.encryption import encrypt_bytes
    from app.documents import repository as doc_repo
    from app.documents import service as doc_service
    from app.documents.exceptions import DocumentNotFoundError

    user, _ = await make_user(email="delete-rollback@test.com")
    doc = await make_document(user=user, status="completed")
    doc.s3_key_encrypted = encrypt_bytes(b"test/key/file.pdf")
    await async_db_session.flush()

    with (
        patch(
            "app.documents.service.delete_object",
            side_effect=RuntimeError("MinIO unavailable"),
        ),
        patch("app.documents.service.get_s3_client", return_value=MagicMock()),
        patch("app.documents.service.logger.warning") as mock_warning,
    ):
        result = await doc_service.delete_document(async_db_session, user, doc.id)

    assert result.deleted is True
    mock_warning.assert_called_once()

    with pytest.raises(DocumentNotFoundError):
        await doc_repo.get_document_by_id(async_db_session, doc.id, user.id)


@pytest.mark.asyncio
async def test_delete_document_minio_failure_returns_success_and_document_is_removed(
    doc_client: tuple[AsyncClient, MockArqRedis],
    make_user,
    make_document,
):
    """The endpoint remains successful when storage cleanup fails after DB commit."""
    client, _ = doc_client
    user, _ = await make_user(email="delete-minio-fail@test.com")
    doc = await make_document(user=user, status="completed")

    with (
        patch(
            "app.documents.service.delete_objects_by_prefix",
            side_effect=RuntimeError("MinIO unavailable"),
        ),
        patch("app.documents.service.get_s3_client", return_value=MagicMock()),
        patch("app.documents.service.logger.warning") as mock_warning,
    ):
        response = await client.delete(
            f"/api/v1/documents/{doc.id}", headers=auth_headers(user)
        )

    assert response.status_code == 200
    assert response.json() == {"deleted": True}
    mock_warning.assert_called_once()

    list_response = await client.get("/api/v1/documents", headers=auth_headers(user))
    assert list_response.status_code == 200
    doc_ids = [d["id"] for d in list_response.json()]
    assert str(doc.id) not in doc_ids


# ---------------------------------------------------------------------------
# POST /api/v1/documents/{document_id}/reupload  (Story 2.5)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reupload_requires_auth(doc_client: tuple[AsyncClient, MockArqRedis]):
    client, _ = doc_client
    response = await client.post(
        f"/api/v1/documents/{uuid.uuid4()}/reupload",
        files=make_upload_file(),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_reupload_success_returns_same_document_id(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    """Retry returns the same document id — no new document row is created."""
    client, _ = doc_client
    user, _ = await make_user(email="retry-ok@test.com")
    doc = await make_document(user=user, status="partial")

    with (
        patch("app.documents.service.upload_object"),
        patch("app.documents.service.get_s3_client", return_value=MagicMock()),
        patch("app.documents.service.delete_object"),
    ):
        response = await client.post(
            f"/api/v1/documents/{doc.id}/reupload",
            files=make_upload_file(),
            headers=auth_headers(user),
        )

    assert response.status_code == 202
    data = response.json()
    # Same document id must be returned — no duplicate row
    assert data["id"] == str(doc.id)
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_reupload_works_for_failed_status(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    """Retry is allowed for documents in 'failed' status."""
    client, _ = doc_client
    user, _ = await make_user(email="retry-failed@test.com")
    doc = await make_document(user=user, status="failed")

    with (
        patch("app.documents.service.upload_object"),
        patch("app.documents.service.get_s3_client", return_value=MagicMock()),
        patch("app.documents.service.delete_object"),
    ):
        response = await client.post(
            f"/api/v1/documents/{doc.id}/reupload",
            files=make_upload_file(),
            headers=auth_headers(user),
        )

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_reupload_rejects_completed_document(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    """Retry is rejected for documents in 'completed' status (non-retryable)."""
    client, _ = doc_client
    user, _ = await make_user(email="retry-completed@test.com")
    doc = await make_document(user=user, status="completed")

    response = await client.post(
        f"/api/v1/documents/{doc.id}/reupload",
        files=make_upload_file(),
        headers=auth_headers(user),
    )

    assert response.status_code == 409
    data = response.json()
    assert data["status"] == 409


@pytest.mark.asyncio
async def test_reupload_rejects_pending_document(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    """Retry is rejected for documents in 'pending' status (processing in flight)."""
    client, _ = doc_client
    user, _ = await make_user(email="retry-pending@test.com")
    doc = await make_document(user=user, status="pending")

    response = await client.post(
        f"/api/v1/documents/{doc.id}/reupload",
        files=make_upload_file(),
        headers=auth_headers(user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_reupload_wrong_user_returns_404(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    """User B cannot retry User A's document."""
    client, _ = doc_client
    user_a, _ = await make_user(email="retry-owner-a@test.com")
    user_b, _ = await make_user(email="retry-owner-b@test.com")
    doc = await make_document(user=user_a, status="partial")

    response = await client.post(
        f"/api/v1/documents/{doc.id}/reupload",
        files=make_upload_file(),
        headers=auth_headers(user_b),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reupload_enqueues_arq_job(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    """Successful reupload enqueues a process_document ARQ job."""
    client, mock_arq = doc_client
    user, _ = await make_user(email="reupload-arq@test.com")
    doc = await make_document(user=user, status="partial")

    with (
        patch("app.documents.service.upload_object"),
        patch("app.documents.service.get_s3_client", return_value=MagicMock()),
        patch("app.documents.service.delete_object"),
    ):
        response = await client.post(
            f"/api/v1/documents/{doc.id}/reupload",
            files=make_upload_file(),
            headers=auth_headers(user),
        )

    assert response.status_code == 202
    assert len(mock_arq.enqueued) == 1
    assert mock_arq.enqueued[0]["func"] == "process_document"
    assert mock_arq.enqueued[0]["kwargs"]["document_id"] == str(doc.id)


@pytest.mark.asyncio
async def test_reupload_rate_limit_429(async_db_session: AsyncSession, make_user, make_document):
    """Retry uploads consume the same rate-limit quota as fresh uploads."""
    user, _ = await make_user(email="retry-ratelimit@test.com")
    doc = await make_document(user=user, status="partial")

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield async_db_session

    async def override_rate_limit_exceeded() -> None:
        raise UploadLimitExceededError()

    async def override_get_arq() -> MockArqRedis:
        return MockArqRedis()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[rate_limit_upload] = override_rate_limit_exceeded
    app.dependency_overrides[get_arq_redis] = override_get_arq

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/documents/{doc.id}/reupload",
            files=make_upload_file(),
            headers=auth_headers(user),
        )

    app.dependency_overrides.clear()

    assert response.status_code == 429
    data = response.json()
    assert data["status"] == 429


# ---------------------------------------------------------------------------
# POST /api/v1/documents/{document_id}/keep-partial  (Story 2.5)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_keep_partial_requires_auth(doc_client: tuple[AsyncClient, MockArqRedis]):
    client, _ = doc_client
    response = await client.post(f"/api/v1/documents/{uuid.uuid4()}/keep-partial")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_keep_partial_success(
    doc_client: tuple[AsyncClient, MockArqRedis],
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """keep-partial sets keep_partial=True without modifying extracted values."""
    from app.documents import repository as doc_repo

    client, _ = doc_client
    user, _ = await make_user(email="keep-partial-ok@test.com")
    doc = await make_document(user=user, status="partial")

    response = await client.post(
        f"/api/v1/documents/{doc.id}/keep-partial",
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["kept"] is True

    updated_doc = await doc_repo.get_document_by_id(async_db_session, doc.id, user.id)
    assert updated_doc.keep_partial is True


@pytest.mark.asyncio
async def test_keep_partial_rejects_non_partial_document(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    """keep-partial is rejected for documents not in partial status."""
    client, _ = doc_client
    user, _ = await make_user(email="keep-partial-wrong@test.com")
    doc = await make_document(user=user, status="completed")

    response = await client.post(
        f"/api/v1/documents/{doc.id}/keep-partial",
        headers=auth_headers(user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_keep_partial_wrong_user_returns_404(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    """User B cannot set keep-partial on User A's document."""
    client, _ = doc_client
    user_a, _ = await make_user(email="keep-partial-a@test.com")
    user_b, _ = await make_user(email="keep-partial-b@test.com")
    doc = await make_document(user=user_a, status="partial")

    response = await client.post(
        f"/api/v1/documents/{doc.id}/keep-partial",
        headers=auth_headers(user_b),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_corrupted_s3_key_uses_prefix_fallback(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """When s3_key decryption fails, prefix-based MinIO cleanup is attempted.

    Verifies that delete_objects_by_prefix is called with the correct
    {user_id}/{document_id}/ prefix and that the document row is deleted.
    """
    from app.core.config import settings as app_settings
    from app.documents import repository as doc_repo
    from app.documents import service as doc_service
    from app.documents.exceptions import DocumentNotFoundError

    user, _ = await make_user(email="delete-prefix-fallback@test.com")
    doc = await make_document(user=user, status="completed")
    # Garbage bytes — decryption will fail, triggering the prefix fallback.
    doc.s3_key_encrypted = b"not-valid-ciphertext"
    await async_db_session.flush()

    mock_prefix_delete = MagicMock(return_value=1)  # sync; called via asyncio.to_thread
    with (
        patch("app.documents.service.delete_objects_by_prefix", mock_prefix_delete),
        patch("app.documents.service.get_s3_client", return_value=MagicMock()),
    ):
        result = await doc_service.delete_document(async_db_session, user, doc.id)

    assert result.deleted is True

    expected_prefix = f"{user.id}/{doc.id}/"
    mock_prefix_delete.assert_called_once()
    call_args = mock_prefix_delete.call_args
    assert call_args.args[1] == app_settings.MINIO_BUCKET
    assert call_args.args[2] == expected_prefix

    # Document row is gone.
    with pytest.raises(DocumentNotFoundError):
        await doc_repo.get_document_by_id(async_db_session, doc.id, user.id)


@pytest.mark.asyncio
async def test_reupload_updates_filename_and_metadata(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document, async_db_session
):
    """After reupload, authoritative filename, size, and type reflect the new file.

    The proxy upload is atomic — the pending_* staging and final commit all happen
    within the single POST /reupload request. The pending columns must be cleared.
    """
    from app.documents import repository as doc_repo

    client, _ = doc_client
    user, _ = await make_user(email="reupload-meta@test.com")
    doc = await make_document(
        user=user,
        status="partial",
        filename="original.pdf",
        file_size_bytes=1000,
        file_type="application/pdf",
    )

    new_content = b"replacement-pdf-content"

    with (
        patch("app.documents.service.upload_object"),
        patch("app.documents.service.get_s3_client", return_value=MagicMock()),
        patch("app.documents.service.delete_object"),
    ):
        response = await client.post(
            f"/api/v1/documents/{doc.id}/reupload",
            files={"file": ("replacement.pdf", new_content, "application/pdf")},
            headers=auth_headers(user),
        )

    assert response.status_code == 202

    # Authoritative fields must now reflect the new upload.
    updated_doc = await doc_repo.get_document_by_id(async_db_session, doc.id, user.id)
    assert updated_doc.filename == "replacement.pdf"
    assert updated_doc.file_size_bytes == len(new_content)

    # Pending columns must be cleared after atomic promotion.
    assert updated_doc.pending_filename is None
    assert updated_doc.pending_file_size_bytes is None
    assert updated_doc.pending_s3_key_encrypted is None


@pytest.mark.asyncio
async def test_reupload_corrupted_s3_key_uses_prefix_cleanup(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document, async_db_session
):
    """When the old s3_key cannot be decrypted, prefix-based MinIO cleanup is used.

    Verifies that delete_objects_by_prefix is called with the correct prefix and
    that the endpoint still returns 202 — the cleanup failure must not block the retry.
    """
    from app.core.config import settings as app_settings

    client, _ = doc_client
    user, _ = await make_user(email="reupload-corrupt-key@test.com")
    doc = await make_document(user=user, status="partial")
    # Corrupt the encrypted key so decryption fails.
    doc.s3_key_encrypted = b"garbage-not-valid-ciphertext"
    await async_db_session.flush()

    mock_prefix_delete = MagicMock(return_value=1)  # sync; called via asyncio.to_thread

    with (
        patch("app.documents.service.upload_object"),
        patch("app.documents.service.get_s3_client", return_value=MagicMock()),
        patch("app.documents.service.delete_objects_by_prefix", mock_prefix_delete),
        patch("app.documents.service.delete_object"),
    ):
        response = await client.post(
            f"/api/v1/documents/{doc.id}/reupload",
            files=make_upload_file(),
            headers=auth_headers(user),
        )

    assert response.status_code == 202
    data = response.json()
    assert data["id"] == str(doc.id)

    # Prefix-based cleanup must have been attempted.
    expected_prefix = f"{user.id}/{doc.id}/"
    mock_prefix_delete.assert_called_once()
    call_args = mock_prefix_delete.call_args
    assert call_args.args[1] == app_settings.MINIO_BUCKET
    assert call_args.args[2] == expected_prefix


# ---------------------------------------------------------------------------
# Story 15.2 — document intelligence fields + confirm-date-year
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_documents_includes_intelligence_fields(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    """AC 1 — new document intelligence fields appear on list responses."""
    client, _ = doc_client
    user, _ = await make_user(email="list-intel@test.com")
    await make_document(user=user, status="completed")

    response = await client.get("/api/v1/documents", headers=auth_headers(user))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    item = data[0]
    assert "document_kind" in item
    assert "needs_date_confirmation" in item
    assert "partial_measured_at_text" in item
    # Fresh rows default to the safe unknown/false/null shape
    assert item["document_kind"] == "unknown"
    assert item["needs_date_confirmation"] is False
    assert item["partial_measured_at_text"] is None


@pytest.mark.asyncio
async def test_get_document_detail_includes_intelligence_fields(
    doc_client: tuple[AsyncClient, MockArqRedis],
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """AC 1 — new document intelligence fields appear on detail responses."""
    client, _ = doc_client
    user, _ = await make_user(email="detail-intel@test.com")
    doc = await make_document(user=user, status="partial")
    doc.document_kind = "analysis"
    doc.needs_date_confirmation = True
    doc.partial_measured_at_text = "12.03"
    await async_db_session.flush()

    response = await client.get(f"/api/v1/documents/{doc.id}", headers=auth_headers(user))
    assert response.status_code == 200
    data = response.json()
    assert data["document_kind"] == "analysis"
    assert data["needs_date_confirmation"] is True
    assert data["partial_measured_at_text"] == "12.03"


@pytest.mark.asyncio
async def test_confirm_date_year_requires_auth(doc_client: tuple[AsyncClient, MockArqRedis]):
    client, _ = doc_client
    response = await client.post(
        f"/api/v1/documents/{uuid.uuid4()}/confirm-date-year",
        json={"year": 2026},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_confirm_date_year_happy_path(
    doc_client: tuple[AsyncClient, MockArqRedis],
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """AC 5 — happy path propagates measured_at, clears flags, returns 200 + detail.

    Seeds 3+ health values with a mix of null / pre-set measured_at to prove
    the bulk update sweeps ALL rows regardless of their prior state. Also
    queries the DB directly after confirmation to verify persisted state,
    not just the HTTP response echo.
    """
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.documents import repository as doc_repo
    from app.health_data.models import HealthValue
    from app.health_data.repository import replace_document_health_values
    from app.processing.schemas import NormalizedHealthValue

    client, _ = doc_client
    user, _ = await make_user(email="confirm-year-ok@test.com")
    doc = await make_document(user=user, status="partial")
    doc.document_kind = "analysis"
    doc.needs_date_confirmation = True
    doc.partial_measured_at_text = "12.03"
    await async_db_session.flush()

    # Seed three health values with measured_at=None (mirrors the yearless
    # extraction path). After confirmation, the bulk helper must set all
    # three to the resolved UTC midnight timestamp.
    await replace_document_health_values(
        async_db_session,
        document_id=doc.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            ),
            NormalizedHealthValue(
                biomarker_name="Cholesterol Total",
                canonical_biomarker_name="cholesterol_total",
                value=180.0,
                unit="mg/dL",
                reference_range_low=0.0,
                reference_range_high=200.0,
                confidence=0.9,
                needs_review=False,
            ),
            NormalizedHealthValue(
                biomarker_name="HDL",
                canonical_biomarker_name="hdl",
                value=60.0,
                unit="mg/dL",
                reference_range_low=40.0,
                reference_range_high=100.0,
                confidence=0.92,
                needs_review=False,
            ),
        ],
    )
    await async_db_session.flush()

    # Use a side_effect-based async function that performs a real ai_memory
    # upsert — a bare AsyncMock(return_value=...) that does no DB work leaves
    # the service's `db.commit()` with no pending work and interacts oddly
    # with the asyncpg MissingGreenlet state-tracking once control returns.
    # The proven pattern (used by test_confirm_date_year_invalidates_and_regenerates_ai_interpretation)
    # is a side_effect that upserts a memory row, mirroring real behavior.
    from app.ai import repository as _ai_repo

    async def _side_effect_generate(db, *, document_id, user_id, values):
        await _ai_repo.upsert_ai_interpretation(
            db,
            user_id=user_id,
            document_id=document_id,
            interpretation_text="Glucose is within range.",
            model_version="claude-sonnet-4-test",
        )
        return "Glucose is within range."

    with patch(
        "app.ai.service.generate_interpretation", side_effect=_side_effect_generate
    ) as gen_mock:
        response = await client.post(
            f"/api/v1/documents/{doc.id}/confirm-date-year",
            json={"year": 2026},
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(doc.id)
    assert data["needs_date_confirmation"] is False
    assert data["partial_measured_at_text"] is None
    assert data["status"] == "completed"
    assert len(data["health_values"]) == 3
    # Every value in the response must parse to the exact resolved UTC-midnight
    # timestamp. We parse rather than string-compare so the assertion does not
    # depend on whether Pydantic serializes the tz as `Z` or `+00:00`.
    expected_dt = datetime(2026, 3, 12, 0, 0, 0, tzinfo=UTC)
    for value in data["health_values"]:
        parsed = datetime.fromisoformat(value["measured_at"].replace("Z", "+00:00"))
        assert parsed == expected_dt
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() == timedelta(0)

    # Database-level verification: persisted document + health rows reflect the sweep.
    # Cache primary-key values as plain UUIDs BEFORE any session expire so
    # subsequent queries don't trigger a lazy-load on the now-potentially-stale
    # ORM instances (which would fail with MissingGreenlet under asyncpg).
    doc_id_uuid = doc.id
    user_id_uuid = user.id
    updated_doc = await doc_repo.get_document_by_id(async_db_session, doc_id_uuid, user_id_uuid)
    assert updated_doc.needs_date_confirmation is False
    assert updated_doc.partial_measured_at_text is None

    rows = (
        await async_db_session.execute(
            select(HealthValue).where(HealthValue.document_id == doc_id_uuid)
        )
    ).scalars().all()
    assert len(rows) == 3
    db_expected = datetime(2026, 3, 12, 0, 0, 0, tzinfo=UTC)
    for row in rows:
        assert row.measured_at is not None
        # Some DBs return naive timestamps; force tz to UTC for a stable compare.
        actual = row.measured_at if row.measured_at.tzinfo else row.measured_at.replace(tzinfo=UTC)
        assert actual == db_expected
    gen_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_date_year_wrong_user_returns_404(
    doc_client: tuple[AsyncClient, MockArqRedis],
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """AC 5 — ownership enforced by get_current_user + repository lookup."""
    client, _ = doc_client
    user_a, _ = await make_user(email="confirm-year-owner-a@test.com")
    user_b, _ = await make_user(email="confirm-year-owner-b@test.com")
    doc = await make_document(user=user_a, status="partial")
    doc.document_kind = "analysis"
    doc.needs_date_confirmation = True
    doc.partial_measured_at_text = "12.03"
    await async_db_session.flush()

    response = await client.post(
        f"/api/v1/documents/{doc.id}/confirm-date-year",
        json={"year": 2026},
        headers=auth_headers(user_b),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_confirm_date_year_rejects_when_not_required(
    doc_client: tuple[AsyncClient, MockArqRedis],
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """AC 5 — documents without needs_date_confirmation=true are rejected (409)."""
    client, _ = doc_client
    user, _ = await make_user(email="confirm-year-not-needed@test.com")
    doc = await make_document(user=user, status="completed")
    # explicit: needs_date_confirmation defaults to False
    assert doc.needs_date_confirmation is False

    response = await client.post(
        f"/api/v1/documents/{doc.id}/confirm-date-year",
        json={"year": 2026},
        headers=auth_headers(user),
    )

    assert response.status_code == 409
    data = response.json()
    assert data["status"] == 409


@pytest.mark.asyncio
async def test_confirm_date_year_rejects_future_year(
    doc_client: tuple[AsyncClient, MockArqRedis],
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """AC 5 — a year beyond the current UTC year is rejected (400)."""
    client, _ = doc_client
    user, _ = await make_user(email="confirm-year-future@test.com")
    doc = await make_document(user=user, status="partial")
    doc.document_kind = "analysis"
    doc.needs_date_confirmation = True
    doc.partial_measured_at_text = "12.03"
    await async_db_session.flush()

    response = await client.post(
        f"/api/v1/documents/{doc.id}/confirm-date-year",
        json={"year": 9999},
        headers=auth_headers(user),
    )

    assert response.status_code == 400
    data = response.json()
    assert data["status"] == 400


@pytest.mark.asyncio
async def test_confirm_date_year_rejects_year_below_minimum(
    doc_client: tuple[AsyncClient, MockArqRedis], make_user, make_document
):
    """AC 5 — year below the Pydantic minimum (1900) is rejected at request validation (422)."""
    client, _ = doc_client
    user, _ = await make_user(email="confirm-year-ancient@test.com")
    doc = await make_document(user=user, status="partial")

    response = await client.post(
        f"/api/v1/documents/{doc.id}/confirm-date-year",
        json={"year": 1800},
        headers=auth_headers(user),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_confirm_date_year_invalidates_and_regenerates_ai_interpretation(
    doc_client: tuple[AsyncClient, MockArqRedis],
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """AC 5 — after confirmation, AI interpretation is invalidated THEN regenerated.

    Asserts repository-level invalidation + service-level regeneration; we assert
    behavior via repository reads rather than only the HTTP surface so that the
    test would fail if either primitive was bypassed.
    """
    from app.ai import repository as ai_repo
    from app.ai.models import AiMemory
    from app.core.encryption import encrypt_bytes
    from app.health_data.repository import replace_document_health_values
    from app.processing.schemas import NormalizedHealthValue

    client, _ = doc_client
    user, _ = await make_user(email="confirm-year-ai@test.com")
    doc = await make_document(user=user, status="partial")
    doc.document_kind = "analysis"
    doc.needs_date_confirmation = True
    doc.partial_measured_at_text = "12.03"
    await async_db_session.flush()

    await replace_document_health_values(
        async_db_session,
        document_id=doc.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )

    # Seed a stale (already-validated) AI memory row.
    memory = AiMemory(
        user_id=user.id,
        document_id=doc.id,
        interpretation_encrypted=encrypt_bytes(b"Stale interpretation pre-confirmation."),
        model_version="claude-sonnet-4-pre-confirm",
        safety_validated=True,
    )
    async_db_session.add(memory)
    await async_db_session.flush()

    # Track repository-level call ordering to prove invalidation ran before regeneration.
    call_order: list[str] = []
    # Snapshot safety_validated AFTER invalidate + BEFORE regenerate to prove
    # the intermediate state passed through invalidated=False.
    post_invalidate_validated: list[bool | None] = []

    real_invalidate = ai_repo.invalidate_interpretation

    async def _wrapped_invalidate(db, *, user_id, document_id):
        call_order.append("invalidate")
        return await real_invalidate(db, user_id=user_id, document_id=document_id)

    async def _fake_generate(db, *, document_id, user_id, values):
        call_order.append("generate")
        # Observe the invalidated state before we replace it with regen.
        from sqlalchemy import select as _select

        from app.ai.models import AiMemory as _AiMemory

        row = (
            await db.execute(
                _select(_AiMemory).where(_AiMemory.document_id == document_id)
            )
        ).scalars().first()
        post_invalidate_validated.append(row.safety_validated if row is not None else None)

        await ai_repo.upsert_ai_interpretation(
            db,
            user_id=user_id,
            document_id=document_id,
            interpretation_text="Regenerated interpretation after year confirmation.",
            model_version="claude-sonnet-4-post-confirm",
        )
        return "Regenerated interpretation after year confirmation."

    with (
        patch("app.ai.repository.invalidate_interpretation", side_effect=_wrapped_invalidate),
        patch("app.ai.service.generate_interpretation", side_effect=_fake_generate),
    ):
        response = await client.post(
            f"/api/v1/documents/{doc.id}/confirm-date-year",
            json={"year": 2026},
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    assert call_order == ["invalidate", "generate"]

    # Round-2 HIGH-fix guard: between invalidate and regenerate, the prior
    # memory row must have been flipped to safety_validated=False so that a
    # regeneration failure would leave a strictly-invalidated row rather than
    # a stale "valid" interpretation.
    assert post_invalidate_validated == [False]

    # Prove the stored interpretation reflects the regenerated text.
    stored = await ai_repo.get_interpretation_and_metadata(
        async_db_session, user_id=user.id, document_id=doc.id
    )
    assert stored is not None
    text, _, memory_row = stored
    assert "Regenerated interpretation" in text
    assert memory_row.model_version == "claude-sonnet-4-post-confirm"
    assert memory_row.safety_validated is True


@pytest.mark.asyncio
async def test_confirm_date_year_ai_regeneration_failure_persists_confirmation(
    doc_client: tuple[AsyncClient, MockArqRedis],
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """AC 5 — AI regeneration failure must not roll back the measured_at/flag updates.

    When the LLM call raises, the endpoint still returns 200 and the document is
    committed with needs_date_confirmation=False + resolved measured_at. The
    stale interpretation stays invalidated (safety_validated=False) rather than
    being replaced by a regenerated one.
    """
    from sqlalchemy import select

    from app.ai import repository as ai_repo
    from app.ai.models import AiMemory
    from app.core.encryption import encrypt_bytes
    from app.documents import repository as doc_repo
    from app.health_data.models import HealthValue
    from app.health_data.repository import replace_document_health_values
    from app.processing.schemas import NormalizedHealthValue

    client, _ = doc_client
    user, _ = await make_user(email="confirm-year-ai-fail@test.com")
    doc = await make_document(user=user, status="partial")
    doc.document_kind = "analysis"
    doc.needs_date_confirmation = True
    doc.partial_measured_at_text = "12.03"
    await async_db_session.flush()

    await replace_document_health_values(
        async_db_session,
        document_id=doc.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )
    # Seed a prior interpretation. After regen failure it should remain but be
    # invalidated (safety_validated=False), not replaced by a new row.
    memory = AiMemory(
        user_id=user.id,
        document_id=doc.id,
        interpretation_encrypted=encrypt_bytes(b"Stale interpretation."),
        model_version="claude-sonnet-4-pre",
        safety_validated=True,
    )
    async_db_session.add(memory)
    await async_db_session.flush()

    # Use a side_effect coroutine so the exception is raised inside a real
    # async call frame — a bare AsyncMock's side_effect behaves oddly with
    # async DB session state-tracking once control returns to the caller.
    async def _raise_llm_outage(db, *, document_id, user_id, values):
        raise RuntimeError("llm outage")

    with patch(
        "app.ai.service.generate_interpretation", side_effect=_raise_llm_outage
    ):
        response = await client.post(
            f"/api/v1/documents/{doc.id}/confirm-date-year",
            json={"year": 2026},
            headers=auth_headers(user),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["needs_date_confirmation"] is False
    assert data["partial_measured_at_text"] is None
    # Health rows were swept to the resolved timestamp before the AI call fired.
    from datetime import datetime as _dt

    expected_dt = _dt(2026, 3, 12, 0, 0, 0, tzinfo=UTC)
    parsed = _dt.fromisoformat(
        data["health_values"][0]["measured_at"].replace("Z", "+00:00")
    )
    assert parsed == expected_dt

    # DB-level: document + health rows reflect the sweep. Cache primary-key
    # UUIDs BEFORE any session expire so subsequent queries don't trigger
    # a lazy-load on stale ORM instances (MissingGreenlet under asyncpg).
    doc_id_uuid = doc.id
    user_id_uuid = user.id
    updated_doc = await doc_repo.get_document_by_id(async_db_session, doc_id_uuid, user_id_uuid)
    assert updated_doc.needs_date_confirmation is False
    assert updated_doc.partial_measured_at_text is None

    rows = (
        await async_db_session.execute(
            select(HealthValue).where(HealthValue.document_id == doc_id_uuid)
        )
    ).scalars().all()
    assert all(r.measured_at is not None for r in rows)

    # The pre-existing AI memory row should remain but be invalidated. The
    # retrieval helper returns None when safety_validated is False, which is
    # precisely the "no valid interpretation" contract we want.
    stored = await ai_repo.get_interpretation_and_metadata(
        async_db_session, user_id=user_id_uuid, document_id=doc_id_uuid
    )
    assert stored is None


@pytest.mark.asyncio
async def test_confirm_date_year_rejects_when_partial_text_is_none(
    doc_client: tuple[AsyncClient, MockArqRedis],
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Defensive — needs_date_confirmation=True but partial_measured_at_text=None is rejected.

    needs_date_confirmation and partial_measured_at_text are set in lockstep by
    the finalizer, but the row shape does permit an inconsistent state. The
    service must refuse rather than synthesize a date without a fragment.
    """
    client, _ = doc_client
    user, _ = await make_user(email="confirm-year-null-fragment@test.com")
    doc = await make_document(user=user, status="partial")
    doc.document_kind = "analysis"
    doc.needs_date_confirmation = True
    doc.partial_measured_at_text = None  # inconsistent but reachable
    await async_db_session.flush()

    response = await client.post(
        f"/api/v1/documents/{doc.id}/confirm-date-year",
        json={"year": 2026},
        headers=auth_headers(user),
    )

    assert response.status_code == 400
    data = response.json()
    assert data["status"] == 400


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("partial_text", "year"),
    [
        ("30.02", 2024),  # Feb 30 never exists
        ("29.02", 2023),  # 2023 is not a leap year
    ],
)
async def test_confirm_date_year_rejects_invalid_calendar_dates(
    doc_client: tuple[AsyncClient, MockArqRedis],
    async_db_session: AsyncSession,
    make_user,
    make_document,
    partial_text: str,
    year: int,
):
    """Invalid calendar combinations (Feb 30, Feb 29 on non-leap) return 400."""
    client, _ = doc_client
    user, _ = await make_user(email=f"confirm-year-invalid-{partial_text}@test.com")
    doc = await make_document(user=user, status="partial")
    doc.document_kind = "analysis"
    doc.needs_date_confirmation = True
    doc.partial_measured_at_text = partial_text
    await async_db_session.flush()

    response = await client.post(
        f"/api/v1/documents/{doc.id}/confirm-date-year",
        json={"year": year},
        headers=auth_headers(user),
    )

    assert response.status_code == 400
    assert response.json()["status"] == 400


@pytest.mark.asyncio
async def test_confirm_date_year_boundary_years(
    doc_client: tuple[AsyncClient, MockArqRedis],
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Boundary year coverage: 1900 inclusive, 1899 rejected, current_year-1/current_year ok, future rejected.

    Separate test bodies per boundary so each uses an isolated document + user
    (needs_date_confirmation is single-shot: once confirmed it flips back to
    False and a second confirm raises 409).
    """
    from datetime import UTC, datetime

    from app.health_data.repository import replace_document_health_values
    from app.processing.schemas import NormalizedHealthValue

    client, _ = doc_client
    current_year = datetime.now(UTC).year

    async def _seed_doc(email: str):
        user, _ = await make_user(email=email)
        doc = await make_document(user=user, status="partial")
        doc.document_kind = "analysis"
        doc.needs_date_confirmation = True
        doc.partial_measured_at_text = "12.03"
        await async_db_session.flush()
        await replace_document_health_values(
            async_db_session,
            document_id=doc.id,
            user_id=user.id,
            measured_at=None,
            values=[
                NormalizedHealthValue(
                    biomarker_name="Glucose",
                    canonical_biomarker_name="glucose",
                    value=91.0,
                    unit="mg/dL",
                    reference_range_low=70.0,
                    reference_range_high=99.0,
                    confidence=0.95,
                    needs_review=False,
                )
            ],
        )
        await async_db_session.commit()
        return user, doc

    # 1900 — inclusive minimum bound → 200.
    user, doc = await _seed_doc("confirm-year-1900@test.com")
    with patch("app.ai.service.generate_interpretation", new=AsyncMock(return_value="ok")):
        resp = await client.post(
            f"/api/v1/documents/{doc.id}/confirm-date-year",
            json={"year": 1900},
            headers=auth_headers(user),
        )
    assert resp.status_code == 200

    # 1899 — below the Pydantic minimum → 422.
    user, doc = await _seed_doc("confirm-year-1899@test.com")
    resp = await client.post(
        f"/api/v1/documents/{doc.id}/confirm-date-year",
        json={"year": 1899},
        headers=auth_headers(user),
    )
    assert resp.status_code == 422

    # current_year - 1 → 200.
    user, doc = await _seed_doc("confirm-year-prev@test.com")
    with patch("app.ai.service.generate_interpretation", new=AsyncMock(return_value="ok")):
        resp = await client.post(
            f"/api/v1/documents/{doc.id}/confirm-date-year",
            json={"year": current_year - 1},
            headers=auth_headers(user),
        )
    assert resp.status_code == 200

    # current_year → 200.
    user, doc = await _seed_doc("confirm-year-current@test.com")
    with patch("app.ai.service.generate_interpretation", new=AsyncMock(return_value="ok")):
        resp = await client.post(
            f"/api/v1/documents/{doc.id}/confirm-date-year",
            json={"year": current_year},
            headers=auth_headers(user),
        )
    assert resp.status_code == 200

    # current_year + 1 → 400 (service-layer future-year rejection).
    user, doc = await _seed_doc("confirm-year-future@test.com")
    resp = await client.post(
        f"/api/v1/documents/{doc.id}/confirm-date-year",
        json={"year": current_year + 1},
        headers=auth_headers(user),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_confirm_date_year_invalidates_even_when_values_for_ai_is_empty(
    doc_client: tuple[AsyncClient, MockArqRedis],
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Round-2 HIGH-fix guard: invalidation is unconditional, regeneration is gated.

    Simulates a concurrent reprocess / full-row decryption failure where the
    post-sweep read returns zero usable records but a positive skipped count.
    The stored AI interpretation MUST be invalidated (safety_validated=False)
    so stale text does not render against the new timeline, and
    ai_service.generate_interpretation MUST NOT be called (no values to feed).
    """
    from app.ai import repository as ai_repo
    from app.ai.models import AiMemory
    from app.core.encryption import encrypt_bytes
    from app.health_data.repository import (
        HealthValueListResult,
        replace_document_health_values,
    )
    from app.processing.schemas import NormalizedHealthValue

    client, _ = doc_client
    user, _ = await make_user(email="confirm-year-empty-ai@test.com")
    doc = await make_document(user=user, status="partial")
    doc.document_kind = "analysis"
    doc.needs_date_confirmation = True
    doc.partial_measured_at_text = "12.03"
    await async_db_session.flush()

    # Seed one real row so the "needs_date_confirmation=True requires ≥1 row"
    # invariant holds at seed time. The patched list_values_by_document will
    # later report an empty records list simulating decryption failure.
    await replace_document_health_values(
        async_db_session,
        document_id=doc.id,
        user_id=user.id,
        measured_at=None,
        values=[
            NormalizedHealthValue(
                biomarker_name="Glucose",
                canonical_biomarker_name="glucose",
                value=91.0,
                unit="mg/dL",
                reference_range_low=70.0,
                reference_range_high=99.0,
                confidence=0.95,
                needs_review=False,
            )
        ],
    )

    # Seed a stale (already-validated) AI memory row.
    memory = AiMemory(
        user_id=user.id,
        document_id=doc.id,
        interpretation_encrypted=encrypt_bytes(b"Stale interpretation pre-confirmation."),
        model_version="claude-sonnet-4-pre-confirm",
        safety_validated=True,
    )
    async_db_session.add(memory)
    await async_db_session.flush()
    await async_db_session.commit()

    async def _empty_list_with_skipped(db, *, document_id, user_id):
        return HealthValueListResult(
            records=[], skipped_corrupt_records=1, scope="list"
        )

    generate_mock = AsyncMock(return_value="should-not-run")

    with (
        patch(
            "app.health_data.repository.list_values_by_document",
            side_effect=_empty_list_with_skipped,
        ),
        patch("app.ai.service.generate_interpretation", generate_mock),
    ):
        response = await client.post(
            f"/api/v1/documents/{doc.id}/confirm-date-year",
            json={"year": 2026},
            headers=auth_headers(user),
        )

    assert response.status_code == 200

    # Regeneration must NOT have fired — values_for_ai was empty.
    generate_mock.assert_not_awaited()

    # The AiMemory row still exists BUT is marked invalid — unconditional
    # invalidation ran independent of the empty values_for_ai.
    from sqlalchemy import select

    rows = (
        await async_db_session.execute(
            select(AiMemory).where(AiMemory.document_id == doc.id)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].safety_validated is False

    # And the retrieval contract reflects the invalidation.
    stored = await ai_repo.get_interpretation_and_metadata(
        async_db_session, user_id=user.id, document_id=doc.id
    )
    assert stored is None
