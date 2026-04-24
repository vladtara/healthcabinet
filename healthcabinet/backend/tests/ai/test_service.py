"""Tests for AI reasoning context construction and follow-up Q&A streaming."""

import contextlib
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.safety import _DISCLAIMER
from app.ai.service import AiServiceUnavailableError, stream_follow_up_answer
from app.processing.schemas import NormalizedHealthValue


@contextlib.contextmanager
def _mock_chat_persistence():
    """Patch the chat-persistence repo calls that stream_follow_up_answer /
    stream_dashboard_follow_up make. Existing service tests use db=AsyncMock(),
    which can't execute real SQL for profile/history lookups. These patches
    keep those tests focused on stream/safety behavior without needing a DB.
    """
    with (
        patch(
            "app.ai.service.users_repository.get_profile_context",
            AsyncMock(return_value=None),
        ),
        patch(
            "app.ai.service.ai_repository.list_chat_messages",
            AsyncMock(return_value=[]),
        ),
        patch(
            "app.ai.service.ai_repository.append_chat_message",
            AsyncMock(),
        ),
        patch(
            "app.ai.service.ai_repository.get_overall_interpretation",
            AsyncMock(return_value=None),
        ),
    ):
        yield


def _value(
    *,
    name: str,
    value: float,
    ref_low: float | None,
    ref_high: float | None,
) -> NormalizedHealthValue:
    return NormalizedHealthValue(
        biomarker_name=name,
        canonical_biomarker_name=name,
        value=value,
        unit="mg/dL",
        reference_range_low=ref_low,
        reference_range_high=ref_high,
        confidence=0.98,
        needs_review=False,
    )


def test_build_reasoning_context_assigns_statuses_and_uncertainty():
    from app.ai.service import _build_reasoning_context

    reasoning = _build_reasoning_context(
        [
            _value(name="Glucose", value=91.0, ref_low=70.0, ref_high=99.0),
            _value(name="LDL", value=145.0, ref_low=0.0, ref_high=130.0),
            _value(name="Ferritin", value=18.0, ref_low=30.0, ref_high=400.0),
            _value(name="HbA1c", value=5.7, ref_low=None, ref_high=None),
            _value(name="Triglycerides", value=120.0, ref_low=0.0, ref_high=None),
        ]
    )

    assert reasoning["values_referenced"] == [
        {
            "name": "Glucose",
            "value": 91.0,
            "unit": "mg/dL",
            "ref_low": 70.0,
            "ref_high": 99.0,
            "status": "normal",
        },
        {
            "name": "LDL",
            "value": 145.0,
            "unit": "mg/dL",
            "ref_low": 0.0,
            "ref_high": 130.0,
            "status": "high",
        },
        {
            "name": "Ferritin",
            "value": 18.0,
            "unit": "mg/dL",
            "ref_low": 30.0,
            "ref_high": 400.0,
            "status": "low",
        },
        {
            "name": "HbA1c",
            "value": 5.7,
            "unit": "mg/dL",
            "ref_low": None,
            "ref_high": None,
            "status": "unknown",
        },
        {
            "name": "Triglycerides",
            "value": 120.0,
            "unit": "mg/dL",
            "ref_low": 0.0,
            "ref_high": None,
            "status": "unknown",
        },
    ]
    assert reasoning["uncertainty_flags"] == ["Insufficient data to interpret HbA1c confidently"]
    assert reasoning["prior_documents_referenced"] == []


@pytest.mark.asyncio
async def test_generate_interpretation_uses_adapter_and_configured_model_version():
    from app.ai.service import generate_interpretation

    values = [_value(name="Glucose", value=91.0, ref_low=70.0, ref_high=99.0)]

    async def _identity_text(text: str) -> str:
        return text

    async def _identity_with_values(text: str, _values: list[NormalizedHealthValue]) -> str:
        return text

    with (
        patch("app.ai.service.call_model_text", AsyncMock(return_value="Plain language summary.")),
        patch("app.ai.service.validate_no_diagnostic", AsyncMock(side_effect=_identity_text)),
        patch("app.ai.service.surface_uncertainty", AsyncMock(side_effect=_identity_with_values)),
        patch("app.ai.service.inject_disclaimer", AsyncMock(side_effect=_identity_text)),
        patch("app.ai.service.get_model_name", return_value="test-model"),
        patch("app.ai.service.ai_repository.upsert_ai_interpretation", AsyncMock()) as upsert_mock,
    ):
        result = await generate_interpretation(
            db=AsyncMock(),
            document_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            values=values,
        )

    assert result == "Plain language summary."
    assert upsert_mock.await_args.kwargs["model_version"] == "test-model"


