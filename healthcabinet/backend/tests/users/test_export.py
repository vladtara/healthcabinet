import csv
import io
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.repository import create_audit_log
from app.ai.models import AiMemory
from app.ai.repository import upsert_ai_interpretation
from app.auth.repository import create_consent_log
from app.core.encryption import encrypt_bytes
from app.core.security import create_access_token
from app.documents.exceptions import DocumentNotFoundError
from app.users.export_repository import get_document_file_bytes


def _read_csv(zip_file: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    """Read a CSV file from a ZIP and return as list of dicts."""
    with zip_file.open(name) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
        return list(reader)


@pytest.fixture
def mock_s3():
    """Mock S3 client and get_object_bytes to return fake document content."""
    fake_content = b"fake-pdf-content"
    client = MagicMock()
    with (
        patch("app.users.router.get_s3_client", return_value=client) as mock_client,
        patch(
            "app.users.export_repository.get_object_bytes",
            return_value=fake_content,
        ) as mock_get,
    ):
        yield mock_client, mock_get, fake_content


async def _setup_user_with_data(
    db: AsyncSession,
    make_user,
    make_document,
    make_health_value,
    *,
    email: str = "export@test.com",
):
    """Create a user with documents, health values, AI interpretation, consent, and audit log."""
    user, password = await make_user(email=email)

    # Document with encrypted s3 key
    doc = await make_document(user=user, status="completed", filename="blood_test.pdf")
    doc.s3_key_encrypted = encrypt_bytes(f"{user.id}/{doc.id}/blood_test.pdf".encode())
    await db.flush()
    await db.refresh(doc)

    # Health value
    hv = await make_health_value(
        user=user,
        document=doc,
        biomarker_name="Cholesterol",
        canonical_biomarker_name="cholesterol_total",
        value=5.2,
        unit="mmol/L",
        confidence=0.95,
    )

    # AI interpretation
    await upsert_ai_interpretation(db, user.id, doc.id, "Your cholesterol is normal.", "claude-3.5")

    # Consent log
    await create_consent_log(db, user.id, "health_data_processing", "1.0")

    # Admin audit log (simulating an admin correction)
    admin_user, _ = await make_user(email=f"admin-{email}")
    admin_user.role = "admin"
    await db.flush()
    await create_audit_log(
        db,
        admin_id=admin_user.id,
        user_id=user.id,
        document_id=doc.id,
        health_value_id=hv.id,
        value_name="Cholesterol",
        original_value="5.0",
        new_value="5.2",
        reason="OCR correction",
    )

    return user, password, doc, hv


@pytest.mark.asyncio
async def test_export_returns_valid_zip_with_all_files(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
    mock_s3,
):
    """4.1: Test export endpoint returns valid ZIP with all expected files."""
    user, _, doc, _ = await _setup_user_with_data(
        async_db_session, make_user, make_document, make_health_value
    )
    token = create_access_token(str(user.id))

    response = await test_client.post(
        "/api/v1/users/me/export",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "healthcabinet-export-" in response.headers["content-disposition"]

    zf = zipfile.ZipFile(io.BytesIO(response.content))
    names = zf.namelist()
    assert "health_values.csv" in names
    assert "ai_interpretations.csv" in names
    assert "admin_corrections.csv" in names
    assert "consent_log.csv" in names
    assert "summary.txt" in names
    assert f"documents/{doc.filename}" in names


@pytest.mark.asyncio
async def test_export_csv_contents_correct(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
    mock_s3,
):
    """4.2: Test CSV contents have correct columns and decrypted values."""
    user, _, doc, _ = await _setup_user_with_data(
        async_db_session,
        make_user,
        make_document,
        make_health_value,
        email="csv@test.com",
    )
    token = create_access_token(str(user.id))

    response = await test_client.post(
        "/api/v1/users/me/export",
        headers={"Authorization": f"Bearer {token}"},
    )

    zf = zipfile.ZipFile(io.BytesIO(response.content))

    # health_values.csv
    hv_rows = _read_csv(zf, "health_values.csv")
    assert len(hv_rows) == 1
    row = hv_rows[0]
    assert row["biomarker_name"] == "Cholesterol"
    assert row["canonical_biomarker_name"] == "cholesterol_total"
    assert float(row["value"]) == 5.2
    assert row["unit"] == "mmol/L"
    assert row["confidence"] == "0.95"
    assert "document_id" in row
    assert "reference_low" in row
    assert "reference_high" in row
    assert "needs_review" in row
    assert "is_flagged" in row
    assert "flagged_at" in row
    assert "flag_reviewed_at" in row
    assert "extracted_at" in row

    # ai_interpretations.csv
    ai_rows = _read_csv(zf, "ai_interpretations.csv")
    assert len(ai_rows) == 1
    assert ai_rows[0]["interpretation"] == "Your cholesterol is normal."
    assert ai_rows[0]["document_id"] == str(doc.id)
    assert ai_rows[0]["created_at"] != ""

    # consent_log.csv
    cl_rows = _read_csv(zf, "consent_log.csv")
    assert len(cl_rows) == 1
    assert cl_rows[0]["consent_type"] == "health_data_processing"
    assert cl_rows[0]["privacy_policy_version"] == "1.0"

    # summary.txt
    summary = zf.read("summary.txt").decode("utf-8")
    assert user.email in summary
    assert "Documents: 1" in summary
    assert "Health values: 1" in summary
    assert "AI interpretations: 1" in summary


@pytest.mark.asyncio
async def test_export_empty_user_gets_minimal_zip(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    mock_s3,
):
    """4.3: Test empty-document user gets ZIP with only consent_log.csv and summary.txt."""
    user, _ = await make_user(email="empty@test.com")
    await create_consent_log(async_db_session, user.id, "health_data_processing", "1.0")
    token = create_access_token(str(user.id))

    response = await test_client.post(
        "/api/v1/users/me/export",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    names = zf.namelist()

    # Must have consent_log.csv and summary.txt
    assert set(names) == {"consent_log.csv", "summary.txt"}

    # No document files
    assert not any(n.startswith("documents/") for n in names)

    summary = zf.read("summary.txt").decode("utf-8")
    assert "Documents: 0" in summary


@pytest.mark.asyncio
async def test_export_scoped_to_authenticated_user(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
    mock_s3,
):
    """4.4: Test export is scoped to authenticated user only (no IDOR)."""
    # Create user A with data
    user_a, _, _, _ = await _setup_user_with_data(
        async_db_session,
        make_user,
        make_document,
        make_health_value,
        email="user_a@test.com",
    )

    # Create user B with different data
    user_b, _ = await make_user(email="user_b@test.com")
    doc_b = await make_document(user=user_b, filename="other.pdf")
    doc_b.s3_key_encrypted = encrypt_bytes(f"{user_b.id}/{doc_b.id}/other.pdf".encode())
    await async_db_session.flush()
    await make_health_value(
        user=user_b,
        document=doc_b,
        biomarker_name="Glucose",
        canonical_biomarker_name="glucose_fasting",
        value=6.1,
    )

    # Export as user B
    token_b = create_access_token(str(user_b.id))
    response = await test_client.post(
        "/api/v1/users/me/export",
        headers={"Authorization": f"Bearer {token_b}"},
    )

    zf = zipfile.ZipFile(io.BytesIO(response.content))

    # User B's export should NOT contain user A's data
    hv_rows = _read_csv(zf, "health_values.csv")
    assert len(hv_rows) == 1
    assert hv_rows[0]["biomarker_name"] == "Glucose"

    # No AI interpretations (user B has none)
    ai_rows = _read_csv(zf, "ai_interpretations.csv")
    assert len(ai_rows) == 0

    # User A's documents should not be present
    names = zf.namelist()
    assert "documents/blood_test.pdf" not in names


@pytest.mark.asyncio
async def test_export_admin_corrections_included(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
    mock_s3,
):
    """4.5: Test admin_corrections.csv includes correction records linked to user's documents."""
    user, _, doc, hv = await _setup_user_with_data(
        async_db_session,
        make_user,
        make_document,
        make_health_value,
        email="corrections@test.com",
    )
    token = create_access_token(str(user.id))

    response = await test_client.post(
        "/api/v1/users/me/export",
        headers={"Authorization": f"Bearer {token}"},
    )

    zf = zipfile.ZipFile(io.BytesIO(response.content))
    ac_rows = _read_csv(zf, "admin_corrections.csv")
    assert len(ac_rows) == 1
    assert ac_rows[0]["value_name"] == "Cholesterol"
    assert ac_rows[0]["original_value"] == "5.0"
    assert ac_rows[0]["new_value"] == "5.2"
    assert ac_rows[0]["reason"] == "OCR correction"
    assert ac_rows[0]["document_id"] == str(doc.id)


@pytest.mark.asyncio
async def test_export_admin_corrections_survive_document_deletion(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
    mock_s3,
):
    """Correction history should remain exportable after the source document is deleted."""
    from app.documents import service as document_service

    user, _, doc, _ = await _setup_user_with_data(
        async_db_session,
        make_user,
        make_document,
        make_health_value,
        email="deleted-corrections@test.com",
    )
    token = create_access_token(str(user.id))

    with (
        patch("app.documents.service.get_s3_client", return_value=MagicMock()),
        patch("app.documents.service.delete_object"),
    ):
        result = await document_service.delete_document(async_db_session, user, doc.id)

    assert result.deleted is True

    response = await test_client.post(
        "/api/v1/users/me/export",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    names = set(zf.namelist())
    assert "admin_corrections.csv" in names
    assert "health_values.csv" not in names
    assert "ai_interpretations.csv" not in names
    assert not any(name.startswith("documents/") for name in names)

    ac_rows = _read_csv(zf, "admin_corrections.csv")
    assert len(ac_rows) == 1
    assert ac_rows[0]["document_id"] == ""
    assert ac_rows[0]["value_name"] == "Cholesterol"
    assert ac_rows[0]["reason"] == "OCR correction"

    summary = zf.read("summary.txt").decode("utf-8")
    assert "Documents: 0" in summary


@pytest.mark.asyncio
async def test_export_sanitizes_and_deduplicates_document_filenames(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    mock_s3,
):
    """Document ZIP entries should not allow traversal and must remain unique."""
    user, _ = await make_user(email="unsafe@test.com")
    await create_consent_log(async_db_session, user.id, "health_data_processing", "1.0")

    doc_a = await make_document(user=user, status="completed", filename="../evil.pdf")
    doc_a.s3_key_encrypted = encrypt_bytes(f"{user.id}/{doc_a.id}/evil.pdf".encode())

    doc_b = await make_document(user=user, status="completed", filename="nested/../evil.pdf")
    doc_b.s3_key_encrypted = encrypt_bytes(f"{user.id}/{doc_b.id}/evil.pdf".encode())
    await async_db_session.flush()

    token = create_access_token(str(user.id))
    response = await test_client.post(
        "/api/v1/users/me/export",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    document_entries = sorted(name for name in zf.namelist() if name.startswith("documents/"))
    assert document_entries == ["documents/evil-1.pdf", "documents/evil.pdf"]


@pytest.mark.asyncio
async def test_export_includes_unvalidated_ai_and_discloses_skipped_corrupt_records(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    make_health_value,
    mock_s3,
):
    """Export should include all held AI text and disclose corrupt rows in the summary."""
    user, _, doc, _ = await _setup_user_with_data(
        async_db_session,
        make_user,
        make_document,
        make_health_value,
        email="corrupt@test.com",
    )

    corrupt_hv = await make_health_value(
        user=user,
        document=doc,
        biomarker_name="Broken Value",
        canonical_biomarker_name="broken_value",
        value=4.2,
    )
    corrupt_hv.value_encrypted = b"not-valid-ciphertext"

    unvalidated_doc = await make_document(
        user=user,
        status="completed",
        filename="pending-review.pdf",
    )
    unvalidated_doc.s3_key_encrypted = encrypt_bytes(
        f"{user.id}/{unvalidated_doc.id}/pending-review.pdf".encode()
    )
    async_db_session.add(
        AiMemory(
            user_id=user.id,
            document_id=unvalidated_doc.id,
            interpretation_encrypted=encrypt_bytes(b"Pending review interpretation."),
            safety_validated=False,
        )
    )

    corrupt_ai_doc = await make_document(
        user=user,
        status="completed",
        filename="broken-ai.pdf",
    )
    corrupt_ai_doc.s3_key_encrypted = encrypt_bytes(
        f"{user.id}/{corrupt_ai_doc.id}/broken-ai.pdf".encode()
    )
    async_db_session.add(
        AiMemory(
            user_id=user.id,
            document_id=corrupt_ai_doc.id,
            interpretation_encrypted=b"not-valid-ciphertext",
            safety_validated=False,
        )
    )
    await async_db_session.flush()

    token = create_access_token(str(user.id))
    response = await test_client.post(
        "/api/v1/users/me/export",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(response.content))

    ai_rows = _read_csv(zf, "ai_interpretations.csv")
    assert {row["interpretation"] for row in ai_rows} == {
        "Your cholesterol is normal.",
        "Pending review interpretation.",
    }

    summary = zf.read("summary.txt").decode("utf-8")
    assert "Health values unavailable due to decryption errors: 1" in summary
    assert "AI interpretations unavailable due to decryption errors: 1" in summary


@pytest.mark.asyncio
async def test_get_document_file_bytes_handles_concurrent_document_deletion(
    async_db_session: AsyncSession,
    make_user,
    make_document,
):
    """Concurrent document deletion should not crash the export."""
    user, _ = await make_user(email="deleted-doc@test.com")
    doc = await make_document(user=user, filename="gone.pdf")

    with patch(
        "app.users.export_repository.get_document_s3_key_optional",
        new=AsyncMock(side_effect=DocumentNotFoundError()),
    ):
        result = await get_document_file_bytes(
            async_db_session,
            user.id,
            doc,
            MagicMock(),
            "bucket",
        )

    assert result is None


@pytest.mark.asyncio
async def test_export_closes_s3_client_after_streaming(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    mock_s3,
):
    """The export route should always close the S3 client it creates."""
    user, _ = await make_user(email="close-s3@test.com")
    token = create_access_token(str(user.id))

    response = await test_client.post(
        "/api/v1/users/me/export",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    mock_client, _, _ = mock_s3
    mock_client.return_value.close.assert_called_once()


@pytest.mark.asyncio
async def test_export_summary_counts_only_written_document_files(
    test_client: AsyncClient,
    async_db_session: AsyncSession,
    make_user,
    make_document,
    mock_s3,
):
    """summary.txt should match the documents actually written into the ZIP."""
    user, _ = await make_user(email="partial-export@test.com")
    await create_consent_log(async_db_session, user.id, "health_data_processing", "1.0")

    doc_a = await make_document(user=user, status="completed", filename="first.pdf")
    doc_a.s3_key_encrypted = encrypt_bytes(f"{user.id}/{doc_a.id}/first.pdf".encode())
    doc_b = await make_document(user=user, status="completed", filename="second.pdf")
    doc_b.s3_key_encrypted = encrypt_bytes(f"{user.id}/{doc_b.id}/second.pdf".encode())
    await async_db_session.flush()

    token = create_access_token(str(user.id))
    with patch(
        "app.users.export_service.get_document_file_bytes",
        new=AsyncMock(side_effect=[b"first-bytes", None]),
    ):
        response = await test_client.post(
            "/api/v1/users/me/export",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    document_entries = [name for name in zf.namelist() if name.startswith("documents/")]
    assert len(document_entries) == 1

    summary = zf.read("summary.txt").decode("utf-8")
    assert "Documents: 1" in summary
    assert "Documents unavailable due to retrieval errors: 1" in summary
