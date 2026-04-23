# Story 4.1: Plain-Language AI Interpretation Per Upload

Status: done

## Story

As a registered user,
I want to receive a plain-language interpretation of every value in my uploaded lab result,
so that I understand what my results mean without needing medical expertise.

## Acceptance Criteria

1. **Given** a document has been successfully processed (status `completed` or `partial`)
   **When** `generate_ai_interpretation()` runs in the worker pipeline after health values are saved
   **Then** Claude produces a plain-language interpretation covering all extracted values
   **And** the output passes through the `safety.py` pipeline: `inject_disclaimer()`, `validate_no_diagnostic()`, `surface_uncertainty()`

2. **Given** the interpretation passes safety validation
   **When** it is stored
   **Then** the interpretation text is stored AES-256-GCM encrypted in the `ai_memories` table linked by `user_id` and `document_id`
   **And** `safety_validated=True` and `model_version` are recorded on the row
   *(Note: `interpretation_embeddings` and Voyage-3 are deferred post-MVP — full-context load will be used for Q&A in Story 4.3)*

3. **Given** any authenticated user opens a document detail view
   **When** `GET /api/v1/ai/documents/{document_id}/interpretation` is called and the document status is `completed` or `partial`
   **Then** the decrypted interpretation text is returned
   **And** ownership is enforced — users cannot read other users' interpretations

4. **Given** the `AiInterpretationCard` renders on the document detail page
   **Then** the full interpretation is displayed with the non-diagnostic disclaimer as the final line of natural language
   **And** the card is visually distinct from regular content (dark container, AI attribution label, accent border)
   **And** an `aria-live="polite"` region announces when interpretation content has loaded

5. **Given** the Anthropic Claude API is called
   **Then** the DPA with Anthropic is already confirmed (2026-03-26) — no blocker
   **And** the `ANTHROPIC_API_KEY` env var is used from Pydantic Settings

## Tasks / Subtasks

### Backend

