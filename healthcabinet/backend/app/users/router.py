from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.auth.repository import list_consent_logs_by_user_desc
from app.core.config import settings
from app.core.database import get_db
from app.documents.storage import get_s3_client
from app.users.export_service import build_export_zip
from app.users.schemas import (
    ConsentHistoryResponse,
    OnboardingStepRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.users.service import (
    delete_user_account,
    get_profile,
    save_onboarding_progress,
    update_profile,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/profile", response_model=ProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    profile = await get_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return ProfileResponse.model_validate(profile)


@router.put("/me/profile", response_model=ProfileResponse)
async def update_my_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    profile = await update_profile(db, current_user.id, data)
    return ProfileResponse.model_validate(profile)


@router.patch("/me/onboarding-step", status_code=status.HTTP_200_OK)
async def save_onboarding_step(
    data: OnboardingStepRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    await save_onboarding_progress(db, current_user.id, data.step)
    return {"ok": True}


@router.post("/me/export")
async def export_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export all user data as a ZIP archive (GDPR Article 20)."""
    s3_client = get_s3_client()
    try:
        buffer = await build_export_zip(db, current_user, s3_client, settings.MINIO_BUCKET)
    finally:
        close = getattr(s3_client, "close", None)
        if callable(close):
            close()
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="healthcabinet-export-{date_str}.zip"'
        },
    )


@router.get(
    "/me/consent-history",
    response_model=ConsentHistoryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_consent_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsentHistoryResponse:
    """Return the authenticated user's consent log history (GDPR transparency)."""
    logs = await list_consent_logs_by_user_desc(db, current_user.id)
    return ConsentHistoryResponse(items=logs)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Permanently delete user account and all associated data (GDPR Article 17)."""
    arq_redis = getattr(request.app.state, "arq_redis", None)
    await delete_user_account(db, current_user.id, arq_redis=arq_redis)
