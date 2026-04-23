"""Provider-agnostic LangChain chat-model wrapper for AI text calls."""

import asyncio
import hashlib
from collections.abc import AsyncIterator, Iterator
from typing import Any

import anthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

from app.core.config import settings

_CALL_MAX_TOKENS = 2048
_STREAM_MAX_TOKENS = 1024
_TEMPORARY_PROVIDER_STATUS_CODES = {408, 429, 500, 502, 503, 504, 529}
_TEMPORARY_PROVIDER_ERROR_TYPES = {"overloaded_error", "rate_limit_error"}

_chat_model_cache: dict[tuple[str, str, int], BaseChatModel] = {}
_cache_lock = asyncio.Lock()


class ModelTemporaryUnavailableError(Exception):
    """Raised when the configured chat provider is temporarily unavailable."""


class ModelPermanentError(Exception):
    """Raised when the configured chat provider returns a non-retriable error."""


def get_model_name() -> str:
    """Return the configured chat-model identifier for text AI flows."""
    return settings.AI_CHAT_MODEL


def _get_api_key() -> str:
    api_key = settings.ANTHROPIC_API_KEY.strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    return api_key


def _build_chat_model(*, max_tokens: int) -> BaseChatModel:
    api_key = _get_api_key()
    chat_model_kwargs: dict[str, Any] = {
        "model": get_model_name(),
        "api_key": SecretStr(api_key),
        "max_tokens": max_tokens,
        "stop": None,
    }
    return ChatAnthropic(**chat_model_kwargs)


def _hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]


async def _get_chat_model(*, max_tokens: int) -> BaseChatModel:
    cache_key = (get_model_name(), _hash_key(_get_api_key()), max_tokens)
    model = _chat_model_cache.get(cache_key)
    if model is None:
        async with _cache_lock:
            model = _chat_model_cache.get(cache_key)
            if model is None:
                model = _build_chat_model(max_tokens=max_tokens)
                _chat_model_cache[cache_key] = model
    return model


def _iter_text_fragments(content: Any) -> Iterator[str]:
    if isinstance(content, str):
        if content:
            yield content
        return

    if isinstance(content, list):
        for item in content:
            if isinstance(item, str):
                if item:
                    yield item
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text:
                    yield text
                continue
            text = getattr(item, "text", None)
            if isinstance(text, str) and text:
                yield text
        return

    text = getattr(content, "text", None)
    if isinstance(text, str) and text:
        yield text


def _extract_text(content: Any) -> str:
    text = "".join(_iter_text_fragments(content)).strip()
    if not text:
        raise ValueError("Model returned an empty or unexpected response")
    return text


def _get_provider_error_type(body: object | None) -> str | None:
    if not isinstance(body, dict):
        return None

    nested_error = body.get("error")
    if isinstance(nested_error, dict):
        nested_type = nested_error.get("type")
        if isinstance(nested_type, str):
            return nested_type

    top_level_type = body.get("type")
    return top_level_type if isinstance(top_level_type, str) else None


def _is_temporary_provider_error(exc: anthropic.AnthropicError) -> bool:
    if isinstance(exc, (anthropic.APIConnectionError, anthropic.APITimeoutError)):
        return True

    if isinstance(exc, anthropic.APIStatusError):
        if _get_provider_error_type(exc.body) in _TEMPORARY_PROVIDER_ERROR_TYPES:
            return True

        status_code = getattr(exc, "status_code", None)
        if not isinstance(status_code, int):
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
        return isinstance(status_code, int) and status_code in _TEMPORARY_PROVIDER_STATUS_CODES

    return False


def _raise_translated_provider_error(exc: anthropic.AnthropicError) -> None:
    """Translate any AnthropicError to a domain exception; always raises."""
    if _is_temporary_provider_error(exc):
        raise ModelTemporaryUnavailableError(
            "The AI provider is temporarily unavailable. Please retry shortly."
        ) from exc
    raise ModelPermanentError(
        "The AI provider returned a non-retriable error."
    ) from exc


async def call_model_text(prompt: str) -> str:
    """Return the complete text response for a single prompt."""
    try:
        model = await _get_chat_model(max_tokens=_CALL_MAX_TOKENS)
        message = await model.ainvoke(prompt)
    except anthropic.AnthropicError as exc:
        _raise_translated_provider_error(exc)
    return _extract_text(message.content)


async def stream_model_text(prompt: str) -> AsyncIterator[str]:
    """Yield text deltas from the configured model for a single prompt."""
    try:
        model = await _get_chat_model(max_tokens=_STREAM_MAX_TOKENS)
        async for chunk in model.astream(prompt):
            for text in _iter_text_fragments(chunk.content):
                yield text
    except anthropic.AnthropicError as exc:
        _raise_translated_provider_error(exc)