@pytest.mark.asyncio
async def test_generate_interpretation_returns_none_on_temporary_unavailability():
    import app.ai.service as ai_service
    from app.ai.service import generate_interpretation

    values = [_value(name="Glucose", value=91.0, ref_low=70.0, ref_high=99.0)]

    with (
        patch(
            "app.ai.service.call_model_text",
            AsyncMock(side_effect=ai_service.ModelTemporaryUnavailableError("busy")),
        ),
        patch("app.ai.service.ai_repository.upsert_ai_interpretation", AsyncMock()) as upsert_mock,
    ):
        result = await generate_interpretation(
            db=AsyncMock(),
            document_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            values=values,
        )

    assert result is None
    upsert_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_interpretation_returns_none_on_safety_failure():
    from app.ai.safety import SafetyValidationError
    from app.ai.service import generate_interpretation

    values = [_value(name="Glucose", value=91.0, ref_low=70.0, ref_high=99.0)]

    with (
        patch("app.ai.service.call_model_text", AsyncMock(return_value="You have diabetes.")),
        patch(
            "app.ai.service.validate_no_diagnostic",
            AsyncMock(side_effect=SafetyValidationError("diagnostic")),
        ),
        patch("app.ai.service.ai_repository.upsert_ai_interpretation", AsyncMock()) as upsert_mock,
    ):
        result = await generate_interpretation(
            db=AsyncMock(),
            document_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            values=values,
        )

    assert result is None
    upsert_mock.assert_not_awaited()


# ──────────────────────────────────────────────────────────────────────────────
# Tests for stream_follow_up_answer (AC: #1, #2, #3)
# ──────────────────────────────────────────────────────────────────────────────


def test_build_follow_up_prompt_includes_prior_documents_referenced():
    from app.ai.service import _build_follow_up_prompt

    row = {
        "document_id": "doc-1",
        "interpretation": "Your glucose is normal.",
        "reasoning": {
            "values_referenced": [],
            "uncertainty_flags": [],
            "prior_documents_referenced": ["doc-2", "doc-3"],
        },
    }
    prompt = _build_follow_up_prompt([row], "What does this mean?")
    assert "Referenced: doc-2, doc-3" in prompt


def test_build_follow_up_prompt_labels_non_active_document_correctly():
    import uuid

    from app.ai.service import _build_follow_up_prompt

    active_doc_id = uuid.uuid4()
    other_doc_id = uuid.uuid4()

    row = {
        "document_id": str(other_doc_id),
        "interpretation": "Some other interpretation.",
    }
    prompt = _build_follow_up_prompt([row], "Question?", active_document_id=active_doc_id)
    assert "[Active document]" not in prompt
    assert "[Previous document 1]" in prompt


def test_build_follow_up_prompt_degrades_on_malformed_reasoning():
    from app.ai.service import _build_follow_up_prompt

    row = {
        "document_id": "doc-1",
        "interpretation": "Your glucose is normal.",
        "reasoning": {
            "values_referenced": 42,
            "uncertainty_flags": "not-a-list",
            "prior_documents_referenced": None,
        },
    }
    # Must not raise; interpretation text should still appear
    prompt = _build_follow_up_prompt([row], "Question?")
    assert "Your glucose is normal." in prompt


def _make_context_row(
    doc_id: str = "doc-1", interpretation: str = "Your glucose is normal."
) -> dict:
    return {
        "document_id": doc_id,
        "interpretation": interpretation,
        "reasoning": {
            "values_referenced": [
                {"name": "Glucose", "value": 91.0, "unit": "mg/dL", "status": "normal"}
            ],
            "uncertainty_flags": [],
        },
    }


