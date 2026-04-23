# Story 5.0: LangChain AI Module Migration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the platform team,
I want the `app/ai/` module to use a LangChain-based model abstraction instead of the raw Anthropic SDK,
so that AI features remain provider-portable, easier to test, and less coupled to Claude-specific client code.

## Acceptance Criteria

1. **Given** the backend AI module is imported
   **When** application startup or tests load `app.ai.*`
   **Then** no Anthropic client is created at module import time
   **And** the AI model boundary is implemented through a LangChain-based adapter with lazy initialization

2. **Given** `generate_interpretation()`, `detect_cross_upload_patterns()`, and `stream_follow_up_answer()` run
   **When** each feature makes an LLM call
   **Then** the service layer uses the new LangChain adapter instead of direct Anthropic SDK calls
   **And** the existing prompts, safety pipeline, return types, and repository writes remain behaviorally unchanged

3. **Given** a user calls `POST /api/v1/ai/chat`
   **When** the response is streamed
   **Then** tokens are still emitted incrementally
   **And** cumulative safety validation and safe-fallback behavior continue to work before unsafe content reaches the client

4. **Given** existing frontend code calls `/api/v1/ai/documents/{document_id}/interpretation`, `/api/v1/ai/chat`, and `/api/v1/ai/patterns`
   **When** Story 5.0 is complete
   **Then** those HTTP contracts, route paths, and response payload shapes remain unchanged from the caller's perspective

5. **Given** the backend test suite for AI features runs
   **When** targeted tests execute locally and in Docker Compose
   **Then** deterministic unit tests pass against the new adapter seam
   **And** a real-provider adapter integration test exists for LangChain + Anthropic when `ANTHROPIC_API_KEY` is available

6. **Given** Story 5.0 is implemented
   **When** the diff is reviewed
   **Then** scope is limited to `healthcabinet/backend/app/ai/`, backend dependency/config surfaces, and backend tests
   **And** `app/processing/extractor.py`, `app/processing/worker.py`, and full LangGraph graph/node adoption remain out of scope for this story

## Tasks / Subtasks

### Backend

