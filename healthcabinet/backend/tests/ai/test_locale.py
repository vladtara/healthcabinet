"""Tests for locale threading in AI endpoints and safety pipeline (spec-16-1)."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.ai.router import get_dashboard_interpretation
from app.ai.safety import _DISCLAIMER_BY_LOCALE, inject_disclaimer
from app.ai.schemas import (
    AiChatRequest,
    DashboardChatRequest,
    DashboardInterpretationResponse,
)
from app.ai.service import AiServiceUnavailableError


@pytest.mark.asyncio
async def test_dashboard_interpretation_locale_uk_threads_output_language():
    """Router passes output_language='uk' to service when locale=uk query param is given."""
    import datetime

    from fastapi import HTTPException

    fake_response = DashboardInterpretationResponse(
        document_id=None,
        document_kind="all",
        source_document_ids=[],
        interpretation="Агрегований огляд.",
        model_version="claude-sonnet-4-6",
        generated_at=datetime.datetime.now(datetime.UTC),
        reasoning=None,
    )

    mock_service = AsyncMock(return_value=fake_response)

    with patch("app.ai.router.ai_service.generate_dashboard_interpretation", mock_service):
        with patch(
            "app.ai.router.check_ai_dashboard_rate_limit", AsyncMock(return_value=None)
        ):
            result = await get_dashboard_interpretation(
                document_kind="all",
                locale="uk",
                current_user=SimpleNamespace(id=uuid.uuid4()),
                db=AsyncMock(),
            )

    assert result.interpretation == "Агрегований огляд."
    # Verify the service was called with output_language='uk'
    mock_service.assert_awaited_once()
    _, kwargs = mock_service.call_args
    assert kwargs.get("output_language") == "uk", (
        f"Expected output_language='uk', got {kwargs}"
    )


@pytest.mark.asyncio
async def test_inject_disclaimer_uk():
    """inject_disclaimer with locale='uk' appends the Ukrainian disclaimer text."""
    text = "Your glucose is within the normal range."
    result = await inject_disclaimer(text, locale="uk")

    uk_disclaimer = _DISCLAIMER_BY_LOCALE["uk"]
    assert result.startswith(text.rstrip())
    assert uk_disclaimer in result
    # Must not contain English disclaimer
    en_disclaimer = _DISCLAIMER_BY_LOCALE["en"]
    assert en_disclaimer not in result


def test_ai_chat_request_rejects_unknown_locale():
    """POST chat schema only accepts the internal locale codes from the spec."""
    with pytest.raises(ValidationError):
        AiChatRequest.model_validate(
            {
                "document_id": str(uuid.uuid4()),
                "question": "What does this mean?",
                "locale": "de",
            }
        )


def test_dashboard_chat_request_rejects_unknown_locale():
    """Dashboard chat schema only accepts en/uk locale values."""
    with pytest.raises(ValidationError):
        DashboardChatRequest.model_validate(
            {
                "document_kind": "all",
                "question": "Summarize this",
                "locale": "de",
            }
        )