def _make_pattern_context_row(
    *,
    doc_id: str = "doc-1",
    interpretation: str = "Your TSH is slightly higher than before.",
    updated_at: str = "2025-01-15",
) -> dict[str, object]:
    return {
        "document_id": doc_id,
        "interpretation": interpretation,
        "updated_at": updated_at,
    }


def test_build_pattern_context_limits_to_max_docs():
    from app.ai.service import _PATTERN_CONTEXT_MAX_DOCS, _build_pattern_context

    # Pass MAX_DOCS + 1 rows; only MAX_DOCS should appear
    context = [
        _make_pattern_context_row(doc_id=f"doc-{idx}", updated_at=f"2025-01-{idx:02d}")
        for idx in range(1, _PATTERN_CONTEXT_MAX_DOCS + 2)
    ]

    built = _build_pattern_context(context)

    assert f"[Document {_PATTERN_CONTEXT_MAX_DOCS} —" in built
    assert f"[Document {_PATTERN_CONTEXT_MAX_DOCS + 1} —" not in built


def test_build_pattern_context_truncates_long_interpretations():
    from app.ai.service import _PATTERN_CONTEXT_MAX_CHARS_PER_DOC, _build_pattern_context

    long_interpretation = "B" * (_PATTERN_CONTEXT_MAX_CHARS_PER_DOC + 100)
    row = _make_pattern_context_row(doc_id="doc-1", interpretation=long_interpretation)

    built = _build_pattern_context([row])

    assert "B" * _PATTERN_CONTEXT_MAX_CHARS_PER_DOC in built
    assert "B" * (_PATTERN_CONTEXT_MAX_CHARS_PER_DOC + 1) not in built


def test_extract_json_array_raises_for_empty_string():
    from app.ai.service import _extract_json_array

    with pytest.raises(ValueError, match="Empty response"):
        _extract_json_array("")


def test_extract_json_array_raises_for_fenced_empty_body():
    from app.ai.service import _extract_json_array

    with pytest.raises(ValueError, match="Empty response"):
        _extract_json_array("```json\n```")


def test_extract_json_array_raises_for_plain_object():
    from app.ai.service import _extract_json_array

    with pytest.raises(ValueError, match="not a JSON array"):
        _extract_json_array('{"description": "something", "document_dates": []}')


@pytest.mark.asyncio
async def test_detect_patterns_with_unknown_date_row():
    from app.ai.service import detect_cross_upload_patterns

    async def fake_validate(text: str) -> str:
        return text

    rows = [
        {"document_id": "doc-1", "interpretation": "TSH was slightly high.", "updated_at": None},
        {"document_id": "doc-2", "interpretation": "TSH rose further.", "updated_at": "2025-06-20"},
    ]

    with (
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(return_value=rows),
        ),
        patch(
            "app.ai.service.call_model_text",
            AsyncMock(
                return_value="""[
  {
    "description": "Your TSH has increased across two uploads.",
    "document_dates": ["2025-01-15", "2025-06-20"],
    "recommendation": "Discuss this pattern with your healthcare provider."
  }
]"""
            ),
        ),
        patch("app.ai.service.validate_no_diagnostic", AsyncMock(side_effect=fake_validate)),
    ):
        result = await detect_cross_upload_patterns(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
        )

    assert len(result.patterns) == 1
    assert result.patterns[0].description == "Your TSH has increased across two uploads."


async def _collect_stream(iterator) -> str:
    chunks = []
    async for chunk in iterator:
        chunks.append(chunk.decode("utf-8"))
    return "".join(chunks)


@pytest.mark.asyncio
async def test_stream_follow_up_answer_builds_prompt_from_full_history():
    """Service loads all AI context rows and sends a prompt to Claude."""
    context = [_make_context_row("doc-1"), _make_context_row("doc-2", "Your LDL is elevated.")]

    async def fake_stream(prompt: str):
        assert "Your glucose is normal." in prompt
        assert "Your LDL is elevated." in prompt
        assert "What should I know?" in prompt
        yield "Answer text."

    import uuid

    doc_id = uuid.uuid4()

    with (
        _mock_chat_persistence(),
        patch("app.ai.service.ai_repository.list_user_ai_context", AsyncMock(return_value=context)),
        patch("app.ai.service.stream_model_text", fake_stream),
    ):
        stream = await stream_follow_up_answer(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
            document_id=doc_id,
            question="What should I know?",
        )
        result = await _collect_stream(stream)

    assert "Answer text." in result


