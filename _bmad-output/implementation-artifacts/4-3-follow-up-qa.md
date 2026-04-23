# Story 4.3: Follow-Up Q&A

Status: done

## Story

As a registered user,
I want to ask follow-up questions about my health data and receive AI responses grounded in my full history,
so that I can explore my results beyond the initial interpretation.

## Acceptance Criteria

1. **Given** any authenticated user views the Q&A section
   **When** they submit a follow-up question
   **Then** `POST /api/v1/ai/chat` is called with the question and the full context from `ai_memories` for that user
   **And** the active document is ownership-checked before any AI call is made

2. **Given** a Q&A response is generated
   **When** it passes through `safety.py`
   **Then** the same constraints apply as Story 4.1: non-diagnostic disclaimer, no treatment recommendations, uncertainty surfaced

3. **Given** a Q&A response is being streamed
   **When** content is arriving
   **Then** an inline skeleton loader is shown until the first token arrives
   **And** the response renders incrementally as tokens stream in

4. **Given** an unauthenticated request hits `POST /api/v1/ai/chat`
   **When** the request is processed
   **Then** `401 Unauthorized` is returned

## Tasks / Subtasks

### Backend

- [x] **Task 1: Add request schema and repository-side context loading** (AC: #1, #4)
  - [x] In `healthcabinet/backend/app/ai/schemas.py`, add a request model for the chat endpoint:
    ```python
    from typing import Annotated
    from pydantic import BaseModel, Field

    class AiChatRequest(BaseModel):
        document_id: uuid.UUID
        question: Annotated[str, Field(min_length=1, max_length=1000)]
    ```
  - [x] In `healthcabinet/backend/app/ai/repository.py`, add a read-side helper that loads **all** `safety_validated=True` interpretation rows for a user, decrypts them, and returns a prompt-ready context list. Suggested shape:
    ```python
    async def list_user_ai_context(
        db: AsyncSession,
        user_id: uuid.UUID,
        active_document_id: uuid.UUID | None = None,
    ) -> list[dict[str, object]]:
        """Return decrypted AI-memory rows ordered with the active document first."""
    ```
  - [x] Query rules:
    - filter to `AiMemory.user_id == user_id`
    - filter to `AiMemory.safety_validated == True`
    - filter to `AiMemory.interpretation_encrypted.is_not(None)`
    - order the current `document_id` first if present, then `updated_at DESC`
  - [x] Decrypt `interpretation_encrypted` in the repository only
  - [x] If `context_json_encrypted` is present, decrypt and parse it in the repository only
  - [x] Skip rows that cannot be decrypted or parsed; log a warning and continue instead of failing the whole request
  - [x] **Do not add a migration** and **do not persist chat transcripts** in Story 4.3. `ai_memories` is a read context source only for this story.

- [x] **Task 2: Add Claude streaming helper without duplicating model/client config** (AC: #1, #3)
  - [x] In `healthcabinet/backend/app/ai/claude_client.py`, add a streaming helper adjacent to `call_claude()`:
    ```python
    from collections.abc import AsyncIterator

    async def stream_claude_text(prompt: str) -> AsyncIterator[str]:
        """Yield text deltas from Claude for a single user prompt."""
    ```
  - [x] Reuse the existing singleton client and the existing model identifier
  - [x] Do not hardcode a second model string in `service.py` or `router.py`
  - [x] Follow the official Anthropic streaming API shape (`messages.stream(...)` and text deltas) rather than inventing a custom polling loop

- [x] **Task 3: Implement follow-up Q&A service with full-history prompt assembly and streaming safety** (AC: #1, #2, #3)
  - [x] In `healthcabinet/backend/app/ai/service.py`, add a prompt builder that combines:
    - the current document context first
    - all other decrypted `ai_memories` rows for that user
    - reasoning context when available (`values_referenced`, `uncertainty_flags`, `prior_documents_referenced`)
    - the user's follow-up question
  - [x] Suggested service entrypoint:
    ```python
    async def stream_follow_up_answer(
        db: AsyncSession,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        question: str,
    ) -> AsyncIterator[bytes]:
        """Yield UTF-8 encoded response chunks for StreamingResponse."""
    ```
  - [x] Prompt rules:
    - answer only from provided health context
    - be explicit when the available data is insufficient
    - never diagnose
    - never recommend medications, dosages, or treatment changes
    - keep tone aligned with Story 4.1 / 4.2: calm, informative, non-alarming
  - [x] Streaming safety rules:
    - accumulate a running text buffer
    - validate the cumulative buffer with `validate_no_diagnostic()` before forwarding each newly received delta
    - append the Story 4.1 disclaimer as the **final streamed sentence**
    - call `surface_uncertainty()` in the same pipeline even though it is currently a no-op
    - if safety validation fails, stop forwarding new model content and emit a safe fallback tail instead of unsafe text
  - [x] If no usable AI context rows are available for the user, raise a domain error that the router maps to `409 Conflict` with a clear RFC 7807 `detail`
  - [x] Keep this story stateless on the backend. Each follow-up request is grounded in `ai_memories` plus the current question; follow-up chat history is not persisted server-side.

- [x] **Task 4: Add `POST /api/v1/ai/chat` router endpoint using `StreamingResponse`** (AC: #1, #3, #4)
  - [x] In `healthcabinet/backend/app/ai/router.py`, add:
    ```python
    from fastapi.responses import StreamingResponse

    @router.post("/chat")
    async def chat_with_ai(
        payload: AiChatRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> StreamingResponse:
        ...
    ```
  - [x] Before starting the stream:
    - verify `payload.document_id` belongs to `current_user` via `document_repository.get_document_by_id(...)`
    - reject missing/foreign documents with `404`
  - [x] Return `StreamingResponse(...)` with `media_type="text/plain; charset=utf-8"`
  - [x] Use the existing auth dependency so `401` behavior and `WWW-Authenticate` headers remain consistent with the rest of the API
  - [x] Do not introduce WebSockets or GET+EventSource for this story. The endpoint is a POST with a streamed response body.

- [x] **Task 5: Add backend tests for repository, service, and streaming router behavior** (AC: #1, #2, #3, #4)
  - [x] In `healthcabinet/backend/tests/ai/test_repository.py`, add:
    - `test_list_user_ai_context_returns_active_document_first`
    - `test_list_user_ai_context_skips_corrupt_rows`
  - [x] In `healthcabinet/backend/tests/ai/test_service.py`, add:
    - `test_stream_follow_up_answer_builds_prompt_from_full_history`
    - `test_stream_follow_up_answer_appends_disclaimer_last`
    - `test_stream_follow_up_answer_stops_on_safety_failure`
  - [x] In `healthcabinet/backend/tests/ai/test_router.py`, add:
    - `test_post_chat_requires_auth`
    - `test_post_chat_returns_404_for_non_owner_document`
    - `test_post_chat_returns_409_when_no_ai_context_exists`
    - `test_post_chat_streams_incremental_text`
  - [x] Use `httpx.AsyncClient.stream("POST", ...)` for the router streaming tests; do not flatten the response into a single JSON expectation

### Frontend

- [x] **Task 6: Add a dedicated streaming API helper instead of forcing `apiFetch()` to buffer the response** (AC: #1, #3)
  - [x] In `healthcabinet/frontend/src/lib/api/client.svelte.ts`, add an `apiStream()` helper or an equivalent shared primitive that:
    - injects the in-memory access token from `tokenState`
    - retries once through `refreshToken()` on `401`, just like `apiFetch()`
    - returns the raw `Response` object for stream consumption
  - [x] In `healthcabinet/frontend/src/lib/api/ai.ts`, add:
    ```typescript
    export interface AiChatRequest {
      document_id: string;
      question: string;
    }

    export async function streamAiChat(payload: AiChatRequest): Promise<Response> {
      ...
    }
    ```
  - [x] Do not duplicate auth header / refresh logic inside the Svelte component
  - [x] Do not use `apiFetch()` for this path; it assumes JSON and would defeat incremental rendering

- [x] **Task 7: Build `AiFollowUpChat.svelte` with incremental rendering and accessibility-safe live regions** (AC: #1, #2, #3)
  - [x] Create `healthcabinet/frontend/src/lib/components/health/AiFollowUpChat.svelte`
  - [x] Props:
    ```typescript
    interface Props {
      documentId: string;
    }
    ```
  - [x] Use the existing `['ai_interpretation', documentId]` query key to gate the form so the component reuses cached interpretation availability instead of inventing a second readiness query
  - [x] Render nothing when the interpretation query resolves to a `404` / unavailable state
  - [x] UI requirements:
    - form label: "Ask a follow-up about these results"
    - `Textarea` from `$lib/components/ui/textarea`
    - `Button` from `$lib/components/ui/button`
    - AI-styled response container visually aligned with `AiInterpretationCard`
    - inline skeleton visible until the first streamed chunk arrives
    - streamed answer appended in place as chunks arrive
  - [x] State requirements:
    - `question`
    - `isStreaming`
    - `waitingForFirstChunk`
    - `streamedAnswer`
    - `errorMessage`
  - [x] UX rules:
    - blank or whitespace-only questions do not submit
    - submit button disabled while streaming
    - local component state resets on `documentId` change
    - a failed stream leaves a clear inline error but does not break the rest of the page
  - [x] Accessibility rules:
    - keep the dynamic answer in its own `aria-live="polite"` region
    - do not nest a new announcer inside the existing atomic live region pattern from `AiInterpretationCard`
    - preserve keyboard accessibility for the form and button

- [x] **Task 8: Mount the follow-up component on the document detail page without changing the routing model** (AC: #1, #3)
  - [x] In `healthcabinet/frontend/src/routes/(app)/documents/[id]/+page.svelte`, mount `<AiFollowUpChat documentId={doc.id} />` directly below `<AiInterpretationCard documentId={doc.id} />`
  - [x] Keep the current document detail route and current processing-state gates unchanged
  - [x] No query invalidation is required after a follow-up request because Story 4.3 does not persist new document state

- [x] **Task 9: Add frontend tests for incremental streaming, gating, and reset behavior** (AC: #1, #3)
  - [x] Create `healthcabinet/frontend/src/lib/components/health/AiFollowUpChat.test.ts`
  - [x] Cover:
    - hidden when interpretation is unavailable
    - blank submit is blocked
    - submit calls the stream helper with `{ document_id, question }`
    - skeleton shows before first chunk and disappears after first chunk
    - answer renders incrementally over multiple chunks
    - submit button disables during streaming
    - component state resets on `documentId` change
    - inline error shown on `409` / network failure
    - axe-core audit on loaded state

## Dev Notes

### Ground Truth from Previous Stories

- Story 4.1 established `ai_memories` as the encrypted source of truth for per-document AI interpretations. Story 4.3 must **read from that data**, not introduce a second AI memory store.
- Story 4.2 already persists structured reasoning in `context_json_encrypted` and hardened `AiInterpretationCard` around duplicate-safe keys and live-region isolation. Reuse those patterns instead of inventing a separate accessibility approach.
- Recent commits for Story 4.2 only touched `AiInterpretationCard.svelte`, `AiInterpretationCard.test.ts`, `backend/tests/ai/test_router.py`, `backend/app/ai/repository.py`, `backend/app/ai/router.py`, and `backend/app/ai/service.py`. Stay inside those same surfaces plus the new chat component/helper; do not spread the feature across unrelated modules.

### Critical Architecture Corrections

- The architecture tree still says `POST /ai/ask`; the epic file is newer and explicitly requires `POST /ai/chat`. **Follow the epic and implement `POST /api/v1/ai/chat`.**
- The architecture tree references `(app)/documents/[document_id]/+page.svelte`, but the actual repo route is `healthcabinet/frontend/src/routes/(app)/documents/[id]/+page.svelte`.
- The architecture tree references a standalone `ReasoningTrail.svelte`; the actual implementation embeds reasoning inside `AiInterpretationCard.svelte`. Story 4.3 should extend the existing document-detail composition, not split reasoning into a new standalone component.

### No New Persistence or Migration in Story 4.3

- `ai_memories` already has the columns Story 4.3 needs.
- The unique `(user_id, document_id)` interpretation row constraint from Story 4.1 means chat transcript persistence would be a separate data-model decision. It is **out of scope** here.
- `document_id` remaining nullable on `AiMemory` is a future affordance; do not start writing ephemeral Q&A rows into it in this story.

### Full-Context Loading Rules

- Embeddings / vector retrieval are still deferred for MVP. Story 4.3 must load full user context from `ai_memories` directly.
- Use all decryptable, `safety_validated=True` interpretation rows for the current user.
- Prefer the active document first in the prompt, then append the rest of the user's history.
- If an old `AiMemory` row is corrupt, skip it and continue. The feature must degrade gracefully instead of 500ing the whole chat request.

### Streaming Implementation Rules

- Backend transport: `StreamingResponse` with an async generator. No WebSocket stack, no polling loop, no EventSource workaround for a POST endpoint.
- Frontend transport: `fetch()` streaming via a shared helper. `apiFetch()` is JSON-oriented and should not be retrofitted for this job.
- Because the answer must remain safe **while** streaming, validate the cumulative buffer before yielding each newly received text delta.
- Append the educational disclaimer as the final streamed sentence so the visible answer still ends with the same non-diagnostic framing used in Story 4.1.
- If the model drifts into forbidden content mid-stream, terminate the stream safely and return a fallback message rather than exposing unsafe text.

### Frontend UX and Accessibility Guardrails

- Keep the visual language aligned with the existing dark-neutral AI card styling: accent border, `bg-card/50`, compact text, no bright warning chrome unless there is an actual error.
- Use `Textarea` and `Button` components that already exist in the repo.
- The skeleton loader is an **inline** loading treatment inside the Q&A area, not a full-page spinner.
- Reset transient state on document change; Story 4.2 already needed a follow-up patch for disclosure state leaking between documents, so do not repeat that mistake here.
- The Q&A component should be self-contained and should not force the document detail page to duplicate interpretation-loading logic.

### Query and State Notes

- Reuse `['ai_interpretation', documentId]` to determine whether the Q&A panel should exist.
- No TanStack Query invalidation is needed after asking a question unless you intentionally add persistence, which this story does not require.
- If you keep local session-only message history in the component, it should be UI-only state. Reloading the page may clear it.

### Testing Notes

- Backend streaming tests should use `httpx.AsyncClient.stream(...)` so chunking behavior is exercised instead of masked.
- Frontend tests will need a mocked `ReadableStream` / streamed `Response` body. Reuse the project’s existing component-test patterns; do not introduce browser-only APIs that JSDOM cannot fake.
- Follow the existing Epic 4 validation habit: run the smallest relevant backend and frontend tests first, then broader regressions once the feature is stable.

### Latest Technical Specifics

- Anthropic's current official docs confirm the Messages API supports streaming and the SDK exposes streamed text deltas; that is the correct primitive for this story rather than polling:
  - https://platform.claude.com/docs/en/build-with-claude/streaming
- Anthropic's current model overview lists `claude-sonnet-4-6` as a current Claude API ID / alias, which matches the repo's existing model selection:
  - https://platform.claude.com/docs/en/about-claude/models/overview
- FastAPI's official docs confirm `StreamingResponse` is the intended response type for async generators that yield streamed response bodies:
  - https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse

### Project Structure Notes

- Backend AI module to extend:
  - `healthcabinet/backend/app/ai/claude_client.py`
  - `healthcabinet/backend/app/ai/repository.py`
  - `healthcabinet/backend/app/ai/router.py`
  - `healthcabinet/backend/app/ai/schemas.py`
  - `healthcabinet/backend/app/ai/service.py`
- Backend tests to extend:
  - `healthcabinet/backend/tests/ai/test_repository.py`
  - `healthcabinet/backend/tests/ai/test_router.py`
  - `healthcabinet/backend/tests/ai/test_service.py`
- Frontend files to extend/add:
  - `healthcabinet/frontend/src/lib/api/client.svelte.ts`
  - `healthcabinet/frontend/src/lib/api/ai.ts`
  - `healthcabinet/frontend/src/lib/components/health/AiFollowUpChat.svelte`
  - `healthcabinet/frontend/src/lib/components/health/AiFollowUpChat.test.ts`
  - `healthcabinet/frontend/src/routes/(app)/documents/[id]/+page.svelte`

### References

- Epic 4 story definition: `_bmad-output/planning-artifacts/epics.md` (Story 4.3 / lines around 885-904)
- PRD FR21: `_bmad-output/planning-artifacts/prd.md` (AI Health Interpretation section / FR21)
- Architecture AI pipeline + module tree: `_bmad-output/planning-artifacts/architecture.md` (AI module tree, processing flow, AI access in MVP)
- UX follow-up and dynamic content guidance: `_bmad-output/planning-artifacts/ux-design-specification.md` (success criteria, AI output patterns, accessibility, loading states)
- AI module audit: `_bmad-output/implementation-artifacts/ai-module-audit-epic4-prep.md`
- Document cache contract: `_bmad-output/implementation-artifacts/document-state-query-contract.md`
- Previous story intelligence:
  - `_bmad-output/implementation-artifacts/4-1-plain-language-ai-interpretation-per-upload.md`
  - `_bmad-output/implementation-artifacts/4-2-ai-reasoning-trail.md`
- Recent git intelligence:
  - `8120a17` feat: reset reasoning state on documentId change and improve screen reader accessibility
  - `0cf82e2` feat: enhance AiInterpretationCard with reasoning handling and test coverage improvements
  - `a768091` 4-2-ai-reasoning-trail: enhance AI interpretation handling with reasoning context and persistence
  - `ef59252` feat: add interpretation invalidation logic to hide stale interpretations before regeneration
  - `6960d50` feat: implement document processing status checks and enhance interpretation retrieval logic
- Official docs:
  - Anthropic streaming: https://platform.claude.com/docs/en/build-with-claude/streaming
  - Anthropic models overview: https://platform.claude.com/docs/en/about-claude/models/overview
  - FastAPI `StreamingResponse`: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Story created from the first backlog item in `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Story 4.3 selected after reading sprint status top-to-bottom; Epic 4 already `in-progress`, so no epic-status transition was required
- Artifact set reviewed: `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, `ux-page-specifications.md`, `project-context.md`, `ai-module-audit-epic4-prep.md`, `document-state-query-contract.md`, Story 4.1, Story 4.2, and the last five git commits

### Completion Notes List

- ✅ Resolved review finding [Patch]: Added `prior_documents_referenced` to prompt context in `_build_follow_up_prompt()` — field was silently dropped; now included when non-empty
- ✅ Resolved review finding [Patch]: Fixed wrong-document labeling — `_build_follow_up_prompt()` now accepts `active_document_id` and labels each row by identity, not position; first row is no longer always labeled "Active document" when the active doc has no interpretation row
- ✅ Resolved review finding [Patch]: Wrapped reasoning block in `try/except` with `isinstance(x, list)` guards — malformed non-iterable fields no longer crash prompt assembly
- ✅ Resolved review finding [Patch]: Added `AbortController` pattern to `AiFollowUpChat.svelte` — `$effect` cleanup aborts in-flight stream on `documentId` change (mirrors `ProcessingPipeline.svelte` EventSource pattern); `streamAiChat` now accepts optional `signal?: AbortSignal`
- Story context was pre-populated with comprehensive guidance from the SM agent
- Implemented `AiChatRequest` schema in `schemas.py` with Pydantic v2 `Annotated[str, Field(...)]` pattern
- Added `list_user_ai_context()` to `repository.py` — reads all `safety_validated=True` rows, decrypts, skips corrupt rows gracefully, orders active document first
- Added `stream_claude_text()` to `claude_client.py` reusing the existing singleton client and model string `claude-sonnet-4-6` — uses `messages.stream()` with `text_stream` async iterator
- Added `NoAiContextError`, `_build_follow_up_prompt()`, and `stream_follow_up_answer()` to `service.py` — streams with cumulative safety validation and disclaimer appended as final token
- Added `POST /api/v1/ai/chat` to `router.py` with document ownership check and `409` on missing context
- Added `apiStream()` helper to `client.svelte.ts` with same auth/refresh logic as `apiFetch()` but returns raw `Response`
- Created `AiFollowUpChat.svelte` with all 5 required state vars, inline skeleton, aria-live response region, form reset on documentId change
- Mounted below `AiInterpretationCard` in document detail page — gates on interpretation availability via shared query key
- Backend tests: 205 total, all pass. Frontend tests: 154 total, all pass
- Added `dev` stage to `backend/Dockerfile` and `backend-test` service to `docker-compose.yml` to enable `docker compose run --rm backend-test uv run pytest` for development workflow
- Added `ENV PATH` and `RUN chmod +x entrypoint.sh` to builder stage to fix startup regression caused by Dockerfile modification

### Change Log

- 2026-03-28: Addressed code review findings — 4 items resolved
- 2026-03-28: Implemented Story 4.3 — follow-up Q&A with streaming AI responses grounded in full ai_memories history

### File List

- _bmad-output/implementation-artifacts/4-3-follow-up-qa.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- healthcabinet/backend/app/ai/schemas.py
- healthcabinet/backend/app/ai/repository.py
- healthcabinet/backend/app/ai/claude_client.py
- healthcabinet/backend/app/ai/service.py
- healthcabinet/backend/app/ai/router.py
- healthcabinet/backend/tests/ai/test_repository.py
- healthcabinet/backend/tests/ai/test_service.py
- healthcabinet/backend/tests/ai/test_router.py
- healthcabinet/backend/Dockerfile
- healthcabinet/docker-compose.yml
- healthcabinet/frontend/src/lib/api/client.svelte.ts
- healthcabinet/frontend/src/lib/api/ai.ts
- healthcabinet/frontend/src/lib/components/health/AiFollowUpChat.svelte
- healthcabinet/frontend/src/lib/components/health/AiFollowUpChatTestWrapper.svelte
- healthcabinet/frontend/src/lib/components/health/AiFollowUpChat.test.ts
- healthcabinet/frontend/src/routes/(app)/documents/[id]/+page.svelte

### Review Findings

- [x] [Review][Patch] Missing `prior_documents_referenced` in follow-up prompt context [healthcabinet/backend/app/ai/service.py:140]
- [x] [Review][Patch] Follow-up chat can answer with the wrong document when the active interpretation row is missing [healthcabinet/backend/app/ai/router.py:68]
- [x] [Review][Patch] Malformed decrypted reasoning rows can crash prompt assembly instead of degrading gracefully [healthcabinet/backend/app/ai/service.py:151]
- [x] [Review][Patch] In-flight follow-up streams are not canceled when `documentId` changes [healthcabinet/frontend/src/lib/components/health/AiFollowUpChat.svelte:31]
- [x] [Review][Patch] Intentional aborts before the chat POST resolves are surfaced as network errors [healthcabinet/frontend/src/lib/api/client.svelte.ts:84]
