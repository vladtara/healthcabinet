"""Processing schemas for document extraction and SSE status events."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypedDict

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine


class DocumentStatusEvent(BaseModel):
    event: str
    document_id: str
    progress: float  # 0.0–1.0
    message: str


class ExtractedHealthValue(BaseModel):
    biomarker_name: str = Field(min_length=1)
    value: float
    unit: str | None = None
    reference_range_low: float | None = None
    reference_range_high: float | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractionResult(BaseModel):
    measured_at: datetime | None = None
    # Story 15.2 — raw day/month fragment recovered from the document when the
    # year is not visible. The extractor MUST NOT invent a year. Downstream
    # code treats this as opaque text and re-parses at confirmation time.
    partial_measured_at_text: str | None = None
    source_language: str | None = None
    raw_lab_name: str | None = None
    values: list[ExtractedHealthValue] = Field(default_factory=list)


class NormalizedHealthValue(BaseModel):
    biomarker_name: str = Field(min_length=1)
    canonical_biomarker_name: str = Field(min_length=1)
    value: float
    unit: str | None = None
    reference_range_low: float | None = None
    reference_range_high: float | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    needs_review: bool = False


class DocumentProcessingState(BaseModel):
    document_id: uuid.UUID
    user_id: uuid.UUID
    measured_at: datetime | None = None
    partial_measured_at_text: str | None = None
    source_language: str | None = None
    raw_lab_name: str | None = None
    values: list[NormalizedHealthValue] = Field(default_factory=list)

    @property
    def has_values(self) -> bool:
        return bool(self.values)

    @property
    def low_confidence_count(self) -> int:
        return sum(1 for value in self.values if value.needs_review)


TerminalDocumentStatus = Literal["completed", "failed", "partial"]
TerminalDocumentEvent = Literal["document.completed", "document.failed", "document.partial"]


@dataclass(slots=True)
class ProcessingGraphRuntime:
    db_engine: AsyncEngine
    redis: object


@dataclass(slots=True)
class ProcessingGraphFallbackState:
    prior_values_existed: bool = False
    values_committed: bool = False
    error_stage: str | None = None
    error_message: str | None = None


class ProcessingGraphState(TypedDict):
    runtime: ProcessingGraphRuntime
    fallback: ProcessingGraphFallbackState
    document_id: uuid.UUID
    document_id_str: str
    user_id: uuid.UUID | None
    document_mime_type: str | None
    s3_key: str | None
    document_bytes: bytes | None
    extraction_result: ExtractionResult | None
    normalized_values: list[NormalizedHealthValue]
    measured_at: datetime | None
    partial_measured_at_text: str | None
    source_language: str | None
    raw_lab_name: str | None
    terminal_status: TerminalDocumentStatus | None
    terminal_event: TerminalDocumentEvent | None


# Maps event name → (human-readable message, progress value)
STAGE_MESSAGES: dict[str, tuple[str, float]] = {
    "document.upload_started": ("Upload received, starting processing…", 0.0),
    "document.reading": ("Reading document…", 0.25),
    "document.extracting": ("Extracting health values…", 0.5),
    "document.generating": ("Generating insights…", 0.75),
    "document.completed": ("Processing complete", 1.0),
    "document.failed": ("Processing failed", 0.0),
    "document.partial": ("Partial extraction — some values need review", 1.0),
}
