# AI Module Audit & Epic 4 Preparation

**Date:** 2026-03-26
**Purpose:** Pre-Epic 4 audit of `app/ai/` against architecture doc. Ground truth for Story 4.1 story creation.

---

## What Actually Exists in `app/ai/`

| File | State | Notes |
|------|-------|-------|
| `models.py` | ✅ Real | `AiMemory` model implemented — see schema below |
| `router.py` | Stub | 2-line placeholder comment only |
| `service.py` | Stub | 1-line placeholder comment only |
| `repository.py` | Stub | 1-line placeholder comment only |
| `schemas.py` | Stub | 1-line placeholder comment only |
| `claude_client.py` | Stub | `call_claude(prompt, images)` stub returning `""` |
| `safety.py` | Stub | `validate_ai_response(response)` stub returning the response unchanged |

### What Exists vs What Epic 4 Needs

| Feature | Exists | Needed for Epic 4 |
|---------|--------|------------------|
| `AiMemory` SQLAlchemy model | ✅ | Story 4.1 |
| `ai_memories` DB table migration | Check alembic | Story 4.1 — verify before coding |
| Anthropic SDK import + client setup | ❌ stub | Story 4.1 |
| `safety.py` → `inject_disclaimer()` | ❌ | Story 4.1 |
| `safety.py` → `validate_no_diagnostic()` | ❌ | Story 4.1 |
| `safety.py` → `surface_uncertainty()` | ❌ | Story 4.1 |
| `generate_interpretation` LangGraph node | ❌ | Story 4.1 |
| `ai_memory` encryption (AES-256-GCM) | ❌ stub (field exists) | Story 4.1 |
| Voyage-3 embeddings storage | ❌ | **Deferred post-MVP** — full-context load used instead |
| `GET/POST /ai/chat` endpoint | ❌ | Story 4.3 |
| Cross-upload pattern detection | ❌ | Story 4.4 |

---

## AiMemory Model (current state)

```python
class AiMemory(Base):
    __tablename__ = "ai_memories"

    id: Mapped[uuid.UUID]           # PK
    user_id: Mapped[uuid.UUID]      # FK → users.id CASCADE
    context_json_encrypted: Mapped[bytes | None]   # encrypted in Epic 4, currently nullable
    created_at: Mapped[datetime]    # server default
    updated_at: Mapped[datetime]    # server default + onupdate
```

**Gaps for Epic 4:**
- No `document_id` FK — needed to link interpretation to a specific document
- No `interpretation_text_encrypted` field — the actual AI interpretation text (separate from `context_json`)
- No embedding columns — Voyage-3 1024-dim embeddings for RAG retrieval
- No `model_version` tracking field

---

## Recommended `AiMemory` Schema Extension (for Story 4.1)

```python
class AiMemory(Base):
    __tablename__ = "ai_memories"

    id: Mapped[uuid.UUID]
    user_id: Mapped[uuid.UUID]       # FK → users.id CASCADE
    document_id: Mapped[uuid.UUID | None]  # FK → documents.id CASCADE (null = Q&A, not per-doc)

    # Encrypted fields (AES-256-GCM, same pattern as health_data)
    interpretation_encrypted: Mapped[bytes | None]   # full AI interpretation text
    context_json_encrypted: Mapped[bytes | None]     # JSON context blob for RAG

    # Metadata
    model_version: Mapped[str | None]   # e.g. "claude-sonnet-4-6"
    safety_validated: Mapped[bool]      # passed safety.py validation

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

The `interpretation_embeddings` table (Voyage-3) can be a separate table linked to `ai_memories.id` to keep the main table lean.

---

## `safety.py` Contract for Epic 4

The Epic 4 spec requires three functions (AC for Story 4.1):

```python
# safety.py — what needs to be implemented

async def inject_disclaimer(text: str) -> str:
    """Append non-diagnostic disclaimer as natural language (not a footnote).

    The disclaimer must be the FINAL sentence of the output, phrased as
    part of the paragraph (not a footnote or bold warning).

    Example: "...These patterns are worth monitoring regularly with your doctor.
    This information is provided for educational purposes only and is not
    a medical diagnosis or treatment recommendation."
    """

async def validate_no_diagnostic(text: str) -> str:
    """Reject output containing specific diagnoses or treatment recommendations.

    Raises a SafetyValidationError if the text contains:
    - Specific disease diagnoses ("you have X", "this indicates X")
    - Treatment recommendations ("take X mg of Y", "you should stop Z")
    - Prognoses ("you will develop X")

    Returns the text unchanged if it passes validation.
    """

async def surface_uncertainty(text: str, values: list[HealthValue]) -> str:
    """Explicitly flag values the AI cannot reliably interpret.

    For values with confidence < 0.7 or status == "unknown", prepend
    a sentence noting interpretive uncertainty before the relevant passage.
    """

class SafetyValidationError(Exception):
    """Raised when AI output fails safety validation."""
    pass
```

---

## Architecture Doc Discrepancies to Fix

| Architecture Doc Says | Reality |
|----------------------|---------|
| Charting: "Recharts (Tailwind-native)" | Wrong — Recharts is React-only. Used raw SVG (Story 3.3). |
| `(app)/dashboard/+page.ts` exists | File doesn't exist — data loading is in `+page.svelte` directly |
| `frontend/src/lib/api/health-data.ts` exists | File doesn't exist — API helpers are in `health-values.ts` |
| `safety.py` has full implementation | Stub only — single pass-through function |
| LangGraph integration in `app/ai/` | Not present — all `app/ai/` files are stubs |

**Action required:** Update architecture doc before writing Story 4.1. Pay particular attention to the AI module section.

---

## EU DPA Status

Confirmed by DUDE on 2026-03-26. DPA with Anthropic is in place.
Story 4.1 implementation may proceed from a compliance standpoint.

---

## Pre-Epic 4 Checklist

- [x] EU DPA with Anthropic confirmed
- [x] `AiMemory` model exists in `app/ai/models.py`
- [ ] Verify `ai_memories` migration exists and is current (`uv run alembic upgrade head` should create the table)
- [ ] Add `document_id` FK and `interpretation_encrypted` field to `AiMemory` via migration
- [ ] Implement `inject_disclaimer()`, `validate_no_diagnostic()`, `surface_uncertainty()` in `safety.py`
- [ ] Update architecture doc AI module section to reflect actual repo state
- [ ] Install `anthropic` SDK in backend (`uv add anthropic`)
- [x] Embeddings deferred to post-MVP — Story 4.3 Q&A will use full-context load from `ai_memories` instead of vector search. No Voyage AI or embedding package needed.
