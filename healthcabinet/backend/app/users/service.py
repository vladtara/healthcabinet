import uuid
from typing import Any

import structlog
from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AuditLog
from app.auth.models import User
from app.core.config import settings
from app.documents.models import Document
from app.documents.storage import delete_objects_by_prefix, get_s3_client
from app.health_data.models import HealthValue
from app.users.models import UserProfile
from app.users.repository import get_user_profile, update_onboarding_step, upsert_user_profile
from app.users.schemas import ProfileUpdateRequest

logger = structlog.get_logger()

ACCOUNT_DELETION_RECONCILIATION_JOB = "reconcile_deleted_user_storage"
ACCOUNT_DELETION_RECONCILIATION_DELAY_SECONDS = 5

# GDPR Article 17 erasure marker. Written to audit_logs.original_value,
# audit_logs.new_value, and audit_logs.value_name when the subject of an
# admin correction is deleted. Preserves the audit row's structural integrity
# (admin_id / reason / corrected_at stay visible for regulatory accountability)
# while scrubbing the deleted user's health data content and the biomarker
# identifier (which can itself identify the subject's condition).
AUDIT_ERASURE_MARKER = "[REDACTED]"


def delete_user_storage_prefix(prefix: str) -> int:
    """Delete all MinIO objects under a user's prefix and return the object count."""
    s3_client = get_s3_client()
    try:
        return delete_objects_by_prefix(s3_client, settings.MINIO_BUCKET, prefix)
    finally:
        close = getattr(s3_client, "close", None)
        if callable(close):
            close()


async def _enqueue_account_deletion_reconciliation(
    arq_redis: Any,
    *,
    user_id: uuid.UUID,
    prefix: str,
) -> None:
    if arq_redis is None:
        logger.warning(
            "account_deletion.storage_reconciliation_unavailable",
            user_id=str(user_id),
            orphaned_prefix=prefix,
        )
        return

    try:
        job = await arq_redis.enqueue_job(
            ACCOUNT_DELETION_RECONCILIATION_JOB,
            user_id=str(user_id),
            prefix=prefix,
            _defer_by=ACCOUNT_DELETION_RECONCILIATION_DELAY_SECONDS,
        )
    except Exception:
        logger.warning(
            "account_deletion.storage_reconciliation_enqueue_failed",
            user_id=str(user_id),
            orphaned_prefix=prefix,
            exc_info=True,
        )
        return

    if job is None:
        logger.warning(
            "account_deletion.storage_reconciliation_enqueue_returned_none",
            user_id=str(user_id),
            orphaned_prefix=prefix,
        )
        return

    logger.info(
        "account_deletion.storage_reconciliation_enqueued",
        user_id=str(user_id),
        prefix=prefix,
        job_id=job.job_id,
    )


async def get_profile(db: AsyncSession, user_id: uuid.UUID) -> UserProfile | None:
    return await get_user_profile(db, user_id)


async def update_profile(
    db: AsyncSession, user_id: uuid.UUID, data: ProfileUpdateRequest
) -> UserProfile:
    fields = data.model_dump(exclude_unset=True)
    return await upsert_user_profile(db, user_id, **fields)


async def save_onboarding_progress(db: AsyncSession, user_id: uuid.UUID, step: int) -> UserProfile:
    return await update_onboarding_step(db, user_id, step)


async def delete_user_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    arq_redis: Any = None,
) -> None:
    """Delete user account and all associated data (GDPR Article 17).

    DB deletion is authoritative: one transaction covers audit redaction,
    FK cascade (documents/health_values/ai_memories/user_profiles), and user delete.
    After commit, MinIO cleanup is enqueued as a deferred ARQ job; MinIO failure
    is logged for operator intervention but does not block the user-facing 204.

    Cascade order (all one transaction):
    1. Redact audit_logs where user is SUBJECT — null user_id / document_id /
       health_value_id AND replace original_value / new_value / value_name with
       AUDIT_ERASURE_MARKER. value_name is redacted because a biomarker name
       (e.g. "HIV viral load") can by itself identify the subject's condition.
       Must run BEFORE user-delete: audit_logs.user_id FK is ondelete=CASCADE, so
       a direct DELETE FROM users would cascade-delete these audit rows and erase
       the regulatory audit trail.
    2. Null audit_logs.admin_id where user is ACTOR — preserves correction content
       (on rows about OTHER users' data) but removes the deleted user's admin link.
    3. DELETE FROM users — FK CASCADE handles documents, health_values, ai_memories,
       user_profiles, subscriptions. consent_logs.user_id set to NULL by FK (retained
       per regulatory requirement).
    """
    user_document_ids = select(Document.id).where(Document.user_id == user_id)
    user_health_value_ids = select(HealthValue.id).where(HealthValue.user_id == user_id)
    legacy_subject_rows = and_(
        AuditLog.user_id.is_(None),
        or_(
            AuditLog.document_id.in_(user_document_ids),
            AuditLog.health_value_id.in_(user_health_value_ids),
        ),
    )

    # 1. Redact audit rows where the user being deleted was the SUBJECT.
    #    Covers both current rows keyed by audit_logs.user_id and legacy rows that
    #    only point at the subject through document_id / health_value_id.
    #    Scrub content + null all FKs in one UPDATE.
    await db.execute(
        update(AuditLog)
        .where(or_(AuditLog.user_id == user_id, legacy_subject_rows))
        .values(
            user_id=None,
            document_id=None,
            health_value_id=None,
            original_value=AUDIT_ERASURE_MARKER,
            new_value=AUDIT_ERASURE_MARKER,
            value_name=AUDIT_ERASURE_MARKER,
        )
    )
    # 2. Null admin_id on rows where the user being deleted was the ACTOR.
    #    Content preserved (those rows are about other users' data).
    await db.execute(update(AuditLog).where(AuditLog.admin_id == user_id).values(admin_id=None))
    # 3. Delete user row — CASCADE handles documents, health_values, user_profiles,
    #    ai_memories, subscriptions. consent_logs.user_id set to NULL by FK.
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()

    # 3. Deferred MinIO cleanup: enqueue a reconciliation job as safety net.
    #    Inline cleanup was removed — it raced with the deferred job causing double-cleanup.
    #    The deferred job runs after ACCOUNT_DELETION_RECONCILIATION_DELAY_SECONDS so it
    #    does not race with normal uploads. Cleanup errors are logged but do not block
    #    the 204 response (GDPR compliance requires the DB deletion to succeed).
    if arq_redis is not None:
        await _enqueue_account_deletion_reconciliation(
            arq_redis,
            user_id=user_id,
            prefix=f"{user_id}/",
        )
    else:
        logger.warning(
            "account_deletion.storage_reconciliation_unavailable",
            user_id=str(user_id),
            orphaned_prefix=f"{user_id}/",
        )
