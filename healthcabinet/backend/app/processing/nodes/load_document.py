"""Load document metadata and bytes for the processing graph."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.documents import repository as document_repository
from app.documents.storage import get_object_bytes, get_s3_client
from app.processing.events import publish_event
from app.processing.schemas import (
    STAGE_MESSAGES,
    ProcessingGraphFallbackState,
    ProcessingGraphState,
)


async def _publish(state: ProcessingGraphState, event_type: str) -> None:
    message, progress = STAGE_MESSAGES[event_type]
    await publish_event(
        state["runtime"].redis,
        state["document_id_str"],
        event_type,
        progress,
        message,
    )


async def load_document(
    state: ProcessingGraphState,
    fallback_state: ProcessingGraphFallbackState | None = None,
) -> dict[str, object]:
    """Verify the document, mark it processing, and load its object bytes."""
    fallback = fallback_state or state["fallback"]
    fallback.error_stage = "load_document"
    fallback.error_message = None

    async with AsyncSession(state["runtime"].db_engine, expire_on_commit=False) as db:
        await document_repository.get_document_by_id_internal(db, state["document_id"])

    await _publish(state, "document.upload_started")

    async with AsyncSession(state["runtime"].db_engine, expire_on_commit=False) as db:
        await document_repository.update_document_status_internal(
            db, state["document_id"], "processing"
        )
        await db.commit()

    await _publish(state, "document.reading")

    async with AsyncSession(state["runtime"].db_engine, expire_on_commit=False) as db:
        document = await document_repository.get_document_by_id_internal(db, state["document_id"])
        s3_key = await document_repository.get_document_s3_key_internal(db, state["document_id"])
        prior_values_existed = await document_repository.has_document_health_values(
            db, state["document_id"]
        )

    fallback.prior_values_existed = prior_values_existed
    document_bytes = get_object_bytes(get_s3_client(), settings.MINIO_BUCKET, s3_key)

    return {
        "document_mime_type": document.file_type,
        "document_bytes": document_bytes,
        "s3_key": s3_key,
        "user_id": document.user_id,
    }
