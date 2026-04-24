"""AI interpretation generation service."""

import datetime
import json
import re
import uuid
from collections.abc import AsyncIterator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import repository as ai_repository
from app.ai.llm_client import (
    ModelPermanentError,
    ModelTemporaryUnavailableError,
    call_model_text,
    get_model_name,
    stream_model_text,
)
from app.ai.safety import (
    _DISCLAIMER,
    _DISCLAIMER_BY_LOCALE,
    SafetyValidationError,
    inject_disclaimer,
    surface_uncertainty,
    validate_no_diagnostic,
)
from app.ai.schemas import (
    AiPatternsResponse,
    DashboardInterpretationResponse,
    DashboardKind,
    PatternObservation,
)
from app.processing.schemas import NormalizedHealthValue

# Pipeline order: validate raw AI output first, then surface uncertainty,
# then inject disclaimer. This is functionally more sound than the spec's
# listed order (inject → validate → surface) because we validate the raw
# output before the disclaimer is appended. The disclaimer text does not
# trigger any safety patterns so behaviour is identical in practice.

logger = structlog.get_logger()

INTERPRETATION_PROMPT_TEMPLATE = """
You are a helpful health information assistant. A user has uploaded lab results.
Explain each value in plain language, noting whether it is within the normal range
and what that may mean for general health — without making any diagnosis.

Lab values:
{values_text}

Guidelines:
- Use plain language a non-expert can understand
- Mention each value name and whether it is within, below, or above the reference range
- Do NOT diagnose, prescribe, or recommend specific medications or treatments
- Keep the total response under 400 words
"""


def _build_reasoning_context(values: list[NormalizedHealthValue]) -> dict[str, object]:
    """Build structured reasoning context from normalised health values."""

    def _compute_status(value: NormalizedHealthValue) -> str:
        if value.reference_range_low is None or value.reference_range_high is None:
            return "unknown"
        if value.value < value.reference_range_low:
            return "low"
        if value.value > value.reference_range_high:
            return "high"
        return "normal"

    values_referenced = [
        {
            "name": value.canonical_biomarker_name,
            "value": value.value,
            "unit": value.unit,
            "ref_low": value.reference_range_low,
            "ref_high": value.reference_range_high,
            "status": _compute_status(value),
        }
        for value in values
    ]
    uncertainty_flags = [
        f"Insufficient data to interpret {value.canonical_biomarker_name} confidently"
        for value in values
        if value.reference_range_low is None and value.reference_range_high is None
    ]
    return {
        "values_referenced": values_referenced,
        "uncertainty_flags": uncertainty_flags,
        "prior_documents_referenced": [],
    }


async def generate_interpretation(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    values: list[NormalizedHealthValue],
) -> str | None:
    """Generate, safety-validate, and store an AI interpretation.

    Returns interpretation text or None on safety failure.
    """
    values_text = "\n".join(
        f"- {v.canonical_biomarker_name}: {v.value} {v.unit or ''}"
        f" (ref: {v.reference_range_low}–{v.reference_range_high})"
        for v in values
    )
    prompt = INTERPRETATION_PROMPT_TEMPLATE.format(values_text=values_text)
    try:
        raw_text = await call_model_text(prompt)
    except ModelTemporaryUnavailableError:
        logger.warning(
            "ai.interpretation_temporarily_unavailable",
            document_id=str(document_id),
        )
        return None

    try:
        text = await validate_no_diagnostic(raw_text)
        text = await surface_uncertainty(text, values)
        text = await inject_disclaimer(text)
    except SafetyValidationError:
        logger.warning("ai.safety_rejection", document_id=str(document_id))
        return None

    reasoning = _build_reasoning_context(values)
    await ai_repository.upsert_ai_interpretation(
        db,
        user_id=user_id,
        document_id=document_id,
        interpretation_text=text,
        model_version=get_model_name(),
        reasoning_json=reasoning,
    )
    return text


