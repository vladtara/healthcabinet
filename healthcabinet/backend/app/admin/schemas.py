from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, StringConstraints

CorrectionReason = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1000),
]


class PlatformMetricsResponse(BaseModel):
    total_signups: int
    total_uploads: int
    upload_success_rate: float | None
    documents_error_or_partial: int
    ai_interpretation_completion_rate: float | None


class ErrorQueueItem(BaseModel):
    document_id: UUID
    user_id: UUID
    filename: str
    upload_date: str
    status: str
    value_count: int
    low_confidence_count: int
    flagged_count: int
    failed: bool


class ErrorQueueResponse(BaseModel):
    items: list[ErrorQueueItem]
    total: int


class DocumentHealthValueDetail(BaseModel):
    id: UUID
    biomarker_name: str
    canonical_biomarker_name: str
    value: float
    unit: str | None
    reference_range_low: float | None
    reference_range_high: float | None
    confidence: float
    needs_review: bool
    is_flagged: bool
    flagged_at: str | None


class DocumentQueueDetail(BaseModel):
    document_id: UUID
    user_id: UUID
    filename: str
    upload_date: str
    status: str
    values: list[DocumentHealthValueDetail]


class CorrectionRequest(BaseModel):
    new_value: float
    reason: CorrectionReason


class CorrectionResponse(BaseModel):
    audit_log_id: UUID
    health_value_id: UUID
    value_name: str
    original_value: float
    new_value: float
    corrected_at: str


# --- Story 5.3: Admin user management & flag review schemas ---


class AdminUserListItem(BaseModel):
    user_id: UUID
    email: str
    registration_date: str
    upload_count: int
    account_status: str


class AdminUserListResponse(BaseModel):
    items: list[AdminUserListItem]
    total: int


class AdminUserDetail(BaseModel):
    user_id: UUID
    email: str
    registration_date: str
    last_login: str | None
    upload_count: int
    account_status: str


class AdminUserStatusUpdate(BaseModel):
    account_status: Literal["active", "suspended"]


class FlaggedReportItem(BaseModel):
    health_value_id: UUID
    user_id: UUID
    document_id: UUID
    value_name: str
    flagged_value: float
    flagged_at: str | None


class FlaggedReportListResponse(BaseModel):
    items: list[FlaggedReportItem]
    total: int


class FlagReviewedResponse(BaseModel):
    health_value_id: UUID
    reviewed_at: str
