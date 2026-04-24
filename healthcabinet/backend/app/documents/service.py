"""
Documents service — business logic only.

Layer contract: calls repository for DB operations, calls storage for MinIO operations.
No direct DB queries, no encryption. Rate limiting injected via router dependency.
"""

import asyncio
import os
import re
import uuid
from datetime import UTC, datetime
from typing import Any, cast

import structlog
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import repository as ai_repo
from app.ai import service as ai_service
from app.auth.models import User
from app.core.config import settings
from app.documents import repository
from app.documents.exceptions import (
    DocumentYearConfirmationInvalidError,
    DocumentYearConfirmationNotAllowedError,
)
from app.documents.schemas import (
    _ALLOWED_FILE_TYPE_PREFIXES,
    _ALLOWED_FILE_TYPES_EXACT,
    DeleteResponse,
    DocumentDetailResponse,
    DocumentKind,
    DocumentResponse,
    DocumentStatus,
    HealthValueItem,
    KeepPartialResponse,
)
from app.documents.storage import (
    delete_object,
    delete_objects_by_prefix,
    get_s3_client,
    upload_object,
)
from app.health_data import repository as health_repo
from app.processing.schemas import NormalizedHealthValue

logger = structlog.get_logger()

_UNSAFE_FILENAME_RE = re.compile(r"[\x00-\x1f\x7f]")


def _sanitize_filename(filename: str) -> str:
    """Strip path traversal components and ASCII control characters from an upload filename."""
    # os.path.basename strips directory separators on any platform
    safe = os.path.basename(filename.replace("\\", "/"))
    # Remove null bytes and other control chars (log injection, shell metachar risk)
    safe = _UNSAFE_FILENAME_RE.sub("", safe)
    return safe[:255] if safe else "upload"


def _validate_upload_file(file: UploadFile) -> str:
    """Return the validated content type or raise HTTP 415 for unsupported uploads."""
    content_type = file.content_type or ""
    if content_type in _ALLOWED_FILE_TYPES_EXACT or content_type.startswith(
        _ALLOWED_FILE_TYPE_PREFIXES
    ):
        return content_type
    raise HTTPException(
        status_code=415,
        detail=f"Unsupported file type '{content_type}': only PDF and images are accepted.",
    )


async def upload_document(
    db: AsyncSession,
    arq_redis: Any,
    user: User,
    file: UploadFile,
) -> DocumentResponse:
    """Receive an uploaded file via multipart, store it in MinIO, and enqueue processing.

    The backend proxies the file to MinIO so the browser never contacts MinIO directly.
    document_id is generated server-side to prevent PK collision and IDOR.
    DB row is inserted BEFORE the MinIO PUT so a stored object always has a DB record.
    s3_key format: {user_id}/{document_id}/{filename} — prevents cross-user key collisions.
    s3_key is AES-256-GCM encrypted before storage.
    """
    content_type = _validate_upload_file(file)
    content = await file.read()
    if len(content) > settings.DOCUMENT_PROCESSING_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {settings.DOCUMENT_PROCESSING_MAX_BYTES} bytes.",
        )

    safe_filename = _sanitize_filename(file.filename or "upload")
    document_id = uuid.uuid4()
    s3_key = f"{user.id}/{document_id}/{safe_filename}"

    await repository.create_document(
        db,
        document_id=document_id,
        user_id=user.id,
        s3_key=s3_key,
        filename=safe_filename,
        file_size_bytes=len(content),
        file_type=content_type,
    )

    await asyncio.to_thread(
        upload_object, get_s3_client(), settings.MINIO_BUCKET, s3_key, content, content_type
    )

    return await notify_upload_complete(db, arq_redis, user, document_id)


