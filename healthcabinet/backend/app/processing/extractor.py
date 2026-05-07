"""Provider-backed document extraction boundary."""

import base64
import json
from collections.abc import Sequence
from typing import Any, Literal, NamedTuple, cast

import structlog
from anthropic import AsyncAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr, ValidationError

from app.core.config import settings
from app.processing.schemas import ExtractionResult

logger = structlog.get_logger()

_DEFAULT_MODEL = "claude-sonnet-4-20250514"
_MAX_OUTPUT_TOKENS = 16_000
ProviderName = Literal["anthropic", "openai"]

_SYSTEM_PROMPT = """
You extract structured laboratory values from medical documents.
Return JSON only. Do not include markdown fences or prose.
Schema:
{
  "measured_at": "ISO-8601 timestamp or null",
  "partial_measured_at_text": "raw day/month fragment string or null",
  "source_language": "language code or language name if visible, else null",
  "raw_lab_name": "lab/provider name if visible, else null",
  "values": [
    {
      "biomarker_name": "string",
      "value": number,
      "unit": "string or null",
      "reference_range_low": number or null,
      "reference_range_high": number or null,
      "confidence": number between 0 and 1
    }
  ]
}
Rules:
- Extract only objective measured lab values.
- Skip narrative interpretation text.
- Use null for missing units or ranges.
- Confidence must be between 0 and 1.
- Do NOT extract the same biomarker twice. For blood cell differentials (CBC), if both absolute count and percentage are reported, extract ONLY the absolute count and skip the percentage row.
- Date handling:
  - If a full result date with a year is visible, populate "measured_at" with an ISO-8601 timestamp and set "partial_measured_at_text" to null.
  - If only a day and month are visible (for example "12.03" or "12 Mar"), set "measured_at" to null and copy the raw source fragment verbatim into "partial_measured_at_text".
  - If no usable date is visible at all, set both "measured_at" and "partial_measured_at_text" to null.
  - NEVER invent a year. Do not guess the year from the current date, from other documents, or from context.
- If the document is not readable or contains no usable lab values, return {"measured_at": null, "partial_measured_at_text": null, "source_language": null, "raw_lab_name": null, "values": []}.
""".strip()


class _ProviderConfig(NamedTuple):
    name: ProviderName
    api_key: str
    model: str


def _clean(value: str) -> str:
    return value.strip()


def _require_provider_key(
    *,
    provider_name: ProviderName,
    api_key: str,
    env_name: str,
    model: str,
) -> _ProviderConfig:
    if not api_key:
        raise RuntimeError(f"{env_name} is not configured")
    if not model:
        raise RuntimeError(f"{provider_name} extraction model is not configured")
    return _ProviderConfig(provider_name, api_key, model)


def _get_provider_config() -> _ProviderConfig:
    anthropic_key = _clean(settings.ANTHROPIC_API_KEY)
    openai_key = _clean(settings.OPENAI_API_KEY)

    if settings.AI_EXTRACTION_PROVIDER == "anthropic":
        return _require_provider_key(
            provider_name="anthropic",
            api_key=anthropic_key,
            env_name="ANTHROPIC_API_KEY",
            model=_clean(settings.ANTHROPIC_EXTRACTION_MODEL or _DEFAULT_MODEL),
        )
    if settings.AI_EXTRACTION_PROVIDER == "openai":
        return _require_provider_key(
            provider_name="openai",
            api_key=openai_key,
            env_name="OPENAI_API_KEY",
            model=_clean(settings.OPENAI_EXTRACTION_MODEL),
        )

    if anthropic_key:
        return _require_provider_key(
            provider_name="anthropic",
            api_key=anthropic_key,
            env_name="ANTHROPIC_API_KEY",
            model=_clean(settings.ANTHROPIC_EXTRACTION_MODEL or _DEFAULT_MODEL),
        )
    if openai_key:
        return _require_provider_key(
            provider_name="openai",
            api_key=openai_key,
            env_name="OPENAI_API_KEY",
            model=_clean(settings.OPENAI_EXTRACTION_MODEL),
        )
    raise RuntimeError("ANTHROPIC_API_KEY or OPENAI_API_KEY is not configured")


def _get_anthropic_client(api_key: str) -> AsyncAnthropic:
    return AsyncAnthropic(api_key=api_key)


def _get_openai_model(*, api_key: str, model: str) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=SecretStr(api_key),
        max_completion_tokens=_MAX_OUTPUT_TOKENS,
    )


def _build_document_block(document_bytes: bytes, mime_type: str) -> dict[str, Any]:
    encoded = base64.b64encode(document_bytes).decode("ascii")
    if mime_type == "application/pdf":
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": mime_type,
                "data": encoded,
            },
        }
    if mime_type.startswith("image/"):
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime_type,
                "data": encoded,
            },
        }
    raise ValueError(f"Unsupported document MIME type: {mime_type}")


