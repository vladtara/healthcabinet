"""Persist normalized health values for the processing graph."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.health_data import repository as health_data_repository
from app.processing.events import publish_event
from app.processing.schemas import (
    STAGE_MESSAGES,
    ProcessingGraphFallbackState,
    ProcessingGraphState,
)


async def persist_values(
    state: ProcessingGraphState,
    fallback_state: ProcessingGraphFallbackState | None = None,
) -> dict[str, object]:
    """Persist health values while preserving the existing retry semantics."""
    fallback = fallback_state or state["fallback"]
    fallback.error_stage = "persist_values"
    fallback.error_message = None

    user_id = state["user_id"]
    if user_id is None:
        raise RuntimeError("Graph state missing user_id before value persistence")

    message, progress = STAGE_MESSAGES["document.generating"]
    await publish_event(
        state["runtime"].redis,
        state["document_id_str"],
        "document.generating",
        progress,
        message,
    )

    values = state["normalized_values"]
    if values:
        async with AsyncSession(state["runtime"].db_engine, expire_on_commit=False) as db:
            await health_data_repository.replace_document_health_values(
                db,
                document_id=state["document_id"],
                user_id=user_id,
                measured_at=state["measured_at"],
                values=values,
            )
            await db.commit()
        fallback.values_committed = True
        return {}

    if not fallback.prior_values_existed:
        async with AsyncSession(state["runtime"].db_engine, expire_on_commit=False) as db:
            await health_data_repository.delete_document_health_values(
                db, document_id=state["document_id"]
            )
            await db.commit()

    return {}
