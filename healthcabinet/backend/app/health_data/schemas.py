"""API-safe response models for health data retrieval."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HealthValueResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    document_id: uuid.UUID
    biomarker_name: str
    canonical_biomarker_name: str
    value: float
    unit: str | None
    reference_range_low: float | None
    reference_range_high: float | None
    measured_at: datetime | None
    confidence: float
    needs_review: bool
    is_flagged: bool
    flagged_at: datetime | None
    created_at: datetime
    status: Literal["optimal", "borderline", "concerning", "action_needed", "unknown"]


class HealthValueTimelineResponse(BaseModel):
    biomarker_name: str
    canonical_biomarker_name: str
    skipped_corrupt_records: int = 0
    values: list[HealthValueResponse]


class FlagValueResponse(BaseModel):
    id: uuid.UUID
    is_flagged: bool
    flagged_at: datetime | None


class RecommendationItem(BaseModel):
    test_name: str
    rationale: str
    frequency: str
    category: Literal["general", "condition_specific"]


class BaselineSummaryResponse(BaseModel):
    recommendations: list[RecommendationItem]
    has_uploads: bool
