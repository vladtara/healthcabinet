import uuid
from datetime import UTC, datetime
from typing import TypedDict

import sqlalchemy as sa
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AuditLog
from app.admin.schemas import PlatformMetricsResponse
from app.ai.models import AiMemory
from app.auth.models import User
from app.documents.models import Document
from app.health_data.models import HealthValue


class ErrorQueueDocumentRow(TypedDict):
    document_id: str
    user_id: str
    filename: str
    upload_date: str
    status: str
    value_count: int
    low_confidence_count: int
    flagged_count: int
    failed: bool


class AdminUserRow(TypedDict):
    user_id: str
    email: str
    registration_date: str
    upload_count: int
    account_status: str


class AdminUserDetailRow(TypedDict):
    user_id: str
    email: str
    registration_date: str
    last_login: str | None
    upload_count: int
    account_status: str


class FlaggedReportRow(TypedDict):
    health_value_id: str
    user_id: str
    document_id: str
    value_name: str
    flagged_at: str


async def list_audit_logs_by_user_documents(db: AsyncSession, user_id: uuid.UUID) -> list[AuditLog]:
    """Return audit log entries linked to a user's data export scope.

    New rows are keyed directly by audit_logs.user_id so correction history
    survives later document/health_value deletion. Legacy rows may still rely
    on the nullable document_id/health_value_id references until backfilled.
    """
    doc_ids = select(Document.id).where(Document.user_id == user_id)
    hv_ids = select(HealthValue.id).where(HealthValue.user_id == user_id)
    result = await db.execute(
        select(AuditLog)
        .where(
            or_(
                AuditLog.user_id == user_id,
                and_(
                    AuditLog.user_id.is_(None),
                    or_(
                        AuditLog.document_id.in_(doc_ids),
                        AuditLog.health_value_id.in_(hv_ids),
                    ),
                ),
            )
        )
        .order_by(AuditLog.corrected_at)
    )
    return list(result.scalars().all())


async def get_platform_metrics(db: AsyncSession) -> PlatformMetricsResponse:
    """Aggregate platform-wide metrics. Returns only counts — no individual user data."""

    # total_signups: COUNT(*) FROM users
    total_signups: int = await db.scalar(select(func.count()).select_from(User)) or 0

    # total_uploads: COUNT(*) FROM documents
    total_uploads: int = await db.scalar(select(func.count()).select_from(Document)) or 0

    # upload_success_rate: completed / total (None when total=0)
    if total_uploads == 0:
        upload_success_rate = None
    else:
        completed_count: int = (
            await db.scalar(
                select(func.count()).select_from(Document).where(Document.status == "completed")
            )
            or 0
        )
        upload_success_rate = completed_count / total_uploads

    # documents_error_or_partial: COUNT WHERE status IN ('failed', 'partial')
    documents_error_or_partial: int = (
        await db.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.status.in_(["failed", "partial"]))
        )
        or 0
    )

    # ai_interpretation_completion_rate: completed interpretations / total_uploads
    if total_uploads == 0:
        ai_interpretation_completion_rate = None
    else:
        interpreted_count: int = (
            await db.scalar(
                select(func.count(AiMemory.document_id.distinct())).where(
                    AiMemory.interpretation_encrypted.is_not(None),
                    AiMemory.safety_validated.is_(True),
                    AiMemory.document_id.is_not(None),
                )
            )
            or 0
        )
        ai_interpretation_completion_rate = interpreted_count / total_uploads

    return PlatformMetricsResponse(
        total_signups=total_signups,
        total_uploads=total_uploads,
        upload_success_rate=upload_success_rate,
        documents_error_or_partial=documents_error_or_partial,
        ai_interpretation_completion_rate=ai_interpretation_completion_rate,
    )


