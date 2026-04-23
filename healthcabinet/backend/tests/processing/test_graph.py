"""Unit tests for the LangGraph-backed processing pipeline."""

import json
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.documents.exceptions import DocumentNotFoundError
from app.processing.graph import (
    ProcessingGraphExecutionError,
    _bind_node,
    run_processing_graph,
)
from app.processing.schemas import (
    ExtractionResult,
    NormalizedHealthValue,
    ProcessingGraphFallbackState,
)
from app.processing.tracing import pipeline_trace

_AUTO_USER_ID = object()


def _make_ctx(db_engine=None, redis=None):
    if redis is None:
        redis = MagicMock()
        redis.set = AsyncMock()
        redis.publish = AsyncMock()
    if db_engine is None:
        db_engine = MagicMock()
    return {"db_engine": db_engine, "redis": redis}


def _make_document(*, user_id: uuid.UUID | None | object = _AUTO_USER_ID) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4() if user_id is _AUTO_USER_ID else user_id,
        file_type="application/pdf",
    )


def _make_session_mock() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


def _published_events(redis: MagicMock) -> list[str]:
    return [json.loads(call.args[1])["event"] for call in redis.publish.call_args_list]


def _mock_all_async_sessions() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    load_session = _make_session_mock()
    persist_session = _make_session_mock()
    generate_session = _make_session_mock()
    finalize_session = _make_session_mock()
    return load_session, persist_session, generate_session, finalize_session


@pytest.mark.asyncio
async def test_run_processing_graph_completed_path_with_confident_values():
    doc = _make_document()
    doc_id = str(doc.id)
    redis = MagicMock()
    redis.set = AsyncMock()
    redis.publish = AsyncMock()
    extraction = ExtractionResult(
        measured_at=datetime(2026, 4, 2),
        source_language="en",
        raw_lab_name="Test Lab",
        values=[],
    )
    normalized = [
        NormalizedHealthValue(
            biomarker_name="Glucose",
            canonical_biomarker_name="glucose",
            value=91.0,
            unit="mg/dL",
            reference_range_low=70.0,
            reference_range_high=99.0,
            confidence=0.98,
            needs_review=False,
        )
    ]
    status_updates: list[str] = []
    load_session, persist_session, generate_session, finalize_session = _mock_all_async_sessions()

    async def _update_status(db, document_id, status):
        status_updates.append(status)
        return doc

    update_intelligence_mock = AsyncMock()

    with (
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_by_id_internal",
            new=AsyncMock(side_effect=[doc, doc]),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_s3_key_internal",
            new=AsyncMock(return_value="bucket/key.pdf"),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.has_document_health_values",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.update_document_status_internal",
            side_effect=_update_status,
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_status_internal",
            side_effect=_update_status,
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_intelligence_internal",
            update_intelligence_mock,
        ),
        patch(
            "app.processing.nodes.persist_values.health_data_repository.replace_document_health_values",
            new=AsyncMock(),
        ) as replace_values,
        patch(
            "app.processing.nodes.persist_values.health_data_repository.delete_document_health_values",
            new=AsyncMock(),
        ) as delete_values,
        patch("app.processing.nodes.load_document.get_s3_client", return_value=MagicMock()),
        patch("app.processing.nodes.load_document.get_object_bytes", return_value=b"%PDF-1.4"),
        patch(
            "app.processing.nodes.extract_values.extract_from_document",
            new=AsyncMock(return_value=extraction),
        ),
        patch("app.processing.nodes.extract_values.normalize_extraction_result", return_value=normalized),
        patch("app.ai.repository.invalidate_interpretation", new=AsyncMock()) as invalidate_mock,
        patch("app.ai.service.generate_interpretation", new=AsyncMock(return_value="ok")) as generate_mock,
        patch("app.processing.nodes.load_document.AsyncSession", return_value=load_session),
        patch("app.processing.nodes.persist_values.AsyncSession", return_value=persist_session),
        patch("app.processing.nodes.generate_interpretation.AsyncSession", return_value=generate_session),
        patch("app.processing.nodes.finalize_document.AsyncSession", return_value=finalize_session),
    ):
        final_state = await run_processing_graph(_make_ctx(redis=redis), doc_id)

    assert final_state["terminal_status"] == "completed"
    assert final_state["fallback"].values_committed is True
    assert final_state["fallback"].error_stage is None
    assert _published_events(redis) == [
        "document.upload_started",
        "document.reading",
        "document.extracting",
        "document.generating",
        "document.completed",
    ]
    assert status_updates == ["processing", "completed"]
    replace_values.assert_awaited_once()
    delete_values.assert_not_awaited()
    invalidate_mock.assert_awaited_once()
    generate_mock.assert_awaited_once()
    update_intelligence_mock.assert_awaited_once()
    intel_kwargs = update_intelligence_mock.call_args.kwargs
    assert intel_kwargs["document_kind"] == "analysis"
    assert intel_kwargs["needs_date_confirmation"] is False