async def notify_upload_complete(
    db: AsyncSession,
    arq_redis: Any,
    user: User,
    document_id: uuid.UUID,
) -> DocumentResponse:
    """Validate document ownership and enqueue processing job.

    Called after the client has finished the MinIO PUT. Verifies the document
    belongs to the authenticated user before enqueueing to prevent job injection.
    Idempotent: repeated calls are safe if the job has already been enqueued.

    For retry uploads, atomically promotes pending_* metadata to authoritative
    fields before enqueueing, ensuring the authoritative document row always
    matches the file that will actually be processed.
    """
    doc = await repository.get_document_by_id(db, document_id, user.id)

    # Idempotency: skip re-enqueueing if a job was already recorded.
    if doc.arq_job_id is not None:
        return DocumentResponse.model_validate(doc)

    # Retry path: promote staged metadata to authoritative now that the file
    # has been confirmed PUT to MinIO by the client calling /notify.
    doc = await repository.commit_pending_retry_metadata(db, document_id, user.id)

    job_id: str | None = None
    if arq_redis is None:
        logger.warning("notify_upload.arq_unavailable", document_id=str(document_id))
    else:
        job = await arq_redis.enqueue_job("process_document", document_id=str(doc.id))
        if job is None:
            logger.warning(
                "notify_upload.arq_enqueue_returned_none",
                document_id=str(document_id),
            )
        else:
            job_id = job.job_id

    doc = await repository.update_document_status(db, doc.id, user.id, "pending", arq_job_id=job_id)
    return DocumentResponse.model_validate(doc)


async def list_documents(
    db: AsyncSession,
    user: User,
) -> list[DocumentResponse]:
    """Return all documents for the authenticated user, newest first."""
    docs = await repository.get_documents_by_user(db, user.id)
    return [DocumentResponse.model_validate(doc) for doc in docs]


async def get_document_detail(
    db: AsyncSession,
    user: User,
    document_id: uuid.UUID,
) -> DocumentDetailResponse:
    """Return a single document with its extracted health values."""
    doc = await repository.get_document_by_id(db, document_id, user.id)

    health_result = await health_repo.list_values_by_document(
        db, document_id=document_id, user_id=user.id
    )
    if health_result.skipped_corrupt_records:
        logger.warning(
            "document_detail.corrupt_health_values_skipped",
            document_id=str(document_id),
            skipped=health_result.skipped_corrupt_records,
        )

    health_items = [
        HealthValueItem(
            id=r.id,
            biomarker_name=r.biomarker_name,
            canonical_biomarker_name=r.canonical_biomarker_name,
            value=r.value,
            unit=r.unit,
            reference_range_low=r.reference_range_low,
            reference_range_high=r.reference_range_high,
            measured_at=r.measured_at,
            confidence=r.confidence,
            needs_review=r.needs_review,
            is_flagged=r.is_flagged,
            flagged_at=r.flagged_at,
        )
        for r in health_result.records
    ]

    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        file_size_bytes=doc.file_size_bytes,
        file_type=doc.file_type,
        status=cast(DocumentStatus, doc.status),
        arq_job_id=doc.arq_job_id,
        keep_partial=doc.keep_partial,
        document_kind=cast(DocumentKind, doc.document_kind),
        needs_date_confirmation=doc.needs_date_confirmation,
        partial_measured_at_text=doc.partial_measured_at_text,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        health_values=health_items,
    )


