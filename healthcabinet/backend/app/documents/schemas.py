import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

# Allowlist mirrors frontend ACCEPTED_TYPES. Only PDF and images are permitted.
# Prevents arbitrary MIME types from being embedded in presigned URL signatures.
_ALLOWED_FILE_TYPE_PREFIXES = ("image/",)
_ALLOWED_FILE_TYPES_EXACT = frozenset({"application/pdf"})


class UploadUrlRequest(BaseModel):
    filename: str
    file_size_bytes: int
    file_type: str

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v: str) -> str:
        if v in _ALLOWED_FILE_TYPES_EXACT or v.startswith(_ALLOWED_FILE_TYPE_PREFIXES):
            return v
        raise ValueError(f"Unsupported file type '{v}': only PDF and images are accepted.")


class UploadUrlResponse(BaseModel):
    upload_url: str
    document_id: uuid.UUID


DocumentStatus = Literal["pending", "processing", "completed", "partial", "failed"]
DocumentKind = Literal["analysis", "document", "unknown"]


class DocumentResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    filename: str
    file_size_bytes: int
    file_type: str
    status: DocumentStatus
    arq_job_id: str | None
    keep_partial: bool | None
    # Document intelligence metadata (Story 15.2)
    document_kind: DocumentKind
    needs_date_confirmation: bool
    partial_measured_at_text: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentDetailResponse(BaseModel):
    """Single document with its extracted health values."""

    id: uuid.UUID
    filename: str
    file_size_bytes: int
    file_type: str
    status: DocumentStatus
    arq_job_id: str | None
    keep_partial: bool | None
    # Document intelligence metadata (Story 15.2)
    document_kind: DocumentKind
    needs_date_confirmation: bool
    partial_measured_at_text: str | None
    created_at: datetime
    updated_at: datetime
    health_values: list["HealthValueItem"]

    model_config = {"from_attributes": True}


class HealthValueItem(BaseModel):
    id: uuid.UUID
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

    model_config = {"from_attributes": True}


class DeleteResponse(BaseModel):
    deleted: bool


class NotifyUploadRequest(BaseModel):
    pass


class KeepPartialResponse(BaseModel):
    kept: bool


# Story 15.2 — year-confirmation contract.
# Year bounds are an inclusive defensible range: clinical lab timestamps below
# 1900 are implausible for a consumer health application, and a year greater than
# the current UTC year is a client-side entry mistake. The check runs at the
# service layer so we can surface a single RFC 7807 problem response; Pydantic
# keeps the field a plain int here to avoid conflating transport validation with
# business validation.
class ConfirmDateYearRequest(BaseModel):
    # strict=True rejects float/str coercion. Without it, Pydantic v2 would
    # silently accept e.g. `{"year": 2026.9}` and truncate to 2026, which would
    # let a client error slip through as if it were a clean integer.
    year: Annotated[int, Field(strict=True)]

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        # Minimum bound only; the service enforces the upper bound against the
        # current UTC year so the check stays deterministic even if the clock
        # ticks over mid-request.
        if v < 1900:
            raise ValueError("year must be >= 1900")
        return v
