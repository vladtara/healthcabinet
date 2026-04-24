"""
Documents repository — ALL DB reads/writes live here.

CRITICAL: encrypt_bytes/decrypt_bytes MUST only be called here, never in service.py or router.py.
s3_key format: {user_id}/{document_id}/{filename}
"""

import logging
import uuid
from datetime import UTC, datetime

from cryptography.exceptions import InvalidTag
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_bytes, encrypt_bytes
from app.documents.exceptions import DocumentNotFoundError, DocumentRetryNotAllowedError
from app.documents.models import Document
from app.health_data.models import HealthValue

logger = logging.getLogger(__name__)


async def create_document(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    s3_key: str,
    filename: str,
    file_size_bytes: int,
    file_type: str,
) -> Document:
    encrypted_key = encrypt_bytes(s3_key.encode())
    doc = Document(
        id=document_id,
        user_id=user_id,
        s3_key_encrypted=encrypted_key,
        filename=filename,
        file_size_bytes=file_size_bytes,
        file_type=file_type,
        status="pending",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


async def get_document_by_id(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None or doc.user_id != user_id:
        raise DocumentNotFoundError()
    return doc


async def get_document_s3_key(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> str:
    """Retrieve and decrypt the s3_key for a document. Callers that need the key use this."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None or doc.user_id != user_id:
        raise DocumentNotFoundError()
    if not doc.s3_key_encrypted:
        raise DocumentNotFoundError()
    try:
        return decrypt_bytes(doc.s3_key_encrypted).decode()
    except (InvalidTag, UnicodeDecodeError, ValueError) as exc:
        raise DocumentNotFoundError() from exc


async def get_documents_by_user(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[Document]:
    result = await db.execute(
        select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document_by_id_internal(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> Document:
    """Look up a document by ID without user_id check.

    INTERNAL USE ONLY — for ARQ worker context where there is no authenticated
    user. Document access scope is enforced at the router layer, never here.
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise DocumentNotFoundError()
    return doc


async def get_document_s3_key_internal(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> str:
    """Retrieve and decrypt a document object key for trusted worker context."""
    doc = await get_document_by_id_internal(db, document_id)
    if not doc.s3_key_encrypted:
        raise DocumentNotFoundError()
    try:
        return decrypt_bytes(doc.s3_key_encrypted).decode()
    except (InvalidTag, UnicodeDecodeError, ValueError) as exc:
        raise DocumentNotFoundError() from exc


_ALLOWED_INTERNAL_STATUSES = frozenset({"processing", "completed", "failed", "partial"})


async def update_document_status_internal(
    db: AsyncSession,
    document_id: uuid.UUID,
    status: str,
) -> Document:
    """Update document status without user_id check.

    INTERNAL USE ONLY — for ARQ worker context. Sets explicit updated_at to
    avoid relying on SQLAlchemy onupdate which does not fire reliably via flush
    without a full commit cycle (asyncpg + server-side func.now()).
    """
    if status not in _ALLOWED_INTERNAL_STATUSES:
        raise ValueError(f"Invalid document status for internal update: {status!r}")
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise DocumentNotFoundError()
    doc.status = status
    doc.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(doc)
    return doc


async def get_document_s3_key_optional(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> str | None:
    """Retrieve and decrypt the s3_key for a document, returning None on decryption failure.

    Enforces user ownership (raises DocumentNotFoundError if the document does not
    exist or belongs to another user). On s3_key decryption failure, logs a
    structured warning — including the MinIO object prefix — so operators can audit
    and clean up any orphaned blobs:

        mc ls myminio/<bucket>/<user_id>/<document_id>/
        mc rm --recursive --force myminio/<bucket>/<user_id>/<document_id>/

    Raising on decryption failure would make the document permanently undeletable,
    so None is returned and the caller skips MinIO deletion instead.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise DocumentNotFoundError()
    if not doc.s3_key_encrypted:
        return None
    try:
        return decrypt_bytes(doc.s3_key_encrypted).decode()
    except (InvalidTag, UnicodeDecodeError, ValueError):
        orphaned_prefix = f"{user_id}/{document_id}/"
        logger.warning(
            "delete_document.s3_key_decryption_failed — MinIO blob will be orphaned",
            extra={
                "document_id": str(document_id),
                "user_id": str(user_id),
                "orphaned_minio_prefix": orphaned_prefix,
            },
        )
        return None


async def delete_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete a document row, flushing within the current transaction.

    Uses a direct DELETE statement to avoid a redundant ownership SELECT —
    ownership was already verified by get_document_s3_key_optional before this
    is called. Raises DocumentNotFoundError if zero rows are affected, which
    handles concurrent deletes gracefully without a TOCTOU window.
    """
    result = await db.execute(
        delete(Document)
        .where(Document.id == document_id, Document.user_id == user_id)
        .returning(Document.id)
    )
    deleted_document_id = result.scalar_one_or_none()
    if deleted_document_id is None:
        raise DocumentNotFoundError()
    await db.flush()


async def update_document_status(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str,
    arq_job_id: str | None = None,
) -> Document:
    # user_id filter ensures callers cannot update documents they do not own.
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise DocumentNotFoundError()
    doc.status = status
    # Explicit updated_at avoids relying on SQLAlchemy onupdate which does not fire
    # reliably via flush without a full commit cycle (asyncpg + server-side func.now()).
    doc.updated_at = datetime.now(UTC)
    if arq_job_id is not None:
        doc.arq_job_id = arq_job_id
    await db.flush()
    await db.refresh(doc)
    return doc


_RETRYABLE_STATUSES = frozenset({"partial", "failed"})


async def prepare_document_for_reupload(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    new_s3_key: str,
    new_filename: str,
    new_file_size_bytes: int,
    new_file_type: str,
) -> tuple[Document, str | None, str | None]:
    """Stage retry metadata without overwriting authoritative document fields.

    Validates that the document belongs to the authenticated user and is in a
    retryable state (partial or failed). Stores the new file metadata in the
    pending_* columns so the authoritative fields (filename, s3_key, size, type)
    remain consistent with the current extracted values until /notify confirms
    the file has actually been PUT to MinIO.

    Resets arq_job_id and keep_partial so the existing notify/processing flow
    can be reused once the upload completes.

    Returns the updated document, the old authoritative s3_key (decrypted), and
    the old pending s3_key if one existed from a prior abandoned retry. Callers
    use these to schedule MinIO cleanup of superseded objects.

    INTERNAL: encryption/decryption of s3_key happens only here.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise DocumentNotFoundError()
    if doc.status not in _RETRYABLE_STATUSES:
        raise DocumentRetryNotAllowedError()

    # Capture old authoritative key so caller can clean up the current MinIO object.
    old_s3_key: str | None = None
    if doc.s3_key_encrypted:
        try:
            old_s3_key = decrypt_bytes(doc.s3_key_encrypted).decode()
        except (InvalidTag, UnicodeDecodeError, ValueError):
            old_s3_key = None  # caller will fall back to prefix-based cleanup

    # Capture any previously staged pending key from an abandoned prior retry so
    # the caller can clean up that orphaned MinIO object too.
    old_pending_s3_key: str | None = None
    if doc.pending_s3_key_encrypted:
        try:
            old_pending_s3_key = decrypt_bytes(doc.pending_s3_key_encrypted).decode()
        except (InvalidTag, UnicodeDecodeError, ValueError):
            old_pending_s3_key = None  # not cleanable by key; caller uses prefix fallback

    # Stage new metadata in pending_* columns — authoritative fields are NOT touched
    # until commit_pending_retry_metadata() is called from notify_upload_complete().
    doc.pending_s3_key_encrypted = encrypt_bytes(new_s3_key.encode())
    doc.pending_filename = new_filename
    doc.pending_file_size_bytes = new_file_size_bytes
    doc.pending_file_type = new_file_type
    doc.arq_job_id = None
    doc.keep_partial = None
    doc.updated_at = datetime.now(UTC)

    await db.flush()
    await db.refresh(doc)
    return doc, old_s3_key, old_pending_s3_key


async def commit_pending_retry_metadata(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document:
    """Atomically promote pending retry metadata to authoritative document fields.

    Called from notify_upload_complete() after the client confirms the new file
    has been PUT to MinIO. Only modifies the document when pending_s3_key_encrypted
    is set (retry path); has no effect for fresh uploads.

    INTERNAL: encryption/decryption of s3_key happens only here.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise DocumentNotFoundError()

    if not doc.pending_s3_key_encrypted:
        # Fresh upload path — no pending metadata to promote.
        return doc

    doc.s3_key_encrypted = doc.pending_s3_key_encrypted
    doc.filename = doc.pending_filename if doc.pending_filename is not None else doc.filename
    doc.file_size_bytes = (
        doc.pending_file_size_bytes
        if doc.pending_file_size_bytes is not None
        else doc.file_size_bytes
    )
    doc.file_type = doc.pending_file_type if doc.pending_file_type is not None else doc.file_type
    doc.pending_s3_key_encrypted = None
    doc.pending_filename = None
    doc.pending_file_size_bytes = None
    doc.pending_file_type = None
    doc.updated_at = datetime.now(UTC)

    await db.flush()
    await db.refresh(doc)
    return doc


async def set_keep_partial(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document:
    """Persist the user's decision to keep partial extraction results.

    Only valid for documents in 'partial' status. Sets keep_partial=True so
    the recovery UI is dismissed on subsequent loads.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise DocumentNotFoundError()
    if doc.status != "partial":
        raise DocumentRetryNotAllowedError(
            "keep-partial is only valid for documents in partial status"
        )
    doc.keep_partial = True
    doc.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(doc)
    return doc


async def has_user_documents(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> bool:
    """Return True if the user has at least one document row (any status)."""
    result = await db.execute(select(func.count()).where(Document.user_id == user_id))
    return result.scalar_one() > 0


async def has_document_health_values(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> bool:
    """Return True if any health values exist for the given document.

    INTERNAL USE ONLY — called by the ARQ worker to detect retry scenarios
    where prior partial values must be preserved on failure.
    """
    result = await db.execute(select(func.count()).where(HealthValue.document_id == document_id))
    count = result.scalar_one()
    return count > 0


_ALLOWED_DOCUMENT_KINDS = frozenset({"analysis", "document", "unknown"})


async def update_document_intelligence_internal(
    db: AsyncSession,
    document_id: uuid.UUID,
    *,
    document_kind: str,
    needs_date_confirmation: bool,
    partial_measured_at_text: str | None,
    user_id: uuid.UUID | None = None,
) -> Document:
    """Persist document intelligence metadata from the processing pipeline.

    INTERNAL USE ONLY — called by the ARQ worker context where ownership is
    enforced upstream by the queue dispatcher. Stays separate from upload
    metadata writes so that classification can be reissued on reprocessing
    without interfering with the authoritative upload columns.

    `user_id` is accepted as defense-in-depth: when provided, the WHERE
    clause also filters by user_id, matching the sibling helpers
    (`update_document_measured_at`, `clear_pending_date_confirmation`). The
    pipeline caller leaves it unset because the ARQ queue dispatcher already
    enforces ownership upstream.
    """
    if document_kind not in _ALLOWED_DOCUMENT_KINDS:
        raise ValueError(f"Invalid document_kind for internal update: {document_kind!r}")
    stmt = select(Document).where(Document.id == document_id)
    if user_id is not None:
        stmt = stmt.where(Document.user_id == user_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        raise DocumentNotFoundError()
    doc.document_kind = document_kind
    doc.needs_date_confirmation = needs_date_confirmation
    doc.partial_measured_at_text = partial_measured_at_text
    doc.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(doc)
    return doc


async def clear_pending_date_confirmation(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document:
    """Clear needs_date_confirmation + partial_measured_at_text after year confirmation.

    Enforces ownership via (document_id, user_id). Intended to be called from
    the year-confirmation service flow after all health_values.measured_at rows
    have been updated in the same transaction.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise DocumentNotFoundError()
    doc.needs_date_confirmation = False
    doc.partial_measured_at_text = None
    doc.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(doc)
    return doc