@pytest.mark.asyncio
async def test_run_processing_graph_partial_path_with_low_confidence_values():
    doc = _make_document()
    doc_id = str(doc.id)
    redis = MagicMock()
    redis.set = AsyncMock()
    redis.publish = AsyncMock()
    normalized = [
        NormalizedHealthValue(
            biomarker_name="Glucose",
            canonical_biomarker_name="glucose",
            value=91.0,
            unit="mg/dL",
            reference_range_low=None,
            reference_range_high=None,
            confidence=0.6,
            needs_review=True,
        )
    ]
    load_session, persist_session, generate_session, finalize_session = _mock_all_async_sessions()

    with (
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_by_id_internal",
            new=AsyncMock(side_effect=[doc, doc]),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_s3_key_internal",
            new=AsyncMock(return_value="bucket/key.pdf"),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.has_document_health_values",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.update_document_status_internal",
            new=AsyncMock(return_value=doc),
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_status_internal",
            new=AsyncMock(return_value=doc),
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_intelligence_internal",
            new=AsyncMock(),
        ),
        patch(
            "app.processing.nodes.persist_values.health_data_repository.replace_document_health_values",
            new=AsyncMock(),
        ),
        patch(
            "app.processing.nodes.load_document.get_s3_client", return_value=MagicMock()
        ),
        patch("app.processing.nodes.load_document.get_object_bytes", return_value=b"%PDF-1.4"),
        patch(
            "app.processing.nodes.extract_values.extract_from_document",
            new=AsyncMock(return_value=ExtractionResult(values=[])),
        ),
        patch("app.processing.nodes.extract_values.normalize_extraction_result", return_value=normalized),
        patch("app.ai.repository.invalidate_interpretation", new=AsyncMock()),
        patch("app.ai.service.generate_interpretation", new=AsyncMock(return_value="ok")),
        patch("app.processing.nodes.load_document.AsyncSession", return_value=load_session),
        patch("app.processing.nodes.persist_values.AsyncSession", return_value=persist_session),
        patch("app.processing.nodes.generate_interpretation.AsyncSession", return_value=generate_session),
        patch("app.processing.nodes.finalize_document.AsyncSession", return_value=finalize_session),
    ):
        final_state = await run_processing_graph(_make_ctx(redis=redis), doc_id)

    assert final_state["terminal_status"] == "partial"
    assert _published_events(redis)[-1] == "document.partial"


