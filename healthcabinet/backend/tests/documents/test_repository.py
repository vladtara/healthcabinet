"""
Tests for documents/repository.py.

Verifies s3_key encryption round-trip and user isolation.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_bytes
from app.documents.exceptions import DocumentNotFoundError
from app.documents.repository import create_document, get_document_by_id, update_document_status


@pytest.mark.asyncio
async def test_create_document_encrypts_s3_key(async_db_session: AsyncSession, make_user):
    """s3_key_encrypted stored in DB must be different from the plaintext s3_key."""
    user, _ = await make_user(email="enctest@test.com")
    doc_id = uuid.uuid4()
    s3_key = f"{user.id}/{doc_id}/test.pdf"

    doc = await create_document(
        async_db_session,
        document_id=doc_id,
        user_id=user.id,
        s3_key=s3_key,
        filename="test.pdf",
        file_size_bytes=1024,
        file_type="application/pdf",
    )

    assert doc.s3_key_encrypted is not None
    assert doc.s3_key_encrypted != s3_key.encode()


@pytest.mark.asyncio
async def test_s3_key_encryption_round_trip(async_db_session: AsyncSession, make_user):
    """Decrypting the stored s3_key_encrypted must yield the original s3_key."""
    user, _ = await make_user(email="roundtrip@test.com")
    doc_id = uuid.uuid4()
    s3_key = f"{user.id}/{doc_id}/lab_results.pdf"

    doc = await create_document(
        async_db_session,
        document_id=doc_id,
        user_id=user.id,
        s3_key=s3_key,
        filename="lab_results.pdf",
        file_size_bytes=2048,
        file_type="application/pdf",
    )

    assert doc.s3_key_encrypted is not None
    decrypted = decrypt_bytes(doc.s3_key_encrypted).decode()
    assert decrypted == s3_key


@pytest.mark.asyncio
async def test_get_document_by_id_user_isolation(
    async_db_session: AsyncSession, make_user, make_document
):
    """User B cannot access User A's document — returns DocumentNotFoundError."""
    user_a, _ = await make_user(email="owner@test.com")
    user_b, _ = await make_user(email="intruder@test.com")
    doc = await make_document(user=user_a)

    with pytest.raises(DocumentNotFoundError):
        await get_document_by_id(async_db_session, doc.id, user_b.id)


@pytest.mark.asyncio
async def test_get_document_by_id_returns_document(
    async_db_session: AsyncSession, make_user, make_document
):
    """Owner can retrieve their own document."""
    user, _ = await make_user(email="retriever@test.com")
    doc = await make_document(user=user)

    retrieved = await get_document_by_id(async_db_session, doc.id, user.id)
    assert retrieved.id == doc.id
    assert retrieved.user_id == user.id


@pytest.mark.asyncio
async def test_get_document_by_id_not_found(async_db_session: AsyncSession, make_user):
    """Non-existent document_id raises DocumentNotFoundError."""
    user, _ = await make_user(email="notfound@test.com")

    with pytest.raises(DocumentNotFoundError):
        await get_document_by_id(async_db_session, uuid.uuid4(), user.id)


@pytest.mark.asyncio
async def test_update_document_status(async_db_session: AsyncSession, make_user, make_document):
    """update_document_status changes status and optionally sets arq_job_id."""
    user, _ = await make_user(email="statusupdate@test.com")
    doc = await make_document(user=user, status="pending")

    job_id = str(uuid.uuid4())
    updated = await update_document_status(
        async_db_session, doc.id, user.id, "pending", arq_job_id=job_id
    )
    assert updated.status == "pending"
    assert updated.arq_job_id == job_id


@pytest.mark.asyncio
async def test_update_document_status_wrong_user_raises(
    async_db_session: AsyncSession, make_user, make_document
):
    """update_document_status raises DocumentNotFoundError when user_id does not match."""
    user_a, _ = await make_user(email="statusowner@test.com")
    user_b, _ = await make_user(email="statusintruder@test.com")
    doc = await make_document(user=user_a, status="pending")

    with pytest.raises(DocumentNotFoundError):
        await update_document_status(async_db_session, doc.id, user_b.id, "processing")