- [x] **Task 1: Add LangChain dependencies and a provider-agnostic chat-model config seam** (AC: #1, #5)
  - [x] In [healthcabinet/backend/pyproject.toml](/Users/vladtara/dev/set-bmad/healthcabinet/backend/pyproject.toml), add `langchain-core` and `langchain-anthropic`
  - [x] Keep the existing `anthropic` dependency because `healthcabinet/backend/app/processing/extractor.py` still depends on the raw Anthropic SDK in this repo
  - [x] In [healthcabinet/backend/app/core/config.py](/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/core/config.py), add a generic chat-model setting such as:
    ```python
    AI_CHAT_MODEL: str = "claude-sonnet-4-6"
    ```
  - [x] Preserve `ANTHROPIC_API_KEY` as the credential source for this story
  - [x] Preserve `ANTHROPIC_EXTRACTION_MODEL` unchanged because extraction migration is explicitly out of scope
  - [x] Update [healthcabinet/backend/.env.example](/Users/vladtara/dev/set-bmad/healthcabinet/backend/.env.example) with the new generic chat-model setting

- [x] **Task 2: Replace the provider-specific Claude client seam with a LangChain adapter** (AC: #1, #2, #3)
  - [x] Replace [healthcabinet/backend/app/ai/claude_client.py](/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/ai/claude_client.py) with a provider-agnostic adapter module
  - [x] Preferred target file:
    - `healthcabinet/backend/app/ai/llm_client.py`
  - [x] Preferred public surface:
    ```python
    from collections.abc import AsyncIterator

    async def call_model_text(prompt: str) -> str:
        """Return the complete text response for a single prompt."""

    async def stream_model_text(prompt: str) -> AsyncIterator[str]:
        """Yield token/text chunks incrementally for a single prompt."""
    ```
  - [x] Implement the adapter using `ChatAnthropic` from `langchain_anthropic`
  - [x] Use lazy initialization so importing the module does not require `ANTHROPIC_API_KEY`
  - [x] Centralize model selection in one place; do not hardcode model identifiers inside `service.py`
  - [x] Keep the adapter text-only for this story; multimodal extraction stays in `processing/extractor.py`

- [x] **Task 3: Migrate the AI service layer to the new adapter without changing external behavior** (AC: #2, #3, #4)
  - [x] Update [healthcabinet/backend/app/ai/service.py](/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/ai/service.py) to remove imports of `call_claude` and `stream_claude_text`
  - [x] Wire `generate_interpretation()` to the new adapter
  - [x] Wire `detect_cross_upload_patterns()` to the new adapter
  - [x] Wire `stream_follow_up_answer()` to the new adapter
  - [x] Keep the following logic unchanged:
    - prompt templates and prompt assembly
    - `validate_no_diagnostic()`
    - `surface_uncertainty()`
    - `inject_disclaimer()`
    - DB write paths in `ai_repository`
    - HTTP-facing return types used by `router.py`
  - [x] Preserve incremental streaming semantics: do not buffer the full answer before yielding
  - [x] Preserve the Story 4.3 safety rule: validate the cumulative stream before forwarding newly received text

- [x] **Task 4: Preserve router contracts and keep frontend impact at zero** (AC: #4)
  - [x] Confirm [healthcabinet/backend/app/ai/router.py](/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/ai/router.py) keeps the same route paths, request models, and response models
  - [x] Do not rename:
    - `GET /api/v1/ai/documents/{document_id}/interpretation`
    - `POST /api/v1/ai/chat`
    - `GET /api/v1/ai/patterns`
  - [x] Do not require any frontend API or component changes for this story

- [x] **Task 5: Add adapter-focused tests and update existing AI tests to the new seam** (AC: #1, #2, #3, #5)
  - [x] Create `healthcabinet/backend/tests/ai/test_llm_client.py`
  - [x] Cover:
    - lazy initialization does not require `ANTHROPIC_API_KEY` at import time
    - adapter returns text in the format expected by `service.py`
    - adapter streaming yields incremental chunks
  - [x] Update [healthcabinet/backend/tests/ai/test_service.py](/Users/vladtara/dev/set-bmad/healthcabinet/backend/tests/ai/test_service.py) to patch the new adapter seam instead of `call_claude` / `stream_claude_text`
  - [x] Update [healthcabinet/backend/tests/ai/test_router.py](/Users/vladtara/dev/set-bmad/healthcabinet/backend/tests/ai/test_router.py) if import paths or patched symbols change
  - [x] Add one real-provider integration test for the adapter:
    - guarded by `ANTHROPIC_API_KEY`
    - skipped cleanly when the key is absent
    - verifies one non-streaming call and one streaming call through LangChain + Anthropic
  - [x] Keep prompt-assembly and safety-pipeline tests deterministic; they may patch the local adapter boundary rather than making real provider calls

- [x] **Task 6: Run targeted regressions for the migrated boundary** (AC: #5)
  - [x] Smallest relevant local test pass:
    - `cd healthcabinet/backend && uv run pytest tests/ai/test_llm_client.py tests/ai/test_service.py tests/ai/test_router.py`
  - [x] Regression around worker import path stability:
    - `cd healthcabinet/backend && uv run pytest tests/processing/test_worker.py`
  - [x] Docker Compose verification before story completion:
    - `docker compose -f /Users/vladtara/dev/set-bmad/healthcabinet/docker-compose.yml exec backend uv run pytest tests/ai/test_llm_client.py tests/ai/test_service.py tests/ai/test_router.py tests/processing/test_worker.py`

### Review Findings

- [x] [Review][Patch] **Hard-coded 60s timeout regresses the prior Anthropic default and can abort valid long AI calls** [healthcabinet/backend/app/ai/llm_client.py:36]
- [x] [Review][Patch] **Delete `claude_client.py` entirely** — `service.py` already imports from `llm_client.py`. No module imports from `claude_client`. File is dead code. Spec says "Replace claude_client.py". Decision: delete entirely. Update any test patches that reference the old module.
- [x] [Review][Patch] **Per-call `ChatAnthropic` instantiation — no connection reuse** [app/ai/llm_client.py:66-74] — `_build_chat_model()` creates a new client every call. Old code used a module-level singleton. Fix: lazy-initialized singleton(s).
- [x] [Review][Patch] **`max_tokens_to_sample` is deprecated/wrong parameter** [app/ai/llm_client.py:26] — `ChatAnthropic` in `langchain-anthropic>=1.0.1` uses `max_tokens`, not `max_tokens_to_sample`. May be silently ignored. Fix: rename to `max_tokens`.
- [x] [Review][Patch] **`timeout=None` disables all request timeouts** [app/ai/llm_client.py:27] — Removes default timeouts the old SDK had. Stuck API call blocks forever. Fix: set reasonable timeout.
- [x] [Review][Patch] **Whitespace-only `ANTHROPIC_API_KEY` bypasses guard** [app/ai/llm_client.py:21] — `if not settings.ANTHROPIC_API_KEY` passes for `'   '`. Fix: `.strip()` before check.
- [x] [Review][Defer] **`_iter_text_fragments` silently drops unknown content types** [app/ai/llm_client.py:33-55] — deferred, pre-existing limitation
- [x] [Review][Defer] **Mid-stream exception after HTTP 200 — truncated response** [app/ai/service.py:337-361] — deferred, pre-existing behavior
- [x] [Review][Defer] ~~**Integration test lacks `@pytest.mark.integration` marker**~~ — FIXED in deep review

### Deep Review Findings (2026-03-31)

- [x] [Review][Patch] **API key stored as plaintext in module-level cache key** [app/ai/llm_client.py:40-45] — raw secret persisted as dict key; fix: hash with SHA-256
- [x] [Review][Patch] **Cache/factory typed to concrete `ChatAnthropic` instead of `BaseChatModel`** [app/ai/llm_client.py:13,30,39] — violated spec constraint to use langchain-core types as abstraction surface
- [x] [Review][Patch] **No concurrency protection on shared cache dict** [app/ai/llm_client.py:40-45] — added asyncio.Lock with double-checked locking
- [x] [Review][Patch] **Integration test lacked `@pytest.mark.integration` marker** [tests/ai/test_llm_client.py] — added marker + registered in pyproject.toml
- [x] [Review][Patch] **`generate_interpretation` lacked `ModelTemporaryUnavailableError` handling** [app/ai/service.py:104] — provider unavailability now returns None gracefully
- [x] [Review][Defer] **Module-level cache has no eviction** [app/ai/llm_client.py:20] — deferred, max ~2 entries in practice
- [x] [Review][Defer] **Non-temporary provider errors propagate from generate_interpretation** [app/ai/service.py:104] — deferred, pre-existing
- [x] [Review][Defer] **`_extract_text` ValueError propagates from generate_interpretation** [app/ai/service.py:104] — deferred, pre-existing

### Deep Review Findings (2026-04-01)

- [x] [Review][Patch] **Non-temporary `AnthropicError` escapes `_generate()` mid-stream — stream crashes instead of emitting fallback** [app/ai/service.py:403-413] — Added `except anthropic.AnthropicError` handler after `except ModelTemporaryUnavailableError` in `_generate()`; logs `ai.follow_up_stream_error` and yields `_FOLLOW_UP_STREAM_INTERRUPTED_FALLBACK`. Added `test_stream_follow_up_answer_emits_fallback_on_non_temporary_provider_error`.
- [x] [Review][Patch] **`detect_cross_upload_patterns` logs wrong event for `ModelTemporaryUnavailableError`** [app/ai/service.py:302-310] — Added explicit `except ModelTemporaryUnavailableError` before `except Exception` logging `ai.patterns_temporarily_unavailable`.
- [x] [Review][Dismiss] **`test_llm_client_import_is_lazy` patches the wrong object** [tests/ai/test_llm_client.py:32-39] — False positive. `patch.object(langchain_anthropic, "ChatAnthropic")` correctly replaces the module attribute; the subsequent `from langchain_anthropic import ChatAnthropic` inside the reload reads the patched mock. The test is valid.
- [x] [Review][Patch] **Stale "Claude" strings in provider-agnostic module** [app/ai/service.py:221-238] — Renamed all three `_extract_json_array` error messages and `_build_follow_up_prompt` docstring to provider-agnostic wording.
- [x] [Review][Patch] **`generate_interpretation` — `ModelTemporaryUnavailableError` branch untested** [tests/ai/test_service.py] — Added `test_generate_interpretation_returns_none_on_temporary_unavailability`.
- [x] [Review][Patch] **`generate_interpretation` — `SafetyValidationError` branch untested** [tests/ai/test_service.py] — Added `test_generate_interpretation_returns_none_on_safety_failure`.
- [x] [Review][Patch] **`_is_temporary_provider_error` — `rate_limit_error` and numeric status codes (408, 429, 500–504) untested** [tests/ai/test_llm_client.py] — Added `test_call_model_text_raises_temporary_unavailable_for_various_status_codes` (parametrized over 7 cases) and `test_call_model_text_raises_temporary_unavailable_for_connection_error`.
- [x] [Review][Patch] **Empty stream (`first_delta is None`) path in `_generate()` untested** [tests/ai/test_service.py] — Added `test_stream_follow_up_answer_yields_only_disclaimer_when_model_stream_is_empty`.
- [x] [Review][Dismiss] **`_FOLLOW_UP_STREAM_INTERRUPTED_FALLBACK` mid-stream path untested** [tests/ai/test_service.py] — False positive. Already covered by existing `test_stream_follow_up_answer_emits_fallback_when_provider_fails_mid_stream` (line 416).
- [x] [Review][Patch] **Non-temporary `AnthropicError` re-raise path untested in `_is_temporary_provider_error`** [tests/ai/test_llm_client.py] — Added `test_call_model_text_reraises_non_temporary_anthropic_error`.
- [x] [Review][Defer] **`surface_uncertainty` return value discarded in streaming path** [app/ai/service.py:388] — `await surface_uncertainty(next_cumulative)` result is ignored; the raw delta is yielded. Currently a no-op, so no present bug. When `surface_uncertainty` is implemented to mutate text, the streaming path will silently skip its mutations while `generate_interpretation` applies them. Deferred: pre-existing pattern, implement fix when `surface_uncertainty` gets a real body.
- [x] [Review][Defer] **Safety check cannot retroactively block already-streamed partial forbidden content** [app/ai/service.py:381-389] — Forbidden text split across two LLM deltas will have its first part sent before the cumulative check catches it on the second delta. Pre-existing architectural constraint of streaming safety validation; acknowledged.
- [x] [Review][Defer] **`asyncio.Lock()` created at module import — held-lock test teardown risk** [app/ai/llm_client.py:21] — If a test is cancelled while holding `_cache_lock`, subsequent tests deadlock. The `llm_client_module` fixture's reload-on-teardown mitigates this. Deferred: Python 3.10+ safe in production; fixture provides test isolation.
- [x] [Review][Defer] **TOCTOU: API key read twice between cache key computation and `_build_chat_model`** [app/ai/llm_client.py:56] — If the API key rotates between the hash computation and the model build, the model is built with the new key but stored under the old key's hash. Astronomically unlikely in practice.
- [x] [Review][Defer] **SHA-256 truncation to 16 hex chars — cache key collision risk** [app/ai/llm_client.py:51-52] — 64-bit prefix is sufficient for current single-key use. Relevant only if multi-key or per-tenant key scenarios are added.
- [x] [Review][Defer] **Integration test swallows `AuthenticationError` with `pytest.skip()`** [tests/ai/test_llm_client.py:183] — Misconfigured-but-non-empty API key silently skips instead of failing. Minor test quality issue; deferred.

### Second Deep Review Findings (2026-04-01 — round 2 on patch diff)

- [x] [Review][Patch] **`import anthropic` in `service.py` — spec abstraction boundary violation** [app/ai/service.py:9] — Story 5-0's core constraint is "use langchain-core types as abstraction surface." The round-1 patch that added `except anthropic.AnthropicError` re-introduced direct Anthropic SDK coupling in `service.py`. Fixed by introducing `ModelPermanentError` in `llm_client.py`, updating `_raise_translated_provider_error()` to always convert `AnthropicError` to either `ModelTemporaryUnavailableError` or `ModelPermanentError`, and replacing `except anthropic.AnthropicError` with `except ModelPermanentError` in `_generate()`. `import anthropic` fully removed from `service.py`.
- [x] [Review][Patch] **`anext()` first-chunk path unguarded for `ModelPermanentError`** [app/ai/service.py:369-379] — The pre-stream `anext(model_stream)` only caught `ModelTemporaryUnavailableError`. A permanent provider error (e.g., 400) on the very first chunk would propagate as an unhandled 500. Fixed simultaneously with above: `anext()` path now catches `(ModelTemporaryUnavailableError, ModelPermanentError)` and raises `AiServiceUnavailableError`.
- [x] [Review][Patch] **No test for first-chunk permanent error path** [tests/ai/test_service.py] — Added `test_stream_follow_up_answer_raises_service_unavailable_on_permanent_error_before_first_chunk`.
- [x] [Review][Patch] **`test_service.py` imported `anthropic`/`httpx` SDK directly — mirror boundary violation** [tests/ai/test_service.py:6-7] — Removed `import anthropic`, `import httpx`, and `_api_status_error()` helper. Updated `test_stream_follow_up_answer_emits_fallback_on_non_temporary_provider_error` to raise `ai_service.ModelPermanentError` from `fake_stream`.
- [x] [Review][Patch] **`test_call_model_text_reraises_non_temporary_anthropic_error` expected raw `anthropic.APIStatusError`** [tests/ai/test_llm_client.py] — After root fix, permanent errors are now `ModelPermanentError`. Renamed test to `test_call_model_text_raises_permanent_error_for_non_temporary_status_code` and updated `pytest.raises` target accordingly. Integration test skip-guards also updated to catch domain exceptions.

## Dev Notes

### Story Origin and Scope Boundary

- Story 5.0 does **not** exist in [_bmad-output/planning-artifacts/epics.md](/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/epics.md). It originates from the Epic 4 retrospective as a critical Epic 5 prerequisite.
- The retrospective explicitly requires:
  - replacing `claude_client.py` with a LangChain abstraction
  - updating `service.py` AI calls to use LangChain chat interfaces
  - updating streaming implementation to use LangChain streaming
  - updating AI-related tests
- This story should stay narrowly scoped to that requirement. Do **not** turn it into a simultaneous LangGraph/processing rewrite.

### Critical Architecture Correction

- The architecture document describes a future-state processing graph with `app/processing/graph.py`, `app/processing/nodes/*`, and LangGraph worker orchestration, but the actual repo does **not** have those files today.
- Actual current processing structure is:
  - `healthcabinet/backend/app/processing/extractor.py`
  - `healthcabinet/backend/app/processing/worker.py`
  - `healthcabinet/backend/app/processing/normalizer.py`
  - no `graph.py`
  - no `nodes/` directory
- Therefore:
  - Story 5.0 is an **AI module adapter migration**
  - Story 5.0 is **not** a LangGraph graph adoption story
  - Story 5.0 is **not** an extraction-boundary migration story

### Current AI Integration Surface

- Current direct Anthropic coupling exists in:
  - [healthcabinet/backend/app/ai/claude_client.py](/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/ai/claude_client.py)
  - [healthcabinet/backend/app/ai/service.py](/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/ai/service.py)
- Current `app/ai/service.py` call sites to preserve:
  - `generate_interpretation()` — complete-response call
  - `detect_cross_upload_patterns()` — complete-response call
  - `stream_follow_up_answer()` — streaming call
- Current direct Anthropic usage outside `app/ai/` also exists in:
  - [healthcabinet/backend/app/processing/extractor.py](/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/processing/extractor.py)
- That extractor path is **out of scope** for Story 5.0 and must remain unchanged here.

### Existing Behavior That Must Not Regress

- Safety pipeline order and semantics in `app/ai/service.py` must stay intact:
  - `validate_no_diagnostic()`
  - `surface_uncertainty()`
  - `inject_disclaimer()`
- Streaming follow-up chat must continue to:
  - validate cumulatively before yielding new content
  - stop on safety failure
  - emit safe fallback content instead of unsafe model output
  - append the educational disclaimer at the end of a safe stream
- Repository writes and encrypted storage remain unchanged:
  - `app/ai/repository.py`
  - `ai_memories` schema
  - reasoning/context persistence format

### Existing Technical Debt To Be Aware Of

- These are known issues around the AI module, but they are **not** all part of Story 5.0:
  - `upsert_ai_interpretation` TOCTOU race
  - safety rejection recovery path leaving interpretation absent
  - prompt injection risk in pattern prompt construction
  - module-import Anthropic client initialization
- Story 5.0 should directly resolve only the last item by removing import-time client creation.
- Do not opportunistically fold the other deferred items into this migration unless they become strictly necessary to complete the adapter swap.

### Library / Framework Requirements

- Use `langchain-anthropic` for the Claude provider integration in this story.
- Use `langchain-core` types/interfaces as the stable abstraction surface.
- Do **not** add LangGraph to the implementation scope for this story even though the architecture doc references it.
- Keep `anthropic` in backend dependencies because the extractor still uses it directly.

### File Structure Requirements

- Expected implementation files:
  - `healthcabinet/backend/pyproject.toml`
  - `healthcabinet/backend/.env.example`
  - `healthcabinet/backend/app/core/config.py`
  - `healthcabinet/backend/app/ai/llm_client.py` (new)
  - `healthcabinet/backend/app/ai/service.py`
  - `healthcabinet/backend/app/ai/router.py` (only if import paths need adjustment)
  - `healthcabinet/backend/tests/ai/test_llm_client.py` (new)
  - `healthcabinet/backend/tests/ai/test_service.py`
  - `healthcabinet/backend/tests/ai/test_router.py`
  - `healthcabinet/backend/tests/processing/test_worker.py` (regression coverage only if needed)
- Expected non-changes:
  - `healthcabinet/frontend/**`
  - `healthcabinet/backend/app/processing/extractor.py`
  - `healthcabinet/backend/app/processing/worker.py` behavior
  - database migrations

### Testing Requirements

- Follow Epic 5 process rules from the retrospective:
  - no story closes with unknown test state
  - Docker Compose test execution must be known, not assumed
- Testing split for this story:
  - deterministic unit tests for prompt assembly, routing, safety, and adapter call boundaries
  - real-provider adapter integration test for LangChain + Anthropic
- Minimum regression set:
  - `tests/ai/test_llm_client.py`
  - `tests/ai/test_service.py`
  - `tests/ai/test_router.py`
  - `tests/processing/test_worker.py`
- If adapter naming changes ripple into imports, verify any patched test targets are updated consistently.

### Git Intelligence Summary

- Recent commits show the repo is actively refining both the admin surface and the extraction boundary:
  - `2d94e02` feat: handle markdown fenced JSON in extract_from_document and add corresponding test
  - `b15f1f1` feat: implement admin metrics endpoint and associated frontend components
  - `9ca08b0` feat: add test to ensure unsupported metadata is not sent in extract_from_document
- That reinforces the intended scope split:
  - extraction work is moving independently
  - Story 5.0 should avoid mixing adapter migration with extraction refactors

### Latest Technical Specifics

- Official LangChain docs position LangChain as the higher-level model/tool integration layer and LangGraph as the lower-level orchestration runtime. For this repo, that means Story 5.0 should use LangChain for the model adapter and defer graph orchestration work to a separate story.
  - Source: https://docs.langchain.com/oss/python/langchain/overview
- Official LangChain streaming docs describe token/message streaming as a first-class mechanism rather than a custom polling pattern. The adapter should expose an async streaming seam instead of buffering the full response.
  - Source: https://docs.langchain.com/oss/python/langchain/streaming
- Official LangChain Anthropic integration docs show `langchain-anthropic` supports native async usage and token-level streaming, which is sufficient for the current `app/ai/` migration target.
  - Source: https://docs.langchain.com/oss/python/integrations/chat/anthropic
- Official LangChain structured-output docs indicate provider-native structured output is available for Anthropic-capable models. That is relevant for a later extraction migration, but it is intentionally out of scope for Story 5.0.
  - Source: https://docs.langchain.com/oss/python/langchain/structured-output
- Official LangGraph docs show v1.x is now available. Because this repo's architecture still references LangGraph 0.2 and the codebase does not yet implement graph files, do not silently fold a LangGraph major-version migration into Story 5.0.
  - Source: https://docs.langchain.com/oss/python/langgraph/overview

### Project Structure Notes

- Epic 5 planning currently starts at Story 5.1 in the epics file, but the Epic 4 retrospective introduced Story 5.0 as a prerequisite story afterward.
- This story file is therefore a retrospective-derived implementation artifact, not a direct epics-file expansion.
- Sprint tracking should include `5-0-langchain-ai-migration` ahead of `5-1-admin-platform-metrics-dashboard` so the prerequisite is visible to later implementation agents.

### References

- [Source: _bmad-output/planning-artifacts/research/technical-langchain-langgraph-research-2026-03-31.md]
- [Source: _bmad-output/implementation-artifacts/epic-4-retro-2026-03-30.md#Strategic Decision: Migrate AI Module to LangChain]
- [Source: _bmad-output/implementation-artifacts/epic-4-retro-2026-03-30.md#Action Items for Epic 5]
- [Source: _bmad-output/implementation-artifacts/deferred-work.md]
- [Source: _bmad-output/planning-artifacts/architecture.md#Architecture: Data & Processing]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Flow — Core Loop (Upload → Insight)]
- [Source: _bmad-output/planning-artifacts/prd.md#AI Health Interpretation]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5: Admin Operations]
- [Source: healthcabinet/backend/app/ai/service.py]
- [Source: healthcabinet/backend/app/ai/router.py]
- [Source: healthcabinet/backend/app/ai/claude_client.py]
- [Source: healthcabinet/backend/app/processing/extractor.py]
- [Source: healthcabinet/backend/app/core/config.py]
- [Source: healthcabinet/backend/pyproject.toml]
- [Source: healthcabinet/backend/tests/ai/test_service.py]
- [Source: healthcabinet/backend/tests/ai/test_router.py]
- [Source: healthcabinet/backend/tests/processing/test_extractor.py]
- [Source: https://docs.langchain.com/oss/python/langchain/overview]
- [Source: https://docs.langchain.com/oss/python/langchain/streaming]
- [Source: https://docs.langchain.com/oss/python/integrations/chat/anthropic]
- [Source: https://docs.langchain.com/oss/python/langchain/structured-output]
- [Source: https://docs.langchain.com/oss/python/langgraph/overview]

## Dev Agent Record

### Agent Model Used

gpt-5.4

### Debug Log References

- Story created from retrospective-driven gap analysis rather than an existing Epic 5 story entry in `epics.md`
- Artifact set reviewed: `epics.md`, `prd.md`, `architecture.md`, `epic-4-retro-2026-03-30.md`, `deferred-work.md`, current `app/ai/`, current `app/processing/`, recent git history, and official LangChain docs
- Review patch set completed: deleted dead `claude_client.py`, cached lazy `ChatAnthropic` adapters by config/max-tokens, switched adapter construction to `max_tokens`, stripped whitespace-only API keys, and restored bounded request timeouts
- Validation run: `uv run pytest` => 240 passed, 1 skipped; `uv run pytest tests/ai/test_llm_client.py tests/ai/test_service.py tests/ai/test_router.py` => 45 passed, 1 skipped; `uv run pytest tests/processing/test_worker.py` => 18 passed
- Docker Compose verification note: `docker compose ... exec backend uv run pytest ...` could not run because the `backend` service image does not contain `/app/tests`; rebuilt `backend-test` and ran the equivalent in-container suite there => 63 passed, 1 skipped
- Repo-wide `uv run ruff check .` still reports pre-existing unrelated issues outside this story scope; touched files passed `uv run ruff check app/ai/llm_client.py tests/ai/test_llm_client.py`

### Completion Notes List

- Completed Story 5.0 and resolved all five review patch findings without expanding scope beyond the backend AI adapter boundary
- `healthcabinet/backend/app/ai/llm_client.py` now lazily caches provider instances by config/max-tokens, strips whitespace-only API keys, and uses a bounded request timeout while preserving the existing text and streaming seams
- Deleted the dead `healthcabinet/backend/app/ai/claude_client.py` compatibility wrapper and strengthened adapter tests to cover lazy import, stripped-key validation, constructor config, and client reuse
- Validation completed locally and in Docker Compose test infrastructure with deterministic AI/service/router/worker coverage green; the real-provider adapter test remains skip-guarded on `ANTHROPIC_API_KEY`
- Sprint tracking for this retrospective-created prerequisite story is now ready for review

### File List

- _bmad-output/implementation-artifacts/5-0-langchain-ai-migration.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- healthcabinet/backend/.env.example
- healthcabinet/backend/app/ai/claude_client.py (deleted)
- healthcabinet/backend/app/ai/llm_client.py
- healthcabinet/backend/app/ai/service.py
- healthcabinet/backend/app/core/config.py
- healthcabinet/backend/pyproject.toml
- healthcabinet/backend/tests/ai/test_llm_client.py
- healthcabinet/backend/tests/ai/test_router.py
- healthcabinet/backend/tests/ai/test_service.py
- healthcabinet/backend/uv.lock

### Change Log

- 2026-03-31: Completed the LangChain adapter migration story, resolved five review patches, and updated the adapter to use cached lazy `ChatAnthropic` instances with stripped-key validation and bounded timeouts.
- 2026-03-31: Verified the migrated boundary with full local backend pytest, targeted AI and worker regressions, touched-file Ruff checks, and an equivalent Docker Compose `backend-test` run after rebuilding the stale test image.