@pytest.mark.asyncio
async def test_stream_follow_up_answer_appends_disclaimer_last():
    """Disclaimer must be appended as the final streamed content."""

    async def fake_stream(prompt: str):
        yield "Some health info."

    import uuid

    with (
        _mock_chat_persistence(),
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(return_value=[_make_context_row()]),
        ),
        patch("app.ai.service.stream_model_text", fake_stream),
    ):
        stream = await stream_follow_up_answer(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            question="Tell me more.",
        )
        result = await _collect_stream(stream)

    assert result.endswith(_DISCLAIMER)
    # Disclaimer comes after the model response
    assert result.index("Some health info.") < result.index(_DISCLAIMER)


@pytest.mark.asyncio
async def test_stream_follow_up_answer_stops_on_safety_failure():
    """When safety validation fails mid-stream, a fallback is emitted instead."""

    async def fake_stream(prompt: str):
        # Yield text that triggers a safety failure
        yield "you have diabetes mellitus disease"

    import uuid

    with (
        _mock_chat_persistence(),
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(return_value=[_make_context_row()]),
        ),
        patch("app.ai.service.stream_model_text", fake_stream),
    ):
        stream = await stream_follow_up_answer(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            question="What is wrong with me?",
        )
        result = await _collect_stream(stream)

    # The forbidden text should NOT appear
    assert "diabetes mellitus disease" not in result
    # A fallback message should appear instead
    assert "unable to provide" in result.lower() or "outside" in result.lower()
    # The standard disclaimer must NOT be appended after a safety failure
    assert not result.endswith(_DISCLAIMER)


@pytest.mark.asyncio
async def test_stream_follow_up_answer_raises_service_unavailable_before_first_chunk():
    from app.ai import service as ai_service

    async def fake_stream(prompt: str):
        if False:
            yield ""
        raise ai_service.ModelTemporaryUnavailableError("busy")

    with (
        _mock_chat_persistence(),
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(return_value=[_make_context_row()]),
        ),
        patch("app.ai.service.stream_model_text", fake_stream),
        pytest.raises(AiServiceUnavailableError, match="temporarily unavailable"),
    ):
        await stream_follow_up_answer(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            question="Tell me more.",
        )


@pytest.mark.asyncio
async def test_stream_follow_up_answer_emits_fallback_when_provider_fails_mid_stream():
    from app.ai import service as ai_service

    async def fake_stream(prompt: str):
        yield "Some health info."
        raise ai_service.ModelTemporaryUnavailableError("busy")

    with (
        _mock_chat_persistence(),
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(return_value=[_make_context_row()]),
        ),
        patch("app.ai.service.stream_model_text", fake_stream),
    ):
        stream = await stream_follow_up_answer(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            question="Tell me more.",
        )
        result = await _collect_stream(stream)

    assert result.startswith("Some health info.")
    assert "temporarily unavailable" in result.lower()
    assert not result.endswith(_DISCLAIMER)


@pytest.mark.asyncio
async def test_stream_follow_up_answer_yields_only_disclaimer_when_model_stream_is_empty():
    async def fake_stream(prompt: str):
        if False:
            yield ""

    with (
        _mock_chat_persistence(),
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(return_value=[_make_context_row()]),
        ),
        patch("app.ai.service.stream_model_text", fake_stream),
    ):
        stream = await stream_follow_up_answer(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            question="Tell me more.",
        )
        result = await _collect_stream(stream)

    assert _DISCLAIMER in result
    assert result.strip() == _DISCLAIMER.strip()


@pytest.mark.asyncio
async def test_stream_follow_up_answer_emits_fallback_on_non_temporary_provider_error():
    from app.ai import service as ai_service

    async def fake_stream(prompt: str):
        yield "Some health info."
        raise ai_service.ModelPermanentError("permanent error")

    with (
        _mock_chat_persistence(),
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(return_value=[_make_context_row()]),
        ),
        patch("app.ai.service.stream_model_text", fake_stream),
    ):
        stream = await stream_follow_up_answer(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            question="Tell me more.",
        )
        result = await _collect_stream(stream)

    assert result.startswith("Some health info.")
    assert "temporarily unavailable" in result.lower()
    assert not result.endswith(_DISCLAIMER)