async def reupload_document(
    db: AsyncSession,
    arq_redis: Any,
    user: User,
    document_id: uuid.UUID,
    file: UploadFile,
) -> DocumentResponse:
    """Receive a retry upload via multipart, store it in MinIO, and enqueue processing.

    Validates that the document is owned by the caller and is in a retryable
    state (partial or failed). The existing document row is reused — no new
    document_id is generated — so cabinet and detail views remain scoped to
    one document slot.

    The old MinIO object is deleted AFTER the DB row is updated, mirroring the
    delete-document pattern: authoritative state is the DB row. If the old
    object deletion fails it is logged and best-effort; the retry proceeds.

    Retries consume the same rate-limit quota as fresh uploads (enforced at the
    router layer via Depends(rate_limit_upload)).
    """
    content_type = _validate_upload_file(file)
    content = await file.read()
    if len(content) > settings.DOCUMENT_PROCESSING_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {settings.DOCUMENT_PROCESSING_MAX_BYTES} bytes.",
        )

    safe_filename = _sanitize_filename(file.filename or "upload")
    new_s3_key = f"{user.id}/{document_id}/{safe_filename}"

    doc, old_s3_key, old_pending_s3_key = await repository.prepare_document_for_reupload(
        db,
        document_id=document_id,
        user_id=user.id,
        new_s3_key=new_s3_key,
        new_filename=safe_filename,
        new_file_size_bytes=len(content),
        new_file_type=content_type,
    )

    s3_client = get_s3_client()
    await asyncio.to_thread(
        upload_object, s3_client, settings.MINIO_BUCKET, new_s3_key, content, content_type
    )

    result = await notify_upload_complete(db, arq_redis, user, document_id)

    prefix = f"{user.id}/{document_id}/"

    # Best-effort cleanup of the superseded authoritative MinIO object.
    # Finding 4: when old_s3_key is None (decryption failure), fall back to prefix-based
    # cleanup — the same pattern used in delete_document() — so no object leaks indefinitely.
    if old_s3_key is None:
        try:
            deleted_count = await asyncio.to_thread(
                delete_objects_by_prefix, s3_client, settings.MINIO_BUCKET, prefix
            )
            logger.info(
                "reupload.old_key_prefix_cleanup_success",
                document_id=str(document_id),
                user_id=str(user.id),
                prefix=prefix,
                deleted_objects=deleted_count,
            )
        except Exception:
            logger.warning(
                "reupload.old_key_prefix_cleanup_failed",
                document_id=str(document_id),
                user_id=str(user.id),
                orphaned_minio_prefix=prefix,
                exc_info=True,
            )
    elif old_s3_key != new_s3_key:
        try:
            await asyncio.to_thread(delete_object, s3_client, settings.MINIO_BUCKET, old_s3_key)
        except Exception:
            logger.warning(
                "reupload.old_object_cleanup_failed",
                document_id=str(document_id),
                user_id=str(user.id),
                old_s3_key=old_s3_key,
                orphaned_minio_prefix=prefix,
                exc_info=True,
            )

    # Best-effort cleanup of any previously staged pending MinIO object from an
    # abandoned prior retry (client called /reupload but never completed).
    if old_pending_s3_key and old_pending_s3_key != new_s3_key:
        try:
            await asyncio.to_thread(
                delete_object, s3_client, settings.MINIO_BUCKET, old_pending_s3_key
            )
        except Exception:
            logger.warning(
                "reupload.abandoned_pending_object_cleanup_failed",
                document_id=str(document_id),
                user_id=str(user.id),
                pending_s3_key=old_pending_s3_key,
                orphaned_minio_prefix=prefix,
                exc_info=True,
            )

    return result


async def keep_document_partial(
    db: AsyncSession,
    user: User,
    document_id: uuid.UUID,
) -> KeepPartialResponse:
    """Persist the user's decision to keep partial extraction results.

    Marks keep_partial=True on the document so the recovery UI is dismissed on
    subsequent loads without deleting or mutating the current extracted values.
    """
    await repository.set_keep_partial(db, document_id=document_id, user_id=user.id)
    await db.commit()
    return KeepPartialResponse(kept=True)


async def delete_document(
    db: AsyncSession,
    user: User,
    document_id: uuid.UUID,
) -> DeleteResponse:
    """Delete the document from the database, then attempt storage cleanup.

    Cross-system atomicity is not achievable here because the DB transaction and
    the MinIO delete are independent systems. The authoritative user-facing state
    is therefore the database:

    1. Resolve the stored S3 key while the row still exists.
    2. Delete health values and the document row.
    3. Commit the DB transaction before returning success.
    4. Attempt MinIO cleanup as a best-effort follow-up; log any failure so
       operators can reconcile orphaned objects.

    This avoids the worse failure mode where the blob is deleted first and a
    later DB commit failure leaves a visible document that can no longer be
    downloaded or retried. When s3_key decryption fails, a prefix-based cleanup
    fallback is used because the key structure is known.
    """
    s3_key = await repository.get_document_s3_key_optional(db, document_id, user.id)
    await health_repo.delete_document_health_values(db, document_id=document_id, user_id=user.id)
    await repository.delete_document(db, document_id, user.id)
    await db.commit()

    prefix = f"{user.id}/{document_id}/"
    try:
        s3_client = get_s3_client()
        if s3_key:
            await asyncio.to_thread(delete_object, s3_client, settings.MINIO_BUCKET, s3_key)
        else:
            deleted_count = await asyncio.to_thread(
                delete_objects_by_prefix, s3_client, settings.MINIO_BUCKET, prefix
            )
            logger.info(
                "delete_document.prefix_deletion_fallback",
                document_id=str(document_id),
                user_id=str(user.id),
                prefix=prefix,
                deleted_objects=deleted_count,
            )
    except Exception:
        logger.warning(
            "delete_document.storage_cleanup_failed",
            document_id=str(document_id),
            user_id=str(user.id),
            s3_key=s3_key,
            orphaned_minio_prefix=prefix,
            exc_info=True,
        )

    return DeleteResponse(deleted=True)


