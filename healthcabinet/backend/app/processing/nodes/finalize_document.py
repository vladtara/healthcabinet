"""Finalize document status and terminal event for the processing graph."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents import repository as document_repository
from app.processing.events import publish_event
from app.processing.schemas import (
    STAGE_MESSAGES,
    ProcessingGraphFallbackState,
    ProcessingGraphState,
    TerminalDocumentEvent,
    TerminalDocumentStatus,
)

logger = structlog.get_logger()


def _resolve_document_kind(
    state: ProcessingGraphState,
    fallback: ProcessingGraphFallbackState,
    *,
    prior_error_stage: str | None,
) -> str:
    """Classify the document from persisted extraction state.

    Story 15.2 AC 2 — classification rules driven by persisted output:
    - `analysis` when normalized lab values are extracted
    - `document` when extraction succeeded but no usable lab values
    - `unknown` when processing failed / unreadable
    On retry paths where no new values were extracted but prior values exist,
    `analysis` is preserved because those persisted rows are the authoritative signal.

    `prior_error_stage` is a snapshot of `fallback.error_stage` taken BEFORE
    `finalize_document` stamps its own stage name — otherwise the `document`
    branch below would never fire at runtime because `fallback.error_stage`
    would always be "finalize_document" by the time we look at it.
    """
    if state["normalized_values"]:
        return "analysis"
    if fallback.prior_values_existed:
        return "analysis"
    if prior_error_stage is None:
        # Processing completed cleanly but the extractor found nothing lab-shaped.
        return "document"
    return "unknown"


def _resolve_needs_date_confirmation(state: ProcessingGraphState) -> bool:
    """A yearless date plus at least one extracted value means the owner must confirm."""
    if not state["normalized_values"]:
        return False
    if state["measured_at"] is not None:
        return False
    return bool(state["partial_measured_at_text"])


def _resolve_terminal_outcome(
    state: ProcessingGraphState,
    fallback: ProcessingGraphFallbackState,
    *,
    document_kind: str,
    needs_date_confirmation: bool,
) -> tuple[TerminalDocumentStatus, TerminalDocumentEvent]:
    """Resolve terminal status per Story 15.2 AC 4 rules.

    Ordering matters: the existing low-confidence `partial` rule is preserved and
    a yearless-date `partial` is stacked on top of it. Non-analysis successful
    documents may still complete; only unreadable/failed cases become `failed`.
    """
    if state["normalized_values"]:
        low_confidence_count = sum(1 for value in state["normalized_values"] if value.needs_review)
        if low_confidence_count or needs_date_confirmation:
            return "partial", "document.partial"
        return "completed", "document.completed"

    if fallback.prior_values_existed:
        # Retry with no fresh values — preserve the prior partial state, classification
        # still maps to `analysis` because persisted rows are the authoritative signal.
        return "partial", "document.partial"

    if document_kind == "document":
        # Successful non-analysis processing (e.g., consent form, referral): terminal complete.
        return "completed", "document.completed"

    return "failed", "document.failed"


async def finalize_document(
    state: ProcessingGraphState,
    fallback_state: ProcessingGraphFallbackState | None = None,
) -> dict[str, object]:
    """Persist the terminal document status and publish the terminal SSE event."""
    fallback = fallback_state or state["fallback"]
    # Snapshot BEFORE we stamp our own stage name, so _resolve_document_kind
    # can tell the difference between "prior stage errored" and "we just entered
    # finalize_document cleanly after a successful upstream node".
    prior_error_stage = fallback.error_stage
    fallback.error_stage = "finalize_document"
    fallback.error_message = None

    document_kind = _resolve_document_kind(
        state, fallback, prior_error_stage=prior_error_stage
    )
    needs_date_confirmation = _resolve_needs_date_confirmation(state)
    partial_text = state["partial_measured_at_text"] if needs_date_confirmation else None
    terminal_status, terminal_event = _resolve_terminal_outcome(
        state,
        fallback,
        document_kind=document_kind,
        needs_date_confirmation=needs_date_confirmation,
    )

    async with AsyncSession(state["runtime"].db_engine, expire_on_commit=False) as db:
        # Persist document intelligence BEFORE terminal status so a later status read
        # always sees the classification that matches it.
        await document_repository.update_document_intelligence_internal(
            db,
            state["document_id"],
            document_kind=document_kind,
            needs_date_confirmation=needs_date_confirmation,
            partial_measured_at_text=partial_text,
        )
        await document_repository.update_document_status_internal(
            db, state["document_id"], terminal_status
        )
        await db.commit()

    message, progress = STAGE_MESSAGES[terminal_event]
    try:
        await publish_event(
            state["runtime"].redis,
            state["document_id_str"],
            terminal_event,
            progress,
            message,
        )
    except Exception:
        logger.warning(
            "worker.terminal_event_publish_failed",
            document_id=state["document_id_str"],
            terminal_event=terminal_event,
        )

    fallback.error_stage = None
    fallback.error_message = None

    return {
        "terminal_event": terminal_event,
        "terminal_status": terminal_status,
    }
