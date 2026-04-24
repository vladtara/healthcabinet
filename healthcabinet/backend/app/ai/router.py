"""AI interpretation router — GET /api/v1/ai/documents/{document_id}/interpretation."""

import uuid
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import repository as ai_repository
from app.ai import service as ai_service
from app.ai.schemas import (
    AiChatRequest,
    AiInterpretationResponse,
    AiPatternsResponse,
    DashboardChatRequest,
    DashboardInterpretationResponse,
    DashboardKind,
    ReasoningContext,
)
from app.ai.service import (
    AiServiceUnavailableError,
    NoAiContextError,
    NoDashboardAiContextError,
)
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.database import get_db
from app.core.rate_limit import check_ai_dashboard_rate_limit, check_ai_patterns_rate_limit
from app.documents import repository as document_repository
from app.documents.exceptions import DocumentNotFoundError

router = APIRouter(prefix="/ai", tags=["ai"])
logger = structlog.get_logger()

_INTERPRETABLE_STATUSES = {"completed", "partial"}


@router.get("/documents/{document_id}/interpretation", response_model=AiInterpretationResponse)
async def get_document_interpretation(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AiInterpretationResponse:
    # Ownership check: verify document belongs to this user
    try:
        document = await document_repository.get_document_by_id(db, document_id, current_user.id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None

    # Document-status gate: only serve interpretations for fully processed documents.
    # During reprocessing the old interpretation may be stale; a new one will be
    # generated once processing completes again.
    if document.status not in _INTERPRETABLE_STATUSES:
        raise HTTPException(status_code=404, detail="Document is still processing")

    result = await ai_repository.get_interpretation_and_metadata(
        db, user_id=current_user.id, document_id=document_id
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Interpretation not available")

    interpretation, reasoning_dict, memory = result
    reasoning: ReasoningContext | None = None
    if reasoning_dict is not None:
        try:
            reasoning = ReasoningContext.model_validate(reasoning_dict)
        except Exception:
            logger.warning("ai.reasoning_schema_mismatch", document_id=str(document_id))
            reasoning = None

    return AiInterpretationResponse(
        document_id=document_id,
        interpretation=interpretation,
        model_version=memory.model_version,
        generated_at=memory.updated_at,
        reasoning=reasoning,
    )


@router.post("/chat")
async def chat_with_ai(
    payload: AiChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    # Ownership check: verify document belongs to this user
    try:
        await document_repository.get_document_by_id(db, payload.document_id, current_user.id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None

    try:
        stream = await ai_service.stream_follow_up_answer(
            db,
            user_id=current_user.id,
            document_id=payload.document_id,
            question=payload.question,
            output_language=payload.locale,
        )
    except NoAiContextError:
        raise HTTPException(
            status_code=409,
            detail="No AI interpretation context is available for this user. Generate an interpretation first.",
        ) from None
    except AiServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None

    return StreamingResponse(stream, media_type="text/plain; charset=utf-8")


@router.get("/patterns", response_model=AiPatternsResponse)
async def get_patterns(
    locale: Literal["en", "uk"] = Query(default="en"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AiPatternsResponse:
    await check_ai_patterns_rate_limit(str(current_user.id))
    return await ai_service.detect_cross_upload_patterns(
        db, user_id=current_user.id, output_language=locale
    )


# ---------------------------------------------------------------------------
# Story 15.3 — dashboard-scoped aggregate AI endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/dashboard/interpretation",
    response_model=DashboardInterpretationResponse,
)
async def get_dashboard_interpretation(
    document_kind: DashboardKind = Query(
        ...,
        description=(
            "Dashboard filter scope. 'all' covers analysis+document and still "
            "excludes 'unknown' (which is rejected by this Literal)."
        ),
    ),
    locale: Literal["en", "uk"] = Query(default="en"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardInterpretationResponse:
    await check_ai_dashboard_rate_limit(str(current_user.id))
    try:
        return await ai_service.generate_dashboard_interpretation(
            db, user_id=current_user.id, document_kind=document_kind, output_language=locale
        )
    except NoDashboardAiContextError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except AiServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@router.post(
    "/dashboard/interpretation/regenerate",
    response_model=DashboardInterpretationResponse,
)
async def regenerate_dashboard_interpretation(
    document_kind: DashboardKind = Query(
        ...,
        description=(
            "Dashboard filter scope. Only 'all' persists to the cached overall "
            "note; other kinds regenerate on demand without writing a cache row."
        ),
    ),
    locale: Literal["en", "uk"] = Query(default="en"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardInterpretationResponse:
    """Force-regenerate the overall/main clinical note.

    Invalidates the cached row (for 'all'), calls the LLM, persists the new
    interpretation, and returns it. This is the endpoint behind the manual
    "Regenerate" button on the dashboard AI clinical note card.
    """
    await check_ai_dashboard_rate_limit(str(current_user.id))
    try:
        return await ai_service.force_regenerate_dashboard_interpretation(
            db, user_id=current_user.id, document_kind=document_kind, output_language=locale
        )
    except NoDashboardAiContextError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except AiServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@router.post("/dashboard/chat")
async def dashboard_chat(
    payload: DashboardChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    await check_ai_dashboard_rate_limit(str(current_user.id))
    try:
        stream = await ai_service.stream_dashboard_follow_up(
            db,
            user_id=current_user.id,
            document_kind=payload.document_kind,
            question=payload.question,
            output_language=payload.locale,
        )
    except NoDashboardAiContextError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except AiServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None

    return StreamingResponse(stream, media_type="text/plain; charset=utf-8")
