"""Database access for AI interpretations. Encryption/decryption only happens here."""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import AiMemory
from app.core.encryption import decrypt_bytes, encrypt_bytes
from app.documents.models import Document

logger = structlog.get_logger()

# Story 15.3 — dashboard filter scope. 'unknown' is deliberately NOT exposed
# to the dashboard because it represents a failure/unreadable classification.
DashboardKind = Literal["all", "analysis", "document"]


def _kinds_for_filter(document_kind: DashboardKind) -> tuple[str, ...]:
    if document_kind == "all":
        return ("analysis", "document")
    return (document_kind,)


@dataclass(slots=True)
class AiMemoryExportRecord:
    document_id: uuid.UUID | None
    interpretation: str
    created_at: datetime | None


@dataclass(slots=True)
class AiMemoryExportResult:
    records: list[AiMemoryExportRecord]
    skipped_corrupt_records: int


async def upsert_ai_interpretation(
    db: AsyncSession,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
    interpretation_text: str,
    model_version: str,
    reasoning_json: dict[str, object] | None = None,
) -> AiMemory:
    """Insert or update the AI interpretation for a (user, document) pair.

    Uses a select-then-update pattern to handle document reprocessing without
    violating the UNIQUE constraint on (user_id, document_id).
    """
    encrypted = encrypt_bytes(interpretation_text.encode("utf-8"))
    encrypted_reasoning: bytes | None = None
    if reasoning_json is not None:
        encrypted_reasoning = encrypt_bytes(json.dumps(reasoning_json).encode("utf-8"))

    result = await db.execute(
        select(AiMemory).where(
            AiMemory.user_id == user_id,
            AiMemory.document_id == document_id,
        )
    )
    memory = result.scalar_one_or_none()
    if memory is not None:
        memory.interpretation_encrypted = encrypted
        memory.context_json_encrypted = encrypted_reasoning
        memory.model_version = model_version
        memory.safety_validated = True
        await db.flush()
        await db.refresh(memory)
    else:
        memory = AiMemory(
            user_id=user_id,
            document_id=document_id,
            context_json_encrypted=encrypted_reasoning,
            interpretation_encrypted=encrypted,
            model_version=model_version,
            safety_validated=True,
        )
        db.add(memory)
        await db.flush()
        await db.refresh(memory)
    return memory


async def invalidate_interpretation(
    db: AsyncSession,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
) -> None:
    """Mark any existing interpretation as not safety-validated (stale).

    Called before AI regeneration so that a failed or rejected regeneration
    does not leave the previous interpretation visible to the user.
    """
    result = await db.execute(
        select(AiMemory).where(
            AiMemory.user_id == user_id,
            AiMemory.document_id == document_id,
        )
    )
    memory = result.scalar_one_or_none()
    if memory is not None:
        memory.safety_validated = False
        await db.flush()


async def list_user_ai_context(
    db: AsyncSession,
    user_id: uuid.UUID,
    active_document_id: uuid.UUID | None = None,
    document_kind: DashboardKind | None = None,
) -> list[dict[str, object]]:
    """Return decrypted AI-memory rows ordered with the active document first.

    When document_kind is None (legacy/document-scoped and cross-upload-pattern
    callers), the full set of safety-validated rows is returned. When set, a
    JOIN to the documents table restricts the result to rows whose owning
    document matches the filter. 'all' covers analysis+document and still
    excludes 'unknown'.
    """
    stmt = select(AiMemory).where(
        AiMemory.user_id == user_id,
        AiMemory.safety_validated == True,  # noqa: E712
        AiMemory.interpretation_encrypted.is_not(None),
    )
    if document_kind is not None:
        kinds = _kinds_for_filter(document_kind)
        # Defense-in-depth: pin the JOIN on Document.user_id as well so a future
        # refactor that drops the AiMemory.user_id predicate cannot silently
        # return other users' rows.
        stmt = stmt.join(
            Document,
            (Document.id == AiMemory.document_id) & (Document.user_id == user_id),
        ).where(Document.document_kind.in_(kinds))
    result = await db.execute(stmt)
    rows = result.scalars().all()

    # Sort: active document first, then by updated_at DESC
    def _sort_key(row: AiMemory) -> tuple[int, object]:
        is_active = (
            0 if (active_document_id is not None and row.document_id == active_document_id) else 1
        )
        return (is_active, -(row.updated_at.timestamp() if row.updated_at else 0))

    rows = sorted(rows, key=_sort_key)

    context: list[dict[str, object]] = []
    for row in rows:
        if row.interpretation_encrypted is None:
            logger.warning("ai.context_missing_interpretation", document_id=str(row.document_id))
            continue
        try:
            interpretation = decrypt_bytes(row.interpretation_encrypted).decode("utf-8")
        except Exception:
            logger.warning("ai.context_decrypt_failed", document_id=str(row.document_id))
            continue

        reasoning: dict[str, object] | None = None
        if row.context_json_encrypted is not None:
            try:
                reasoning = json.loads(decrypt_bytes(row.context_json_encrypted).decode("utf-8"))
            except Exception:
                logger.warning(
                    "ai.context_reasoning_decrypt_failed", document_id=str(row.document_id)
                )

        entry: dict[str, object] = {
            "document_id": str(row.document_id),
            "interpretation": interpretation,
            "updated_at": row.updated_at.date().isoformat() if row.updated_at else None,
        }
        if reasoning is not None:
            entry["reasoning"] = reasoning
        context.append(entry)

    return context


async def list_ai_memories_by_user(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> AiMemoryExportResult:
    """Return decrypted AI interpretations with created_at for data export.

    Unlike list_user_ai_context (which returns updated_at and sorts by active doc),
    this returns created_at and all stored interpretations without sorting.
    """
    result = await db.execute(
        select(AiMemory).where(
            AiMemory.user_id == user_id,
            AiMemory.interpretation_encrypted.is_not(None),
        )
    )
    rows = result.scalars().all()

    entries: list[AiMemoryExportRecord] = []
    skipped = 0
    for row in rows:
        if row.interpretation_encrypted is None:
            continue
        try:
            interpretation = decrypt_bytes(row.interpretation_encrypted).decode("utf-8")
        except Exception:
            logger.warning("ai.export_decrypt_failed", document_id=str(row.document_id))
            skipped += 1
            continue
        entries.append(
            AiMemoryExportRecord(
                document_id=row.document_id,
                interpretation=interpretation,
                created_at=row.created_at,
            )
        )
    return AiMemoryExportResult(records=entries, skipped_corrupt_records=skipped)


async def get_interpretation_and_metadata(
    db: AsyncSession,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
) -> tuple[str, dict[str, object] | None, AiMemory] | None:
    """Return (decrypted_text, reasoning_dict_or_none, memory_row), or None if absent."""
    result = await db.execute(
        select(AiMemory).where(
            AiMemory.user_id == user_id,
            AiMemory.document_id == document_id,
            AiMemory.safety_validated == True,  # noqa: E712
        )
    )
    memory = result.scalar_one_or_none()
    if memory is None or memory.interpretation_encrypted is None:
        return None
    text = decrypt_bytes(memory.interpretation_encrypted).decode("utf-8")
    reasoning: dict[str, object] | None = None
    if memory.context_json_encrypted is not None:
        try:
            reasoning = json.loads(decrypt_bytes(memory.context_json_encrypted).decode("utf-8"))
        except Exception:
            logger.warning("ai.reasoning_decrypt_failed", document_id=str(document_id))
            reasoning = None
    return text, reasoning, memory
