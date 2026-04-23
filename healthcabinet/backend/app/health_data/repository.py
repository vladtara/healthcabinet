"""Database access for extracted health values."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from cryptography.exceptions import InvalidTag
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_bytes, encrypt_bytes
from app.documents.models import Document
from app.health_data.exceptions import HealthValueNotFoundError
from app.health_data.models import HealthValue
from app.processing.schemas import NormalizedHealthValue


@dataclass(slots=True)
class HealthValueRecord:
    id: uuid.UUID
    user_id: uuid.UUID
    document_id: uuid.UUID
    biomarker_name: str
    canonical_biomarker_name: str
    value: float
    unit: str | None
    reference_range_low: float | None
    reference_range_high: float | None
    measured_at: datetime | None
    confidence: float
    needs_review: bool
    is_flagged: bool
    flagged_at: datetime | None
    flag_reviewed_at: datetime | None
    created_at: datetime


__all__ = ["HealthValueNotFoundError"]  # re-export for existing imports


class HealthValueDecryptionError(ValueError):
    """Raised when a stored encrypted health value cannot be decrypted."""


def _encrypt_numeric_value(value: float) -> bytes:
    return encrypt_bytes(str(value).encode("utf-8"))


def _decrypt_numeric_value(value_encrypted: bytes) -> float:
    try:
        return float(decrypt_bytes(value_encrypted).decode("utf-8"))
    except (InvalidTag, UnicodeDecodeError, ValueError) as exc:
        raise HealthValueDecryptionError("Stored health value could not be decrypted") from exc


def _to_record(model: HealthValue) -> HealthValueRecord:
    return HealthValueRecord(
        id=model.id,
        user_id=model.user_id,
        document_id=model.document_id,
        biomarker_name=model.biomarker_name,
        canonical_biomarker_name=model.canonical_biomarker_name,
        value=_decrypt_numeric_value(model.value_encrypted),
        unit=model.unit,
        reference_range_low=(
            float(model.reference_range_low) if model.reference_range_low is not None else None
        ),
        reference_range_high=(
            float(model.reference_range_high) if model.reference_range_high is not None else None
        ),
        measured_at=model.measured_at,
        confidence=model.confidence,
        needs_review=model.needs_review,
        is_flagged=model.is_flagged,
        flagged_at=model.flagged_at,
        flag_reviewed_at=model.flag_reviewed_at,
        created_at=model.created_at,
    )


@dataclass(slots=True)
class HealthValueListResult:
    records: list[HealthValueRecord]
    skipped_corrupt_records: int
    scope: Literal["list", "timeline"]


async def delete_document_health_values(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> None:
    """Delete all health values for a document.

    When user_id is provided (delete flow), includes it as a defense-in-depth
    guard so a future misuse of this function cannot delete another user's values.
    When user_id is None (worker/reprocessing context), deletes by document_id only.
    """
    conditions = [HealthValue.document_id == document_id]
    if user_id is not None:
        conditions.append(HealthValue.user_id == user_id)
    await db.execute(delete(HealthValue).where(*conditions))
    await db.flush()


async def replace_document_health_values(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    measured_at: datetime | None,
    values: list[NormalizedHealthValue],
) -> list[HealthValue]:
    # Enforce document-owner invariant: the document must belong to the given user.
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise ValueError(f"Document {document_id} does not exist")
    if doc.user_id != user_id:
        raise ValueError(f"Document {document_id} belongs to user {doc.user_id}, not {user_id}")

    await db.execute(delete(HealthValue).where(HealthValue.document_id == document_id))

    records: list[HealthValue] = []
    for value in values:
        record = HealthValue(
            user_id=user_id,
            document_id=document_id,
            biomarker_name=value.biomarker_name,
            canonical_biomarker_name=value.canonical_biomarker_name,
            value_encrypted=_encrypt_numeric_value(value.value),
            unit=value.unit,
            reference_range_low=(
                Decimal(str(value.reference_range_low))
                if value.reference_range_low is not None
                else None
            ),
            reference_range_high=(
                Decimal(str(value.reference_range_high))
                if value.reference_range_high is not None
                else None
            ),
            measured_at=measured_at,
            confidence=value.confidence,
            needs_review=value.needs_review,
        )
        db.add(record)
        records.append(record)

    await db.flush()
    return records


# Story 15.3 — dashboard filter scope. 'unknown' is never exposed to the
# dashboard because it represents a failure/unreadable classification.
DashboardKind = Literal["all", "analysis", "document"]


def _kinds_for_filter(document_kind: DashboardKind) -> tuple[str, ...]:
    if document_kind == "all":
        return ("analysis", "document")
    return (document_kind,)


async def list_values_by_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    document_kind: DashboardKind | None = None,
) -> HealthValueListResult:
    """List the user's health values, optionally filtered by document_kind.

    When document_kind is None (pre-15.3 callers) the full set is returned —
    including values owned by documents classified 'unknown'. When set, a
    JOIN to documents restricts the result to the requested kinds; 'all'
    means analysis + document and still excludes 'unknown'.
    """
    stmt = (
        select(HealthValue)
        .where(HealthValue.user_id == user_id)
        .order_by(HealthValue.measured_at.desc(), HealthValue.created_at.desc())
    )
    if document_kind is not None:
        kinds = _kinds_for_filter(document_kind)
        # Defense-in-depth: pin the JOIN on Document.user_id as well so a future
        # refactor that drops the HealthValue.user_id predicate cannot silently
        # return other users' rows.
        stmt = stmt.join(
            Document,
            (Document.id == HealthValue.document_id) & (Document.user_id == user_id),
        ).where(Document.document_kind.in_(kinds))
    result = await db.execute(stmt)
    records: list[HealthValueRecord] = []
    skipped = 0
    for value in result.scalars().all():
        try:
            records.append(_to_record(value))
        except HealthValueDecryptionError:
            skipped += 1
    return HealthValueListResult(records=records, skipped_corrupt_records=skipped, scope="list")


async def list_values_by_document(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> HealthValueListResult:
    """List health values for a single document scoped to the owning user."""
    result = await db.execute(
        select(HealthValue)
        .where(HealthValue.document_id == document_id, HealthValue.user_id == user_id)
        .order_by(HealthValue.created_at.asc())
    )
    records: list[HealthValueRecord] = []
    skipped = 0
    for value in result.scalars().all():
        try:
            records.append(_to_record(value))
        except HealthValueDecryptionError:
            skipped += 1
    return HealthValueListResult(records=records, skipped_corrupt_records=skipped, scope="list")


async def list_timeline_values(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    canonical_biomarker_name: str,
) -> HealthValueListResult:
    result = await db.execute(
        select(HealthValue)
        .where(
            HealthValue.user_id == user_id,
            HealthValue.canonical_biomarker_name == canonical_biomarker_name,
        )
        .order_by(HealthValue.measured_at.asc(), HealthValue.created_at.asc())
    )
    records: list[HealthValueRecord] = []
    skipped = 0
    for value in result.scalars().all():
        try:
            records.append(_to_record(value))
        except HealthValueDecryptionError:
            skipped += 1
    return HealthValueListResult(records=records, skipped_corrupt_records=skipped, scope="timeline")


async def update_document_measured_at(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    measured_at: datetime,
) -> int:
    """Set measured_at on every health_values row for a given (document, user).

    Story 15.2 — year-confirmation flow uses this to propagate the resolved
    timestamp to every extracted value in a single statement so timeline
    queries immediately sort correctly. Returns the number of rows updated.

    Ownership is enforced by including user_id in the WHERE clause as
    defense-in-depth even though the caller already verified ownership.
    """
    result = await db.execute(
        update(HealthValue)
        .where(
            HealthValue.document_id == document_id,
            HealthValue.user_id == user_id,
        )
        .values(measured_at=measured_at)
    )
    await db.flush()
    return int(result.rowcount or 0)


async def flag_health_value(
    db: AsyncSession,
    *,
    health_value_id: uuid.UUID,
    user_id: uuid.UUID,
) -> HealthValueRecord:
    """Set is_flagged=True on exactly one health_values row owned by the given user.

    flagged_at is only written on the first flag transition — repeated calls are idempotent
    and preserve the original timestamp for stable admin queue ordering.

    Raises HealthValueNotFoundError when the row does not exist or belongs to another user
    (unified 404 response avoids ownership leakage).
    """
    result = await db.execute(
        select(HealthValue)
        .where(
            HealthValue.id == health_value_id,
            HealthValue.user_id == user_id,
        )
        .with_for_update()
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HealthValueNotFoundError(
            f"Health value {health_value_id} not found"
        )

    if not row.is_flagged:
        row.is_flagged = True
        row.flagged_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(row)

    return _to_record(row)
