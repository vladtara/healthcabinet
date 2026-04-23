# Story 4.4: Cross-Upload Pattern Detection

Status: done  <!-- code review round 2 complete: 2026-03-30 -->

## Story

As a **registered user with multiple uploads**,
I want the AI to detect patterns across my upload history and surface notable observations,
so that I can catch trends my doctor might miss between appointments.

## Acceptance Criteria

1. **Given** a user has 2 or more processed documents with `safety_validated=True` AI interpretations
   **When** `GET /api/v1/ai/patterns` is called by an authenticated user
   **Then** cross-upload patterns are detected (e.g., a biomarker consistently trending in one direction)
   **And** the response includes a list of `PatternObservation` objects, each with: a plain-language description, the document dates it spans, and a "discuss with your healthcare provider" recommendation
   **And** all pattern descriptions pass through `validate_no_diagnostic()` before being returned

2. **Given** a pattern is detected
   **Then** it never states a diagnosis or recommends specific medications or treatments
   **And** the recommendation field always reads "Discuss this pattern with your healthcare provider."

3. **Given** a user has only one processed document (or zero)
   **When** `GET /api/v1/ai/patterns` is called
   **Then** `{ "patterns": [] }` is returned (section simply absent on frontend — no empty or error state)

4. **Given** an unauthenticated request hits `GET /api/v1/ai/patterns`
   **When** the request is processed
   **Then** `401 Unauthorized` is returned

5. **Given** the PatternCard renders on the document detail page
   **When** the patterns API returns an empty list
   **Then** the PatternCard section is entirely absent from the DOM (no empty state, no placeholder)

## Tasks / Subtasks

### Backend