# ---------------------------------------------------------------------------
# Story 15.2 — year confirmation
# ---------------------------------------------------------------------------

# Accepted partial-date shapes. Each pattern MUST capture exactly two groups:
# (day, month). We deliberately keep this conservative — the extractor is the
# source of truth for fragment shape and these three cover the shapes it emits.
_PARTIAL_DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*(?P<day>\d{1,2})[.\-/](?P<month>\d{1,2})\.?\s*$"),
    # Patterns 2 and 3 allow whitespace, hyphen, or dot between the day and the
    # named month so that extractor emissions like "12-Mar" and "Mar-12" are
    # accepted alongside "12 Mar" / "Mar 12".
    re.compile(
        r"^\s*(?P<day>\d{1,2})[\s\-\.]+(?P<month>[A-Za-z]+)\.?\s*$",
    ),
    re.compile(
        r"^\s*(?P<month>[A-Za-z]+)\.?[\s\-\.]+(?P<day>\d{1,2})\s*$",
    ),
)

_MONTH_NAMES: dict[str, int] = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def _parse_partial_date(partial_text: str) -> tuple[int, int] | None:
    """Return (day, month) if the fragment can be parsed, else None.

    Accepts numeric (`12.03`, `12/03`, `12-03`) and named-month (`12 Mar`,
    `Mar 12`) shapes. Rejects anything with a year embedded — the year is
    supplied by the user. Returned month is 1–12 and day is 1–31 (day-of-month
    validity is re-checked by `datetime` when the confirmed year is applied).
    """
    for pattern in _PARTIAL_DATE_PATTERNS:
        match = pattern.match(partial_text)
        if match is None:
            continue
        groups = match.groupdict()
        day_raw = groups["day"]
        month_raw = groups["month"]
        try:
            day = int(day_raw)
        except ValueError:
            continue
        if month_raw.isdigit():
            try:
                month = int(month_raw)
            except ValueError:
                continue
        else:
            month = _MONTH_NAMES.get(month_raw.lower(), 0)
        if not (1 <= month <= 12):
            continue
        if not (1 <= day <= 31):
            continue
        return day, month
    return None


def _records_to_normalized_values(
    records: list[Any],
) -> list[NormalizedHealthValue]:
    """Map persisted HealthValueRecord rows back into NormalizedHealthValue.

    Story 15.2 — AI regeneration after year confirmation reuses
    app.ai.service.generate_interpretation(), which expects NormalizedHealthValue.
    We translate the persisted shape into that primitive here rather than
    branching a second AI persistence path.
    """
    values: list[NormalizedHealthValue] = []
    for record in records:
        values.append(
            NormalizedHealthValue(
                biomarker_name=record.biomarker_name,
                canonical_biomarker_name=record.canonical_biomarker_name,
                value=record.value,
                unit=record.unit,
                reference_range_low=record.reference_range_low,
                reference_range_high=record.reference_range_high,
                confidence=record.confidence,
                needs_review=record.needs_review,
            )
        )
    return values


def _resolve_post_confirmation_status(records: list[Any]) -> DocumentStatus:
    """After year confirmation, remaining partial conditions determine terminal status.

    Any persisted low-confidence value keeps the document in `partial`. Otherwise
    it transitions to `completed`. `failed`/`pending`/`processing` are never
    produced here because confirmation only runs on terminal analyses with
    persisted values.
    """
    if any(record.needs_review for record in records):
        return "partial"
    return "completed"


