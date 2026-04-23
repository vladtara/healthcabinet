"""Tests for the LangChain-backed AI model adapter."""

import importlib
from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import anthropic
import httpx
import langchain_anthropic
import pytest


def _message(content: object) -> SimpleNamespace:
    return SimpleNamespace(content=content)


async def _stream_messages(*contents: object) -> AsyncIterator[SimpleNamespace]:
    for content in contents:
        yield _message(content)


@pytest.fixture
def llm_client_module():
    import app.ai.llm_client as llm_client

    module = importlib.reload(llm_client)
    yield module
    importlib.reload(module)


def test_llm_client_import_is_lazy(llm_client_module):
    llm_client = llm_client_module

    with patch.object(langchain_anthropic, "ChatAnthropic") as chat_cls:
        importlib.reload(llm_client)
        chat_cls.assert_not_called()

    importlib.reload(llm_client)


@pytest.mark.asyncio
async def test_call_model_text_raises_when_api_key_missing(llm_client_module):
    llm_client = llm_client_module

    with (
        patch.object(llm_client.settings, "ANTHROPIC_API_KEY", ""),
        pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"),
    ):
        await llm_client.call_model_text("Hello")


@pytest.mark.asyncio
async def test_call_model_text_treats_whitespace_api_key_as_missing(llm_client_module):
    llm_client = llm_client_module

    with (
        patch.object(llm_client.settings, "ANTHROPIC_API_KEY", "   "),
        pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"),
    ):
        await llm_client.call_model_text("Hello")


@pytest.mark.asyncio
async def test_call_model_text_returns_text_from_langchain_response_and_reuses_client(
    llm_client_module,
):
    llm_client = llm_client_module

    fake_model = SimpleNamespace(
        ainvoke=AsyncMock(return_value=_message([{"type": "text", "text": "Hello world"}]))
    )

    with (
        patch.object(llm_client.settings, "ANTHROPIC_API_KEY", "  test-key  "),
        patch.object(llm_client, "ChatAnthropic", return_value=fake_model) as chat_cls,
    ):
        first = await llm_client.call_model_text("Hello")
        second = await llm_client.call_model_text("Hello again")

    assert first == "Hello world"
    assert second == "Hello world"
    assert chat_cls.call_count == 1
    assert chat_cls.call_args.kwargs == {
        "model": llm_client.settings.AI_CHAT_MODEL,
        "api_key": llm_client.SecretStr("test-key"),
        "max_tokens": llm_client._CALL_MAX_TOKENS,
        "stop": None,
    }


@pytest.mark.asyncio
async def test_stream_model_text_yields_incremental_text_chunks_and_reuses_client(
    llm_client_module,
):
    llm_client = llm_client_module

    def _astream(_prompt: str) -> AsyncIterator[SimpleNamespace]:
        return _stream_messages(
            "Your ",
            [{"type": "text", "text": "glucose "}],
            "",
            [{"type": "tool_use", "name": "ignored"}],
            SimpleNamespace(text="is normal."),
        )

    fake_model = SimpleNamespace(astream=_astream)

    with (
        patch.object(llm_client.settings, "ANTHROPIC_API_KEY", "test-key"),
        patch.object(llm_client, "ChatAnthropic", return_value=fake_model) as chat_cls,
    ):
        first_chunks = [chunk async for chunk in llm_client.stream_model_text("Prompt")]
        second_chunks = [chunk async for chunk in llm_client.stream_model_text("Prompt again")]

    assert first_chunks == ["Your ", "glucose ", "is normal."]
    assert second_chunks == ["Your ", "glucose ", "is normal."]
    assert chat_cls.call_count == 1
    assert chat_cls.call_args.kwargs["max_tokens"] == llm_client._STREAM_MAX_TOKENS


def _status_error(*, status_code: int, body: object) -> anthropic.APIStatusError:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code=status_code, request=request)
    return anthropic.APIStatusError("Provider request failed", response=response, body=body)


@pytest.mark.asyncio
async def test_call_model_text_raises_temporary_unavailable_for_overloaded_provider(
    llm_client_module,
):
    llm_client = llm_client_module
    overloaded_error = _status_error(
        status_code=529,
        body={"error": {"type": "overloaded_error", "message": "Overloaded"}},
    )

    with (
        patch.object(llm_client.settings, "ANTHROPIC_API_KEY", "test-key"),
        patch.object(
            llm_client,
            "ChatAnthropic",
            return_value=SimpleNamespace(ainvoke=AsyncMock(side_effect=overloaded_error)),
        ),
        pytest.raises(llm_client.ModelTemporaryUnavailableError, match="temporarily unavailable"),
    ):
        await llm_client.call_model_text("Prompt")