@pytest.mark.asyncio
async def test_run_processing_graph_completes_as_document_when_no_usable_values_and_no_prior_values():
    """AC 2 + AC 4 — successful processing with zero lab values and no prior error stage.

    Terminal status is `completed` and classification is `document` (not `unknown`/`failed`).
    This covers the non-analysis success path: consent forms, referrals, or prints with
    no lab-shaped fields, where the extractor succeeded but produced nothing persistable.
    """
    doc = _make_document()
    doc_id = str(doc.id)
    redis = MagicMock()
    redis.set = AsyncMock()
    redis.publish = AsyncMock()
    load_session, persist_session, finalize_session = (
        _make_session_mock(),
        _make_session_mock(),
        _make_session_mock(),
    )

    invalidate_mock = AsyncMock()
    update_intelligence_mock = AsyncMock()

    with (
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_by_id_internal",
            new=AsyncMock(side_effect=[doc, doc]),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_s3_key_internal",
            new=AsyncMock(return_value="bucket/key.pdf"),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.has_document_health_values",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.update_document_status_internal",
            new=AsyncMock(return_value=doc),
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_status_internal",
            new=AsyncMock(return_value=doc),
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_intelligence_internal",
            update_intelligence_mock,
        ),
        patch(
            "app.processing.nodes.persist_values.health_data_repository.replace_document_health_values",
            new=AsyncMock(),
        ) as replace_values,
        patch(
            "app.processing.nodes.persist_values.health_data_repository.delete_document_health_values",
            new=AsyncMock(),
        ) as delete_values,
        patch("app.processing.nodes.load_document.get_s3_client", return_value=MagicMock()),
        patch("app.processing.nodes.load_document.get_object_bytes", return_value=b"%PDF-1.4"),
        patch(
            "app.processing.nodes.extract_values.extract_from_document",
            new=AsyncMock(return_value=ExtractionResult(values=[])),
        ),
        patch("app.processing.nodes.extract_values.normalize_extraction_result", return_value=[]),
        patch("app.ai.repository.invalidate_interpretation", invalidate_mock),
        patch("app.processing.nodes.load_document.AsyncSession", return_value=load_session),
        patch("app.processing.nodes.persist_values.AsyncSession", return_value=persist_session),
        patch("app.processing.nodes.finalize_document.AsyncSession", return_value=finalize_session),
    ):
        final_state = await run_processing_graph(_make_ctx(redis=redis), doc_id)

    assert final_state["terminal_status"] == "completed"
    assert _published_events(redis)[-1] == "document.completed"
    replace_values.assert_not_awaited()
    delete_values.assert_awaited_once()
    invalidate_mock.assert_not_awaited()
    update_intelligence_mock.assert_awaited_once()
    intel_kwargs = update_intelligence_mock.call_args.kwargs
    assert intel_kwargs["document_kind"] == "document"
    assert intel_kwargs["needs_date_confirmation"] is False
    assert intel_kwargs["partial_measured_at_text"] is None


@pytest.mark.asyncio
async def test_run_processing_graph_retry_with_no_new_values_preserves_partial_state():
    doc = _make_document()
    doc_id = str(doc.id)
    redis = MagicMock()
    redis.set = AsyncMock()
    redis.publish = AsyncMock()
    load_session, persist_session, finalize_session = (
        _make_session_mock(),
        _make_session_mock(),
        _make_session_mock(),
    )
    invalidate_mock = AsyncMock()

    with (
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_by_id_internal",
            new=AsyncMock(side_effect=[doc, doc]),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_s3_key_internal",
            new=AsyncMock(return_value="bucket/key.pdf"),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.has_document_health_values",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.update_document_status_internal",
            new=AsyncMock(return_value=doc),
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_status_internal",
            new=AsyncMock(return_value=doc),
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_intelligence_internal",
            new=AsyncMock(),
        ),
        patch(
            "app.processing.nodes.persist_values.health_data_repository.replace_document_health_values",
            new=AsyncMock(),
        ) as replace_values,
        patch(
            "app.processing.nodes.persist_values.health_data_repository.delete_document_health_values",
            new=AsyncMock(),
        ) as delete_values,
        patch("app.processing.nodes.load_document.get_s3_client", return_value=MagicMock()),
        patch("app.processing.nodes.load_document.get_object_bytes", return_value=b"%PDF-1.4"),
        patch(
            "app.processing.nodes.extract_values.extract_from_document",
            new=AsyncMock(return_value=ExtractionResult(values=[])),
        ),
        patch("app.processing.nodes.extract_values.normalize_extraction_result", return_value=[]),
        patch("app.ai.repository.invalidate_interpretation", invalidate_mock),
        patch("app.processing.nodes.load_document.AsyncSession", return_value=load_session),
        patch("app.processing.nodes.persist_values.AsyncSession", return_value=persist_session),
        patch("app.processing.nodes.finalize_document.AsyncSession", return_value=finalize_session),
    ):
        final_state = await run_processing_graph(_make_ctx(redis=redis), doc_id)

    assert final_state["terminal_status"] == "partial"
    assert final_state["fallback"].prior_values_existed is True
    replace_values.assert_not_awaited()
    delete_values.assert_not_awaited()
    invalidate_mock.assert_not_awaited()
    assert _published_events(redis)[-1] == "document.partial"