async def confirm_date_year(
    db: AsyncSession,
    user: User,
    document_id: uuid.UUID,
    year: int,
) -> DocumentDetailResponse:
    """Resolve a pending year-confirmation for an analysis document.

    Flow (AC 5):
    1. Ownership check via repository (DocumentNotFoundError -> 404).
    2. Reject if needs_date_confirmation is false (409).
    3. Validate year against defensible bounds + the stored partial fragment
       (400 on invalid).
    4. Compose a timezone-aware measured_at at 00:00:00+00:00 — the repo works
       with date-only lab results so UTC midnight is the safest stable choice.
    5. Propagate measured_at to every persisted health value via the new bulk
       update helper, clear confirmation flags, recompute terminal status.
    6. Invalidate the AI interpretation and best-effort regenerate it. Any
       regeneration failure is logged; the confirmation response still returns
       the updated document detail.
    """
    doc = await repository.get_document_by_id(db, document_id, user.id)

    if not doc.needs_date_confirmation:
        raise DocumentYearConfirmationNotAllowedError()

    current_year = datetime.now(UTC).year
    if year > current_year:
        raise DocumentYearConfirmationInvalidError(
            f"year {year} is in the future (current year is {current_year})"
        )

    if not doc.partial_measured_at_text:
        # Defensive — should not happen because needs_date_confirmation is set
        # in lockstep with partial_measured_at_text, but if somehow present we
        # cannot safely compose a timestamp, so reject.
        raise DocumentYearConfirmationInvalidError("Document is missing stored partial date text")

    parsed = _parse_partial_date(doc.partial_measured_at_text)
    if parsed is None:
        raise DocumentYearConfirmationInvalidError(
            f"Stored partial date '{doc.partial_measured_at_text}' could not be parsed"
        )
    day, month = parsed

    try:
        measured_at = datetime(year, month, day, 0, 0, 0, tzinfo=UTC)
    except ValueError as exc:
        # e.g. Feb 30, or Feb 29 on a non-leap year
        raise DocumentYearConfirmationInvalidError(
            f"Resolved date {year}-{month:02d}-{day:02d} is invalid"
        ) from exc

    await health_repo.update_document_measured_at(
        db,
        document_id=document_id,
        user_id=user.id,
        measured_at=measured_at,
    )

    await repository.clear_pending_date_confirmation(db, document_id, user.id)

    # Recompute terminal status from remaining partial conditions (low-confidence rows).
    health_result = await health_repo.list_values_by_document(
        db, document_id=document_id, user_id=user.id
    )
    if health_result.skipped_corrupt_records:
        logger.warning(
            "confirm_date_year.corrupt_health_values_skipped",
            document_id=str(document_id),
            skipped=health_result.skipped_corrupt_records,
        )
    new_status = _resolve_post_confirmation_status(health_result.records)
    await repository.update_document_status_internal(db, document_id, new_status)

    # Invalidation is unconditional — the prior interpretation described
    # measurements at an unresolved date, and we just resolved the date. The
    # stored text may contradict the new timeline, so mark it invalid until
    # a regeneration succeeds. Cheap and idempotent when no prior row exists.
    await ai_repo.invalidate_interpretation(db, user_id=user.id, document_id=document_id)

    await db.commit()

    # Only regenerate if we still have persisted values. A concurrent reprocess
    # (or full-row decryption failure) can leave values empty; without values
    # there is nothing to regenerate from, and the prior interpretation stays
    # invalidated until new values land via re-upload — strictly safer than
    # showing a stale "valid" interpretation against a now-resolved date.
    values_for_ai = _records_to_normalized_values(health_result.records)
    if values_for_ai:
        try:
            await ai_service.generate_interpretation(
                db,
                document_id=document_id,
                user_id=user.id,
                values=values_for_ai,
            )
            await db.commit()
        except Exception:
            logger.warning(
                "confirm_date_year.ai_regeneration_failed",
                document_id=str(document_id),
                user_id=str(user.id),
                exc_info=True,
            )
            await db.rollback()

    return await get_document_detail(db, user, document_id)
