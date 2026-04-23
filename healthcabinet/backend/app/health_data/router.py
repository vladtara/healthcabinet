"""HTTP routes for health values."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.database import get_db
from app.health_data import service
from app.health_data.schemas import (
    BaselineSummaryResponse,
    FlagValueResponse,
    HealthValueResponse,
    HealthValueTimelineResponse,
)

router = APIRouter(prefix="/health-values", tags=["health-data"])


@router.get("/baseline", response_model=BaselineSummaryResponse, status_code=200)
async def get_dashboard_baseline(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BaselineSummaryResponse:
    return await service.get_dashboard_baseline(db, current_user)


@router.get("", response_model=list[HealthValueResponse], status_code=200)
async def get_health_values(
    document_kind: Literal["all", "analysis", "document"] | None = Query(
        default=None,
        description=(
            "Optional dashboard filter. When omitted, all values are returned "
            "(including those owned by 'unknown' documents) for back-compat. "
            "When set, a JOIN to documents restricts the result. 'all' covers "
            "analysis + document and still excludes 'unknown'."
        ),
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[HealthValueResponse]:
    return await service.list_health_values(db, current_user, document_kind=document_kind)


@router.get(
    "/timeline/{canonical_biomarker_name}",
    response_model=HealthValueTimelineResponse,
    status_code=200,
)
async def get_health_value_timeline(
    canonical_biomarker_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HealthValueTimelineResponse:
    return await service.list_health_value_timeline(db, current_user, canonical_biomarker_name)


@router.put(
    "/{health_value_id}/flag",
    response_model=FlagValueResponse,
    status_code=200,
)
async def flag_health_value(
    health_value_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FlagValueResponse:
    return await service.flag_health_value(db, current_user, health_value_id)