@pytest.mark.asyncio
async def test_run_processing_graph_document_not_found_wraps_with_load_context():
    doc_id = str(uuid.uuid4())

    with (
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_by_id_internal",
            new=AsyncMock(side_effect=DocumentNotFoundError()),
        ),
        patch("app.processing.nodes.load_document.AsyncSession", return_value=_make_session_mock()),
        pytest.raises(ProcessingGraphExecutionError) as exc_info,
    ):
        await run_processing_graph(_make_ctx(), doc_id)

    assert exc_info.value.fallback_state.error_stage == "load_document"
    assert exc_info.value.fallback_state.prior_values_existed is False
    assert exc_info.value.fallback_state.values_committed is False


@pytest.mark.asyncio
async def test_run_processing_graph_extraction_failure_preserves_fallback_context():
    doc = _make_document()
    doc_id = str(doc.id)
    redis = MagicMock()
    redis.set = AsyncMock()
    redis.publish = AsyncMock()
    load_session = _make_session_mock()

    with (
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_by_id_internal",
            new=AsyncMock(side_effect=[doc, doc]),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_s3_key_internal",
            new=AsyncMock(return_value="bucket/key.pdf"),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.has_document_health_values",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.update_document_status_internal",
            new=AsyncMock(return_value=doc),
        ),
        patch("app.processing.nodes.load_document.get_s3_client", return_value=MagicMock()),
        patch("app.processing.nodes.load_document.get_object_bytes", return_value=b"%PDF-1.4"),
        patch(
            "app.processing.nodes.extract_values.extract_from_document",
            new=AsyncMock(side_effect=RuntimeError("extract failed")),
        ),
        patch("app.processing.nodes.load_document.AsyncSession", return_value=load_session),
        pytest.raises(ProcessingGraphExecutionError) as exc_info,
    ):
        await run_processing_graph(_make_ctx(redis=redis), doc_id)

    assert exc_info.value.fallback_state.error_stage == "extract_values"
    assert exc_info.value.fallback_state.prior_values_existed is True
    assert exc_info.value.fallback_state.values_committed is False
    assert _published_events(redis) == [
        "document.upload_started",
        "document.reading",
        "document.extracting",
    ]


@pytest.mark.asyncio
async def test_run_processing_graph_missing_user_id_does_not_publish_generating_event():
    doc = _make_document(user_id=None)
    doc_id = str(doc.id)
    redis = MagicMock()
    redis.set = AsyncMock()
    redis.publish = AsyncMock()
    normalized = [
        NormalizedHealthValue(
            biomarker_name="Glucose",
            canonical_biomarker_name="glucose",
            value=91.0,
            unit="mg/dL",
            reference_range_low=70.0,
            reference_range_high=99.0,
            confidence=0.98,
            needs_review=False,
        )
    ]
    load_session, persist_session = _make_session_mock(), _make_session_mock()

    with (
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_by_id_internal",
            new=AsyncMock(side_effect=[doc, doc]),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_s3_key_internal",
            new=AsyncMock(return_value="bucket/key.pdf"),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.has_document_health_values",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.update_document_status_internal",
            new=AsyncMock(return_value=doc),
        ),
        patch(
            "app.processing.nodes.persist_values.health_data_repository.replace_document_health_values",
            new=AsyncMock(),
        ),
        patch("app.processing.nodes.load_document.get_s3_client", return_value=MagicMock()),
        patch("app.processing.nodes.load_document.get_object_bytes", return_value=b"%PDF-1.4"),
        patch(
            "app.processing.nodes.extract_values.extract_from_document",
            new=AsyncMock(return_value=ExtractionResult(values=[])),
        ),
        patch("app.processing.nodes.extract_values.normalize_extraction_result", return_value=normalized),
        patch("app.processing.nodes.load_document.AsyncSession", return_value=load_session),
        patch("app.processing.nodes.persist_values.AsyncSession", return_value=persist_session),
        pytest.raises(ProcessingGraphExecutionError) as exc_info,
    ):
        await run_processing_graph(_make_ctx(redis=redis), doc_id)

    assert exc_info.value.fallback_state.error_stage == "persist_values"
    assert "document.generating" not in _published_events(redis)