async def get_error_queue_documents(db: AsyncSession) -> list[ErrorQueueDocumentRow]:
    """Return documents with extraction problems.

    Includes docs with status IN ('failed', 'partial') OR any health_value with
    confidence < 0.7 OR any health_value with is_flagged = true AND flag_reviewed_at IS NULL.
    Reviewed flags no longer keep a document in the active queue.
    """
    # Subquery: documents that have low-confidence or unreviewed-flagged health values
    problematic_hv_subq = (
        select(HealthValue.document_id)
        .where(
            (HealthValue.confidence < 0.7)
            | (HealthValue.is_flagged.is_(True) & HealthValue.flag_reviewed_at.is_(None))
        )
        .distinct()
    ).subquery()

    stmt = (
        select(
            Document.id,
            Document.user_id,
            Document.filename,
            Document.created_at,
            Document.status,
            func.count(HealthValue.id).label("value_count"),
            func.sum(func.cast(HealthValue.confidence < 0.7, sa.Integer)).label(
                "low_confidence_count"
            ),
            func.sum(
                func.cast(
                    HealthValue.is_flagged.is_(True) & HealthValue.flag_reviewed_at.is_(None),
                    sa.Integer,
                )
            ).label("flagged_count"),
        )
        .outerjoin(HealthValue, Document.id == HealthValue.document_id)
        .where(
            (Document.status.in_(["failed", "partial"]))
            | (Document.id.in_(select(problematic_hv_subq)))
        )
        .group_by(
            Document.id, Document.user_id, Document.filename, Document.created_at, Document.status
        )
        .order_by(
            # failed first, then partial, then by created_at DESC
            case(
                (Document.status == "failed", 0),
                (Document.status == "partial", 1),
                else_=2,
            ),
            Document.created_at.desc(),
        )
    )

    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "document_id": str(row.id),
            "user_id": str(row.user_id),
            "filename": row.filename,
            "upload_date": row.created_at.isoformat(),
            "status": row.status,
            "value_count": row.value_count or 0,
            "low_confidence_count": row.low_confidence_count or 0,
            "flagged_count": row.flagged_count or 0,
            "failed": row.status == "failed",
        }
        for row in rows
    ]


async def get_document_values_for_correction(
    db: AsyncSession, document_id: uuid.UUID
) -> tuple[Document | None, list[HealthValue]]:
    """Load a document and all its health_values for correction.

    Returns raw ORM objects — decryption happens in service layer via
    _decrypt_numeric_value.
    """
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    doc = doc_result.scalar_one_or_none()
    if doc is None:
        return None, []

    hv_result = await db.execute(
        select(HealthValue)
        .where(HealthValue.document_id == document_id)
        .order_by(HealthValue.created_at.asc())
    )
    health_values = list(hv_result.scalars().all())
    return doc, health_values