async def _load_main_summary_for_chat(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> tuple[str, datetime.datetime | None] | None:
    """Return (summary_text, updated_at) for the user's overall note, or None.

    Invalidated rows (safety_validated=False) are still usable as chat anchor
    context — the user explicitly asked for this to be available whenever the
    assistant runs. A later regenerate will refresh it; in the meantime the
    previous narrative is safer to keep than to drop.

    Best-effort: any error loading or decrypting the overall row is logged
    and the chat proceeds without the anchor block. The main-summary context
    is an enhancement, never a requirement for answering.
    """
    return await _load_overall_summary_for_chat(
        db, user_id=user_id, scope=ai_repository.OVERALL_SCOPE_ALL
    )


async def _load_overall_summary_for_chat(
    db: AsyncSession,
    user_id: uuid.UUID,
    scope: str,
) -> tuple[str, datetime.datetime | None] | None:
    """Same shape as _load_main_summary_for_chat but for any aggregate scope."""
    try:
        row = await ai_repository.get_overall_interpretation(
            db, user_id=user_id, scope=scope
        )
    except Exception:
        logger.warning(
            "ai.chat_overall_summary_lookup_failed",
            user_id=str(user_id),
            scope=scope,
        )
        return None
    if row is None:
        return None
    try:
        decrypted = await ai_repository.decrypt_overall_interpretation(row)
    except Exception:
        logger.warning(
            "ai.chat_overall_summary_decrypt_failed",
            user_id=str(user_id),
            scope=scope,
        )
        return None
    if decrypted is None:
        return None
    return decrypted[0], row.updated_at


class NoAiContextError(Exception):
    """Raised when a user has no usable AI context rows for follow-up Q&A."""


class NoDashboardAiContextError(Exception):
    """Raised when a dashboard filter yields zero contributing documents.

    Surfaced at the router layer as HTTP 409 with a filter-aware detail
    string; the frontend treats this as a filter-empty state (AC 5), not a
    generic error.
    """


class AiServiceUnavailableError(Exception):
    """Raised when follow-up AI answers cannot be generated right now."""


_FOLLOW_UP_PROMPT_TEMPLATE = """You are a helpful health information assistant. A user is asking a follow-up question about their health lab results.

You have access to the following health interpretation context from the user's documents:

{context_section}

User's follow-up question: {question}

Guidelines:
- Answer only from the provided health context above
- Be explicit when the available data is insufficient to answer the question
- Never diagnose any condition
- Never recommend medications, dosages, or treatment changes
- Keep tone calm, informative, and non-alarming
- Use plain language a non-expert can understand
- If uncertain, surface that uncertainty clearly
- {language_instruction}
"""

_PATTERN_RECOMMENDATION: dict[str, str] = {
    "en": "Discuss this pattern with your healthcare provider.",
    "uk": "Обговоріть цю закономірність зі своїм лікарем.",
}
_PATTERN_CONTEXT_MAX_DOCS = 10
_PATTERN_CONTEXT_MAX_CHARS_PER_DOC = 500
_FOLLOW_UP_SCOPE_FALLBACK: dict[str, str] = {
    "en": (
        " I'm unable to provide a response to that question as it falls outside "
        "the scope of educational health information."
    ),
    "uk": (
        " Я не можу відповісти на це запитання, оскільки воно виходить за межі "
        "освітньої інформації про здоров'я."
    ),
}
_FOLLOW_UP_UNAVAILABLE_DETAIL: dict[str, str] = {
    "en": "AI follow-up is temporarily unavailable. Please try again in a moment.",
    "uk": "Функція чату з ШІ тимчасово недоступна. Будь ласка, спробуйте пізніше.",
}
_FOLLOW_UP_STREAM_INTERRUPTED_FALLBACK: dict[str, str] = {
    "en": (
        " The AI service became temporarily unavailable before the response finished. "
        "Please try again in a moment."
    ),
    "uk": (
        " Сервіс ШІ став тимчасово недоступним до завершення відповіді. "
        "Будь ласка, спробуйте пізніше."
    ),
}


_DASHBOARD_UNAVAILABLE_DETAIL: dict[str, str] = {
    "en": "AI dashboard interpretation is temporarily unavailable. Please try again in a moment.",
    "uk": "Зведений аналіз ШІ тимчасово недоступний. Будь ласка, спробуйте пізніше.",
}
_DASHBOARD_SAFETY_REJECTION_DETAIL: dict[str, str] = {
    "en": "AI dashboard interpretation could not be generated safely. Please try again in a moment.",
    "uk": "Зведений аналіз ШІ не вдалося безпечно сформувати. Будь ласка, спробуйте пізніше.",
}


def _fb(strings: dict[str, str], locale: str) -> str:
    """Look up a locale string from a two-entry dict, falling back to 'en'."""
    return strings.get(locale, strings["en"])


def _is_valid_iso_date(s: str) -> bool:
    try:
        datetime.date.fromisoformat(s.strip())
        return True
    except ValueError:
        return False


_PATTERN_DETECTION_PROMPT_TEMPLATE = """You are a helpful health information assistant. A user has {count} lab result documents with the following AI interpretations:

{context_section}

Identify observable cross-upload patterns — trends in specific biomarkers across 2 or more of these documents.

Rules:
- Describe each pattern in plain, non-alarming language
- List the document dates each pattern spans
- Do NOT state a diagnosis or name a medical condition
- Do NOT recommend specific medications, dosages, or treatments
- Only include patterns that are clearly observable from the data
- If no meaningful patterns exist, return an empty JSON array
- {language_instruction}

Return ONLY a valid JSON array with this exact structure (no prose, no markdown fences):
[
  {{
    "description": "Your TSH has increased across three consecutive results",
    "document_dates": ["2024-09-15", "2025-01-20", "2025-06-10"],
    "recommendation": "Discuss this pattern with your healthcare provider."
  }}
]
"""


def _build_pattern_context(context_rows: list[dict[str, object]]) -> str:
    parts: list[str] = []
    for i, row in enumerate(context_rows[:_PATTERN_CONTEXT_MAX_DOCS], start=1):
        updated_at = row.get("updated_at")
        date = str(updated_at) if updated_at else "unknown date"
        interpretation = str(row.get("interpretation", ""))[:_PATTERN_CONTEXT_MAX_CHARS_PER_DOC]
        parts.append(f"[Document {i} — {date}]\n{interpretation}")
    return "\n\n".join(parts)


def _extract_json_array(text: str) -> list[dict[str, object]]:
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    cleaned = re.sub(r"```(?:\w+)?", "", text).strip()

    if not cleaned:
        raise ValueError("Empty response from AI model after fence stripping")

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as err:
        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1
        if start == -1 or end <= start:
            raise ValueError(f"No JSON array found in AI model response: {cleaned[:80]!r}") from err
        parsed = json.loads(cleaned[start:end])

    if not isinstance(parsed, list):
        raise ValueError(
            f"AI model response was not a JSON array (got {type(parsed).__name__}): {str(parsed)[:80]!r}"
        )

    return [item for item in parsed if isinstance(item, dict)]


def _build_follow_up_prompt(
    context_rows: list[dict[str, object]],
    question: str,
    active_document_id: uuid.UUID | None = None,
    output_language: str = "en",
    main_summary: tuple[str, datetime.datetime | None] | None = None,
    filter_summary: tuple[str, str, datetime.datetime | None] | None = None,
) -> str:
    """Combine context rows and question into a follow-up prompt.

    When `main_summary` is provided, a `[Main health summary]` block is
    prepended to the context section — this is the user-level overall note
    from `ai_memories(scope='overall_all')`. The chat model is instructed to
    treat it as the anchor summary and to reconcile per-document details
    against it.

    When `filter_summary` is provided (as a `(filter_label, text, updated_at)`
    triple), an additional `[Filter view]` block is inserted after the main
    summary. The filter view is a subset perspective; on conflict the model
    is instructed to prefer the main summary.
    """
    context_parts: list[str] = []
    if main_summary is not None:
        summary_text, summary_updated = main_summary
        date_label = summary_updated.date().isoformat() if summary_updated else "unknown date"
        context_parts.append(
            f"[Main health summary — {date_label}]\n"
            "This is the anchor overview of the user's health across all documents; "
            "reconcile any per-document details against it.\n"
            f"{summary_text}"
        )
    if filter_summary is not None:
        filter_label, filter_text, filter_updated = filter_summary
        filter_clip = filter_text[:_PRIOR_OVERALL_MAX_CHARS]
        filter_date = filter_updated.date().isoformat() if filter_updated else "unknown date"
        context_parts.append(
            f"[Filter view: {filter_label} — {filter_date}]\n"
            f'Cached overview for the user\'s currently active filter ("{filter_label}"). '
            "Use it alongside the main summary; when they conflict, prefer the main summary.\n"
            f"{filter_clip}"
        )
    prev_count = 0
    for row in context_rows:
        row_doc_id = row.get("document_id", "")
        if active_document_id is not None and row_doc_id == str(active_document_id):
            label = "Active document"
        else:
            prev_count += 1
            label = f"Previous document {prev_count}"
        interpretation = str(row.get("interpretation", ""))
        reasoning = row.get("reasoning")
        part = f"[{label}]\nInterpretation: {interpretation}"
        if reasoning and isinstance(reasoning, dict):
            try:
                values = reasoning.get("values_referenced", [])
                if isinstance(values, list) and values:
                    values_text = ", ".join(
                        f"{v['name']}: {v['value']} {v.get('unit', '')} ({v.get('status', 'unknown')})"
                        for v in values
                        if isinstance(v, dict)
                    )
                    part += f"\nValues: {values_text}"
                flags = reasoning.get("uncertainty_flags", [])
                if isinstance(flags, list) and flags:
                    part += f"\nUncertainty: {'; '.join(str(f) for f in flags)}"
                prior_docs = reasoning.get("prior_documents_referenced", [])
                if isinstance(prior_docs, list) and prior_docs:
                    part += f"\nReferenced: {', '.join(str(d) for d in prior_docs)}"
            except Exception:
                logger.warning("ai.prompt_reasoning_malformed")
        context_parts.append(part)

    context_section = "\n\n".join(context_parts)
    lang_instruction = (
        "Відповідай українською мовою." if output_language == "uk" else "Respond in English."
    )
    return _FOLLOW_UP_PROMPT_TEMPLATE.format(
        context_section=context_section,
        question=question,
        language_instruction=lang_instruction,
    )


async def detect_cross_upload_patterns(
    db: AsyncSession,
    user_id: uuid.UUID,
    output_language: str = "en",
) -> AiPatternsResponse:
    """Detect cross-upload health patterns for a user. Returns empty list if < 2 documents."""
    context_rows = await ai_repository.list_user_ai_context(db, user_id=user_id)
    if len(context_rows) < 2:
        return AiPatternsResponse(patterns=[])

    lang_instruction = (
        "Відповідай українською мовою." if output_language == "uk" else "Respond in English."
    )
    prompt = _PATTERN_DETECTION_PROMPT_TEMPLATE.format(
        count=len(context_rows),
        context_section=_build_pattern_context(context_rows),
        language_instruction=lang_instruction,
    )

    try:
        raw_text = await call_model_text(prompt)
        raw_patterns = _extract_json_array(raw_text)
    except (json.JSONDecodeError, ValueError):
        logger.warning("ai.pattern_json_parse_failed")
        return AiPatternsResponse(patterns=[])
    except ModelTemporaryUnavailableError:
        logger.warning("ai.patterns_temporarily_unavailable")
        return AiPatternsResponse(patterns=[])
    except Exception as exc:
        logger.warning("ai.pattern_detection_failed", error=str(exc))
        return AiPatternsResponse(patterns=[])

    patterns: list[PatternObservation] = []
    for raw_pattern in raw_patterns:
        description = str(raw_pattern.get("description", "")).strip()
        if not description:
            continue

        try:
            safe_description = await validate_no_diagnostic(description)
        except SafetyValidationError:
            logger.warning("ai.pattern_safety_rejection", description_prefix=description[:40])
            continue

        raw_dates = raw_pattern.get("document_dates", [])
        document_dates = (
            [str(v) for v in raw_dates if isinstance(v, str) and _is_valid_iso_date(v)]
            if isinstance(raw_dates, list)
            else []
        )
        if len(document_dates) < 2:
            logger.warning(
                "ai.pattern_missing_dates",
                description_prefix=description[:40],
                document_dates=document_dates,
                raw_dates=raw_dates,
            )
            continue
        patterns.append(
            PatternObservation(
                description=safe_description,
                document_dates=document_dates,
                recommendation=_fb(_PATTERN_RECOMMENDATION, output_language),
            )
        )

    return AiPatternsResponse(patterns=patterns)


async def stream_follow_up_answer(
    db: AsyncSession,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
    question: str,
    output_language: str = "en",
) -> AsyncIterator[bytes]:
    """Yield UTF-8 encoded response chunks for StreamingResponse."""
    context_rows = await ai_repository.list_user_ai_context(
        db, user_id=user_id, active_document_id=document_id
    )
    if not context_rows:
        raise NoAiContextError("No usable AI context available for this user")

    main_summary = await _load_main_summary_for_chat(db, user_id=user_id)

    prompt = _build_follow_up_prompt(
        context_rows,
        question,
        active_document_id=document_id,
        output_language=output_language,
        main_summary=main_summary,
    )
    model_stream = stream_model_text(prompt)

    try:
        first_delta = await anext(model_stream)
    except StopAsyncIteration:
        first_delta = None
    except (ModelTemporaryUnavailableError, ModelPermanentError) as exc:
        logger.warning(
            "ai.follow_up_temporarily_unavailable",
            user_id=str(user_id),
            document_id=str(document_id),
        )
        raise AiServiceUnavailableError(
            _fb(_FOLLOW_UP_UNAVAILABLE_DETAIL, output_language)
        ) from exc

    async def _validate_and_encode(
        delta: str,
        *,
        cumulative: str,
    ) -> tuple[str, bytes | None, bool]:
        next_cumulative = cumulative + delta
        try:
            await validate_no_diagnostic(next_cumulative)
        except SafetyValidationError:
            return cumulative, _fb(_FOLLOW_UP_SCOPE_FALLBACK, output_language).encode(), True

        await surface_uncertainty(next_cumulative)
        return next_cumulative, delta.encode(), False

    async def _generate() -> AsyncIterator[bytes]:
        cumulative = ""

        if first_delta is not None:
            cumulative, chunk, should_stop = await _validate_and_encode(
                first_delta,
                cumulative=cumulative,
            )
            if chunk is not None:
                yield chunk
            if should_stop:
                return

        try:
            async for delta in model_stream:
                cumulative, chunk, should_stop = await _validate_and_encode(
                    delta,
                    cumulative=cumulative,
                )
                if chunk is not None:
                    yield chunk
                if should_stop:
                    return
        except ModelTemporaryUnavailableError:
            logger.warning(
                "ai.follow_up_stream_interrupted",
                user_id=str(user_id),
                document_id=str(document_id),
            )
            yield _fb(_FOLLOW_UP_STREAM_INTERRUPTED_FALLBACK, output_language).encode()
            return
        except ModelPermanentError:
            logger.warning(
                "ai.follow_up_stream_error",
                user_id=str(user_id),
                document_id=str(document_id),
            )
            yield _fb(_FOLLOW_UP_STREAM_INTERRUPTED_FALLBACK, output_language).encode()
            return

        disclaimer = _DISCLAIMER_BY_LOCALE.get(output_language, _DISCLAIMER)
        yield f" {disclaimer}".encode()

    return _generate()


# ---------------------------------------------------------------------------
# Story 15.3 — dashboard-scoped aggregate AI
# ---------------------------------------------------------------------------

_DASHBOARD_KIND_LABEL: dict[DashboardKind, str] = {
    "all": "all documents",
    "analysis": "lab analysis documents",
    "document": "non-analysis documents",
}

_NO_DASHBOARD_AI_CONTEXT_DETAIL = "No analyses available for the active filter"

# Token-budget guards for the aggregate prompt. Mirrors the `_PATTERN_CONTEXT_*`
# caps used by detect_cross_upload_patterns so a user with N completed documents
# cannot blow the context window or unbounded provider spend.
_DASHBOARD_CONTEXT_MAX_DOCS = 10
_DASHBOARD_CONTEXT_MAX_CHARS_PER_DOC = 500

_DASHBOARD_INTERPRETATION_PROMPT_TEMPLATE = """You are a helpful health information assistant. A user is reviewing an aggregate dashboard view over their {filter_label}. Below are the AI interpretations already generated for each contributing document, in reverse chronological order.

{context_section}

Write a single plain-language overview that:
- Summarizes what the user can see across this dataset
- Highlights consistent themes or contrasts between documents when they exist
- Calls out meaningful gaps (missing categories of data, uncertain values)
- Uses plain language a non-expert can understand
- Does NOT diagnose, prescribe, or recommend treatments
- Does NOT re-interpret raw values — quote or paraphrase what the per-document interpretations already said
- Keeps the total response under 400 words
- {language_instruction}
"""


_PRIOR_OVERALL_MAX_CHARS = 1500


def _build_dashboard_prompt(
    context_rows: list[dict[str, object]],
    document_kind: DashboardKind,
    output_language: str = "en",
    prior_overall: tuple[str, datetime.datetime | None] | None = None,
) -> str:
    parts: list[str] = []
    if prior_overall is not None:
        prior_text, prior_updated = prior_overall
        prior_clip = prior_text[:_PRIOR_OVERALL_MAX_CHARS]
        date_label = prior_updated.date().isoformat() if prior_updated else "unknown date"
        parts.append(
            f"[Prior overall summary — {date_label}]\n"
            "Use this as continuity only; evolve it rather than restarting.\n"
            f"{prior_clip}"
        )
    for i, row in enumerate(context_rows[:_DASHBOARD_CONTEXT_MAX_DOCS], start=1):
        updated_at = row.get("updated_at")
        date = str(updated_at) if updated_at else "unknown date"
        interpretation = str(row.get("interpretation", ""))[:_DASHBOARD_CONTEXT_MAX_CHARS_PER_DOC]
        parts.append(f"[Document {i} — {date}]\n{interpretation}")
    context_section = "\n\n".join(parts)
    lang_instruction = (
        "Відповідай українською мовою." if output_language == "uk" else "Respond in English."
    )
    return _DASHBOARD_INTERPRETATION_PROMPT_TEMPLATE.format(
        filter_label=_DASHBOARD_KIND_LABEL[document_kind],
        context_section=context_section,
        language_instruction=lang_instruction,
    )


async def _generate_and_persist_overall(
    db: AsyncSession,
    user_id: uuid.UUID,
    document_kind: DashboardKind,
    output_language: str,
) -> DashboardInterpretationResponse:
    """Call the LLM for the overall note and persist it to its per-kind
    aggregate scope. Each filter keeps exactly one cached row, kept in sync by
    the upload/delete invalidation hooks.
    """
    scope = ai_repository.overall_scope_for_kind(document_kind)
    context_rows = await ai_repository.list_user_ai_context(
        db, user_id=user_id, document_kind=document_kind
    )
    if not context_rows:
        raise NoDashboardAiContextError(_NO_DASHBOARD_AI_CONTEXT_DETAIL)

    # Provenance invariant: every row fed into the prompt must also appear in
    # source_document_ids. list_user_ai_context always stringifies the UUID, so
    # a parse failure is a hard contract break — skip the row from BOTH the
    # prompt and the source list rather than understating provenance.
    prompt_rows: list[dict[str, object]] = []
    source_document_ids: list[uuid.UUID] = []
    for row in context_rows:
        raw_id = row.get("document_id")
        if not isinstance(raw_id, str):
            logger.warning("ai.dashboard_missing_source_id", raw_id=raw_id)
            continue
        try:
            source_document_ids.append(uuid.UUID(raw_id))
        except ValueError:
            logger.warning("ai.dashboard_bad_source_id", raw_id=raw_id)
            continue
        prompt_rows.append(row)

    if not prompt_rows:
        # Every row was unparseable — treat as no-context rather than silently
        # producing an empty aggregate.
        raise NoDashboardAiContextError(_NO_DASHBOARD_AI_CONTEXT_DETAIL)

    # Feed the prior same-scope note back in as continuity context when we
    # have one, so each filter evolves its own summary rather than restarting
    # from scratch (and without bleeding cross-filter content).
    prior_overall: tuple[str, datetime.datetime | None] | None = None
    prior_row = await ai_repository.get_overall_interpretation(
        db, user_id=user_id, scope=scope
    )
    if prior_row is not None:
        decrypted = await ai_repository.decrypt_overall_interpretation(prior_row)
        if decrypted is not None:
            prior_overall = (decrypted[0], prior_row.updated_at)

    prompt = _build_dashboard_prompt(
        prompt_rows,
        document_kind,
        output_language=output_language,
        prior_overall=prior_overall,
    )
    try:
        raw_text = await call_model_text(prompt)
    except (ModelTemporaryUnavailableError, ModelPermanentError) as exc:
        logger.warning(
            "ai.dashboard_interpretation_temporarily_unavailable",
            user_id=str(user_id),
            document_kind=document_kind,
        )
        raise AiServiceUnavailableError(
            _fb(_DASHBOARD_UNAVAILABLE_DETAIL, output_language)
        ) from exc

    try:
        text = await validate_no_diagnostic(raw_text)
        # surface_uncertainty's per-value flags are not meaningful at aggregate
        # scope; the per-document interpretations already went through that
        # pipeline when they were generated. Pass empty values list.
        text = await surface_uncertainty(text, [])
        text = await inject_disclaimer(text, locale=output_language)
    except SafetyValidationError as exc:
        logger.warning(
            "ai.dashboard_safety_rejection",
            user_id=str(user_id),
            document_kind=document_kind,
        )
        raise AiServiceUnavailableError(
            _fb(_DASHBOARD_SAFETY_REJECTION_DETAIL, output_language)
        ) from exc

    model_version = get_model_name()
    generated_at = datetime.datetime.now(datetime.UTC)

    reasoning_snapshot: dict[str, object] = {
        "source_document_ids": [str(d) for d in source_document_ids],
        "locale": output_language,
    }
    memory = await ai_repository.upsert_overall_interpretation(
        db,
        user_id=user_id,
        interpretation_text=text,
        model_version=model_version,
        reasoning_json=reasoning_snapshot,
        scope=scope,
    )
    await db.commit()
    generated_at = memory.updated_at or generated_at

    return DashboardInterpretationResponse(
        document_id=None,
        document_kind=document_kind,
        source_document_ids=source_document_ids,
        interpretation=text,
        model_version=model_version,
        generated_at=generated_at,
        reasoning=None,
    )


async def generate_dashboard_interpretation(
    db: AsyncSession,
    user_id: uuid.UUID,
    document_kind: DashboardKind,
    output_language: str = "en",
) -> DashboardInterpretationResponse:
    """Cache-first dashboard interpretation.

    Returns the persisted aggregate note for the requested filter scope when
    it exists, is safety_validated, and matches the requested locale. Otherwise
    calls the LLM, persists the new row under the same scope, and returns it.

    Raises NoDashboardAiContextError when the filter yields zero contributing
    per-document rows (empty state at the router layer).
    """
    scope = ai_repository.overall_scope_for_kind(document_kind)
    cached = await ai_repository.get_overall_interpretation(
        db, user_id=user_id, scope=scope
    )
    if cached is not None and cached.safety_validated:
        decrypted = await ai_repository.decrypt_overall_interpretation(cached)
        if decrypted is not None:
            text, reasoning = decrypted
            cached_locale = None
            cached_source_ids: list[uuid.UUID] = []
            if isinstance(reasoning, dict):
                loc = reasoning.get("locale")
                if isinstance(loc, str):
                    cached_locale = loc
                raw_ids = reasoning.get("source_document_ids")
                if isinstance(raw_ids, list):
                    for raw_id in raw_ids:
                        if not isinstance(raw_id, str):
                            continue
                        try:
                            cached_source_ids.append(uuid.UUID(raw_id))
                        except ValueError:
                            continue
            # Locale mismatch → regenerate so the user sees content in the
            # language they requested rather than a silently-wrong cache.
            if cached_locale == output_language:
                return DashboardInterpretationResponse(
                    document_id=None,
                    document_kind=document_kind,
                    source_document_ids=cached_source_ids,
                    interpretation=text,
                    model_version=cached.model_version,
                    generated_at=cached.updated_at,
                    reasoning=None,
                )

    return await _generate_and_persist_overall(
        db,
        user_id=user_id,
        document_kind=document_kind,
        output_language=output_language,
    )


async def force_regenerate_dashboard_interpretation(
    db: AsyncSession,
    user_id: uuid.UUID,
    document_kind: DashboardKind,
    output_language: str = "en",
) -> DashboardInterpretationResponse:
    """Always call the LLM and persist the aggregate note for the requested
    filter scope. Used by the manual regenerate button. Invalidates the cached
    row before regenerating so a mid-run failure leaves nothing stale-but-valid
    behind.
    """
    scope = ai_repository.overall_scope_for_kind(document_kind)
    await ai_repository.invalidate_overall_interpretation(
        db, user_id=user_id, scope=scope
    )
    await db.commit()
    return await _generate_and_persist_overall(
        db,
        user_id=user_id,
        document_kind=document_kind,
        output_language=output_language,
    )


async def stream_dashboard_follow_up(
    db: AsyncSession,
    user_id: uuid.UUID,
    document_kind: DashboardKind,
    question: str,
    output_language: str = "en",
) -> AsyncIterator[bytes]:
    """Yield UTF-8 encoded response chunks for dashboard-scoped chat.

    Reuses the document-scoped follow-up prompt shape with active_document_id
    set to None so every contributing row is labeled as a "Previous document"
    in the prompt. Reuses the existing safety pipeline per chunk.
    """
    context_rows = await ai_repository.list_user_ai_context(
        db, user_id=user_id, document_kind=document_kind
    )
    if not context_rows:
        raise NoDashboardAiContextError(_NO_DASHBOARD_AI_CONTEXT_DETAIL)

    main_summary = await _load_main_summary_for_chat(db, user_id=user_id)
    # When the user is filtered, also inject the active-filter's cached
    # summary so the chat has the filter-scoped narrative available alongside
    # the main overall anchor. Skip for "all" since the filter scope IS the
    # main scope and duplication is pointless.
    filter_summary: tuple[str, str, datetime.datetime | None] | None = None
    if document_kind != "all":
        filter_scope = ai_repository.overall_scope_for_kind(document_kind)
        loaded = await _load_overall_summary_for_chat(
            db, user_id=user_id, scope=filter_scope
        )
        if loaded is not None:
            filter_summary = (document_kind, loaded[0], loaded[1])

    prompt = _build_follow_up_prompt(
        context_rows,
        question,
        active_document_id=None,
        output_language=output_language,
        main_summary=main_summary,
        filter_summary=filter_summary,
    )
    model_stream = stream_model_text(prompt)

    try:
        first_delta = await anext(model_stream)
    except StopAsyncIteration:
        first_delta = None
    except (ModelTemporaryUnavailableError, ModelPermanentError) as exc:
        logger.warning(
            "ai.dashboard_follow_up_temporarily_unavailable",
            user_id=str(user_id),
            document_kind=document_kind,
        )
        raise AiServiceUnavailableError(
            _fb(_FOLLOW_UP_UNAVAILABLE_DETAIL, output_language)
        ) from exc

    # If the model returned zero deltas, treat as unavailable rather than
    # emitting just a leading-space disclaimer with no content.
    if first_delta is None:
        logger.warning(
            "ai.dashboard_follow_up_empty_stream",
            user_id=str(user_id),
            document_kind=document_kind,
        )
        raise AiServiceUnavailableError(_fb(_FOLLOW_UP_UNAVAILABLE_DETAIL, output_language))

    async def _validate_and_encode(
        delta: str,
        *,
        cumulative: str,
    ) -> tuple[str, bytes | None, bool]:
        next_cumulative = cumulative + delta
        try:
            await validate_no_diagnostic(next_cumulative)
        except SafetyValidationError:
            return cumulative, _fb(_FOLLOW_UP_SCOPE_FALLBACK, output_language).encode(), True

        await surface_uncertainty(next_cumulative)
        return next_cumulative, delta.encode(), False

    async def _generate() -> AsyncIterator[bytes]:
        cumulative, chunk, should_stop = await _validate_and_encode(
            first_delta,
            cumulative="",
        )
        if chunk is not None:
            yield chunk
        if should_stop:
            return

        try:
            async for delta in model_stream:
                cumulative, chunk, should_stop = await _validate_and_encode(
                    delta,
                    cumulative=cumulative,
                )
                if chunk is not None:
                    yield chunk
                if should_stop:
                    return
        except ModelTemporaryUnavailableError:
            logger.warning(
                "ai.dashboard_follow_up_stream_interrupted",
                user_id=str(user_id),
                document_kind=document_kind,
            )
            yield _fb(_FOLLOW_UP_STREAM_INTERRUPTED_FALLBACK, output_language).encode()
            return
        except ModelPermanentError:
            logger.warning(
                "ai.dashboard_follow_up_stream_error",
                user_id=str(user_id),
                document_kind=document_kind,
            )
            yield _fb(_FOLLOW_UP_STREAM_INTERRUPTED_FALLBACK, output_language).encode()
            return

        disclaimer = _DISCLAIMER_BY_LOCALE.get(output_language, _DISCLAIMER)
        yield f" {disclaimer}".encode()

    return _generate()