@pytest.mark.asyncio
async def test_run_processing_graph_interpretation_failure_after_value_commit_keeps_terminal_status():
    doc = _make_document()
    doc_id = str(doc.id)
    redis = MagicMock()
    redis.set = AsyncMock()
    redis.publish = AsyncMock()
    normalized = [
        NormalizedHealthValue(
            biomarker_name="Glucose",
            canonical_biomarker_name="glucose",
            value=91.0,
            unit="mg/dL",
            reference_range_low=70.0,
            reference_range_high=99.0,
            confidence=0.98,
            needs_review=False,
        )
    ]
    call_order: list[str] = []
    load_session, persist_session, generate_session, finalize_session = _mock_all_async_sessions()

    async def _mock_invalidate(*args, **kwargs):
        call_order.append("invalidate")

    async def _mock_generate(*args, **kwargs):
        call_order.append("generate")
        raise RuntimeError("llm outage")

    with (
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_by_id_internal",
            new=AsyncMock(side_effect=[doc, doc]),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_s3_key_internal",
            new=AsyncMock(return_value="bucket/key.pdf"),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.has_document_health_values",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.update_document_status_internal",
            new=AsyncMock(return_value=doc),
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_status_internal",
            new=AsyncMock(return_value=doc),
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_intelligence_internal",
            new=AsyncMock(),
        ),
        patch(
            "app.processing.nodes.persist_values.health_data_repository.replace_document_health_values",
            new=AsyncMock(),
        ),
        patch("app.processing.nodes.load_document.get_s3_client", return_value=MagicMock()),
        patch("app.processing.nodes.load_document.get_object_bytes", return_value=b"%PDF-1.4"),
        patch(
            "app.processing.nodes.extract_values.extract_from_document",
            new=AsyncMock(return_value=ExtractionResult(values=[])),
        ),
        patch("app.processing.nodes.extract_values.normalize_extraction_result", return_value=normalized),
        patch("app.ai.repository.invalidate_interpretation", side_effect=_mock_invalidate),
        patch("app.ai.service.generate_interpretation", side_effect=_mock_generate),
        patch("app.processing.nodes.load_document.AsyncSession", return_value=load_session),
        patch("app.processing.nodes.persist_values.AsyncSession", return_value=persist_session),
        patch("app.processing.nodes.generate_interpretation.AsyncSession", return_value=generate_session),
        patch("app.processing.nodes.finalize_document.AsyncSession", return_value=finalize_session),
    ):
        final_state = await run_processing_graph(_make_ctx(redis=redis), doc_id)

    assert call_order == ["invalidate", "generate"]
    assert final_state["fallback"].values_committed is True
    assert final_state["terminal_status"] == "completed"
    assert _published_events(redis)[-1] == "document.completed"