def _build_openai_document_block(
    *,
    document_id: str,
    document_bytes: bytes,
    mime_type: str,
) -> dict[str, Any]:
    encoded = base64.b64encode(document_bytes).decode("ascii")
    if mime_type == "application/pdf":
        return {
            "type": "file",
            "file": {
                "filename": f"{document_id}.pdf",
                "file_data": f"data:application/pdf;base64,{encoded}",
            },
        }
    if mime_type.startswith("image/"):
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{encoded}",
            },
        }
    raise ValueError(f"Unsupported document MIME type: {mime_type}")


def _extract_text_blocks(content: Sequence[Any] | str) -> str:
    if isinstance(content, str):
        if content.strip():
            return content.strip()
        raise ValueError("Provider response did not contain text output")

    text_parts: list[str] = []
    for block in content:
        if isinstance(block, str) and block.strip():
            text_parts.append(block.strip())
            continue
        if isinstance(block, dict):
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())
            continue
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            text_parts.append(text.strip())
    if not text_parts:
        raise ValueError("Provider response did not contain text output")
    return "\n".join(text_parts)


def _extract_structured_payload(response: Any) -> dict[str, Any]:
    structured_output = getattr(response, "output", None)
    if structured_output is not None:
        if isinstance(structured_output, dict):
            return structured_output
        if hasattr(structured_output, "model_dump"):
            payload = structured_output.model_dump(mode="python")
            if isinstance(payload, dict):
                return cast(dict[str, Any], payload)

    raw_text = _extract_text_blocks(response.content)
    # Strip optional markdown code fences (model sometimes ignores the prompt instruction)
    stripped = raw_text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        stripped = stripped[first_newline + 1 :] if first_newline != -1 else stripped[3:]
        if stripped.rstrip().endswith("```"):
            stripped = stripped[: stripped.rstrip().rfind("```")].rstrip()
        raw_text = stripped
    decoder = json.JSONDecoder()
    payload, end = decoder.raw_decode(raw_text.lstrip())
    remainder = raw_text.lstrip()[end:].strip()
    if remainder:
        raise ValueError("Provider response contained trailing non-JSON content")
    if not isinstance(payload, dict):
        raise ValueError("Provider response JSON must be an object")
    return cast(dict[str, Any], payload)


async def extract_from_document(
    *,
    document_id: str,
    document_bytes: bytes,
    mime_type: str,
) -> ExtractionResult:
    """Extract structured lab values from a PDF or image document."""
    provider_config = _get_provider_config()

    logger.info(
        "processing.extractor.request",
        document_id=document_id,
        mime_type=mime_type,
        byte_size=len(document_bytes),
        provider=provider_config.name,
        model=provider_config.model,
    )

    if provider_config.name == "anthropic":
        response = await _extract_with_anthropic(
            provider_config=provider_config,
            document_bytes=document_bytes,
            mime_type=mime_type,
        )
    else:
        response = await _extract_with_openai(
            provider_config=provider_config,
            document_id=document_id,
            document_bytes=document_bytes,
            mime_type=mime_type,
        )

    response_metadata = getattr(response, "response_metadata", {})
    if getattr(response, "stop_reason", None) == "max_tokens" or (
        isinstance(response_metadata, dict) and response_metadata.get("finish_reason") == "length"
    ):
        raise ValueError(
            f"Extraction response truncated at {_MAX_OUTPUT_TOKENS} tokens; "
            "document may contain too many values"
        )

    payload = _extract_structured_payload(response)
    try:
        result = ExtractionResult.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Provider response did not match extraction schema") from exc

    logger.info(
        "processing.extractor.response",
        document_id=document_id,
        extracted_value_count=len(result.values),
        source_language=result.source_language,
    )

    return result


async def _extract_with_anthropic(
    *,
    provider_config: _ProviderConfig,
    document_bytes: bytes,
    mime_type: str,
) -> Any:
    client = _get_anthropic_client(provider_config.api_key)
    return await client.messages.create(
        model=provider_config.model,
        max_tokens=_MAX_OUTPUT_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=cast(
            Any,
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extract structured biomarker values from this document. "
                                "Return JSON only."
                            ),
                        },
                        _build_document_block(document_bytes, mime_type),
                    ],
                }
            ],
        ),
    )


async def _extract_with_openai(
    *,
    provider_config: _ProviderConfig,
    document_id: str,
    document_bytes: bytes,
    mime_type: str,
) -> Any:
    model = _get_openai_model(api_key=provider_config.api_key, model=provider_config.model)
    return await model.ainvoke(
        [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(
                content=cast(
                    Any,
                    [
                        {
                            "type": "text",
                            "text": (
                                "Extract structured biomarker values from this document. "
                                "Return JSON only."
                            ),
                        },
                        _build_openai_document_block(
                            document_id=document_id,
                            document_bytes=document_bytes,
                            mime_type=mime_type,
                        ),
                    ],
                )
            ),
        ]
    )