@pytest.mark.asyncio
async def test_stream_follow_up_answer_raises_service_unavailable_on_permanent_error_before_first_chunk():
    from app.ai import service as ai_service

    async def fake_stream(prompt: str):
        if False:
            yield ""
        raise ai_service.ModelPermanentError("permanent error on first chunk")

    with (
        _mock_chat_persistence(),
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(return_value=[_make_context_row()]),
        ),
        patch("app.ai.service.stream_model_text", fake_stream),
        pytest.raises(AiServiceUnavailableError, match="temporarily unavailable"),
    ):
        await stream_follow_up_answer(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            question="Tell me more.",
        )


@pytest.mark.asyncio
async def test_detect_patterns_returns_empty_when_fewer_than_two_documents():
    from app.ai.service import detect_cross_upload_patterns

    call_model_text_mock = AsyncMock(return_value="[]")

    with (
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(return_value=[_make_pattern_context_row()]),
        ),
        patch("app.ai.service.call_model_text", call_model_text_mock),
    ):
        result = await detect_cross_upload_patterns(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
        )

    assert result.patterns == []
    call_model_text_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_detect_patterns_calls_claude_and_returns_observations():
    from app.ai.service import detect_cross_upload_patterns

    context_rows = [
        _make_pattern_context_row(
            doc_id="doc-1",
            interpretation="TSH was 3.2 mIU/L on this upload.",
            updated_at="2025-01-15",
        ),
        _make_pattern_context_row(
            doc_id="doc-2",
            interpretation="TSH rose to 4.1 mIU/L on this upload.",
            updated_at="2025-06-20",
        ),
    ]
    call_model_text_mock = AsyncMock(
        return_value="""```json
[
  {
    "description": "Your TSH has increased across two recent uploads.",
    "document_dates": ["2025-01-15", "2025-06-20"],
    "recommendation": "Discuss this pattern with your healthcare provider."
  }
]
```"""
    )

    async def fake_validate(text: str) -> str:
        return text

    with (
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(return_value=context_rows),
        ),
        patch("app.ai.service.call_model_text", call_model_text_mock),
        patch("app.ai.service.validate_no_diagnostic", AsyncMock(side_effect=fake_validate)),
    ):
        result = await detect_cross_upload_patterns(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
        )

    assert len(result.patterns) == 1
    assert result.patterns[0].description == "Your TSH has increased across two recent uploads."
    assert result.patterns[0].document_dates == ["2025-01-15", "2025-06-20"]
    assert (
        result.patterns[0].recommendation == "Discuss this pattern with your healthcare provider."
    )

    prompt = call_model_text_mock.await_args.args[0]
    assert "[Document 1 — 2025-01-15]" in prompt
    assert "[Document 2 — 2025-06-20]" in prompt


@pytest.mark.asyncio
async def test_detect_patterns_prompt_contains_context_up_to_max_docs():
    from app.ai.service import _PATTERN_CONTEXT_MAX_DOCS, detect_cross_upload_patterns

    context_rows = [
        _make_pattern_context_row(
            doc_id=f"doc-{idx}",
            interpretation=f"Interpretation {idx}",
            updated_at=f"2025-01-{idx:02d}",
        )
        for idx in range(1, _PATTERN_CONTEXT_MAX_DOCS + 2)  # one row beyond the cap
    ]
    call_model_text_mock = AsyncMock(return_value="[]")

    with (
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(return_value=context_rows),
        ),
        patch("app.ai.service.call_model_text", call_model_text_mock),
    ):
        await detect_cross_upload_patterns(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
        )

    prompt = call_model_text_mock.await_args.args[0]
    # Total row count passed to Claude includes all rows (count= is the full list length)
    assert f"A user has {_PATTERN_CONTEXT_MAX_DOCS + 1} lab result documents" in prompt
    # Context section is capped at MAX_DOCS
    assert f"[Document {_PATTERN_CONTEXT_MAX_DOCS} —" in prompt
    assert f"[Document {_PATTERN_CONTEXT_MAX_DOCS + 1} —" not in prompt


