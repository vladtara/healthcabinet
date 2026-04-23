import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import (
    AdminUserDetail,
    AdminUserListResponse,
    AdminUserStatusUpdate,
    CorrectionRequest,
    CorrectionResponse,
    DocumentQueueDetail,
    ErrorQueueResponse,
    FlaggedReportListResponse,
    FlagReviewedResponse,
    PlatformMetricsResponse,
)
from app.admin.service import (
    fetch_admin_user_detail,
    fetch_admin_users,
    fetch_flagged_reports,
    fetch_platform_metrics,
    get_document_for_correction,
    get_error_queue,
    review_flag,
    revoke_sessions,
    submit_correction,
    update_user_status,
)
from app.auth.dependencies import require_admin
from app.auth.models import User
from app.core.database import get_db
from app.health_data.exceptions import HealthValueNotFoundError

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics", response_model=PlatformMetricsResponse, status_code=200)
async def get_metrics(
    _current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PlatformMetricsResponse:
    """Return aggregate platform metrics. Requires admin role."""
    return await fetch_platform_metrics(db)


@router.get("/queue", response_model=ErrorQueueResponse, status_code=200)
async def list_error_queue(
    _current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ErrorQueueResponse:
    """Return documents with extraction problems (failed/partial status, low confidence, or flagged values)."""
    return await get_error_queue(db)


@router.get("/queue/{document_id}", response_model=DocumentQueueDetail, status_code=200)
async def get_document_queue_detail(
    document_id: uuid.UUID,
    _current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DocumentQueueDetail:
    """Return a document with all its health values for admin correction."""
    detail = await get_document_for_correction(db, document_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return detail


@router.post(
    "/queue/{document_id}/values/{health_value_id}/correct",
    response_model=CorrectionResponse,
    status_code=200,
)
async def correct_health_value(
    document_id: uuid.UUID,
    health_value_id: uuid.UUID,
    request: CorrectionRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CorrectionResponse:
    """Submit a corrected value for a health data point. Writes an immutable audit log."""
    try:
        return await submit_correction(
            db,
            admin_id=current_user.id,
            document_id=document_id,
            health_value_id=health_value_id,
            request=request,
        )
    except HealthValueNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health value not found",
        ) from err


# ---------------------------------------------------------------------------
# Story 5.3: Admin user management endpoints
# ---------------------------------------------------------------------------


@router.get("/users", response_model=AdminUserListResponse, status_code=200)
async def list_users(
    _current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None, description="Search by email or user ID"),
) -> AdminUserListResponse:
    """Return searchable list of user accounts. No health data exposed."""
    return await fetch_admin_users(db, q)


@router.get("/users/{user_id}", response_model=AdminUserDetail, status_code=200)
async def get_user_detail(
    user_id: uuid.UUID,
    _current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserDetail:
    """Return account metadata for a single user. No health data exposed."""
    detail = await fetch_admin_user_detail(db, user_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return detail


@router.patch("/users/{user_id}/status", status_code=200)
async def update_user_account_status(
    user_id: uuid.UUID,
    request: AdminUserStatusUpdate,
    _current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserDetail:
    """Suspend or reactivate a user account."""
    found = await update_user_status(db, user_id, request.account_status)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    detail = await fetch_admin_user_detail(db, user_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return detail


@router.post("/users/{user_id}/revoke-sessions", status_code=200)
async def revoke_user_sessions_endpoint(
    user_id: uuid.UUID,
    _current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserDetail:
    """Force-logout a user on every device without suspending the account.

    Bumps users.tokens_invalid_before to now(); every access/refresh token with an
    earlier iat is rejected at validation time. Safe to call repeatedly (idempotent
    per call — each invocation moves the cutoff forward). Scoped to role='user' at
    the repository layer to prevent admins from locking themselves out of the console.
    """
    found = await revoke_sessions(db, user_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    detail = await fetch_admin_user_detail(db, user_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return detail


# ---------------------------------------------------------------------------
# Story 5.3: Flagged value report endpoints
# ---------------------------------------------------------------------------


@router.get("/flags", response_model=FlaggedReportListResponse, status_code=200)
async def list_flagged_reports(
    _current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> FlaggedReportListResponse:
    """Return unreviewed flagged value reports."""
    return await fetch_flagged_reports(db)


@router.post(
    "/flags/{health_value_id}/review",
    response_model=FlagReviewedResponse,
    status_code=200,
)
async def mark_flag_as_reviewed(
    health_value_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> FlagReviewedResponse:
    """Mark a flagged value as reviewed. Removes it from the active flag queue."""
    try:
        return await review_flag(db, health_value_id, current_user.id)
    except HealthValueNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flagged value not found",
        ) from err
