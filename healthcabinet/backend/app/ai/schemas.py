"""Pydantic schemas for AI interpretation API responses."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

# Story 15.3 — dashboard filter scope. 'unknown' is deliberately excluded from
# this Literal so Pydantic 422s any attempt to query the dashboard over
# unreadable/failed classifications.
DashboardKind = Literal["all", "analysis", "document"]


class ValueReasoning(BaseModel):
    name: str
    value: float
    unit: str | None
    ref_low: float | None
    ref_high: float | None
    status: Literal["normal", "high", "low", "unknown"]


class ReasoningContext(BaseModel):
    values_referenced: list[ValueReasoning]
    uncertainty_flags: list[str]
    prior_documents_referenced: list[str]


class AiChatRequest(BaseModel):
    document_id: uuid.UUID
    question: Annotated[str, Field(min_length=1, max_length=1000)]
    locale: Literal["en", "uk"] = "en"


class AiInterpretationResponse(BaseModel):
    document_id: uuid.UUID
    interpretation: str
    model_version: str | None
    generated_at: datetime
    reasoning: ReasoningContext | None = None


class DashboardChatRequest(BaseModel):
    document_kind: DashboardKind
    question: Annotated[str, Field(min_length=1, max_length=1000)]
    locale: Literal["en", "uk"] = "en"


class DashboardInterpretationResponse(BaseModel):
    """Aggregate interpretation spanning every contributing document for a filter.

    document_id is always None — the aggregate is not owned by a single
    document. source_document_ids lists the contributing per-document rows so
    callers can show provenance without the frontend needing a second fetch.
    """

    document_id: uuid.UUID | None = None
    document_kind: DashboardKind
    source_document_ids: list[uuid.UUID]
    interpretation: str
    model_version: str | None
    generated_at: datetime
    reasoning: ReasoningContext | None = None


class PatternObservation(BaseModel):
    description: str
    document_dates: list[str]
    recommendation: str


class AiPatternsResponse(BaseModel):
    patterns: list[PatternObservation]


ChatMessageRole = Literal["user", "assistant"]


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    role: ChatMessageRole
    text: str
    created_at: datetime


class ChatMessageListResponse(BaseModel):
    messages: list[ChatMessageResponse]
    has_more: bool
    next_cursor: uuid.UUID | None = None