- [x] **Task 1: Add `PatternObservation` and `AiPatternsResponse` schemas** (AC: #1, #3)
  - [x] In `healthcabinet/backend/app/ai/schemas.py`, add:
    ```python
    class PatternObservation(BaseModel):
        description: str
        document_dates: list[str]  # ISO date strings, e.g. ["2025-01-15", "2025-06-20"]
        recommendation: str        # always "Discuss this pattern with your healthcare provider."

    class AiPatternsResponse(BaseModel):
        patterns: list[PatternObservation]
    ```
  - [x] Do NOT add a `document_ids` field — frontend does not need to link back to specific documents

- [x] **Task 2: Extend `list_user_ai_context()` to include `updated_at`** (AC: #1)
  - [x] In `healthcabinet/backend/app/ai/repository.py`, inside `list_user_ai_context()`, add `updated_at` to each returned entry dict:
    ```python
    entry: dict[str, object] = {
        "document_id": str(row.document_id),
        "interpretation": interpretation,
        "updated_at": row.updated_at.date().isoformat() if row.updated_at else None,
    }
    ```
  - [x] This is backward-compatible: Story 4.3's `_build_follow_up_prompt()` ignores unknown keys
  - [x] Do NOT modify the function signature or return type annotation (it returns `list[dict[str, object]]`)

- [x] **Task 3: Implement `detect_cross_upload_patterns()` service function** (AC: #1, #2, #3)
  - [x] In `healthcabinet/backend/app/ai/service.py`, add:
    ```python
    async def detect_cross_upload_patterns(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> AiPatternsResponse:
        """Detect cross-upload health patterns for a user. Returns empty list if < 2 documents."""
    ```
  - [x] Logic:
    1. Call `await ai_repository.list_user_ai_context(db, user_id=user_id)` — already filters `safety_validated=True` rows
    2. If `len(context_rows) < 2`, return `AiPatternsResponse(patterns=[])`
    3. Build prompt from context rows (include document dates from `updated_at` key)
    4. Call `raw_text = await call_claude(prompt)`
    5. Extract JSON array from `raw_text` (Claude may wrap in markdown code blocks — strip ` ```json ` / ` ``` ` wrappers before `json.loads()`)
    6. For each raw pattern dict, run `await validate_no_diagnostic(pattern["description"])` — if it raises `SafetyValidationError`, skip that pattern (log warning, continue)
    7. Build `PatternObservation` list; ensure `recommendation` is always "Discuss this pattern with your healthcare provider." (override Claude's value if needed)
    8. Return `AiPatternsResponse(patterns=[...])`
    9. On `json.loads()` failure or any unexpected error: log warning, return `AiPatternsResponse(patterns=[])` — NEVER raise 500
  - [x] **Pattern analysis prompt** (add as module constant `_PATTERN_DETECTION_PROMPT_TEMPLATE`):
    ```python
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

    Return ONLY a valid JSON array with this exact structure (no prose, no markdown fences):
    [
      {{
        "description": "Your TSH has increased across three consecutive results",
        "document_dates": ["2024-09-15", "2025-01-20", "2025-06-10"],
        "recommendation": "Discuss this pattern with your healthcare provider."
      }}
    ]
    """
    ```
  - [x] **Context section builder** (private helper `_build_pattern_context`):
    ```python
    def _build_pattern_context(context_rows: list[dict[str, object]]) -> str:
        parts = []
        for i, row in enumerate(context_rows, start=1):
            date = str(row.get("updated_at", "unknown date"))
            interp = str(row.get("interpretation", ""))
            parts.append(f"[Document {i} — {date}]\n{interp}")
        return "\n\n".join(parts)
    ```
  - [x] **JSON extraction helper** (private `_extract_json_array`):
    ```python
    import json, re
    def _extract_json_array(text: str) -> list[dict]:
        # Strip markdown code fences if present
        text = re.sub(r"```(?:json)?\s*", "", text).strip()
        return json.loads(text)
    ```
  - [x] Do NOT call `inject_disclaimer()` on patterns — the recommendation field already fulfils the non-diagnostic framing requirement. Do NOT call `surface_uncertainty()` on pattern text.
  - [x] `call_claude()` reuses the existing singleton client and model string `claude-sonnet-4-6` — do NOT hardcode a second model string

- [x] **Task 4: Add `GET /api/v1/ai/patterns` router endpoint** (AC: #1, #3, #4)
  - [x] In `healthcabinet/backend/app/ai/router.py`, add:
    ```python
    from app.ai.schemas import AiPatternsResponse

    @router.get("/patterns", response_model=AiPatternsResponse)
    async def get_patterns(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> AiPatternsResponse:
        return await ai_service.detect_cross_upload_patterns(db, user_id=current_user.id)
    ```
  - [x] No document_id parameter — patterns are user-level, not document-level
  - [x] No additional DB call in the router — delegate fully to service
  - [x] Auth is via existing `get_current_user` dependency → 401 behavior is consistent

- [x] **Task 5: Add backend tests** (AC: #1, #2, #3, #4)
  - [x] In `healthcabinet/backend/tests/ai/test_service.py`, add:
    - `test_detect_patterns_returns_empty_when_fewer_than_two_documents` — mock `list_user_ai_context` returning 0 or 1 row; assert `patterns == []`, Claude not called
    - `test_detect_patterns_calls_claude_and_returns_observations` — mock 2 context rows + mock `call_claude` returning valid JSON; assert `PatternObservation` fields populated
    - `test_detect_patterns_skips_safety_rejected_pattern` — mock Claude returning 2 patterns where one fails `validate_no_diagnostic`; assert only 1 pattern returned
    - `test_detect_patterns_returns_empty_on_json_parse_error` — mock `call_claude` returning non-JSON; assert `patterns == []` (no exception raised)
    - `test_detect_patterns_overrides_recommendation_field` — mock Claude returning wrong recommendation text; assert it is normalized to "Discuss this pattern with your healthcare provider."
  - [x] In `healthcabinet/backend/tests/ai/test_router.py`, add:
    - `test_get_patterns_requires_auth` — unauthenticated request returns 401
    - `test_get_patterns_returns_empty_list_for_single_document_user` — mock service returning empty; assert `{"patterns": []}`
    - `test_get_patterns_returns_observations` — mock service returning 1 pattern; assert shape matches `AiPatternsResponse`

### Frontend

- [x] **Task 6: Add `getAiPatterns()` API function** (AC: #1, #5)
  - [x] In `healthcabinet/frontend/src/lib/api/ai.ts`, add:
    ```typescript
    export interface PatternObservation {
      description: string;
      document_dates: string[];
      recommendation: string;
    }

    export interface AiPatternsResponse {
      patterns: PatternObservation[];
    }

    export async function getAiPatterns(): Promise<AiPatternsResponse> {
      return apiFetch<AiPatternsResponse>('/api/v1/ai/patterns');
    }
    ```
  - [x] Uses `apiFetch()` — this is a JSON endpoint, not a stream
  - [x] No document_id parameter — patterns are user-level

- [x] **Task 7: Create `PatternCard.svelte` component** (AC: #1, #2, #5)
  - [x] Create `healthcabinet/frontend/src/lib/components/health/PatternCard.svelte`
  - [x] Props:
    ```typescript
    interface Props {
      userId?: string; // optional, for cache key disambiguation if needed — not strictly required
    }
    ```
    Actually, no prop needed since patterns are user-level. Use a stable query key `['ai_patterns']`.
  - [x] Use `createQuery` with `queryKey: ['ai_patterns'] as const` and `queryFn: () => getAiPatterns()`
  - [x] **Rendering rules:**
    - When `patterns.length === 0` (or query pending/error): render **nothing** — no skeleton, no empty state
    - When 1+ patterns present: render a `<section>` for each pattern
  - [x] **Visual design** (distinct from `AiInterpretationCard`'s accent-blue border):
    ```svelte
    <section
      aria-label="Health Pattern Observation"
      class="mt-4 border-l-4 border-l-[#F08430] bg-card/50 rounded-md p-4"
    >
      <h3 class="text-base font-semibold mb-2 text-foreground">Pattern Observed</h3>
      <p class="text-[15px] leading-relaxed text-foreground mb-2">{pattern.description}</p>
      <p class="text-[12px] text-muted-foreground mb-1">
        Spans: {pattern.document_dates.join(' · ')}
      </p>
      <p class="text-[11px] text-muted-foreground">{pattern.recommendation}</p>
    </section>
    ```
  - [x] If multiple patterns, render one `<section>` per pattern, each with `mt-4`
  - [x] No aria-live needed — patterns are static content (not streaming)
  - [x] Do NOT add a loading skeleton — when pending/empty, nothing renders. If query errors, nothing renders (silent fail).
  - [x] Query `retry: false` — same pattern as `AiInterpretationCard`

- [x] **Task 8: Mount PatternCard on the document detail page** (AC: #5)
  - [x] In `healthcabinet/frontend/src/routes/(app)/documents/[id]/+page.svelte`, mount `<PatternCard />` directly below `<AiFollowUpChat documentId={doc.id} />` inside the `status === 'completed' || status === 'partial'` gate
  - [x] Import: `import PatternCard from '$lib/components/health/PatternCard.svelte';`
  - [x] `PatternCard` takes no props (patterns are user-level, not document-specific)
  - [x] Keep the current document detail route, processing-state gates, and all existing components unchanged

- [x] **Task 9: Add frontend tests for PatternCard** (AC: #1, #5)
  - [x] Create `healthcabinet/frontend/src/lib/components/health/PatternCard.test.ts`
  - [x] Use the same TestWrapper pattern as `AiFollowUpChatTestWrapper.svelte` — create `PatternCardTestWrapper.svelte`
  - [x] Cover:
    - renders nothing when patterns array is empty
    - renders nothing when query is pending (loading state)
    - renders a section for each pattern when 1+ patterns returned
    - pattern description text is visible
    - document dates are displayed
    - recommendation text is displayed
    - axe-core audit on loaded state with 1 pattern

## Dev Notes

### Architecture Compliance

- **Encryption boundary:** `repository.py` only — `detect_cross_upload_patterns()` in service.py never calls `encrypt_bytes()` or `decrypt_bytes()` directly. It calls `list_user_ai_context()` which handles decryption internally.
- **user_id source:** Always from `Depends(get_current_user)` in router — never from request body.
- **DB call in router:** FORBIDDEN — router delegates to service; service delegates to repository.
- **Model constant:** Use existing `"claude-sonnet-4-6"` from `claude_client.py`. Do NOT hardcode a new string.
- **Anti-pattern prevention:** Do NOT add a new Anthropic client or API key configuration — reuse the existing singleton from `claude_client.py`.

### No Migration Required

- Pattern detection is on-demand (computed per request, not stored).
- `list_user_ai_context()` already loads all user's `safety_validated=True` rows.
- Adding `updated_at` to the returned dict is backward compatible — Story 4.3's `_build_follow_up_prompt()` ignores unknown keys in context row dicts.
- `AiMemory.document_id` nullable affordance is NOT used in this story — no `ai_memories` writes.

### Safety Pipeline for Patterns

For pattern text, the pipeline differs from Story 4.1/4.3:
- **DO** call `validate_no_diagnostic(description)` on each pattern description — skip unsafe patterns
- **DO NOT** call `inject_disclaimer()` — the `recommendation` field fulfils non-diagnostic framing
- **DO NOT** call `surface_uncertainty()` — n/a for trend patterns
- On `SafetyValidationError`, skip that pattern and log: `logger.warning("ai.pattern_safety_rejection", description_prefix=description[:40])`
- On any `json.loads()` failure, log `logger.warning("ai.pattern_json_parse_failed")` and return `AiPatternsResponse(patterns=[])`

### Ground Truth from Previous Stories

- Story 4.1 established `ai_memories` as the encrypted source of truth; Story 4.4 reads from that data via `list_user_ai_context()` — do NOT create a second read path or a new repository function for loading interpretations.
- Story 4.2 hardened `AiInterpretationCard` around `aria-live` region isolation. `PatternCard` renders **static** content (no streaming, no live region needed) — do NOT copy the aria-live pattern from `AiInterpretationCard` into `PatternCard`.
- Story 4.3 added `apiStream()` to `client.svelte.ts`. `PatternCard` uses `apiFetch()` (JSON response, not a stream) — do NOT use `apiStream()` for the patterns endpoint.
- Story 4.3 added `AiFollowUpChatTestWrapper.svelte` as a test isolation helper. Create an equivalent `PatternCardTestWrapper.svelte` following the same pattern.
- Pattern: `$effect(() => { documentId; resetState(); })` was needed in `AiFollowUpChat` because local streaming state leaks between documents. `PatternCard` has no local state to reset — TanStack Query caching handles this correctly. Do NOT add a `$effect` for documentId reset in PatternCard.

### Existing File Surfaces

**Backend files to extend (DO NOT create new files):**
- `healthcabinet/backend/app/ai/schemas.py` — add `PatternObservation`, `AiPatternsResponse`
- `healthcabinet/backend/app/ai/repository.py` — add `updated_at` to `list_user_ai_context()` return dicts
- `healthcabinet/backend/app/ai/service.py` — add `detect_cross_upload_patterns()`, `_build_pattern_context()`, `_extract_json_array()`, `_PATTERN_DETECTION_PROMPT_TEMPLATE`
- `healthcabinet/backend/app/ai/router.py` — add `GET /patterns` endpoint
- `healthcabinet/backend/tests/ai/test_service.py` — add 5 new tests
- `healthcabinet/backend/tests/ai/test_router.py` — add 3 new tests

**Frontend files to create:**
- `healthcabinet/frontend/src/lib/components/health/PatternCard.svelte`
- `healthcabinet/frontend/src/lib/components/health/PatternCardTestWrapper.svelte`
- `healthcabinet/frontend/src/lib/components/health/PatternCard.test.ts`

**Frontend files to extend:**
- `healthcabinet/frontend/src/lib/api/ai.ts` — add `PatternObservation`, `AiPatternsResponse`, `getAiPatterns()`
- `healthcabinet/frontend/src/routes/(app)/documents/[id]/+page.svelte` — import and mount `PatternCard`

### Frontend Patterns

- Svelte 5 runes: `$state`, `$derived`, `$effect` — not Svelte 4 stores
- `createQuery` from `@tanstack/svelte-query` — same pattern as `AiInterpretationCard`
- Query key: `['ai_patterns'] as const` — no documentId needed (user-level endpoint)
- `retry: false` — same as interpretation card; don't retry on 404
- Components are imported from `$lib/components/ui/...` (shadcn-svelte) — PatternCard needs no interactive widgets (no Button, no Textarea)
- Tailwind CSS v4 tokens: `bg-card/50`, `text-foreground`, `text-muted-foreground`, `border-border` — use these, not raw hex values (except for the orange left border `border-l-[#F08430]`)
- Font scale: `text-base` (15px heading), `text-[15px]` (body), `text-[12px]` (meta), `text-[11px]` (disclaimer/recommendation)

### Architecture Corrections vs Old Architecture Doc

- Architecture file shows `GET /documents/{id}/interpretation, POST /ai/ask` — the actual codebase uses `POST /ai/chat` (implemented in Story 4.3) and `GET /documents/{id}/interpretation`. Story 4.4 adds `GET /ai/patterns`.
- Architecture file mentions `generate_interpretation` as a LangGraph node. The actual implementation uses direct Claude calls in `service.py`. Pattern detection follows the same pragmatic pattern: `call_claude()` in service, no LangGraph dependency.
- Architecture tree references `(app)/documents/[document_id]/+page.svelte` — the actual route is `healthcabinet/frontend/src/routes/(app)/documents/[id]/+page.svelte` (note `[id]`, not `[document_id]`).

### JSON Parsing Robustness

Claude may respond with the JSON array wrapped in markdown code fences. The `_extract_json_array()` helper must handle:
- Raw JSON: `[{...}]`
- Fenced: ` ```json\n[{...}]\n``` `
- Fenced without lang: ` ```\n[{...}]\n``` `

Use `re.sub(r"```(?:json)?\s*", "", text).strip()` before `json.loads()`.

Claude may also occasionally add prose before/after the array. A more robust approach: find the first `[` and last `]` and slice. Add this as a fallback:
```python
start = text.find("[")
end = text.rfind("]") + 1
if start != -1 and end > start:
    json.loads(text[start:end])
```

### Testing Notes

- Backend: mock `ai_repository.list_user_ai_context` with `AsyncMock` returning a list of dicts (same shape as real function)
- Backend: mock `call_claude` with `AsyncMock` returning a JSON string
- Backend: test `_extract_json_array` with the edge cases above in a separate unit test if desired
- Frontend: use `vi.mock('$lib/api/ai', ...)` and mock `getAiPatterns` — follow the exact same pattern as `AiFollowUpChat.test.ts`
- Frontend: `QueryClient` with `retry: false` in the test wrapper — same as AiFollowUpChatTestWrapper
- Frontend: axe-core audit should run after the query resolves with 1+ patterns (when section is rendered)

### Latest Technical Specifics

- `anthropic` SDK (`claude-sonnet-4-6`) is already in use in the repo. The `call_claude()` function uses `max_tokens=2048`. Pattern detection responses are small (JSON array of short strings) — 2048 tokens is sufficient.
- FastAPI `response_model=AiPatternsResponse` auto-serialises the Pydantic model to JSON. No manual `jsonable_encoder()` needed.
- TanStack Svelte Query v6 runes-native: `createQuery(() => ({ ... }))` — the arrow function wrapping is required for rune reactivity. Follow existing query patterns in `AiInterpretationCard.svelte`.

### References

- Epic 4 Story 4.4: `_bmad-output/planning-artifacts/epics.md` (lines 910–934)
- PRD FR22: `_bmad-output/planning-artifacts/prd.md` (AI Health Interpretation section)
- Architecture AI module tree + pipeline: `_bmad-output/planning-artifacts/architecture.md` (lines 666–694, 756–780)
- UX: `_bmad-output/planning-artifacts/ux-design-specification.md` (AIInterpretationBlock `pattern` variant, line ~630)
- Previous story: `_bmad-output/implementation-artifacts/4-3-follow-up-qa.md`
- Previous story: `_bmad-output/implementation-artifacts/4-2-ai-reasoning-trail.md`
- Recent git: `91e0e4f` — Story 4.3 implementation (streaming chat, apiStream, AiFollowUpChat)

## Dev Agent Record

### Agent Model Used

_to be filled_

### Debug Log References

- Story 4.4 created from sprint-status.yaml first backlog item: `4-4-cross-upload-pattern-detection`
- Epic 4 already `in-progress` — no epic-status transition required
- Artifacts reviewed: `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, `ux-page-specifications.md`, Story 4.1, 4.2, 4.3, last 5 git commits, all AI module source files
- Implemented backend pattern detection via existing AI context repository path, added user-level `/api/v1/ai/patterns`, and mounted a static PatternCard below follow-up chat on document detail
- Validation run: `uv run pytest` in `healthcabinet/backend` (216 passed), `docker compose ... exec frontend npm run test:unit` (160 passed), targeted `uv run ruff check` on touched backend files (passed)
- Repo-wide static checks remain noisy outside this story: backend mypy still reports `app/documents/repository.py`, frontend `npm run check` fails in existing files (`src/lib/api/auth.ts`, `vite.config.ts`, `src/routes/(app)/settings/+page.svelte`), and frontend `npm run lint` fails on existing build/prettier issues

### Completion Notes List

- Added `PatternObservation`/`AiPatternsResponse`, propagated `updated_at` through AI context rows, and implemented safe cross-upload pattern detection with JSON fence stripping, recommendation normalization, and silent empty/error fallbacks.
- Added authenticated `GET /api/v1/ai/patterns` coverage plus backend tests for empty histories, parsed responses, safety rejections, invalid JSON, and router auth/shape behavior.
- Added frontend pattern API types, `PatternCard`, test wrapper, and component tests; mounted the card under `AiFollowUpChat` so completed/partial document detail pages now surface cross-upload pattern observations when present.

### Change Log

- 2026-03-29: Implemented Story 4.4 cross-upload AI pattern detection across backend service/router/schemas and frontend document-detail rendering with automated coverage.

### File List

- `_bmad-output/implementation-artifacts/4-4-cross-upload-pattern-detection.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `healthcabinet/backend/app/ai/repository.py`
- `healthcabinet/backend/app/ai/router.py`
- `healthcabinet/backend/app/ai/schemas.py`
- `healthcabinet/backend/app/ai/service.py`
- `healthcabinet/backend/tests/ai/test_router.py`
- `healthcabinet/backend/tests/ai/test_service.py`
- `healthcabinet/frontend/src/lib/api/ai.ts`
- `healthcabinet/frontend/src/lib/components/health/PatternCard.svelte`
- `healthcabinet/frontend/src/lib/components/health/PatternCard.test.ts`
- `healthcabinet/frontend/src/lib/components/health/PatternCardTestWrapper.svelte`
- `healthcabinet/frontend/src/routes/(app)/documents/[id]/+page.svelte`

### Review Findings

#### Patches

- [x] [Review][Patch] Apply existing rate limiter to `GET /patterns` — endpoint calls Claude with no per-user throttle; apply `rate_limit.py` infrastructure [`app/ai/router.py:get_patterns`]
- [x] [Review][Patch] Add user ID to `PatternCard` query key — `['ai_patterns']` has no user scope; cross-session cache reuse possible on SPA login/logout [`PatternCard.svelte:6`]
- [x] [Review][Patch] Add truncation to `_build_pattern_context` — no length cap; overflow of Claude context window silently returns empty patterns [`service.py:_build_pattern_context`]
- [x] [Review][Patch] Add `staleTime` to `PatternCard` query — every document page navigation fires a fresh Claude call; add `staleTime` to prevent redundant LLM calls [`PatternCard.svelte:6-10`]
- [x] [Review][Patch] `_extract_json_array` regex leaves closing markdown fence unconsumed — `re.sub(r"```(?:json)?\s*", "", text)` strips the opening fence but closing ` ``` ` may remain, causing json.loads to fail and silently falling back to bracket-search heuristic [`service.py:_extract_json_array`]
- [x] [Review][Patch] `_extract_json_array` bare `raise` when no array brackets found — if bracket fallback finds no `[`/`]`, the original `json.JSONDecodeError` is re-raised; the outer handler catches it, but "no brackets" is indistinguishable from malformed JSON in logs [`service.py:_extract_json_array`]
- [x] [Review][Patch] `document_dates` from Claude not validated — entries accepted as any string with no ISO-8601 validation, length cap, or sanitization; rendered directly in frontend via `{pattern.document_dates.join(' · ')}` [`service.py:detect_cross_upload_patterns`, `PatternCard.svelte:26`]
- [x] [Review][Patch] `AiFollowUpChat` reader never cancelled on abort — when `AbortError` is caught the stream reader is silently returned without `reader.cancel()`; in long SPA sessions with frequent document switching this can exhaust stream reader locks [`AiFollowUpChat.svelte:85-91`]
- [x] [Review][Patch] `_build_follow_up_prompt` "Previous document" numbering gap — non-active docs labeled `f"Previous document {i + 1}"` using raw loop index; active doc at index 0 causes next doc to be labeled "Previous document 2", skipping 1 [`service.py:_build_follow_up_prompt`]
- [x] [Review][Patch] `PatternCard` identical `aria-label` on all pattern sections — every `<section>` announces as "Health Pattern Observation" with no differentiating info; screen reader navigation between multiple patterns is ambiguous [`PatternCard.svelte:20`]
- [x] [Review][Patch] Test name `test_get_patterns_returns_empty_list_for_single_document_user` is misleading — test mocks the service at router level and never exercises the `< 2 documents` guard; name implies the opposite [`tests/ai/test_router.py`]

#### Deferred

- [x] [Review][Defer] `stream_follow_up_answer` disclaimer appended outside safety validation window [`service.py:stream_follow_up_answer`] — deferred, pre-existing
- [x] [Review][Defer] `apiStream` `isRedirectingToLogin` flag not reset on successful retry after 401 [`client.svelte.ts:apiStream`] — deferred, pre-existing
- [x] [Review][Defer] `updated_at` date strips timezone info — `row.updated_at.date().isoformat()` loses UTC offset; docs crossing UTC midnight show wrong date in Claude prompt [`repository.py:list_user_ai_context`] — deferred, pre-existing
- [x] [Review][Defer] `list_user_ai_context` Python `None` guard on `interpretation_encrypted` redundant — SQL already filters `is_not(None)`; Python guard can never fire, produces misleading warning logs if it does [`repository.py:109`] — deferred, pre-existing

#### Round 2 (2026-03-30)

##### Decision Needed

- [x] [Review][Patch] Invalidate `['ai_patterns', userId]` when document processing completes — `staleTime: 5min` means patterns are stale after a new upload; wherever `['document', documentId]` is invalidated on processing complete, also invalidate `['ai_patterns', userId]` [`PatternCard.svelte:9-15`, `documents/[id]/+page.svelte`]

##### Patches

- [x] [Review][Patch] `_build_pattern_context` truncation from Round 1 marked done but not applied — prior review patch checkbox `[x]` but `_build_pattern_context` has no row or interpretation-length cap in current code; test `test_detect_patterns_uses_all_context_rows_in_prompt` confirms 11 rows flow untruncated to Claude prompt [`service.py:170-177`]
- [x] [Review][Patch] `_extract_json_array` silently returns `[]` when Claude responds with plain object `{...}` instead of array — `isinstance(parsed, list)` is `False`, raises `ValueError`, outer handler swallows it; no test documents this degradation path [`service.py:195-196`]
- [x] [Review][Patch] `_extract_json_array` empty-body fence (` ```json\n``` `) produces opaque error — cleaned string is `""`, fallback finds no `[`, raises `ValueError` with `''` as evidence; add early-exit guard returning `[]` when `cleaned` is empty [`service.py:184-193`]
- [x] [Review][Patch] `_ISO_DATE_RE` accepts calendar-impossible dates — `r"^\d{4}-\d{2}-\d{2}$"` passes `"2025-02-30"`, `"2025-13-01"`; replace with `datetime.date.fromisoformat` try/except for full calendar validation [`service.py:143, 283-285`]
- [x] [Review][Patch] `ai.pattern_missing_dates` warning omits raw dates from Claude — `document_dates` logged is already filtered; add `raw_dates=raw_dates` to the structlog call so operators can see what Claude returned [`service.py:289-293`]
- [x] [Review][Patch] Missing unit tests for `_extract_json_array` edge cases — no tests for: plain object input `{...}`, empty string `""`, and fenced empty body; add to `test_service.py` [`tests/ai/test_service.py`]
- [x] [Review][Patch] Missing test: `detect_cross_upload_patterns` with a row where `updated_at=None` — the "unknown date" branch in `_build_pattern_context` and `sort_key` fallback-to-epoch are untested [`tests/ai/test_service.py`]
- [x] [Review][Patch] Missing test: `GET /patterns` returns 429 when rate limit exceeded — no router test verifies `check_ai_patterns_rate_limit` is wired and returns correct status, `Retry-After` header, and error detail [`tests/ai/test_router.py`]
- [x] [Review][Patch] Router test `test_get_patterns_router_returns_200_with_service_response` does not exercise the `< 2 documents` guard — patches service entirely; add a dedicated test for the single-document early-return path, distinct from the generic "service returns empty" mock [`tests/ai/test_router.py`]
- [x] [Review][Patch] Missing frontend test: `PatternCard` renders nothing when query is in error state — no test for `mockGetAiPatterns.mockRejectedValue(...)` → `container.querySelector('section')` is null; key AC5 guarantee is unverified [`PatternCard.test.ts`]

##### Deferred

- [x] [Review][Defer] Prompt injection via unescaped health document content in `_build_pattern_context` — interpretations injected verbatim into Claude prompt; pre-existing design shared with follow-up Q&A prompt builder [`service.py:170-177`] — deferred, pre-existing
- [x] [Review][Defer] Rate limit has no per-IP secondary cap — `check_ai_patterns_rate_limit` is per-user only (10/min); consistent with `/ai/chat` rate limit design [`rate_limit.py`] — deferred, design decision
- [x] [Review][Defer] `updated_at` on `AiMemory` is interpretation write time, not lab draw date — semantic drift: patterns show interpretation dates, not actual test dates; no `document.created_at` is available [`repository.py:130`] — deferred, pre-existing design
- [x] [Review][Defer] `list_user_ai_context` authorization relies on caller passing correct `user_id` — query scope depends on `WHERE user_id = :user_id` enforcement in repository layer; pre-existing trust boundary from Story 4.1 [`repository.py`] — deferred, pre-existing
- [x] [Review][Defer] `updated_at=None` rows sort to epoch (timestamp 0), silently placed last — non-deterministic relative ordering when multiple rows have `None`; low impact in prod where server_default always fires [`repository.py`] — deferred, pre-existing
- [x] [Review][Defer] `AiInterpretationResponse.generated_at` non-optional but sourced from `server_default` column — if `db.refresh()` is skipped in a non-standard path, `updated_at=None` causes Pydantic 422 at serialization; pre-existing from Story 4.1 [`router.py`] — deferred, pre-existing