async def create_audit_log(
    db: AsyncSession,
    *,
    admin_id: uuid.UUID,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
    health_value_id: uuid.UUID,
    value_name: str,
    original_value: str,
    new_value: str,
    reason: str,
) -> AuditLog:
    """Insert a new audit log row. INSERT only — append-only table."""
    row = AuditLog(
        admin_id=admin_id,
        user_id=user_id,
        document_id=document_id,
        health_value_id=health_value_id,
        value_name=value_name,
        original_value=original_value,
        new_value=new_value,
        reason=reason,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def update_health_value_encrypted(
    db: AsyncSession, *, health_value_id: uuid.UUID, new_value_encrypted: bytes
) -> None:
    """Update a health_value's encrypted value. Uses FOR UPDATE to prevent concurrent modification."""
    result = await db.execute(
        select(HealthValue).where(HealthValue.id == health_value_id).with_for_update()
    )
    row = result.scalar_one_or_none()
    if row is None:
        return
    row.value_encrypted = new_value_encrypted
    await db.flush()
    await db.refresh(row)


# ---------------------------------------------------------------------------
# Story 5.3: Admin user management
# ---------------------------------------------------------------------------


async def list_admin_users(db: AsyncSession, query: str | None = None) -> list[AdminUserRow]:
    """List end-user accounts with upload count. Scoped to role='user' only.

    Search matches email or id::text when query is provided.
    """
    upload_count_subq = (
        select(
            Document.user_id,
            func.count(Document.id).label("upload_count"),
        ).group_by(Document.user_id)
    ).subquery()

    stmt = (
        select(
            User.id,
            User.email,
            User.created_at,
            func.coalesce(upload_count_subq.c.upload_count, 0).label("upload_count"),
            User.account_status,
        )
        .outerjoin(upload_count_subq, User.id == upload_count_subq.c.user_id)
        .where(User.role == "user")
        .order_by(User.created_at.desc())
    )

    if query:
        escaped_query = query.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        q = f"%{escaped_query}%"
        stmt = stmt.where(
            func.lower(User.email).like(q, escape="\\")
            | func.cast(User.id, sa.Text).like(q, escape="\\")
        )

    result = await db.execute(stmt)
    return [
        {
            "user_id": str(row.id),
            "email": row.email,
            "registration_date": row.created_at.isoformat(),
            "upload_count": row.upload_count,
            "account_status": row.account_status,
        }
        for row in result.all()
    ]


async def get_admin_user_detail(db: AsyncSession, user_id: uuid.UUID) -> AdminUserDetailRow | None:
    """Return account metadata for a single end-user. No health data."""
    upload_count_subq = (
        select(func.count(Document.id)).where(Document.user_id == user_id)
    ).scalar_subquery()

    stmt = select(
        User.id,
        User.email,
        User.created_at,
        User.last_login_at,
        upload_count_subq.label("upload_count"),
        User.account_status,
    ).where(User.id == user_id, User.role == "user")
    result = await db.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return None
    return {
        "user_id": str(row.id),
        "email": row.email,
        "registration_date": row.created_at.isoformat(),
        "last_login": row.last_login_at.isoformat() if row.last_login_at else None,
        "upload_count": row.upload_count or 0,
        "account_status": row.account_status,
    }


async def set_user_account_status(
    db: AsyncSession, user_id: uuid.UUID, account_status: str
) -> bool:
    """Idempotent update of account_status. Returns True if user found, False if not.

    Scoped to role='user' to prevent admin self-suspension.
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.role == "user").with_for_update()
    )
    user = result.scalar_one_or_none()
    if user is None:
        return False
    user.account_status = account_status
    await db.flush()
    return True


async def revoke_user_sessions(db: AsyncSession, user_id: uuid.UUID, revoked_at: datetime) -> bool:
    """Stamp users.tokens_invalid_before, invalidating every JWT with iat < revoked_at.

    Scoped to role='user' for the same reason as account-status updates: admin self-
    revocation would lock out the admin console from the current session and is best
    handled through an explicit password reset flow, not this endpoint.

    Returns True if the user was found and updated, False if no matching row.

    The cutoff is monotonic: a new revoke_at smaller than the existing value is
    ignored. NTP clock step-backs and rapid successive revokes must never lower the
    cutoff, which would silently re-validate previously-revoked tokens.
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.role == "user").with_for_update()
    )
    user = result.scalar_one_or_none()
    if user is None:
        return False
    if user.tokens_invalid_before is None or revoked_at > user.tokens_invalid_before:
        user.tokens_invalid_before = revoked_at
        await db.flush()
    return True


# ---------------------------------------------------------------------------
# Story 5.3: Flagged value reports
# ---------------------------------------------------------------------------


async def get_flagged_reports(db: AsyncSession) -> list[tuple[HealthValue, str | None]]:
    """Return unreviewed flagged health values with their flagged_at.

    Returns raw ORM objects — decryption happens in service layer.
    Filter: is_flagged = true AND flag_reviewed_at IS NULL.
    Returns tuples of (HealthValue, flagged_at_iso).
    """
    stmt = (
        select(HealthValue)
        .where(
            HealthValue.is_flagged.is_(True),
            HealthValue.flag_reviewed_at.is_(None),
        )
        .order_by(HealthValue.flagged_at.desc().nullslast())
    )
    result = await db.execute(stmt)
    return [
        (hv, hv.flagged_at.isoformat() if hv.flagged_at else None) for hv in result.scalars().all()
    ]


async def mark_flag_reviewed(
    db: AsyncSession, health_value_id: uuid.UUID, admin_id: uuid.UUID
) -> HealthValue | None:
    """Mark a flagged health value as reviewed. Idempotent under concurrent clicks.

    Sets review metadata exactly once. Returns the HealthValue or None if not found.
    """
    result = await db.execute(
        select(HealthValue)
        .where(
            HealthValue.id == health_value_id,
            HealthValue.is_flagged.is_(True),
        )
        .with_for_update()
    )
    hv = result.scalar_one_or_none()
    if hv is None:
        return None
    # Only write review metadata once
    if hv.flag_reviewed_at is None:
        hv.flag_reviewed_at = datetime.now(UTC)
        hv.flag_reviewed_by_admin_id = admin_id
        await db.flush()
        await db.refresh(hv)
    return hv
