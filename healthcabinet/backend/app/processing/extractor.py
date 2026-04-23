"""Claude-backed document extraction boundary."""

import base64
import json
from collections.abc import Sequence
from typing import Any, cast

import structlog
from anthropic import AsyncAnthropic
from pydantic import ValidationError

from app.core.config import settings
from app.processing.schemas import ExtractionResult

logger = structlog.get_logger()

_DEFAULT_MODEL = "claude-sonnet-4-20250514"
_MAX_OUTPUT_TOKENS = 16_000

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


def _get_client() -> AsyncAnthropic:
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    return AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


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


def _extract_text_blocks(content: Sequence[Any]) -> str:
    text_parts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            text_parts.append(text.strip())
    if not text_parts:
        raise ValueError("Claude response did not contain text output")
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
        raise ValueError("Claude response contained trailing non-JSON content")
    if not isinstance(payload, dict):
        raise ValueError("Claude response JSON must be an object")
    return cast(dict[str, Any], payload)


async def extract_from_document(
    *,
    document_id: str,
    document_bytes: bytes,
    mime_type: str,
) -> ExtractionResult:
    """Extract structured lab values from a PDF or image document."""
    client = _get_client()
    model = settings.ANTHROPIC_EXTRACTION_MODEL or _DEFAULT_MODEL

    logger.info(
        "processing.extractor.request",
        document_id=document_id,
        mime_type=mime_type,
        byte_size=len(document_bytes),
        model=model,
    )

    response = await client.messages.create(
        model=model,
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

    if getattr(response, "stop_reason", None) == "max_tokens":
        raise ValueError(
            f"Extraction response truncated at {_MAX_OUTPUT_TOKENS} tokens; "
            "document may contain too many values"
        )

    payload = _extract_structured_payload(response)
    try:
        result = ExtractionResult.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Claude response did not match extraction schema") from exc

    logger.info(
        "processing.extractor.response",
        document_id=document_id,
        extracted_value_count=len(result.values),
        source_language=result.source_language,
    )

    return result
