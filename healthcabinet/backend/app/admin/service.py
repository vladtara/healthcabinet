import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.repository import (
    create_audit_log,
    get_document_values_for_correction,
    get_error_queue_documents,
    get_flagged_reports,
    list_admin_users,
    mark_flag_reviewed,
)
from app.admin.schemas import (
    AdminUserDetail,
    AdminUserListItem,
    AdminUserListResponse,
    CorrectionRequest,
    CorrectionResponse,
    DocumentHealthValueDetail,
    DocumentQueueDetail,
    ErrorQueueItem,
    ErrorQueueResponse,
    FlaggedReportItem,
    FlaggedReportListResponse,
    FlagReviewedResponse,
    PlatformMetricsResponse,
)
from app.health_data.exceptions import HealthValueNotFoundError
from app.health_data.models import HealthValue
from app.health_data.repository import _decrypt_numeric_value, _encrypt_numeric_value


async def fetch_platform_metrics(db: AsyncSession) -> PlatformMetricsResponse:
    """Fetch aggregate platform metrics. Delegates to repository."""
    from app.admin.repository import get_platform_metrics

    return await get_platform_metrics(db)


async def get_error_queue(db: AsyncSession) -> ErrorQueueResponse:
    """Fetch error queue documents with extraction problem counts."""
    rows = await get_error_queue_documents(db)
    items = [
        ErrorQueueItem(
            document_id=uuid.UUID(r["document_id"]),
            user_id=uuid.UUID(r["user_id"]),
            filename=r["filename"],
            upload_date=r["upload_date"],
            status=r["status"],
            value_count=r["value_count"],
            low_confidence_count=r["low_confidence_count"],
            flagged_count=r["flagged_count"],
            failed=r["failed"],
        )
        for r in rows
    ]
    return ErrorQueueResponse(items=items, total=len(items))


async def get_document_for_correction(
    db: AsyncSession, document_id: uuid.UUID
) -> DocumentQueueDetail | None:
    """Load document with all decrypted health values for admin correction."""
    doc, health_values = await get_document_values_for_correction(db, document_id)
    if doc is None:
        return None

    values = [
        DocumentHealthValueDetail(
            id=hv.id,
            biomarker_name=hv.biomarker_name,
            canonical_biomarker_name=hv.canonical_biomarker_name,
            value=_decrypt_numeric_value(hv.value_encrypted),
            unit=hv.unit,
            reference_range_low=(
                float(hv.reference_range_low) if hv.reference_range_low is not None else None
            ),
            reference_range_high=(
                float(hv.reference_range_high) if hv.reference_range_high is not None else None
            ),
            confidence=hv.confidence,
            needs_review=hv.needs_review,
            is_flagged=hv.is_flagged,
            flagged_at=hv.flagged_at.isoformat() if hv.flagged_at else None,
        )
        for hv in health_values
    ]

    return DocumentQueueDetail(
        document_id=doc.id,
        user_id=doc.user_id,
        filename=doc.filename,
        upload_date=doc.created_at.isoformat(),
        status=doc.status,
        values=values,
    )


