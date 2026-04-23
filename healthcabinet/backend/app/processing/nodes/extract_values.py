"""Extract and normalize health values for the processing graph."""

from app.processing.events import publish_event
from app.processing.extractor import extract_from_document
from app.processing.normalizer import normalize_extraction_result
from app.processing.schemas import (
    STAGE_MESSAGES,
    ProcessingGraphFallbackState,
    ProcessingGraphState,
)
from app.processing.tracing import pipeline_trace


async def extract_values(
    state: ProcessingGraphState,
    fallback_state: ProcessingGraphFallbackState | None = None,
) -> dict[str, object]:
    """Run the existing extraction and normalization boundaries inside a graph node."""
    fallback = fallback_state or state["fallback"]
    fallback.error_stage = "extract_values"
    fallback.error_message = None

    mime_type = state["document_mime_type"]
    document_bytes = state["document_bytes"]
    if mime_type is None or document_bytes is None:
        raise RuntimeError("Graph state missing document bytes or MIME type before extraction")

    message, progress = STAGE_MESSAGES["document.extracting"]
    await publish_event(
        state["runtime"].redis,
        state["document_id_str"],
        "document.extracting",
        progress,
        message,
    )

    async with pipeline_trace(document_id=state["document_id_str"], document_type=mime_type):
        extraction = await extract_from_document(
            document_id=state["document_id_str"],
            document_bytes=document_bytes,
            mime_type=mime_type,
        )

    normalized_values = normalize_extraction_result(extraction)
    return {
        "extraction_result": extraction,
        "measured_at": extraction.measured_at,
        "partial_measured_at_text": extraction.partial_measured_at_text,
        "normalized_values": normalized_values,
        "raw_lab_name": extraction.raw_lab_name,
        "source_language": extraction.source_language,
    }