@pytest.mark.asyncio
async def test_run_processing_graph_raises_with_fallback_context_after_late_failure():
    doc = _make_document()
    doc_id = str(doc.id)
    normalized = [
        NormalizedHealthValue(
            biomarker_name="Glucose",
            canonical_biomarker_name="glucose",
            value=91.0,
            unit="mg/dL",
            reference_range_low=70.0,
            reference_range_high=99.0,
            confidence=0.98,
            needs_review=False,
        )
    ]
    load_session, persist_session, generate_session, finalize_session = _mock_all_async_sessions()
    update_call_count = 0

    async def _update_status(db, document_id, status):
        nonlocal update_call_count
        update_call_count += 1
        if update_call_count >= 2:
            raise RuntimeError("status write failed")
        return doc

    with (
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_by_id_internal",
            new=AsyncMock(side_effect=[doc, doc]),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_s3_key_internal",
            new=AsyncMock(return_value="bucket/key.pdf"),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.has_document_health_values",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.update_document_status_internal",
            side_effect=_update_status,
        ),
        patch(
            "app.processing.nodes.persist_values.health_data_repository.replace_document_health_values",
            new=AsyncMock(),
        ),
        patch("app.processing.nodes.load_document.get_s3_client", return_value=MagicMock()),
        patch("app.processing.nodes.load_document.get_object_bytes", return_value=b"%PDF-1.4"),
        patch(
            "app.processing.nodes.extract_values.extract_from_document",
            new=AsyncMock(return_value=ExtractionResult(values=[])),
        ),
        patch("app.processing.nodes.extract_values.normalize_extraction_result", return_value=normalized),
        patch("app.ai.repository.invalidate_interpretation", new=AsyncMock()),
        patch("app.ai.service.generate_interpretation", new=AsyncMock(return_value="ok")),
        patch("app.processing.nodes.load_document.AsyncSession", return_value=load_session),
        patch("app.processing.nodes.persist_values.AsyncSession", return_value=persist_session),
        patch("app.processing.nodes.generate_interpretation.AsyncSession", return_value=generate_session),
        patch("app.processing.nodes.finalize_document.AsyncSession", return_value=finalize_session),
        pytest.raises(ProcessingGraphExecutionError) as exc_info,
    ):
        await run_processing_graph(_make_ctx(), doc_id)

    assert exc_info.value.fallback_state.values_committed is True
    assert exc_info.value.fallback_state.prior_values_existed is False
    assert exc_info.value.fallback_state.error_stage == "finalize_document"


@pytest.mark.asyncio
async def test_run_processing_graph_swallows_terminal_publish_failures_after_status_commit():
    doc = _make_document()
    doc_id = str(doc.id)
    redis = MagicMock()
    redis.set = AsyncMock()
    redis.publish = AsyncMock()
    normalized = [
        NormalizedHealthValue(
            biomarker_name="Glucose",
            canonical_biomarker_name="glucose",
            value=91.0,
            unit="mg/dL",
            reference_range_low=70.0,
            reference_range_high=99.0,
            confidence=0.98,
            needs_review=False,
        )
    ]
    status_updates: list[str] = []
    load_session, persist_session, generate_session, finalize_session = _mock_all_async_sessions()

    async def _update_status(db, document_id, status):
        status_updates.append(status)
        return doc

    with (
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_by_id_internal",
            new=AsyncMock(side_effect=[doc, doc]),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.get_document_s3_key_internal",
            new=AsyncMock(return_value="bucket/key.pdf"),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.has_document_health_values",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.processing.nodes.load_document.document_repository.update_document_status_internal",
            side_effect=_update_status,
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_status_internal",
            side_effect=_update_status,
        ),
        patch(
            "app.processing.nodes.finalize_document.document_repository.update_document_intelligence_internal",
            new=AsyncMock(),
        ),
        patch(
            "app.processing.nodes.persist_values.health_data_repository.replace_document_health_values",
            new=AsyncMock(),
        ),
        patch("app.processing.nodes.load_document.get_s3_client", return_value=MagicMock()),
        patch("app.processing.nodes.load_document.get_object_bytes", return_value=b"%PDF-1.4"),
        patch(
            "app.processing.nodes.extract_values.extract_from_document",
            new=AsyncMock(return_value=ExtractionResult(values=[])),
        ),
        patch("app.processing.nodes.extract_values.normalize_extraction_result", return_value=normalized),
        patch("app.ai.repository.invalidate_interpretation", new=AsyncMock()),
        patch("app.ai.service.generate_interpretation", new=AsyncMock(return_value="ok")),
        patch(
            "app.processing.nodes.finalize_document.publish_event",
            new=AsyncMock(side_effect=RuntimeError("redis down")),
        ),
        patch("app.processing.nodes.load_document.AsyncSession", return_value=load_session),
        patch("app.processing.nodes.persist_values.AsyncSession", return_value=persist_session),
        patch("app.processing.nodes.generate_interpretation.AsyncSession", return_value=generate_session),
        patch("app.processing.nodes.finalize_document.AsyncSession", return_value=finalize_session),
    ):
        final_state = await run_processing_graph(_make_ctx(redis=redis), doc_id)

    assert final_state["terminal_status"] == "completed"
    assert final_state["fallback"].error_stage is None
    assert status_updates == ["processing", "completed"]