- [x] **Task 1**: Create Alembic migration `008_ai_memories_epic4.py` (AC: #2)
  - [x] Extend the `ai_memories` table with the new fields (the existing model is missing required columns — migration needed to sync DB with model):
    ```python
    # In the upgrade() function:
    op.add_column('ai_memories', sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=True))
    op.add_column('ai_memories', sa.Column('interpretation_encrypted', sa.LargeBinary(), nullable=True))
    op.add_column('ai_memories', sa.Column('model_version', sa.String(length=64), nullable=True))
    op.add_column('ai_memories', sa.Column('safety_validated', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index('ix_ai_memories_document_id', 'ai_memories', ['document_id'])
    ```
  - [x] Update `app/ai/models.py` to add the four new fields so SQLAlchemy model matches:
    ```python
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    interpretation_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    safety_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    ```
  - [x] Run `docker compose exec backend uv run alembic upgrade head` to apply

- [x] **Task 2**: Implement `app/ai/safety.py` (AC: #1)
  - [x] Replace the single `validate_ai_response` stub with three functions and `SafetyValidationError`:
    ```python
    class SafetyValidationError(Exception):
        pass

    async def inject_disclaimer(text: str) -> str:
        """Append non-diagnostic disclaimer as natural language (final sentence, not footnote)."""
        disclaimer = (
            "This information is provided for educational purposes only and is not "
            "a medical diagnosis or treatment recommendation — please discuss your results "
            "with your healthcare provider."
        )
        return f"{text.rstrip()} {disclaimer}"

    async def validate_no_diagnostic(text: str) -> str:
        """Raise SafetyValidationError if text contains specific diagnoses or treatment recommendations."""
        FORBIDDEN_PATTERNS = [
            r"\byou have\b.*\b(disease|disorder|syndrome|condition)\b",
            r"\bdiagnosed with\b",
            r"\btake\b.*\b(mg|mcg|units)\b",
            r"\bprescrib",
            r"\byou should (start|stop|take|avoid)\b",
        ]
        import re
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                raise SafetyValidationError(
                    f"AI output contains disallowed diagnostic language. Pattern: {pattern}"
                )
        return text

    async def surface_uncertainty(text: str, values: list | None = None) -> str:
        """No-op at MVP — uncertainty is surfaced in Claude's prompt rather than post-hoc."""
        return text
    ```

- [x] **Task 3**: Implement `app/ai/claude_client.py` (AC: #1, #5)
  - [x] Replace the stub with a real Anthropic SDK call:
    ```python
    import anthropic
    from app.core.config import settings

    _client: anthropic.AsyncAnthropic | None = None

    def get_client() -> anthropic.AsyncAnthropic:
        global _client
        if _client is None:
            _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return _client

    async def call_claude(prompt: str, images: list[bytes] | None = None) -> str:
        """Call Claude claude-sonnet-4-6 and return response text."""
        client = get_client()
        content: list = []
        if images:
            for img_bytes in images:
                import base64
                content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg",
                               "data": base64.b64encode(img_bytes).decode()},
                })
        content.append({"type": "text", "text": prompt})
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": content}],
        )
        return message.content[0].text
    ```
  - [x] Add `ANTHROPIC_API_KEY: str` to `app/core/config.py` Pydantic Settings
  - [x] Install SDK: `docker compose exec backend uv add anthropic`

- [x] **Task 4**: Implement `app/ai/repository.py` — encryption-layer storage (AC: #2, #3)
  - [x] Follow the exact same encryption pattern as `health_data/repository.py` — `encrypt_bytes` / `decrypt_bytes` MUST only be called here, never in service or router:
    ```python
    from app.core.encryption import decrypt_bytes, encrypt_bytes

    async def create_ai_interpretation(
        db: AsyncSession,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        interpretation_text: str,
        model_version: str,
    ) -> AiMemory:
        encrypted = encrypt_bytes(interpretation_text.encode("utf-8"))
        memory = AiMemory(
            user_id=user_id,
            document_id=document_id,
            interpretation_encrypted=encrypted,
            model_version=model_version,
            safety_validated=True,
        )
        db.add(memory)
        await db.flush()
        await db.refresh(memory)
        return memory

    async def get_interpretation_for_document(
        db: AsyncSession, user_id: uuid.UUID, document_id: uuid.UUID
    ) -> str | None:
        result = await db.execute(
            select(AiMemory).where(
                AiMemory.user_id == user_id,
                AiMemory.document_id == document_id,
                AiMemory.safety_validated == True,
            )
        )
        memory = result.scalar_one_or_none()
        if memory is None or memory.interpretation_encrypted is None:
            return None
        return decrypt_bytes(memory.interpretation_encrypted).decode("utf-8")
    ```

- [x] **Task 5**: Implement `app/ai/service.py` — interpretation generation logic (AC: #1)
  - [x] Build the `generate_interpretation()` function that the worker calls:
    ```python
    from app.ai.claude_client import call_claude
    from app.ai.safety import inject_disclaimer, validate_no_diagnostic, surface_uncertainty, SafetyValidationError

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

    async def generate_interpretation(
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        values: list[NormalizedHealthValue],
    ) -> str | None:
        """Generate, safety-validate, and store an AI interpretation. Returns interpretation text or None on safety failure."""
        values_text = "\n".join(
            f"- {v.canonical_biomarker_name}: {v.value} {v.unit or ''}"
            f" (ref: {v.reference_range_low}–{v.reference_range_high})"
            for v in values
        )
        prompt = INTERPRETATION_PROMPT_TEMPLATE.format(values_text=values_text)
        raw_text = await call_claude(prompt)

        try:
            text = await validate_no_diagnostic(raw_text)
            text = await surface_uncertainty(text, values)
            text = await inject_disclaimer(text)
        except SafetyValidationError:
            logger.warning("ai.safety_rejection", document_id=str(document_id))
            return None

        await ai_repository.create_ai_interpretation(
            db,
            user_id=user_id,
            document_id=document_id,
            interpretation_text=text,
            model_version="claude-sonnet-4-6",
        )
        return text
    ```

- [x] **Task 6**: Implement `app/ai/schemas.py` (AC: #3)
  - [x] Add response schema:
    ```python
    from pydantic import BaseModel

    class AiInterpretationResponse(BaseModel):
        document_id: uuid.UUID
        interpretation: str
        model_version: str | None
        generated_at: datetime
    ```

- [x] **Task 7**: Implement `app/ai/router.py` — GET endpoint (AC: #3)
  - [x] Create `GET /api/v1/ai/documents/{document_id}/interpretation`:
    ```python
    router = APIRouter(prefix="/ai", tags=["ai"])

    @router.get("/documents/{document_id}/interpretation", response_model=AiInterpretationResponse)
    async def get_document_interpretation(
        document_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> AiInterpretationResponse:
        # Ownership check: verify document belongs to this user
        document = await document_repository.get_document_by_id(db, current_user.id, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        interpretation = await ai_repository.get_interpretation_for_document(
            db, user_id=current_user.id, document_id=document_id
        )
        if interpretation is None:
            raise HTTPException(status_code=404, detail="Interpretation not available")
        memory = await ai_repository.get_memory_row_for_document(db, current_user.id, document_id)
        return AiInterpretationResponse(
            document_id=document_id,
            interpretation=interpretation,
            model_version=memory.model_version if memory else None,
            generated_at=memory.created_at if memory else datetime.utcnow(),
        )
    ```
  - [x] Register the router in `app/main.py`: `app.include_router(ai_router, prefix="/api/v1")`

- [x] **Task 8**: Hook `generate_ai_interpretation` into the worker pipeline (AC: #1, #2)
  - [x] In `app/processing/worker.py`, after `health_data_repository.replace_document_health_values(...)` and before `document_repository.update_document_status_internal(...)`, add the AI interpretation step:
    ```python
    # After saving health values, generate AI interpretation
    try:
        from app.ai import service as ai_service
        await ai_service.generate_interpretation(
            db,
            document_id=state.document_id,
            user_id=state.user_id,
            values=state.values,
        )
    except Exception:
        logger.warning("worker.ai_interpretation_failed", document_id=document_id)
        # Non-fatal: document still completes, interpretation will be missing
    ```
  - [x] The AI step is **non-fatal** — a Claude API failure must NOT change document status to `failed`
  - [x] Only call this when `state.has_values` is True (already gated by the `if state.has_values` block)

- [x] **Task 9**: Add backend tests (AC: #1, #2, #3)
  - [x] Create `tests/ai/test_safety.py`:
    - `test_inject_disclaimer_appends_to_end` — disclaimer is final sentence
    - `test_validate_no_diagnostic_rejects_diagnosis` — "you have hypothyroidism" raises `SafetyValidationError`
    - `test_validate_no_diagnostic_passes_clean_text` — normal interpretive text passes
  - [x] Create `tests/ai/test_router.py`:
    - `test_get_interpretation_returns_200_for_owner` — user gets their own document's interpretation
    - `test_get_interpretation_returns_404_for_other_user` — ownership enforced
    - `test_get_interpretation_returns_404_when_not_generated` — no interpretation yet returns 404
  - [x] Run: `docker compose exec backend uv run pytest tests/ai/ -v`

### Frontend

- [x] **Task 10**: Create `app/ai/` TypeScript type + API helper (AC: #3, #4)
  - [x] Create `healthcabinet/frontend/src/lib/api/ai.ts`:
    ```typescript
    import { apiFetch } from './client';

    export interface AiInterpretationResponse {
      document_id: string;
      interpretation: string;
      model_version: string | null;
      generated_at: string;
    }

    export async function getDocumentInterpretation(
      documentId: string
    ): Promise<AiInterpretationResponse> {
      return apiFetch<AiInterpretationResponse>(
        `/api/v1/ai/documents/${documentId}/interpretation`
      );
    }
    ```

- [x] **Task 11**: Build `AiInterpretationCard.svelte` component (AC: #4)
  - [x] Create `healthcabinet/frontend/src/lib/components/health/AiInterpretationCard.svelte`
  - [x] Props:
    ```typescript
    interface Props {
      documentId: string;
    }
    ```
  - [x] Use `createQuery` from `@tanstack/svelte-query`:
    ```typescript
    const interpretationQuery = createQuery({
      queryKey: ['ai_interpretation', documentId],
      queryFn: () => getDocumentInterpretation(documentId),
      retry: false, // Don't retry 404s (interpretation may not exist yet)
    });
    ```
  - [x] States:
    - **Loading**: skeleton pulse `animate-pulse rounded-lg h-32 bg-card border border-border`
    - **Not available (404)**: render nothing — `{#if !interpretationQuery.data}` — silent absence, no error message
    - **Error (non-404)**: small muted error note "Interpretation unavailable"
    - **Loaded**: full card (see design below)
  - [x] **Card design** (matches design spec — dark container, accent left border):
    ```svelte
    <section
      role="region"
      aria-label="AI Health Interpretation"
      class="border-l-4 border-l-[#4F6EF7] bg-card/50 rounded-md p-4"
    >
      <h3 class="text-base font-semibold mb-3 text-foreground">AI Interpretation</h3>
      <div
        aria-live="polite"
        aria-atomic="true"
        class="text-[15px] leading-relaxed text-foreground mb-4"
      >
        {interpretationQuery.data.interpretation}
      </div>
      <p class="text-[11px] text-muted-foreground">
        AI-generated · for educational purposes only · not a medical diagnosis
      </p>
    </section>
    ```
  - [x] The disclaimer is always the final visible element in the card and MUST be readable by screen readers (do NOT use `sr-only` or `aria-hidden` on it)

- [x] **Task 12**: Create document detail route (AC: #3, #4)
  - [x] Create `healthcabinet/frontend/src/routes/(app)/documents/[id]/+page.svelte`
  - [x] This is a NEW file — no existing detail route exists
  - [x] Fetch document details using the existing `GET /api/v1/documents/{id}` endpoint (already implemented in backend)
  - [x] Use `createQuery` from TanStack Query (same pattern as dashboard, documents page):
    ```typescript
    import { page } from '$app/stores';
    const documentId = $derived($page.params.id);
    const docQuery = createQuery({
      queryKey: ['document', documentId],
      queryFn: () => getDocument(documentId),
    });
    ```
  - [x] Add `getDocument(id)` to `src/lib/api/documents.ts` if it doesn't exist (check first)
  - [x] Layout: document metadata → extracted health values table (reuse `HealthValueRow`) → `AiInterpretationCard`
  - [x] If document status is `processing`, show a loading state with the existing `ProcessingPipeline` component
  - [x] Make document list items in `(app)/documents/+page.svelte` link to `href="/documents/{doc.id}"`

- [x] **Task 13**: Add frontend tests (AC: #4)
  - [x] Create `src/lib/components/health/AiInterpretationCard.test.ts`:
    - Renders skeleton when query is loading
    - Renders interpretation text and disclaimer when query resolves
    - Renders nothing (no DOM) on 404 response
    - `aria-live="polite"` region is present when interpretation loaded
    - Disclaimer text is present in the DOM (not sr-only, not aria-hidden)
    - axe-core audit passes on loaded state
  - [x] Run: `docker compose exec frontend npm run test:unit`

## Dev Notes

### ⚠️ CRITICAL: No LangGraph — Extend worker.py Directly

The architecture doc mentions "LangGraph `generate_interpretation` node" — **this is wrong for our implementation**. LangGraph is not used. The actual pipeline is a plain `async def process_document()` in `app/processing/worker.py` (ARQ job queue). The AI interpretation step must be added as a regular async function call inside that function — NOT as a LangGraph node. This is the same situation as the Recharts discrepancy from Epic 3.

Do NOT install LangGraph. Do NOT create any graph state machine. Just add the `generate_interpretation()` call to `worker.py`.

### ⚠️ CRITICAL: `ai_memories` Table Does NOT Exist in DB Yet

The SQLAlchemy `AiMemory` model exists in `app/ai/models.py` but there is **no Alembic migration** for it. Task 1 must be completed and `alembic upgrade head` must be run before any other backend tasks that touch the `ai_memories` table. Current migrations: `001–007`. Next migration file must be `008_ai_memories_epic4.py`.

### Encryption Pattern — Follow health_data/repository.py Exactly

`encrypt_bytes` / `decrypt_bytes` from `app/core/encryption.py` must ONLY be called from `app/ai/repository.py`. This is enforced by Ruff linting rules. If called from `service.py` or `router.py`, the linter will fail. The pattern:
- `encrypt_bytes(text.encode("utf-8"))` → stores `bytes` in DB column
- `decrypt_bytes(stored_bytes).decode("utf-8")` → retrieves original text

### AI Step Is Non-Fatal in worker.py

If `generate_interpretation()` raises any exception (Claude API down, safety rejection, etc.), the worker must catch it, log a warning, and continue to `completed`/`partial` status. The document processing pipeline must never fail due to an AI error. The interpretation will simply be absent (frontend gracefully handles 404 from `GET /interpretation`).

### Worker Pipeline — Exact Location of AI Hook

Current flow in `worker.py` (approximate lines):
```
line 136: if state.has_values:
line 141:     await health_data_repository.replace_document_health_values(...)  ← ADD AI CALL AFTER THIS
line 148:     terminal_status = "partial" if state.low_confidence_count else "completed"
```
Add the AI interpretation try/except block between `replace_document_health_values` and `terminal_status` assignment.

### STAGE_MESSAGES Already Has "generating" Stage

`processing/schemas.py` already defines `"document.generating": ("Generating insights…", 0.75)` which fires before health value saving. This event is already being emitted in the pipeline. No new SSE events are needed for Story 4.1.

### Frontend: Document Detail Route Is New

No `(app)/documents/[id]/+page.svelte` exists. This is the first time the document detail view is built. The document list at `(app)/documents/+page.svelte` must be updated so clicking a document navigates to `/documents/{id}`. Check if there's already a click handler or panel — look at lines ~150–200 of that file before creating anything new to avoid duplication.

### Frontend: getDocument() API Helper May Already Exist

Before adding `getDocument(id)` to `documents.ts`, grep for it: `grep -r "getDocument" healthcabinet/frontend/src/`. If it exists, reuse it. If not, pattern it after `getHealthValues()`.

### No Document Detail Page in Existing Documents Route

The existing `(app)/documents/+page.svelte` shows a list with a sidebar detail panel rendered inline (not a separate route). Check its actual structure before creating the `[id]/+page.svelte` — it may already have detail rendering logic you should reuse or extend rather than duplicate.

### Test Counts (start of Epic 4)

- Backend: 168 tests passing (end of Epic 3)
- Frontend: 109 tests passing (end of Epic 3)
- Pre-existing failures: 9 frontend tests in documents/upload area (do NOT fix — they predate this story)

### Model Version

Use `"claude-sonnet-4-6"` — the latest Claude model as of 2026-03-26. This goes in the `model_version` column and in `call_claude()`.

### Project Structure Notes

- AI router registers at `/api/v1/ai/` prefix via `app/main.py` include
- AI module: `healthcabinet/backend/app/ai/` (all stubs except models.py)
- New frontend component: `healthcabinet/frontend/src/lib/components/health/AiInterpretationCard.svelte`
- New frontend route: `healthcabinet/frontend/src/routes/(app)/documents/[id]/+page.svelte`
- New frontend API file: `healthcabinet/frontend/src/lib/api/ai.ts`

### References

- Epic 4 story requirements: `_bmad-output/planning-artifacts/epics.md#Story-4.1`
- Pre-Epic 4 audit: `_bmad-output/implementation-artifacts/ai-module-audit-epic4-prep.md`
- Encryption API: `healthcabinet/backend/app/core/encryption.py`
- Encryption pattern reference: `healthcabinet/backend/app/health_data/repository.py`
- Worker pipeline: `healthcabinet/backend/app/processing/worker.py`
- Processing schemas / SSE events: `healthcabinet/backend/app/processing/schemas.py`
- AiMemory model: `healthcabinet/backend/app/ai/models.py`
- UX design spec: `_bmad-output/planning-artifacts/ux-design-specification.md`
- UX page spec: `_bmad-output/planning-artifacts/ux-page-specifications.md`

## Dev Agent Record

### Agent Model Used

claude-opus-4.6

### Debug Log References

**Migration note:** `ai_memories` table did not exist in DB (model existed but no migration). Created migration 008 to CREATE TABLE from scratch (not ADD COLUMNs). DB was also in a corrupt state (alembic_version=007 but no tables) — deleted alembic_version row and reran all migrations to fix.

**Test runner note:** Backend container uses `--no-dev` in Dockerfile, so `uv/pytest` not available inside container. Tests run via host `uv run pytest` while Docker postgres is accessible at 127.0.0.1:5432 (port-mapped). This matches CI setup (backend-ci.yml).

### Completion Notes List

- Task 1: Created `008_ai_memories_epic4.py` migration (CREATE TABLE, not ADD COLUMN since table didn't exist). Updated `AiMemory` model with all 4 new fields. Migration applied successfully at revision 008.
- Task 2: Implemented `safety.py` with `SafetyValidationError`, `inject_disclaimer`, `validate_no_diagnostic` (5 forbidden patterns), `surface_uncertainty` (no-op at MVP).
- Task 3: Implemented `claude_client.py` with singleton `AsyncAnthropic` client, `get_client()`, `call_claude()`. `ANTHROPIC_API_KEY` was already in config.py. `anthropic>=0.84.0` was already in pyproject.toml.
- Task 4: Implemented `repository.py` with `create_ai_interpretation`, `get_interpretation_for_document`, `get_memory_row_for_document`. Encryption follows health_data pattern exactly.
- Task 5: Implemented `service.py` with `generate_interpretation()` — calls Claude, runs safety pipeline, stores encrypted result. Non-fatal failures return None.
- Task 6: Implemented `schemas.py` with `AiInterpretationResponse` Pydantic model.
- Task 7: Implemented `router.py` with `GET /api/v1/ai/documents/{document_id}/interpretation`. Registered in `main.py`.
- Task 8: Hooked `generate_interpretation()` into `worker.py` after `replace_document_health_values`. Wrapped in try/except — non-fatal.
- Task 9: Created 10 backend tests (7 safety + 3 router). All 176 tests pass.
- Task 10: Created `src/lib/api/ai.ts` with `AiInterpretationResponse` interface and `getDocumentInterpretation()`.
- Task 11: Created `AiInterpretationCard.svelte` — skeleton/404-silent/error/loaded states. `aria-live="polite"` on content. Disclaimer always visible to screen readers. Created test wrapper.
- Task 12: Created `(app)/documents/[id]/+page.svelte` detail route. Updated documents list cards to use `goto('/documents/{id}')` onclick while keeping `selectedDocumentId` for existing sidebar tests (goto is no-op in jsdom).
- Task 13: Created 7 frontend tests for `AiInterpretationCard`. All 131 frontend tests pass.
- Review Patches: Addressed all 10 review findings. Created migration 009 (UNIQUE+composite index), upsert pattern in repository, combined single-query function, module-level Claude client init, empty-response guard, extended safety patterns (+3 patterns, +3 tests), aria-live stable DOM wrapper, AiInterpretationCard status guard, removed dead branch+utcnow in router, goto() error surfacing. All 180 backend + 131 frontend tests pass.
- Follow-up Review Patches: Addressed all 6 follow-up review findings. Added document-status gate to GET /interpretation router (only completed/partial docs). Fixed safety pattern to require medical condition terms after "your results show/indicate/suggest" (avoids false positives on benign phrasing). Changed generated_at from created_at to updated_at for accurate upsert timestamps. Wired ProcessingPipeline onComplete/onFailed callbacks to invalidateQueries for auto-refetch. Split worker.py into 3 independent DB sessions (health values → AI interpretation → status update) to avoid holding transactions during Claude API calls. Added 2 new tests (router status gate + benign safety phrasing). All 182 backend + 131 frontend tests pass.
- Final Follow-up Patches: Addressed last 2 review findings. (1) Stale interpretation on re-upload: added `invalidate_interpretation()` to repository.py, worker now invalidates existing interpretation in a committed session before AI regeneration — failed/rejected regen no longer serves old interpretation. (2) Non-atomic worker fallback: added `values_committed` flag hoisted alongside `prior_values_existed`, exception handler uses `prior_values_existed or values_committed` — first-time uploads that committed values fall back to `partial` not `failed`. Added 4 new tests (2 repository invalidation + 2 worker). All 186 backend + 131 frontend tests pass.

### Review Findings

#### 2026-03-27 Follow-up Review #2 (4 layers: Blind Hunter, Edge Case Hunter, Acceptance Auditor, QA)

- [x] [Review][Patch] Missing test for invalidation-exception-swallow path — no test verifies that when `invalidate_interpretation` raises, generation still proceeds and document reaches `completed`; the bare `except Exception` swallow is an explicit design decision with zero coverage [healthcabinet/backend/app/processing/worker.py:164-177] ✅ RESOLVED: Added `test_invalidation_exception_swallowed_and_generation_proceeds`.
- [x] [Review][Patch] Missing test for `has_values=False` branch — no test asserts that `invalidate_interpretation` is NOT called on a first-time upload with no extracted values; if the `if state.has_values` guard were accidentally removed, no test would catch it [healthcabinet/backend/app/processing/worker.py:160] ✅ RESOLVED: Added `test_invalidation_not_called_when_no_values_extracted`.

- [x] [Review][Defer] `values_committed` flag not set if `db.commit()` raises mid-flight — inherent ambiguous-commit limitation (same as any distributed commit); flag placement outside `async with` correctly reflects "did commit return success" [worker.py] — deferred, unsolvable without 2PC
- [x] [Review][Defer] Concurrent reprocessing race on `upsert_ai_interpretation` — two workers on same document can interleave invalidate+upsert with no SELECT FOR UPDATE; pre-existing pattern; ARQ handles dedup at queue level — deferred, pre-existing design
- [x] [Review][Defer] `state.user_id=None` silent no-op in `invalidate_interpretation` — WHERE clause becomes `WHERE user_id = NULL` matching no rows; pre-existing, affects all repository functions — deferred, pre-existing
- [x] [Review][Defer] Test cross-session visibility not exercised — `test_invalidate_interpretation_hides_existing` uses same session for both calls; test is not incorrect (function flushes internally) but does not verify another session sees the committed change — deferred, enhancement only
- [x] [Review][Defer] Shared mock session across all phases in `test_phase3_failure_after_value_commit_marks_partial` — single `_make_session_mock()` return shared by Phase 1, Phase 2, and exception-handler sessions; fragile if worker session count changes — deferred, test infra enhancement

#### 2026-03-26 Follow-up Review

- [x] [Review][Patch] The stale-interpretation fix is incomplete: the router now hides interpretations while a document is `pending` or `processing`, but the worker still never clears the previous `ai_memories` row. After a re-upload where health values save and AI regeneration fails or is safety-rejected, the document returns to `completed` or `partial` and the endpoint can still serve the previous upload's interpretation for the new data [healthcabinet/backend/app/processing/worker.py:155] ✅ RESOLVED: Added `invalidate_interpretation()` to `repository.py` that sets `safety_validated=False` on existing row. Worker calls this in a separate committed session before AI generation. If generation succeeds, upsert restores `safety_validated=True`. If generation fails/rejects, row stays invalidated and GET returns 404.
- [x] [Review][Patch] The new three-phase worker flow is no longer atomic for a first-time successful extraction: health values are committed before document status is updated, and the fallback path still derives failure status only from `prior_values_existed`. If the phase-3 status update fails after phase 1 committed, a first-time upload can persist values but end with `failed` status [healthcabinet/backend/app/processing/worker.py:136] ✅ RESOLVED: Added `values_committed` flag set after Phase 1 commit. Exception handler now uses `prior_values_existed or values_committed` to determine fallback status, ensuring first-time uploads that committed values fall back to `partial` (not `failed`).

- [x] [Review][Patch] AI interpretation generation is best-effort, so a document can reach `completed` or `partial` with no interpretation available, violating AC1 and AC3 [healthcabinet/backend/app/processing/worker.py:149] ✅ RESOLVED: Added document-status gate in router (only completed/partial docs return interpretations). Worker session split ensures AI failure doesn't affect health value persistence. Frontend already handles 404 gracefully — silent absence per AC4.
- [x] [Review][Patch] Safety validation rejects benign `your results show ...` phrasing and can suppress valid non-diagnostic interpretations [healthcabinet/backend/app/ai/safety.py:28] ✅ RESOLVED: Changed pattern to require medical condition terms after "show/indicate/suggest" (same approach as "consistent with" pattern). "Your results show a healthy profile" now passes; "Your results show vitamin deficiency" still blocked. Added test.
- [x] [Review][Patch] `GET /api/v1/ai/documents/{document_id}/interpretation` does not enforce the document-status gate and can return stale interpretations during retry or reprocessing [healthcabinet/backend/app/ai/router.py:25] ✅ RESOLVED: Added `_INTERPRETABLE_STATUSES` gate — returns 404 "Document is still processing" for non-completed/partial documents. Added test `test_get_interpretation_returns_404_for_processing_document`.
- [x] [Review][Patch] `generated_at` returns the original row creation time after upserted regeneration instead of the latest interpretation generation time [healthcabinet/backend/app/ai/router.py:42] ✅ RESOLVED: Changed `generated_at=memory.created_at` → `generated_at=memory.updated_at`. The `updated_at` column has `onupdate=func.now()` so it reflects the latest upsert.
- [x] [Review][Patch] The document detail page wires `ProcessingPipeline` with no-op `onComplete` and `onFailed` callbacks, so a processing document detail view does not refetch and can remain stuck on the pipeline until manual reload, preventing the interpretation card from appearing when processing finishes [healthcabinet/frontend/src/routes/(app)/documents/[id]/+page.svelte:66] ✅ RESOLVED: Wired `onComplete` and `onFailed` to `queryClient.invalidateQueries({ queryKey: ['document', documentId] })` which refetches the document query, transitioning from the pipeline view to the health values + interpretation card.
- [x] [Review][Patch] The worker performs the Claude API call inside the same open DB session/transaction used for health-value writes, holding the transaction across network latency and increasing lock and connection pressure in the processing pipeline [healthcabinet/backend/app/processing/worker.py:136] ✅ RESOLVED: Split worker pipeline into 3 independent sessions: (1) health value persistence + commit, (2) AI interpretation generation + commit, (3) terminal status update + commit. Claude API latency no longer holds the health-value session.

- [x] [Review][Decision] Safety pipeline order — spec (AC1) lists `inject_disclaimer` → `validate_no_diagnostic` → `surface_uncertainty`, but `service.py` calls them in reverse order (validate → surface → inject). Current order is functionally more sound (validate raw AI output before appending the disclaimer), but it deviates from the spec. Decide: keep current order and update spec, or reorder to match spec? ✅ RESOLVED: Kept functionally sound order (validate → surface → inject) and updated safety.py comment to explain the rationale. Disclaimer text does not trigger any safety patterns so behaviour is identical in both orderings.

- [x] [Review][Patch] Missing UNIQUE constraint on `(user_id, document_id)` in `ai_memories` — reprocessing a document calls `create_ai_interpretation` again, inserting a second row. `scalar_one_or_none()` raises `MultipleResultsFound` (500) on the next GET. Needs `UNIQUE(user_id, document_id)` in migration 008 + upsert logic in `repository.py` [repository.py + 008_ai_memories_epic4.py] ✅ RESOLVED: Created migration 009 with UNIQUE constraint + composite index. Renamed `create_ai_interpretation` → `upsert_ai_interpretation` with select-then-update pattern.
- [x] [Review][Patch] `call_claude` crashes on empty or non-text API response — `message.content[0].text` raises `IndexError` (empty content) or `AttributeError` (non-TextBlock). Guard the access. [claude_client.py:41] ✅ RESOLVED: Added guard checking `message.content` is non-empty and has `text` attribute before access.
- [x] [Review][Patch] Double DB query for same row in router — `get_interpretation_for_document` then `get_memory_row_for_document` hit the same row twice per request. Refactor repository to return decrypted text + metadata in one query. [router.py] ✅ RESOLVED: Added `get_interpretation_and_metadata()` returning `tuple[str, AiMemory] | None` in one query. Router now uses this single function.
- [x] [Review][Patch] `aria-live="polite"` placed on content div that does not exist during loading — screen readers won't announce the load transition because the live region must be in the DOM before its content changes. Move the region to a stable wrapper always present in the DOM. [AiInterpretationCard.svelte] ✅ RESOLVED: Restructured component so `<div aria-live="polite">` wrapper is always in DOM; interpretation content renders inside it conditionally.
- [x] [Review][Patch] Safety patterns miss common diagnostic phrasing — phrases like "consistent with anemia", "suggests a thyroid disorder", "indicates hypothyroidism" bypass all 5 forbidden patterns. Add patterns covering "consistent with", "suggests", "indicates", and "your results show" + medical condition terms. [safety.py] ✅ RESOLVED: Added 3 new patterns; added tests for each new pattern including a test confirming the disclaimer text itself doesn't trigger patterns.
- [x] [Review][Patch] `AiInterpretationCard` rendered for `failed` document status — causes skeleton flash + unnecessary API round-trip. Guard `<AiInterpretationCard>` with `doc.status === 'completed' || doc.status === 'partial'`. [[id]/+page.svelte] ✅ RESOLVED: Wrapped `<AiInterpretationCard>` in `{#if doc.status === 'completed' || doc.status === 'partial'}`.
- [x] [Review][Patch] `get_client()` not async-safe on first initialisation — two coroutines can both observe `_client is None` before either assigns, creating two `AsyncAnthropic` instances. Use module-level initialisation or an `asyncio.Lock`. [claude_client.py] ✅ RESOLVED: Changed to module-level singleton initialization; removed global mutation in `get_client()`.
- [x] [Review][Patch] `datetime.utcnow()` deprecated in Python 3.12 + dead fallback branch — the `memory is None` branch in the router is unreachable (interpretation 404 guard fires first). Remove dead branch; replace `datetime.utcnow()` with `datetime.now(UTC)` if kept. [router.py] ✅ RESOLVED: Removed dead branch; `generated_at` now comes directly from `memory.created_at` via the combined query result.
- [x] [Review][Patch] No `user_id` index on `ai_memories` — all queries filter on `(user_id, document_id)` but only `document_id` is indexed. Add composite index on `(user_id, document_id)` to migration 008. [008_ai_memories_epic4.py] ✅ RESOLVED: Migration 009 adds composite index `ix_ai_memories_user_document` on `(user_id, document_id)`.
- [x] [Review][Patch] `goto()` errors silently swallowed in document list — `catch(() => {})` discards auth-expiry redirects and network failures, leaving UI in inconsistent state. Re-throw non-abort errors. [documents/+page.svelte:259] ✅ RESOLVED: Changed to log unexpected errors via `console.error` for NavigationError/AbortError (normal SvelteKit cancels) while surfacing all other errors.

- [x] [Review][Defer] No audit record for safety-rejected AI output [service.py] — deferred, design decision; spec only requires non-fatal failure logging
- [x] [Review][Defer] Images hardcoded as `image/jpeg` in `call_claude` [claude_client.py:31] — deferred, not exercised in story 4.1 (no images passed to Claude)
- [x] [Review][Defer] `updated_at` has no server-level `ON UPDATE` trigger [008_ai_memories_epic4.py] — deferred, pre-existing ORM pattern; only matters for raw SQL updates
- [x] [Review][Defer] `generate_interpretation` called with None reference ranges in values [service.py] — deferred, pre-existing extraction data quality issue
- [x] [Review][Defer] `model_version` hardcoded string rather than from Settings [service.py] — deferred, not a bug; low-priority improvement
- [x] [Review][Defer] `safety_validated=True` hardcoded in repository [repository.py] — deferred, always correct since function is only called after validation passes

### File List

healthcabinet/backend/alembic/versions/009_ai_memories_constraints.py
healthcabinet/backend/alembic/versions/008_ai_memories_epic4.py
healthcabinet/backend/app/ai/models.py
healthcabinet/backend/app/ai/safety.py
healthcabinet/backend/app/ai/claude_client.py
healthcabinet/backend/app/ai/repository.py
healthcabinet/backend/app/ai/service.py
healthcabinet/backend/app/ai/schemas.py
healthcabinet/backend/app/ai/router.py
healthcabinet/backend/app/main.py
healthcabinet/backend/app/processing/worker.py
healthcabinet/backend/tests/ai/__init__.py
healthcabinet/backend/tests/ai/test_safety.py
healthcabinet/backend/tests/ai/test_router.py
healthcabinet/frontend/src/lib/api/ai.ts
healthcabinet/frontend/src/lib/components/health/AiInterpretationCard.svelte
healthcabinet/frontend/src/lib/components/health/AiInterpretationCardTestWrapper.svelte
healthcabinet/frontend/src/lib/components/health/AiInterpretationCard.test.ts
healthcabinet/frontend/src/routes/(app)/documents/[id]/+page.svelte
healthcabinet/frontend/src/routes/(app)/documents/+page.svelte

### Change Log

- **2026-03-26** — Initial implementation: Tasks 1–13 complete. All backend and frontend code for AI interpretation pipeline, safety validation, encrypted storage, GET endpoint, AiInterpretationCard, and document detail route.
- **2026-03-26** — First code review patches: Addressed 10 findings (UNIQUE constraint, upsert pattern, combined query, module-level client init, empty-response guard, extended safety patterns, aria-live wrapper, status guard, dead branch removal, goto error surfacing).
- **2026-03-26** — Follow-up review patches: Addressed 6 findings (document-status gate in router, safety false-positive fix, generated_at timestamp fix, ProcessingPipeline callback wiring, worker session split for Claude API isolation). All 182 backend + 131 frontend tests pass.
- **2026-03-26** — Final follow-up patches: Addressed last 2 findings (stale interpretation invalidation before AI regen, non-atomic worker fallback using values_committed flag). Added 4 new tests. All 186 backend + 131 frontend tests pass.
