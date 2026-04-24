"""Unit tests for the finalize_document node classification + status rules.

Story 15.2 — covers:
- AC 2: deterministic classification from persisted extraction state.
- AC 3: yearless-date extraction does not fabricate timestamps.
- AC 4: terminal status reflects unresolved year confirmation.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.processing.nodes.finalize_document import finalize_document
from app.processing.schemas import (
    NormalizedHealthValue,
    ProcessingGraphFallbackState,
    ProcessingGraphRuntime,
    ProcessingGraphState,
)


def _make_session_mock() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


def _make_state(
    *,
    normalized_values: list[NormalizedHealthValue] | None = None,
    measured_at: datetime | None = None,
    partial_measured_at_text: str | None = None,
    prior_values_existed: bool = False,
    error_stage: str | None = None,
) -> tuple[ProcessingGraphState, ProcessingGraphFallbackState]:
    fallback = ProcessingGraphFallbackState(
        prior_values_existed=prior_values_existed,
        error_stage=error_stage,
    )
    state: ProcessingGraphState = {
        "runtime": ProcessingGraphRuntime(db_engine=MagicMock(), redis=MagicMock()),
        "fallback": fallback,
        "document_id": uuid.uuid4(),
        "document_id_str": "doc-1",
        "user_id": uuid.uuid4(),
        "document_mime_type": "application/pdf",
        "s3_key": None,
        "document_bytes": None,
        "extraction_result": None,
        "normalized_values": normalized_values or [],
        "measured_at": measured_at,
        "partial_measured_at_text": partial_measured_at_text,
        "source_language": None,
        "raw_lab_name": None,
        "terminal_status": None,
        "terminal_event": None,
    }
    return state, fallback


def _make_value(*, needs_review: bool = False) -> NormalizedHealthValue:
    return NormalizedHealthValue(
        biomarker_name="Glucose",
        canonical_biomarker_name="glucose",
        value=91.0,
        unit="mg/dL",
        reference_range_low=70.0,
        reference_range_high=99.0,
        confidence=0.95,
        needs_review=needs_review,
    )


@pytest.mark.asyncio
async def test_finalize_classifies_analysis_with_full_date():
    """AC 2 — persisted lab values with a full date produce `analysis` + `completed`."""
    state, fallback = _make_state(
        normalized_values=[_make_value()],
        measured_at=datetime(2026, 4, 19, tzinfo=UTC),
        partial_measured_at_text=None,
    )
    fallback.error_stage = None

    intelligence_calls: list[dict] = []
    status_updates: list[str] = []

    async def _record_intelligence(db, document_id, **kwargs):
        intelligence_calls.append(kwargs)

    async def _record_status(db, document_id, status):
        status_updates.append(status)

    with (
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_intelligence_internal",
            side_effect=_record_intelligence,
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_status_internal",
            side_effect=_record_status,
        ),
        patch(
            "app.processing.nodes.finalize_document.AsyncSession", return_value=_make_session_mock()
        ),
        patch("app.processing.nodes.finalize_document.publish_event", new=AsyncMock()),
    ):
        result = await finalize_document(state, fallback)

    assert result == {"terminal_event": "document.completed", "terminal_status": "completed"}
    assert len(intelligence_calls) == 1
    assert intelligence_calls[0]["document_kind"] == "analysis"
    assert intelligence_calls[0]["needs_date_confirmation"] is False
    assert intelligence_calls[0]["partial_measured_at_text"] is None
    assert status_updates == ["completed"]


@pytest.mark.asyncio
async def test_finalize_classifies_analysis_with_yearless_date_as_partial():
    """AC 3, 4 — yearless date persists raw fragment and forces `partial` terminal status."""
    state, fallback = _make_state(
        normalized_values=[_make_value()],
        measured_at=None,
        partial_measured_at_text="12.03",
    )
    fallback.error_stage = None

    intelligence_calls: list[dict] = []
    status_updates: list[str] = []

    async def _record_intelligence(db, document_id, **kwargs):
        intelligence_calls.append(kwargs)

    async def _record_status(db, document_id, status):
        status_updates.append(status)

    with (
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_intelligence_internal",
            side_effect=_record_intelligence,
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_status_internal",
            side_effect=_record_status,
        ),
        patch(
            "app.processing.nodes.finalize_document.AsyncSession", return_value=_make_session_mock()
        ),
        patch("app.processing.nodes.finalize_document.publish_event", new=AsyncMock()),
    ):
        result = await finalize_document(state, fallback)

    assert result == {"terminal_event": "document.partial", "terminal_status": "partial"}
    assert intelligence_calls[0]["document_kind"] == "analysis"
    assert intelligence_calls[0]["needs_date_confirmation"] is True
    assert intelligence_calls[0]["partial_measured_at_text"] == "12.03"
    assert status_updates == ["partial"]


@pytest.mark.asyncio
async def test_finalize_classifies_document_when_no_values_but_processing_succeeded():
    """AC 2 — successful processing with no usable lab values => `document` + `completed`."""
    state, fallback = _make_state(
        normalized_values=[], measured_at=None, partial_measured_at_text=None
    )
    fallback.error_stage = None

    intelligence_calls: list[dict] = []
    status_updates: list[str] = []

    async def _record_intelligence(db, document_id, **kwargs):
        intelligence_calls.append(kwargs)

    async def _record_status(db, document_id, status):
        status_updates.append(status)

    with (
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_intelligence_internal",
            side_effect=_record_intelligence,
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_status_internal",
            side_effect=_record_status,
        ),
        patch(
            "app.processing.nodes.finalize_document.AsyncSession", return_value=_make_session_mock()
        ),
        patch("app.processing.nodes.finalize_document.publish_event", new=AsyncMock()),
    ):
        result = await finalize_document(state, fallback)

    assert result == {"terminal_event": "document.completed", "terminal_status": "completed"}
    assert intelligence_calls[0]["document_kind"] == "document"
    assert intelligence_calls[0]["needs_date_confirmation"] is False
    assert intelligence_calls[0]["partial_measured_at_text"] is None
    assert status_updates == ["completed"]


@pytest.mark.asyncio
async def test_finalize_classifies_unknown_when_processing_failed_and_no_prior_values():
    """AC 2 — fresh processing failure with no prior persisted values => `unknown` + `failed`."""
    state, fallback = _make_state(
        normalized_values=[],
        measured_at=None,
        partial_measured_at_text=None,
        prior_values_existed=False,
        error_stage="extract_values",  # indicates the extractor failed earlier
    )

    intelligence_calls: list[dict] = []
    status_updates: list[str] = []

    async def _record_intelligence(db, document_id, **kwargs):
        intelligence_calls.append(kwargs)

    async def _record_status(db, document_id, status):
        status_updates.append(status)

    with (
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_intelligence_internal",
            side_effect=_record_intelligence,
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_status_internal",
            side_effect=_record_status,
        ),
        patch(
            "app.processing.nodes.finalize_document.AsyncSession", return_value=_make_session_mock()
        ),
        patch("app.processing.nodes.finalize_document.publish_event", new=AsyncMock()),
    ):
        result = await finalize_document(state, fallback)

    assert result == {"terminal_event": "document.failed", "terminal_status": "failed"}
    assert intelligence_calls[0]["document_kind"] == "unknown"
    assert intelligence_calls[0]["needs_date_confirmation"] is False
    assert status_updates == ["failed"]


@pytest.mark.asyncio
async def test_finalize_retries_with_prior_values_preserves_analysis_classification():
    """Retry with no new values + persisted prior values => `analysis` + `partial` (existing rule preserved)."""
    state, fallback = _make_state(
        normalized_values=[],
        measured_at=None,
        partial_measured_at_text=None,
        prior_values_existed=True,
    )
    fallback.error_stage = None

    intelligence_calls: list[dict] = []
    status_updates: list[str] = []

    async def _record_intelligence(db, document_id, **kwargs):
        intelligence_calls.append(kwargs)

    async def _record_status(db, document_id, status):
        status_updates.append(status)

    with (
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_intelligence_internal",
            side_effect=_record_intelligence,
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_status_internal",
            side_effect=_record_status,
        ),
        patch(
            "app.processing.nodes.finalize_document.AsyncSession", return_value=_make_session_mock()
        ),
        patch("app.processing.nodes.finalize_document.publish_event", new=AsyncMock()),
    ):
        result = await finalize_document(state, fallback)

    assert result == {"terminal_event": "document.partial", "terminal_status": "partial"}
    # persisted-values-existed signal keeps classification as analysis even on empty re-extraction
    assert intelligence_calls[0]["document_kind"] == "analysis"
    assert status_updates == ["partial"]


@pytest.mark.asyncio
async def test_finalize_document_recomputes_classification_on_reprocess():
    """Reprocessing: classification must reflect the new state, not a cached prior one.

    First invocation: analysis (persisted lab values present).
    Second invocation: document (no values, no prior values, no prior error stage).
    The second call's intelligence kwargs must carry `document_kind="document"`,
    proving the finalizer doesn't leak state across runs.
    """
    intelligence_calls: list[dict] = []
    status_updates: list[str] = []

    async def _record_intelligence(db, document_id, **kwargs):
        intelligence_calls.append(kwargs)

    async def _record_status(db, document_id, status):
        status_updates.append(status)

    # First pass: analysis / completed.
    state_a, fallback_a = _make_state(
        normalized_values=[_make_value()],
        measured_at=datetime(2026, 4, 19, tzinfo=UTC),
        partial_measured_at_text=None,
    )
    fallback_a.error_stage = None

    with (
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_intelligence_internal",
            side_effect=_record_intelligence,
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_status_internal",
            side_effect=_record_status,
        ),
        patch(
            "app.processing.nodes.finalize_document.AsyncSession", return_value=_make_session_mock()
        ),
        patch("app.processing.nodes.finalize_document.publish_event", new=AsyncMock()),
    ):
        await finalize_document(state_a, fallback_a)

    assert intelligence_calls[-1]["document_kind"] == "analysis"

    # Reset captures so we can assert against the SECOND call in isolation.
    intelligence_calls.clear()
    status_updates.clear()

    # Second pass: document / completed (no values, no prior values, no prior error).
    state_b, fallback_b = _make_state(
        normalized_values=[],
        measured_at=None,
        partial_measured_at_text=None,
        prior_values_existed=False,
    )
    fallback_b.error_stage = None

    with (
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_intelligence_internal",
            side_effect=_record_intelligence,
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_status_internal",
            side_effect=_record_status,
        ),
        patch(
            "app.processing.nodes.finalize_document.AsyncSession", return_value=_make_session_mock()
        ),
        patch("app.processing.nodes.finalize_document.publish_event", new=AsyncMock()),
    ):
        result = await finalize_document(state_b, fallback_b)

    assert result["terminal_status"] == "completed"
    assert intelligence_calls[0]["document_kind"] == "document"
    assert intelligence_calls[0]["needs_date_confirmation"] is False
    assert status_updates == ["completed"]


@pytest.mark.asyncio
async def test_finalize_low_confidence_values_still_partial_even_with_full_date():
    """Existing AC (preserved): low-confidence values force `partial` independent of date state."""
    state, fallback = _make_state(
        normalized_values=[_make_value(needs_review=True)],
        measured_at=datetime(2026, 4, 19, tzinfo=UTC),
        partial_measured_at_text=None,
    )
    fallback.error_stage = None

    status_updates: list[str] = []

    async def _record_status(db, document_id, status):
        status_updates.append(status)

    with (
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_intelligence_internal",
            new=AsyncMock(),
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_status_internal",
            side_effect=_record_status,
        ),
        patch(
            "app.processing.nodes.finalize_document.AsyncSession", return_value=_make_session_mock()
        ),
        patch("app.processing.nodes.finalize_document.publish_event", new=AsyncMock()),
    ):
        result = await finalize_document(state, fallback)

    assert result["terminal_status"] == "partial"
    assert status_updates == ["partial"]