@pytest.mark.asyncio
async def test_run_processing_graph_wraps_initial_state_errors():
    with pytest.raises(ProcessingGraphExecutionError) as exc_info:
        await run_processing_graph({"redis": MagicMock()}, str(uuid.uuid4()))

    assert exc_info.value.fallback_state.error_stage == "graph_initialization"


@pytest.mark.asyncio
async def test_bind_node_preserves_wrapped_function_name():
    async def sample_node(
        state: dict[str, object],
        fallback_state: ProcessingGraphFallbackState | None = None,
    ) -> dict[str, object]:
        return {"ok": True}

    wrapped = _bind_node(sample_node, ProcessingGraphFallbackState())

    assert wrapped.__name__ == "sample_node"


@pytest.mark.asyncio
async def test_bind_node_preserves_downstream_breadcrumb_set_by_node():
    """A node may deliberately set error_stage/error_message to a value that is NOT
    its own name so a downstream consumer can read a soft-failure breadcrumb.

    The Round-2 fix scopes the clear-on-success to markers matching the node's
    own __name__. Any other value must survive past the wrapper so downstream
    logic sees it intact.
    """
    fallback_state = ProcessingGraphFallbackState()

    async def fake_node(state, fb):
        fb.error_stage = "downstream_hint"
        fb.error_message = "soft-failure recovered"
        return {"ok": True}

    # node.__name__ is "fake_node" — distinct from "downstream_hint", so the
    # wrapper must NOT clear the fields.
    wrapped = _bind_node(fake_node, fallback_state)
    await wrapped({})

    assert fallback_state.error_stage == "downstream_hint"
    assert fallback_state.error_message == "soft-failure recovered"


@pytest.mark.asyncio
async def test_bind_node_clears_when_node_stamped_its_own_name():
    """Regression guard for the Round-1.5 behavior: when a node follows the
    standard stamp-on-entry pattern (error_stage = <own __name__>) and
    returns normally, the wrapper must clear both fields so finalize_document
    can distinguish 'previous stage completed cleanly' from 'errored'.
    """
    fallback_state = ProcessingGraphFallbackState()

    async def sample_stage(state, fb):
        # Real nodes do this as the first line after entering.
        fb.error_stage = "sample_stage"
        fb.error_message = None
        return {"ok": True}

    wrapped = _bind_node(sample_stage, fallback_state)
    await wrapped({})

    assert fallback_state.error_stage is None
    assert fallback_state.error_message is None


@pytest.mark.asyncio
async def test_pipeline_trace_invokes_langsmith_when_enabled():
    with (
        patch("app.processing.tracing.settings") as mock_settings,
        patch("app.processing.tracing.langsmith_trace") as mock_trace,
    ):
        mock_settings.LANGSMITH_TRACING = True
        mock_settings.LANGSMITH_PROJECT = "test-project"
        mock_trace_ctx = MagicMock()
        mock_trace_ctx.__enter__ = MagicMock(return_value=mock_trace_ctx)
        mock_trace_ctx.__exit__ = MagicMock(return_value=False)
        mock_trace.return_value = mock_trace_ctx

        async with pipeline_trace(document_id="doc-123", document_type="application/pdf"):
            pass

        mock_trace.assert_called_once_with(
            name="document_extraction_pipeline",
            run_type="chain",
            project_name="test-project",
            metadata={
                "document_id": "doc-123",
                "document_type": "application/pdf",
            },
            tags=["extraction", "application/pdf"],
        )


@pytest.mark.asyncio
async def test_pipeline_trace_skips_langsmith_when_disabled():
    with (
        patch("app.processing.tracing.is_tracing_enabled", return_value=False),
        patch("app.processing.tracing.langsmith_trace") as mock_trace,
    ):
        async with pipeline_trace(document_id="doc-123", document_type="application/pdf"):
            pass

        mock_trace.assert_not_called()