@pytest.mark.asyncio
async def test_detect_patterns_skips_safety_rejected_pattern():
    from app.ai.safety import SafetyValidationError
    from app.ai.service import detect_cross_upload_patterns

    async def fake_validate(text: str) -> str:
        if "Unsafe pattern" in text:
            raise SafetyValidationError("diagnostic language")
        return text

    with (
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(
                return_value=[
                    _make_pattern_context_row(doc_id="doc-1", updated_at="2025-01-15"),
                    _make_pattern_context_row(doc_id="doc-2", updated_at="2025-06-20"),
                ]
            ),
        ),
        patch(
            "app.ai.service.call_model_text",
            AsyncMock(
                return_value="""[
  {
    "description": "Unsafe pattern suggests a diagnosis.",
    "document_dates": ["2025-01-15", "2025-06-20"],
    "recommendation": "Bad recommendation"
  },
  {
    "description": "Your ferritin has been lower on both uploads.",
    "document_dates": ["2025-01-15", "2025-06-20"],
    "recommendation": "Bad recommendation"
  }
]"""
            ),
        ),
        patch("app.ai.service.validate_no_diagnostic", AsyncMock(side_effect=fake_validate)),
    ):
        result = await detect_cross_upload_patterns(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
        )

    assert len(result.patterns) == 1
    assert result.patterns[0].description == "Your ferritin has been lower on both uploads."


@pytest.mark.asyncio
async def test_detect_patterns_returns_empty_on_json_parse_error():
    from app.ai.service import detect_cross_upload_patterns

    with (
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(
                return_value=[
                    _make_pattern_context_row(doc_id="doc-1"),
                    _make_pattern_context_row(doc_id="doc-2", updated_at="2025-06-20"),
                ]
            ),
        ),
        patch("app.ai.service.call_model_text", AsyncMock(return_value="definitely not json")),
    ):
        result = await detect_cross_upload_patterns(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
        )

    assert result.patterns == []


@pytest.mark.asyncio
async def test_detect_patterns_overrides_recommendation_field():
    from app.ai.service import detect_cross_upload_patterns

    async def fake_validate(text: str) -> str:
        return text

    with (
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(
                return_value=[
                    _make_pattern_context_row(doc_id="doc-1"),
                    _make_pattern_context_row(doc_id="doc-2", updated_at="2025-06-20"),
                ]
            ),
        ),
        patch(
            "app.ai.service.call_model_text",
            AsyncMock(
                return_value="""[
  {
    "description": "Your LDL has moved upward across two uploads.",
    "document_dates": ["2025-01-15", "2025-06-20"],
    "recommendation": "Ask for medication."
  }
]"""
            ),
        ),
        patch("app.ai.service.validate_no_diagnostic", AsyncMock(side_effect=fake_validate)),
    ):
        result = await detect_cross_upload_patterns(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
        )

    assert len(result.patterns) == 1
    assert (
        result.patterns[0].recommendation == "Discuss this pattern with your healthcare provider."
    )


@pytest.mark.asyncio
async def test_detect_patterns_skips_pattern_when_document_dates_are_invalid():
    from app.ai.service import detect_cross_upload_patterns

    async def fake_validate(text: str) -> str:
        return text

    with (
        patch(
            "app.ai.service.ai_repository.list_user_ai_context",
            AsyncMock(
                return_value=[
                    _make_pattern_context_row(doc_id="doc-1"),
                    _make_pattern_context_row(doc_id="doc-2", updated_at="2025-06-20"),
                ]
            ),
        ),
        patch(
            "app.ai.service.call_model_text",
            AsyncMock(
                return_value="""[
  {
    "description": "Your LDL has moved upward across two uploads.",
    "document_dates": ["not-a-date"],
    "recommendation": "Ask for medication."
  }
]"""
            ),
        ),
        patch("app.ai.service.validate_no_diagnostic", AsyncMock(side_effect=fake_validate)),
    ):
        result = await detect_cross_upload_patterns(
            db=AsyncMock(),
            user_id=uuid.uuid4(),
        )

    assert result.patterns == []
