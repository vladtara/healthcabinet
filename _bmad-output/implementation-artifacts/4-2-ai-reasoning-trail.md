# Story 4.2: AI Reasoning Trail

Status: done

## Story

As a registered user,
I want to see which data informed each AI insight,
so that I can trust the interpretation and understand what it's based on.

## Acceptance Criteria

1. **Given** an AI interpretation has been generated for a document
   **When** the user views the `AiInterpretationCard`
   **Then** a "Show reasoning" toggle is visible but collapsed by default

2. **Given** a user expands the reasoning trail
   **When** the toggle is activated
   **Then** the source data behind each insight is shown:
   - Which biomarker values were referenced (name, value, unit, reference range)
   - The status of each value relative to its reference range (Normal / High / Low / Unknown)
   - (For users with 2+ uploads) which prior documents were compared, referenced by date

3. **Given** the reasoning trail expands
   **When** the content appears
   **Then** the expansion is announced via an `aria-live` region

4. **Given** the AI explicitly could not reliably interpret a value
   **When** the reasoning trail is shown
   **Then** that uncertainty is surfaced explicitly: "Insufficient data to interpret [value name] confidently"

5. **Given** a prior document's interpretation was used as context (cross-session RAG)
   **When** the reasoning trail is shown
   **Then** the prior document is referenced by date so the user can see which historical data informed the current insight
   *(Note: at Story 4.2, cross-session RAG is not yet implemented — `prior_documents_referenced` will always be an empty list. The schema and UI slot are built now so Story 4.4 can populate them without frontend changes.)*

6. **Given** the `reasoning` field is absent from an API response (old rows with no context stored, or safety rejection)
   **Then** the "Show reasoning" toggle is not rendered at all — no empty state, no error

## Tasks / Subtasks

### Backend