async def submit_correction(
    db: AsyncSession,
    *,
    admin_id: uuid.UUID,
    document_id: uuid.UUID,
    health_value_id: uuid.UUID,
    request: CorrectionRequest,
) -> CorrectionResponse:
    """Submit an admin value correction.

    In a single transaction: (1) update health_value with new encrypted value,
    (2) insert audit_log row.
    """
    from sqlalchemy import select

    result = await db.execute(
        select(HealthValue)
        .where(
            HealthValue.id == health_value_id,
            HealthValue.document_id == document_id,
        )
        .with_for_update()
    )
    hv = result.scalar_one_or_none()
    if hv is None:
        raise HealthValueNotFoundError(f"Health value {health_value_id} not found")

    # Decrypt original value for audit log
    original_value = _decrypt_numeric_value(hv.value_encrypted)

    # Encrypt new value and update row
    hv.value_encrypted = _encrypt_numeric_value(request.new_value)
    await db.flush()
    await db.refresh(hv)

    # Insert audit log
    audit_log = await create_audit_log(
        db,
        admin_id=admin_id,
        user_id=hv.user_id,
        document_id=hv.document_id,
        health_value_id=health_value_id,
        value_name=hv.canonical_biomarker_name,
        original_value=str(original_value),
        new_value=str(request.new_value),
        reason=request.reason,
    )

    return CorrectionResponse(
        audit_log_id=audit_log.id,
        health_value_id=health_value_id,
        value_name=hv.canonical_biomarker_name,
        original_value=original_value,
        new_value=request.new_value,
        corrected_at=audit_log.corrected_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Story 5.3: Admin user management
# ---------------------------------------------------------------------------


async def fetch_admin_users(db: AsyncSession, query: str | None = None) -> AdminUserListResponse:
    """Fetch admin user list with upload counts."""
    rows = await list_admin_users(db, query)
    items = [
        AdminUserListItem(
            user_id=uuid.UUID(r["user_id"]),
            email=r["email"],
            registration_date=r["registration_date"],
            upload_count=r["upload_count"],
            account_status=r["account_status"],
        )
        for r in rows
    ]
    return AdminUserListResponse(items=items, total=len(items))


async def fetch_admin_user_detail(db: AsyncSession, user_id: uuid.UUID) -> AdminUserDetail | None:
    """Fetch single user detail. Returns None if not found or not a regular user."""
    from app.admin.repository import get_admin_user_detail

    row = await get_admin_user_detail(db, user_id)
    if row is None:
        return None
    return AdminUserDetail(
        user_id=uuid.UUID(row["user_id"]),
        email=row["email"],
        registration_date=row["registration_date"],
        last_login=row["last_login"],
        upload_count=row["upload_count"],
        account_status=row["account_status"],
    )


async def update_user_status(db: AsyncSession, user_id: uuid.UUID, account_status: str) -> bool:
    """Update user account status. Returns True if found, False if not."""
    from app.admin.repository import set_user_account_status

    if account_status not in ("active", "suspended"):
        raise ValueError(f"Invalid account_status: {account_status}")
    return await set_user_account_status(db, user_id, account_status)


async def revoke_sessions(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Force-logout a user on all devices by bumping tokens_invalid_before to now.

    Works independently of account_status: revoked users can log in again immediately
    (unlike suspend), but every pre-existing access/refresh token is rejected.
    Returns True if the user was found and updated, False if not.

    The cutoff is floored to second precision because JWT `iat` is encoded as integer
    seconds. Without flooring, a user who re-logs in during the same wall-clock second
    as the revocation would receive a new token whose iat is numerically less than the
    microsecond-precise cutoff — the fresh token would be incorrectly rejected.
    """
    from app.admin.repository import revoke_user_sessions

    return await revoke_user_sessions(db, user_id, datetime.now(UTC).replace(microsecond=0))


# ---------------------------------------------------------------------------
# Story 5.3: Flagged value reports
# ---------------------------------------------------------------------------


async def fetch_flagged_reports(db: AsyncSession) -> FlaggedReportListResponse:
    """Fetch unreviewed flagged value reports with decrypted values."""
    rows = await get_flagged_reports(db)
    items: list[FlaggedReportItem] = []
    for hv, flagged_at_iso in rows:
        try:
            decrypted_value = _decrypt_numeric_value(hv.value_encrypted)
        except Exception:
            structlog.get_logger().warning(
                "admin.flagged_report.decrypt_failed",
                health_value_id=str(hv.id),
            )
            continue
        items.append(
            FlaggedReportItem(
                health_value_id=hv.id,
                user_id=hv.user_id,
                document_id=hv.document_id,
                value_name=hv.canonical_biomarker_name,
                flagged_value=decrypted_value,
                flagged_at=flagged_at_iso,
            )
        )
    return FlaggedReportListResponse(items=items, total=len(items))


async def review_flag(
    db: AsyncSession, health_value_id: uuid.UUID, admin_id: uuid.UUID
) -> FlagReviewedResponse:
    """Mark a flagged value as reviewed."""
    hv = await mark_flag_reviewed(db, health_value_id, admin_id)
    if hv is None:
        raise HealthValueNotFoundError(f"Flagged value {health_value_id} not found")
    return FlagReviewedResponse(
        health_value_id=hv.id,
        reviewed_at=hv.flag_reviewed_at.isoformat() if hv.flag_reviewed_at else "",
    )
