"""Generate AI interpretation for persisted health values."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.processing.schemas import ProcessingGraphFallbackState, ProcessingGraphState

logger = structlog.get_logger()


async def generate_interpretation(
    state: ProcessingGraphState,
    fallback_state: ProcessingGraphFallbackState | None = None,
) -> dict[str, object]:
    """Invalidate stale interpretation and attempt regeneration without changing fallback rules."""
    fallback = fallback_state or state["fallback"]
    fallback.error_stage = "generate_interpretation"
    fallback.error_message = None

    values = state["normalized_values"]
    user_id = state["user_id"]
    if not values or user_id is None:
        return {}

    try:
        from app.ai import repository as ai_repository

        async with AsyncSession(state["runtime"].db_engine, expire_on_commit=False) as db:
            await ai_repository.invalidate_interpretation(
                db,
                user_id=user_id,
                document_id=state["document_id"],
            )
            await db.commit()
    except Exception:
        logger.warning("worker.ai_invalidation_failed", document_id=state["document_id_str"])

    try:
        from app.ai import service as ai_service

        async with AsyncSession(state["runtime"].db_engine, expire_on_commit=False) as db:
            await ai_service.generate_interpretation(
                db,
                document_id=state["document_id"],
                user_id=user_id,
                values=values,
            )
            await db.commit()
    except Exception:
        logger.warning("worker.ai_interpretation_failed", document_id=state["document_id_str"])

    # The per-document note just changed, so every aggregate-scope note
    # (overall_all / overall_analysis / overall_document) is now stale.
    # Invalidate lazily — we do not regenerate here because the user may
    # still be mid-upload of several documents; regeneration happens on the
    # next GET /dashboard/interpretation or on an explicit
    # POST /dashboard/interpretation/regenerate. This is what saves LLM
    # tokens versus the previous "regenerate every page load" behaviour.
    try:
        from app.ai import repository as ai_repository

        async with AsyncSession(state["runtime"].db_engine, expire_on_commit=False) as db:
            await ai_repository.invalidate_all_overall_interpretations(db, user_id=user_id)
            await db.commit()
    except Exception:
        logger.warning(
            "worker.overall_ai_invalidation_failed", document_id=state["document_id_str"]
        )

    return {}
