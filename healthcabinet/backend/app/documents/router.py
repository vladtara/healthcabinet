import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.database import get_db
from app.documents import service
from app.documents.dependencies import get_arq_redis, rate_limit_upload
from app.documents.schemas import (
    ConfirmDateYearRequest,
    DeleteResponse,
    DocumentDetailResponse,
    DocumentResponse,
    KeepPartialResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse], status_code=200)
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """Return all documents for the authenticated user, sorted newest first."""
    return await service.list_documents(db, current_user)


@router.get("/{document_id}", response_model=DocumentDetailResponse, status_code=200)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    """Return a single owned document with its extracted health values."""
    return await service.get_document_detail(db, current_user, document_id)


@router.delete("/{document_id}", response_model=DeleteResponse, status_code=200)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeleteResponse:
    """Delete a document and its health values; storage cleanup is best-effort."""
    return await service.delete_document(db, current_user, document_id)


@router.post("/upload", response_model=DocumentResponse, status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    arq_redis: object = Depends(get_arq_redis),
    _rate_limit: None = Depends(rate_limit_upload),
) -> DocumentResponse:
    """Accept a multipart file upload, store it in MinIO, and enqueue processing.

    The backend proxies the upload to MinIO — the browser never contacts MinIO directly.
    Rate limited: free-tier users may call this at most 5 times per day.
    Requires valid access token.
    """
    return await service.upload_document(db, arq_redis, current_user, file)


@router.post("/{document_id}/reupload", response_model=DocumentResponse, status_code=202)
async def reupload_document(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    arq_redis: object = Depends(get_arq_redis),
    _rate_limit: None = Depends(rate_limit_upload),
) -> DocumentResponse:
    """Accept a multipart file upload for retrying an existing document slot.

    Only valid for documents in 'partial' or 'failed' status owned by the caller.
    Returns 404 if the document does not exist or belongs to another user.
    Returns 409 if the document is not in a retryable state.

    Rate limited: consumes the same daily upload quota as fresh uploads.
    """
    return await service.reupload_document(db, arq_redis, current_user, document_id, file)


@router.post("/{document_id}/keep-partial", response_model=KeepPartialResponse)
async def keep_partial(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KeepPartialResponse:
    """Persist the user's decision to keep partial extraction results.

    Only valid for documents in 'partial' status. Sets keep_partial=True so the
    recovery UI is dismissed on subsequent loads without changing extracted values.
    Returns 404 if the document does not exist or belongs to another user.
    Returns 409 if the document is not in partial status.
    """
    return await service.keep_document_partial(db, current_user, document_id)


@router.post("/{document_id}/confirm-date-year", response_model=DocumentDetailResponse)
async def confirm_date_year(
    document_id: uuid.UUID,
    payload: ConfirmDateYearRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    """Resolve a document's pending year-confirmation (Story 15.2 AC 5).

    Composes a timezone-aware measured_at from the stored partial date fragment
    and the user-supplied year, propagates it to every health value row, clears
    the confirmation flag, recomputes terminal status, and invalidates +
    regenerates the AI interpretation.

    Returns 404 if the document does not exist or belongs to another user.
    Returns 409 if the document does not require year confirmation.
    Returns 400 if the supplied year is invalid for the stored partial date.
    """
    return await service.confirm_date_year(db, current_user, document_id, payload.year)
