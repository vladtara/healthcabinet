"""ARQ async job queue worker — document processing pipeline."""

import asyncio
import uuid

import redis.asyncio as aioredis
import structlog
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.database import import_orm_models
from app.documents import repository as document_repository
from app.processing.events import publish_event
from app.processing.graph import ProcessingGraphExecutionError, run_processing_graph
from app.processing.schemas import STAGE_MESSAGES, ProcessingGraphFallbackState
from app.users.service import delete_user_storage_prefix

logger = structlog.get_logger()


async def startup(ctx: dict) -> None:  # type: ignore[type-arg]
    """Initialise shared resources for the ARQ worker process."""
    import_orm_models()
    ctx["db_engine"] = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    ctx["redis"] = aioredis.from_url(  # type: ignore[no-untyped-call]
        settings.REDIS_URL,
        decode_responses=True,
    )


async def shutdown(ctx: dict) -> None:  # type: ignore[type-arg]
    """Dispose shared resources on worker shutdown."""
    await ctx["db_engine"].dispose()
    await ctx["redis"].aclose()


async def process_document(ctx: dict, document_id: str) -> None:  # type: ignore[type-arg]
    """Delegate document processing to the LangGraph pipeline and keep safe fallback handling."""
    doc_id_uuid: uuid.UUID | None = None
    redis = ctx["redis"]

    async def _publish(event_type: str) -> None:
        msg, progress = STAGE_MESSAGES[event_type]
        await publish_event(redis, document_id, event_type, progress, msg)

    try:
        doc_id_uuid = uuid.UUID(document_id)
        await run_processing_graph(ctx, document_id)
    except Exception as exc:
        fallback_state = (
            exc.fallback_state
            if isinstance(exc, ProcessingGraphExecutionError)
            else ProcessingGraphFallbackState()
        )
        if fallback_state.error_stage is None:
            fallback_state.error_stage = "worker_input_validation"
        if fallback_state.error_message is None:
            fallback_state.error_message = str(exc)
        logger.exception(
            "worker.process_document_failed",
            document_id=document_id,
            error_stage=fallback_state.error_stage,
        )
        # Finding 2: if prior partial values existed before this (retry) run, revert to
        # "partial" so those values stay visible and the document status is not contradictory.
        # Also covers the case where Phase 1 committed new values but Phase 3 failed —
        # values_committed ensures the fallback is "partial" rather than "failed".
        # For first-time processing with no committed values the safe fallback is "failed".
        exception_status = (
            "partial"
            if (fallback_state.prior_values_existed or fallback_state.values_committed)
            else "failed"
        )
        exception_event = f"document.{exception_status}"
        if doc_id_uuid is not None:
            try:
                async with AsyncSession(ctx["db_engine"], expire_on_commit=False) as db:
                    await document_repository.update_document_status_internal(
                        db, doc_id_uuid, exception_status
                    )
                    await db.commit()
            except Exception:
                logger.exception("worker.update_failed_status_error", document_id=document_id)
            try:
                await _publish(exception_event)
            except Exception:
                logger.exception("worker.publish_failed_event_error", document_id=document_id)


async def reconcile_deleted_user_storage(
    ctx: dict[str, object],
    user_id: str,
    prefix: str,
) -> None:
    """Perform a deferred, durable storage sweep after account deletion."""
    del ctx

    try:
        deleted_count = await asyncio.to_thread(delete_user_storage_prefix, prefix)
        logger.info(
            "account_deletion.storage_cleanup_complete",
            user_id=user_id,
            deleted_object_count=deleted_count,
            prefix=prefix,
            cleanup_mode="reconciliation",
        )
    except Exception:
        logger.warning(
            "account_deletion.storage_cleanup_failed",
            user_id=user_id,
            orphaned_prefix=prefix,
            cleanup_mode="reconciliation",
            exc_info=True,
        )


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [process_document, reconcile_deleted_user_storage]
    on_startup = startup
    on_shutdown = shutdown
    queues = ["default", "priority"]