@pytest.mark.asyncio
async def test_stream_model_text_raises_temporary_unavailable_for_overloaded_provider(
    llm_client_module,
):
    llm_client = llm_client_module
    overloaded_error = _status_error(
        status_code=529,
        body={"error": {"type": "overloaded_error", "message": "Overloaded"}},
    )

    async def _astream(_prompt: str) -> AsyncIterator[SimpleNamespace]:
        if False:
            yield _message("")
        raise overloaded_error

    with (
        patch.object(llm_client.settings, "ANTHROPIC_API_KEY", "test-key"),
        patch.object(llm_client, "ChatAnthropic", return_value=SimpleNamespace(astream=_astream)),
        pytest.raises(llm_client.ModelTemporaryUnavailableError, match="temporarily unavailable"),
    ):
        [chunk async for chunk in llm_client.stream_model_text("Prompt")]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,body",
    [
        (429, {"error": {"type": "rate_limit_error", "message": "Rate limited"}}),
        (429, {"type": "rate_limit_error"}),  # top-level type fallback
        (408, {}),
        (500, {}),
        (502, {}),
        (503, {}),
        (504, {}),
    ],
)
async def test_call_model_text_raises_temporary_unavailable_for_various_status_codes(
    llm_client_module, status_code: int, body: object
):
    llm_client = llm_client_module
    error = _status_error(status_code=status_code, body=body)

    with (
        patch.object(llm_client.settings, "ANTHROPIC_API_KEY", "test-key"),
        patch.object(
            llm_client,
            "ChatAnthropic",
            return_value=SimpleNamespace(ainvoke=AsyncMock(side_effect=error)),
        ),
        pytest.raises(llm_client.ModelTemporaryUnavailableError, match="temporarily unavailable"),
    ):
        await llm_client.call_model_text("Prompt")


@pytest.mark.asyncio
async def test_call_model_text_raises_temporary_unavailable_for_connection_error(
    llm_client_module,
):
    llm_client = llm_client_module
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    conn_error = anthropic.APIConnectionError(request=request)

    with (
        patch.object(llm_client.settings, "ANTHROPIC_API_KEY", "test-key"),
        patch.object(
            llm_client,
            "ChatAnthropic",
            return_value=SimpleNamespace(ainvoke=AsyncMock(side_effect=conn_error)),
        ),
        pytest.raises(llm_client.ModelTemporaryUnavailableError, match="temporarily unavailable"),
    ):
        await llm_client.call_model_text("Prompt")


@pytest.mark.asyncio
async def test_call_model_text_raises_permanent_error_for_non_temporary_status_code(
    llm_client_module,
):
    llm_client = llm_client_module
    permanent_error = _status_error(status_code=400, body={"type": "invalid_request_error"})

    with (
        patch.object(llm_client.settings, "ANTHROPIC_API_KEY", "test-key"),
        patch.object(
            llm_client,
            "ChatAnthropic",
            return_value=SimpleNamespace(ainvoke=AsyncMock(side_effect=permanent_error)),
        ),
        pytest.raises(llm_client.ModelPermanentError),
    ):
        await llm_client.call_model_text("Prompt")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_llm_client_real_provider_integration_skips_without_api_key(llm_client_module):
    llm_client = llm_client_module

    if not llm_client.settings.ANTHROPIC_API_KEY:
        pytest.skip("ANTHROPIC_API_KEY is not configured")

    try:
        text = await llm_client.call_model_text("Reply with exactly: OK")
    except (llm_client.ModelTemporaryUnavailableError, llm_client.ModelPermanentError) as exc:
        pytest.skip(f"Real provider integration unavailable: {exc}")
    assert "OK" in text

    try:
        streamed = "".join(
            [chunk async for chunk in llm_client.stream_model_text("Reply with exactly: OK")]
        )
    except (llm_client.ModelTemporaryUnavailableError, llm_client.ModelPermanentError) as exc:
        pytest.skip(f"Real provider streaming unavailable: {exc}")
    assert "OK" in streamed
