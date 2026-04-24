"""Data collection orchestration for user data export."""

import asyncio
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AuditLog
from app.admin.repository import list_audit_logs_by_user_documents
from app.ai.repository import AiMemoryExportResult, list_ai_memories_by_user
from app.auth.repository import list_consent_logs_by_user
from app.documents.exceptions import DocumentNotFoundError
from app.documents.models import Document
from app.documents.repository import get_document_s3_key_optional, get_documents_by_user
from app.documents.storage import get_object_bytes
from app.health_data.repository import HealthValueListResult, list_values_by_user
from app.users.models import ConsentLog

logger = structlog.get_logger()


async def list_health_values_for_export(
    db: AsyncSession, user_id: uuid.UUID
) -> HealthValueListResult:
    """Return all decrypted health values for a user."""
    return await list_values_by_user(db, user_id=user_id)


async def list_documents_for_export(db: AsyncSession, user_id: uuid.UUID) -> list[Document]:
    """Return all documents for a user."""
    return await get_documents_by_user(db, user_id)


async def get_document_file_bytes(
    db: AsyncSession,
    user_id: uuid.UUID,
    document: Document,
    s3_client: object,
    bucket: str,
) -> bytes | None:
    """Fetch document file bytes from MinIO. Returns None on failure."""
    try:
        s3_key = await get_document_s3_key_optional(db, document.id, user_id)
    except DocumentNotFoundError:
        logger.warning(
            "export.document_missing_during_download",
            document_id=str(document.id),
            user_id=str(user_id),
        )
        return None
    if s3_key is None:
        logger.warning(
            "export.s3_key_unavailable",
            document_id=str(document.id),
            user_id=str(user_id),
        )
        return None
    try:
        return await asyncio.to_thread(get_object_bytes, s3_client, bucket, s3_key)
    except Exception:
        logger.warning(
            "export.document_download_failed",
            document_id=str(document.id),
            user_id=str(user_id),
        )
        return None


async def list_ai_interpretations_for_export(
    db: AsyncSession, user_id: uuid.UUID
) -> AiMemoryExportResult:
    """Return decrypted AI interpretations with created_at for export."""
    return await list_ai_memories_by_user(db, user_id)


async def list_consent_logs_for_export(db: AsyncSession, user_id: uuid.UUID) -> list[ConsentLog]:
    """Return all consent log entries for a user."""
    return await list_consent_logs_by_user(db, user_id)


async def list_admin_corrections_for_export(db: AsyncSession, user_id: uuid.UUID) -> list[AuditLog]:
    """Return all audit log entries linked to a user's documents/health values."""
    return await list_audit_logs_by_user_documents(db, user_id)