- [x] **Task 1**: Add reasoning schemas to `app/ai/schemas.py` (AC: #2, #4, #5)
  - [x] Add `ValueReasoning` and `ReasoningContext` Pydantic models:
    ```python
    from typing import Literal

    class ValueReasoning(BaseModel):
        name: str
        value: float
        unit: str | None
        ref_low: float | None
        ref_high: float | None
        status: Literal["normal", "high", "low", "unknown"]

    class ReasoningContext(BaseModel):
        values_referenced: list[ValueReasoning]
        uncertainty_flags: list[str]          # e.g. ["Insufficient data to interpret HbA1c confidently"]
        prior_documents_referenced: list[str]  # ISO date strings, always [] until Story 4.4
    ```
  - [x] Extend `AiInterpretationResponse` with the optional field:
    ```python
    class AiInterpretationResponse(BaseModel):
        document_id: uuid.UUID
        interpretation: str
        model_version: str | None
        generated_at: datetime
        reasoning: ReasoningContext | None = None   # ← ADD
    ```

- [x] **Task 2**: Implement `_build_reasoning_context()` in `app/ai/service.py` (AC: #2, #4)
  - [x] Add the helper (private — not called outside this module):
    ```python
    import json
    from app.processing.schemas import NormalizedHealthValue

    def _build_reasoning_context(values: list[NormalizedHealthValue]) -> dict:
        """Build structured reasoning context from normalised health values.

        The returned dict is JSON-serialisable and matches the ReasoningContext schema.
        Status logic:
          - "normal"  — value within [ref_low, ref_high] inclusive
          - "high"    — value > ref_high
          - "low"     — value < ref_low
          - "unknown" — reference range absent (ref_low or ref_high is None)
        """
        def _compute_status(v: NormalizedHealthValue) -> str:
            if v.reference_range_low is None or v.reference_range_high is None:
                return "unknown"
            if v.value < v.reference_range_low:
                return "low"
            if v.value > v.reference_range_high:
                return "high"
            return "normal"

        values_referenced = [
            {
                "name": v.canonical_biomarker_name,
                "value": v.value,
                "unit": v.unit,
                "ref_low": v.reference_range_low,
                "ref_high": v.reference_range_high,
                "status": _compute_status(v),
            }
            for v in values
        ]
        uncertainty_flags = [
            f"Insufficient data to interpret {v.canonical_biomarker_name} confidently"
            for v in values
            if v.reference_range_low is None and v.reference_range_high is None
        ]
        return {
            "values_referenced": values_referenced,
            "uncertainty_flags": uncertainty_flags,
            "prior_documents_referenced": [],
        }
    ```
  - [x] Call it inside `generate_interpretation()` — pass the result to `upsert_ai_interpretation()`:
    ```python
    # After safety pipeline, before upsert:
    reasoning = _build_reasoning_context(values)

    await ai_repository.upsert_ai_interpretation(
        db,
        user_id=user_id,
        document_id=document_id,
        interpretation_text=text,
        model_version="claude-sonnet-4-6",
        reasoning_json=reasoning,        # ← new kwarg
    )
    ```

- [x] **Task 3**: Extend `upsert_ai_interpretation()` in `app/ai/repository.py` to store reasoning (AC: #2)
  - [x] Add `reasoning_json: dict | None = None` parameter:
    ```python
    async def upsert_ai_interpretation(
        db: AsyncSession,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        interpretation_text: str,
        model_version: str,
        reasoning_json: dict | None = None,  # ← ADD
    ) -> AiMemory:
    ```
  - [x] Serialize and encrypt the reasoning before the select-then-update logic:
    ```python
    import json

    encrypted_reasoning: bytes | None = None
    if reasoning_json is not None:
        encrypted_reasoning = encrypt_bytes(json.dumps(reasoning_json).encode("utf-8"))
    ```
  - [x] Apply the encrypted reasoning in both the update branch and the insert branch:
    ```python
    # update branch:
    memory.context_json_encrypted = encrypted_reasoning

    # insert branch (AiMemory(...)):
    context_json_encrypted=encrypted_reasoning,
    ```
  - [x] **Encryption rule**: `encrypt_bytes` / `decrypt_bytes` are called ONLY from `repository.py`. The `reasoning_json` dict travels as plain Python dict from `service.py` into this function, where it is serialised + encrypted. Never serialise or call encrypt in `service.py`.

- [x] **Task 4**: Extend `get_interpretation_and_metadata()` in `app/ai/repository.py` to return reasoning (AC: #2, #6)
  - [x] Change the return type from `tuple[str, AiMemory] | None` to `tuple[str, dict | None, AiMemory] | None`:
    ```python
    async def get_interpretation_and_metadata(
        db: AsyncSession,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> tuple[str, dict | None, AiMemory] | None:
        """Return (decrypted_text, reasoning_dict_or_None, memory_row), or None if absent."""
    ```
  - [x] Decrypt and deserialise reasoning after decrypting the interpretation:
    ```python
    text = decrypt_bytes(memory.interpretation_encrypted).decode("utf-8")
    reasoning: dict | None = None
    if memory.context_json_encrypted is not None:
        try:
            reasoning = json.loads(
                decrypt_bytes(memory.context_json_encrypted).decode("utf-8")
            )
        except Exception:
            logger.warning("ai.reasoning_decrypt_failed", document_id=str(document_id))
            reasoning = None
    return text, reasoning, memory
    ```
  - [x] Add `import json` at the top of `repository.py` (it is not present yet)

- [x] **Task 5**: Update `app/ai/router.py` to include reasoning in the response (AC: #2, #6)
  - [x] Unpack the new 3-tuple return value from `get_interpretation_and_metadata()`:
    ```python
    result = await ai_repository.get_interpretation_and_metadata(
        db, user_id=current_user.id, document_id=document_id
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Interpretation not available")

    interpretation, reasoning_dict, memory = result   # ← was: interpretation, memory
    ```
  - [x] Pass reasoning into the response schema:
    ```python
    from app.ai.schemas import AiInterpretationResponse, ReasoningContext

    reasoning: ReasoningContext | None = None
    if reasoning_dict is not None:
        try:
            reasoning = ReasoningContext.model_validate(reasoning_dict)
        except Exception:
            logger.warning("ai.reasoning_schema_mismatch", document_id=str(document_id))
            reasoning = None

    return AiInterpretationResponse(
        document_id=document_id,
        interpretation=interpretation,
        model_version=memory.model_version,
        generated_at=memory.updated_at,
        reasoning=reasoning,            # ← ADD
    )
    ```

- [x] **Task 6**: Add backend tests (AC: #2, #4, #5, #6)
  - [x] In `tests/ai/test_repository.py` (create file if it doesn't exist):
    - `test_upsert_stores_reasoning_json` — call `upsert_ai_interpretation()` with `reasoning_json={"values_referenced": [...], ...}`, then call `get_interpretation_and_metadata()` and assert the returned dict matches
    - `test_upsert_stores_no_reasoning_when_none` — call with `reasoning_json=None`, assert returned reasoning dict is `None`
    - `test_reasoning_roundtrip_encrypted` — assert raw `context_json_encrypted` column value is bytes (not plaintext JSON), confirming encryption occurred
  - [x] In `tests/ai/test_router.py` (file exists — add to it):
    - `test_get_interpretation_includes_reasoning_when_present` — seed AiMemory with `context_json_encrypted` set, assert `GET /interpretation` response contains non-null `reasoning` field with `values_referenced`
    - `test_get_interpretation_reasoning_null_when_not_stored` — seed AiMemory with `context_json_encrypted=None`, assert response has `reasoning: null`
  - [x] Run: `docker compose exec backend uv run pytest tests/ai/ -v`

### Frontend

- [x] **Task 7**: Update `src/lib/api/ai.ts` with reasoning types (AC: #2, #4, #5, #6)
  - [x] Add TypeScript interfaces:
    ```typescript
    export type ValueStatus = 'normal' | 'high' | 'low' | 'unknown';

    export interface ValueReasoning {
      name: string;
      value: number;
      unit: string | null;
      ref_low: number | null;
      ref_high: number | null;
      status: ValueStatus;
    }

    export interface ReasoningContext {
      values_referenced: ValueReasoning[];
      uncertainty_flags: string[];
      prior_documents_referenced: string[];  // ISO date strings
    }
    ```
  - [x] Extend `AiInterpretationResponse`:
    ```typescript
    export interface AiInterpretationResponse {
      document_id: string;
      interpretation: string;
      model_version: string | null;
      generated_at: string;
      reasoning: ReasoningContext | null;   // ← ADD
    }
    ```

- [x] **Task 8**: Update `AiInterpretationCard.svelte` with reasoning toggle (AC: #1, #2, #3, #4, #5, #6)
  - [x] Add toggle state and imports in the `<script>` block:
    ```typescript
    import type { ReasoningContext, ValueReasoning, ValueStatus } from '$lib/api/ai';

    let showReasoning = $state(false);

    function statusLabel(status: ValueStatus): string {
      return { normal: 'Normal', high: 'High', low: 'Low', unknown: 'Unknown' }[status];
    }

    function statusClass(status: ValueStatus): string {
      return {
        normal:  'text-[#2DD4A0]',   // Optimal — design token
        high:    'text-[#E05252]',   // Action
        low:     'text-[#F08430]',   // Concerning
        unknown: 'text-muted-foreground',
      }[status];
    }
    ```
  - [x] Inside the loaded card (after the interpretation text `<div>` and before the disclaimer `<p>`), add the toggle and collapsible section:
    ```svelte
    {#if interpretationQuery.data.reasoning}
      <button
        type="button"
        class="mt-3 text-[13px] text-[#4F6EF7] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#4F6EF7]"
        aria-expanded={showReasoning}
        aria-controls="reasoning-panel"
        onclick={() => (showReasoning = !showReasoning)}
      >
        {showReasoning ? 'Hide reasoning' : 'Show reasoning'}
      </button>

      <div
        id="reasoning-panel"
        aria-live="polite"
        aria-atomic="false"
        class="mt-3 {showReasoning ? '' : 'hidden'}"
      >
        {#if showReasoning}
          {@const r = interpretationQuery.data.reasoning}

          <!-- Values table -->
          {#if r.values_referenced.length > 0}
            <table class="w-full text-[13px] mb-3 border-collapse">
              <caption class="sr-only">Biomarker values used in this interpretation</caption>
              <thead>
                <tr class="text-left text-muted-foreground border-b border-border">
                  <th class="pb-1 pr-3 font-medium">Biomarker</th>
                  <th class="pb-1 pr-3 font-medium">Value</th>
                  <th class="pb-1 pr-3 font-medium">Reference range</th>
                  <th class="pb-1 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {#each r.values_referenced as v (v.name)}
                  <tr class="border-b border-border/40">
                    <td class="py-1 pr-3 text-foreground">{v.name}</td>
                    <td class="py-1 pr-3 text-foreground">{v.value}{v.unit ? ` ${v.unit}` : ''}</td>
                    <td class="py-1 pr-3 text-muted-foreground">
                      {v.ref_low != null && v.ref_high != null
                        ? `${v.ref_low}–${v.ref_high}`
                        : '—'}
                    </td>
                    <td class="py-1 {statusClass(v.status)} font-medium">
                      {statusLabel(v.status)}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}

          <!-- Uncertainty flags -->
          {#if r.uncertainty_flags.length > 0}
            <ul class="text-[12px] text-muted-foreground space-y-0.5 mb-3">
              {#each r.uncertainty_flags as flag (flag)}
                <li class="flex items-start gap-1">
                  <span aria-hidden="true">⚠</span>
                  <span>{flag}</span>
                </li>
              {/each}
            </ul>
          {/if}

          <!-- Prior documents -->
          {#if r.prior_documents_referenced.length > 0}
            <p class="text-[12px] text-muted-foreground">
              Prior documents referenced:
              {r.prior_documents_referenced.join(', ')}
            </p>
          {/if}
        {/if}
      </div>
    {/if}
    ```
  - [x] The `aria-live="polite"` wrapper on `#reasoning-panel` announces the expansion to screen readers. The outer `aria-live="polite"` on the card root still handles interpretation load announcement — both regions coexist fine because they serve different content.
  - [x] Status color rules:
    - Normal → `#2DD4A0` (Optimal design token)
    - High → `#E05252` (Action design token)
    - Low → `#F08430` (Concerning design token)
    - Unknown → `text-muted-foreground`
  - [x] Color is NEVER used as the sole indicator — `statusLabel()` always pairs the color class with the text label.

- [x] **Task 9**: Add frontend tests (AC: #1, #2, #3, #4, #6)
  - [x] In `src/lib/components/health/AiInterpretationCard.test.ts` (file exists — add to it):
    - `renders no toggle when reasoning is null` — mock response with `reasoning: null`, assert no `[aria-expanded]` button in DOM
    - `renders toggle when reasoning is present` — mock with reasoning containing 1 value, assert toggle button visible
    - `panel is hidden by default` — mock with reasoning, assert panel has `hidden` class before any click
    - `panel becomes visible after toggle click` — click toggle, assert hidden class removed, table row visible
    - `aria-expanded reflects open state` — assert `aria-expanded="false"` before click, `aria-expanded="true"` after
    - `uncertainty flags render when present` — mock reasoning with `uncertainty_flags: ["Insufficient data..."]`, assert text in DOM
    - `axe-core passes on expanded state` — open panel, run axe audit
  - [x] Run: `docker compose exec frontend npm run test:unit`

## Dev Notes

### No New Alembic Migration Needed

`context_json_encrypted` is **already in the database** — added by migration `008_ai_memories_epic4.py` (line 45):
```python
sa.Column("context_json_encrypted", sa.LargeBinary(), nullable=True)
```
The column exists but was never populated (always NULL for existing rows). Story 4.2 starts writing to it. No `alembic revision` or `alembic upgrade` is needed.

### Return Type Change in `get_interpretation_and_metadata()`

The function currently returns `tuple[str, AiMemory] | None`. After Task 4 it returns `tuple[str, dict | None, AiMemory] | None` (3-tuple). This is a **breaking internal change** — the router is the only caller. Update the router's destructuring in the same PR. No external callers exist (confirmed by grep).

Before editing `repository.py`, grep for all callers:
```bash
grep -r "get_interpretation_and_metadata" healthcabinet/backend/
```
Expected: exactly `app/ai/router.py` and `tests/ai/test_router.py`.

### Encryption Rule — Same as Story 4.1

`encrypt_bytes` / `decrypt_bytes` are called ONLY from `app/ai/repository.py`. The `reasoning_json: dict` flows from `service.py` as a plain Python dict — `repository.py` handles `json.dumps()` + `encrypt_bytes()`. This is the same pattern as `interpretation_text: str`.

### Status Logic Is Local — No Claude Call for Reasoning

The reasoning context is computed purely from the `NormalizedHealthValue` list that already exists in memory at interpretation time — no additional Claude API call is needed. `_build_reasoning_context()` is deterministic Python logic.

### Uncertainty Flags: Only Values with No Ref Range

An uncertainty flag is generated only when **both** `reference_range_low` and `reference_range_high` are `None`. A value with one bound set (e.g., only `reference_range_low`) is NOT flagged — status computation handles it as `unknown` but this is the rarer case. Keep the flag threshold strict to avoid false positives.

### Prior Documents — Always Empty at Story 4.2

`prior_documents_referenced` will always be `[]` until Story 4.4 (cross-upload pattern detection) implements cross-session RAG. The slot is built now in the schema, JSON, and UI so that Story 4.4 can populate it from backend without any frontend changes.

### Frontend Color Tokens

Use these design token values verbatim — same as `HealthStatusBadge`:
- Optimal/Normal: `#2DD4A0`
- Borderline: `#F5C842` (not used for reasoning status)
- Concerning/Low: `#F08430`
- Action/High: `#E05252`

Color is NEVER the sole indicator. Always pair with text: Normal / High / Low / Unknown.

### Toggle Button: No shadcn — Use Plain `<button>`

The toggle is a plain `<button type="button">` with Tailwind classes. Do not use a shadcn `Button` component variant — keep the interaction lightweight and avoid importing the button component just for a toggle.

### `aria-live` on Reasoning Panel

The reasoning panel itself carries `aria-live="polite"` so that expansion is announced. The outer card `aria-live="polite"` region only wraps the interpretation text and fires on initial load — it does not wrap the reasoning toggle, so there is no duplicate announcement.

Use `aria-atomic="false"` on the reasoning panel (not `true`) because screen readers should read added content naturally rather than re-reading the entire panel on any update.

### Test Counts (start of Story 4.2)

- Backend: tests pass at end of Story 4.1 (exact count depends on Story 4.1 patches — check with `docker compose exec backend uv run pytest --co -q | tail -3` before starting)
- Frontend: 109 tests passing (end of Epic 3 baseline; Story 4.1 added frontend tests)

### Existing Test File Locations

- `tests/ai/test_router.py` — exists, has 5+ tests; add the 2 new reasoning tests here
- `tests/ai/test_repository.py` — check if it exists first; create if not
- `src/lib/components/health/AiInterpretationCard.test.ts` — exists; add 7 new tests

## Dev Agent Record

### Agent Model Used

gpt-5-codex

### Debug Log References

- `docker compose exec backend uv run pytest ...` failed because the backend container does not have `uv` on `PATH`; backend validation was rerun successfully via host `uv run ...` inside `healthcabinet/backend`.
- Full-suite validation completed for backend tests and frontend unit tests.
- Full-repo `uv run ruff check .`, `npm run check`, and `npm run lint` still report pre-existing repository/tooling issues outside this story's change set:
  - Backend Ruff: existing unrelated findings in Alembic, documents, health-data, and older tests.
  - Frontend check: existing unrelated errors in `src/lib/api/auth.ts`, `vite.config.ts`, and `src/routes/(app)/settings/+page.svelte`.
  - Frontend lint: existing Prettier/plugin failures across many Svelte files and generated `build/` artifacts.
- Targeted checks for the Story 4.2 AI change set pass:
  - `uv run pytest tests/ai/ -q`
  - `uv run ruff check app/ai/... tests/ai/...`
  - `uv run mypy app/ai/claude_client.py app/ai/safety.py app/ai/repository.py app/ai/service.py app/ai/schemas.py`
  - `docker compose exec frontend npm run test:unit`
- Follow-up review-patch validation completed after resolving open findings:
  - `uv run pytest tests/ai/test_router.py -q` → `10 passed`
  - `uv run pytest tests/ai/ -q` → `26 passed`
  - `npm run test:unit -- --run src/lib/components/health/AiInterpretationCard.test.ts` → `18 passed`
  - `git diff --check` → passed
  - Vitest/JSDOM still emits the pre-existing `axe-core` canvas stderr (`HTMLCanvasElement.getContext()` not implemented), but the accessibility assertions and test run pass.
- Full completion-gate regression rerun completed on `2026-03-28`:
  - `uv run pytest -q` → `196 passed, 2 warnings`
  - `npm run test:unit` → `142 passed`
  - `uv run ruff check app/ai/claude_client.py app/ai/safety.py app/ai/repository.py app/ai/service.py app/ai/router.py app/ai/schemas.py tests/ai/test_repository.py tests/ai/test_router.py tests/ai/test_service.py` → passed
  - `uv run mypy app/ai/claude_client.py app/ai/safety.py app/ai/repository.py app/ai/service.py app/ai/schemas.py` → passed
  - Backend emits 2 pre-existing `httpx` cookie deprecation warnings in auth tests; frontend suite still emits the known JSDOM `axe-core` canvas stderr and existing jsdom navigation stderr in documents-page tests, but the full suite passes.

### Completion Notes List

- Added `ValueReasoning` and `ReasoningContext` schemas plus optional `reasoning` on `AiInterpretationResponse`.
- Implemented `_build_reasoning_context()` in `app/ai/service.py` to compute status labels and uncertainty flags directly from `NormalizedHealthValue` records, with `prior_documents_referenced` reserved as an empty list for Story 4.4.
- Extended `upsert_ai_interpretation()` and `get_interpretation_and_metadata()` to encrypt/decrypt reasoning JSON in `context_json_encrypted` while keeping encryption confined to `repository.py`.
- Updated the AI interpretation router to validate/degrade reasoning payloads safely and return `reasoning: null` when data is missing or malformed.
- Added backend coverage for reasoning round-trip storage/encryption, router response serialization, and service-level reasoning status/uncertainty computation.
- Extended the frontend AI API types and added a reasoning toggle to `AiInterpretationCard.svelte`, collapsed by default, with a live-region announcement, status table, uncertainty messages, and future-ready prior document rendering.
- Added frontend tests for hidden-by-default behavior, toggle rendering, `aria-expanded`, uncertainty rendering, and expanded-state accessibility.
- Follow-up review patches resolved the remaining frontend/runtime issues by using duplicate-safe list keys, moving expansion announcements to a dedicated screen-reader live region, adding defensive status fallbacks, and removing the redundant `role="region"` accessibility warning on the named section.
- Added regression coverage for duplicate biomarker rows, duplicate uncertainty flags, reasoning-expansion announcements, unknown runtime statuses, and router graceful degradation when stored reasoning cannot be decrypted or validated.
- Re-ran the full backend and frontend regression suites on `2026-03-28` and advanced the story to `review` after the completion gates passed with no regressions.
- Validation summary:
  - `uv run pytest -q` → `194 passed`
  - `uv run pytest tests/ai/ -q` → `24 passed`
  - `docker compose exec frontend npm run test:unit` → `138 passed`
  - `uv run ruff check app/ai/claude_client.py app/ai/safety.py app/ai/repository.py app/ai/service.py app/ai/router.py app/ai/schemas.py tests/ai/test_repository.py tests/ai/test_router.py tests/ai/test_service.py` → passed
  - `uv run mypy app/ai/claude_client.py app/ai/safety.py app/ai/repository.py app/ai/service.py app/ai/schemas.py` → passed
  - Follow-up review patch validation:
    - `uv run pytest tests/ai/test_router.py -q` → `10 passed`
    - `uv run pytest tests/ai/ -q` → `26 passed`
    - `npm run test:unit -- --run src/lib/components/health/AiInterpretationCard.test.ts` → `18 passed`
    - `git diff --check` → passed
  - Full completion-gate rerun (`2026-03-28`):
    - `uv run pytest -q` → `196 passed, 2 warnings`
    - `npm run test:unit` → `142 passed`
    - `uv run ruff check app/ai/claude_client.py app/ai/safety.py app/ai/repository.py app/ai/service.py app/ai/router.py app/ai/schemas.py tests/ai/test_repository.py tests/ai/test_router.py tests/ai/test_service.py` → passed
    - `uv run mypy app/ai/claude_client.py app/ai/safety.py app/ai/repository.py app/ai/service.py app/ai/schemas.py` → passed

### File List

healthcabinet/backend/app/ai/claude_client.py
healthcabinet/backend/app/ai/repository.py
healthcabinet/backend/app/ai/router.py
healthcabinet/backend/app/ai/safety.py
healthcabinet/backend/app/ai/schemas.py
healthcabinet/backend/app/ai/service.py
healthcabinet/backend/tests/ai/test_repository.py
healthcabinet/backend/tests/ai/test_router.py
healthcabinet/backend/tests/ai/test_service.py
healthcabinet/frontend/src/lib/api/ai.ts
healthcabinet/frontend/src/lib/components/health/AiInterpretationCard.svelte
healthcabinet/frontend/src/lib/components/health/AiInterpretationCard.test.ts

### Review Findings

- [x] [Review][Patch] Reasoning disclosure state is never reset when `documentId` changes, so navigating between document detail pages can leave the next document expanded instead of collapsed by default [healthcabinet/frontend/src/lib/components/health/AiInterpretationCard.svelte:12] ✅ RESOLVED: Added `$effect(() => { documentId; showReasoning = false; reasoningAnnouncement = ''; })` to reset disclosure state on every documentId change. Added frontend regression test that rerenders with a new documentId and asserts the panel is collapsed.
- [x] [Review][Patch] The new hidden announcer sits inside an existing atomic live region, so expanding reasoning can still re-announce the entire AI card or produce duplicate screen-reader output instead of an isolated expansion announcement [healthcabinet/frontend/src/lib/components/health/AiInterpretationCard.svelte:71] ✅ RESOLVED: Moved `<p class="sr-only" aria-live="polite" aria-atomic="true">` outside the outer `<div aria-live="polite" aria-atomic="true">` wrapper so it is an independent live region. Added frontend structural test that asserts the announcer is not nested inside the outer atomic region.
- [x] [Review][Patch] `{#each value (value.name)}` — biomarker name used as Svelte key; duplicate names in one result set cause silent DOM reconciliation failures [AiInterpretationCard.svelte] ✅ RESOLVED: Replaced name-only keys with composite keys that include row index so duplicate biomarker names render deterministically. Added frontend regression coverage for duplicate biomarker rows.
- [x] [Review][Patch] `{#each flag (flag)}` — uncertainty flag string used as Svelte key; duplicate flags (from duplicate biomarkers) cause key collision and silently dropped list items [AiInterpretationCard.svelte] ✅ RESOLVED: Replaced flag-string keys with duplicate-safe composite keys. Added frontend regression coverage for duplicate uncertainty messages.
- [x] [Review][Patch] `statusLabel()`/`statusClass()` return `undefined` for any status value not in the map literal — no fallback; renders blank cell if backend adds a new status value [AiInterpretationCard.svelte] ✅ RESOLVED: Switched to explicit `switch` fallbacks so unknown runtime statuses degrade to `Unknown` + `text-muted-foreground`. Added frontend regression coverage for unexpected runtime statuses.
- [x] [Review][Patch] Inner `aria-live="polite"` panel wrapped with `class:hidden` (Tailwind `display:none`) — content injected into a hidden live region may not be announced by screen readers; violates AC3 [AiInterpretationCard.svelte:72-77] ✅ RESOLVED: Moved the expansion announcement to a dedicated always-present screen-reader live region and kept the visual panel separate. Added a frontend test that asserts the live-region announcement on expand.
- [x] [Review][Patch] No tests for router silent-failure paths: `ai.reasoning_decrypt_failed` (decrypt exception) and `ai.reasoning_schema_mismatch` (Pydantic validation failure) paths have zero test coverage [tests/ai/test_router.py] ✅ RESOLVED: Added router tests for invalid encrypted reasoning bytes and schema-invalid reasoning payloads; both paths now return `reasoning: null` with HTTP 200 as intended.
- [x] [Review][Defer] `upsert_ai_interpretation(reasoning_json=None)` overwrites previously-stored reasoning with NULL; safe today (only one caller, always passes reasoning), but fragile if callers diverge — deferred, pre-existing design choice
- [x] [Review][Defer] Bare `except Exception` in `repository.py` and `router.py` degrades silently without distinguishing decrypt failure from absent data; intentional per spec graceful-degradation requirement — deferred, pre-existing
- [x] [Review][Defer] `json.dumps` default encoder permits NaN/Infinity (produces non-standard JSON that `json.loads` later rejects); low risk given controlled internal types — deferred, pre-existing data-quality concern
- [x] [Review][Defer] `decrypt_bytes(memory.interpretation_encrypted)` (pre-existing line) has no exception guard; corruption raises unhandled 500 — deferred, pre-existing not introduced by 4.2
- [x] [Review][Defer] `prior_documents_referenced: list[str]` will render raw strings (possibly UUIDs or internal IDs) without formatting when Story 4.4 populates it — deferred, Story 4.4 owns presentation
- [x] [Review][Defer] `upsert_ai_interpretation` SELECT-then-INSERT race: two concurrent workers for the same (user_id, document_id) can both see no row and both attempt INSERT, hitting the UNIQUE constraint as an unhandled IntegrityError — deferred, pre-existing concurrency pattern; low practical risk [healthcabinet/backend/app/ai/repository.py]
- [x] [Review][Defer] Safety rejection permanently hides invalidated row: if `invalidate_interpretation` is called before regeneration and Claude's output is rejected by the safety pipeline, the row stays `safety_validated=False` with no recovery path — deferred, intentional design per function docstring [healthcabinet/backend/app/ai/service.py + repository.py]
- [x] [Review][Defer] `memory.updated_at` used for `generated_at` in router; if the column has no `server_default` (only `onupdate`), a freshly-inserted row has `updated_at=None`, causing Pydantic validation failure — deferred, tests pass and model likely has server_default [healthcabinet/backend/app/ai/router.py]
- [x] [Review][Defer] Anthropic client singleton initialised at module import time — requires `ANTHROPIC_API_KEY` at import, removing the lazy-init window previously used by tests — deferred, intentional simplification, all 196 backend tests pass [healthcabinet/backend/app/ai/claude_client.py]
- [x] [Review][Defer] Outer `<div aria-live="polite" aria-atomic="true">` still wraps the reasoning panel; when reasoning is expanded, DOM mutations inside the atomic region could cause some screen readers to re-announce the entire card — deferred, pre-existing outer-wrapper scope issue not introduced by 4.2 [healthcabinet/frontend/src/lib/components/health/AiInterpretationCard.svelte]

### Change Log

- **2026-03-27** — Implemented Story 4.2 AI reasoning trail across backend storage/response plumbing and the `AiInterpretationCard` UI, including reasoning schemas, encrypted context persistence, router serialization, and reasoning toggle UX.
- **2026-03-27** — Added backend and frontend test coverage for reasoning round-trip storage, router responses, reasoning status computation, toggle behavior, and accessibility.
- **2026-03-27** — Ran full backend regression (`194 passed`) and full frontend unit regression (`138 passed`); documented unrelated existing repo/tooling failures from whole-repo lint/check commands.
- **2026-03-27** — Applied follow-up review patches to resolve duplicate-key rendering hazards, reasoning live-region accessibility, defensive status fallbacks, redundant Svelte accessibility warning, and missing router graceful-degradation coverage. Follow-up validation: `10` targeted router tests passed, `26` AI backend tests passed, `18` `AiInterpretationCard` unit tests passed.
- **2026-03-28** — Re-ran completion-gate validation and moved the story to `review`. Current full-suite results: `uv run pytest -q` → `196 passed, 2 warnings`; `npm run test:unit` → `142 passed`; targeted AI `ruff` and `mypy` checks passed.
- **2026-03-28** — Code review reopened the story with 2 new frontend follow-up patches: reset reasoning disclosure state on document changes, and narrow the live-region scope so expanding reasoning does not re-announce the entire card.
- **2026-03-28** — Resolved final 2 review findings: added `$effect` to reset `showReasoning`/`reasoningAnnouncement` on `documentId` change; moved SR announcer `<p>` outside the outer atomic live region. Added 2 new frontend tests (20 total for `AiInterpretationCard`). Full suite: `npm run test:unit` → `144 passed`.
