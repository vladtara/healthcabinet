# Story 2.3: Universal Value Extraction & Confidence Scoring

Status: done

## Story

As a **registered user**,
I want the system to automatically extract structured health values from my uploaded document regardless of format, language, or lab,
So that I have normalized, queryable health data with clear quality indicators.

## Acceptance Criteria

1. **LangGraph extraction pipeline:** Given a document has been uploaded and the ARQ worker picks up the job, When the extraction pipeline runs, Then Claude's multi-modal API is called with the document (image or PDF) to extract health values, And each extracted value is stored as a `health_values` row with `document_id`, `user_id`, `name`, `value` (encrypted via AES-256-GCM at repository layer), `unit`, `reference_low`, `reference_high`, and `confidence` (0.0–1.0).

2. **Atomic writes + terminal status:** Given extraction completes, When values are written to the database, Then all values for the document are written in a single SQLAlchemy transaction (all saved or none), And the document `status` is updated to `completed`, `partial`, or `failed` accordingly.

3. **Low-confidence handling:** Given one or more extracted values have `confidence < 0.7`, When document processing completes, Then the document is marked `partial` (never silently accepted), And low-confidence values are flagged for user review.

4. **Unified user timeline:** Given multiple documents exist for the same user, When a new document is processed, Then biomarker values from all documents are linked to a unified per-user timeline queryable by biomarker name across all `document_id` values for that user.

5. **Format and language robustness:** Given a document is non-English or from an unusual lab format, When extraction runs, Then the pipeline still produces structured output, And the `user_id` on every saved `health_values` row matches the authenticated uploader's user ID.

6. **Observability:** Given the pipeline is executed, Then LangSmith tracing is enabled per `document_id` so every node execution is observable.

## Tasks / Subtasks

- [x] Task 1 - Establish processing state + extraction schema (AC: 1, 3, 5)
  - [x] Add a processing state type in `healthcabinet/backend/app/processing/schemas.py` for the extraction pipeline result, separate from the existing SSE event payloads.
  - [x] Define a strict Pydantic schema for Claude output with fields aligned to product needs and storage needs:
    - [x] document-level summary: `measured_at`, `source_language`, `raw_lab_name` or equivalent metadata if available
    - [x] value-level rows: `biomarker_name`, `value`, `unit`, `reference_range_low`, `reference_range_high`, `confidence`
  - [x] Keep `confidence` bounded to `0.0 <= confidence <= 1.0`.
  - [x] Make missing ranges and units explicit with nullable fields rather than overloaded sentinel strings.

- [x] Task 2 - Implement extraction client boundary (AC: 1, 5)
  - [x] Replace the placeholder in `healthcabinet/backend/app/processing/extractor.py` with a real Claude-backed extractor function.
  - [x] Support both image documents and PDFs from the stored object, without assuming only images.
  - [x] Keep Anthropic API calls isolated in extractor-facing code so `worker.py` remains orchestration, not prompt construction.
  - [x] Return validated structured extraction output, not free-form text.
  - [x] Log enough metadata for debugging, but never log raw health values or raw document bytes.

- [x] Task 3 - Add normalization helpers for biomarker naming and unit handling (AC: 1, 4, 5)
  - [x] Replace the placeholder in `healthcabinet/backend/app/processing/normalizer.py`.
  - [x] Normalize common biomarker aliases to a canonical name so future timeline queries can group values across labs.
  - [x] Normalize units where safe and deterministic; if conversion is not trustworthy, preserve the original unit and reduce confidence instead of inventing conversions.
  - [x] Keep normalization pure and side-effect free so it can be unit-tested thoroughly.

- [x] Task 4 - Build health data persistence layer with encryption boundary (AC: 1, 2, 4, 5)
  - [x] Implement `healthcabinet/backend/app/health_data/repository.py`.
  - [x] Add repository functions for:
    - [x] writing a batch of extracted `HealthValue` records atomically for one document
    - [x] deleting/replacing prior values for one document if reprocessing is needed later
    - [x] listing values by `user_id`
    - [x] listing timeline values by `user_id` and canonical `biomarker_name`
  - [x] Encrypt numeric value payloads in the repository only, following the same boundary rule used by `documents/repository.py`.
  - [x] Do not move encryption into routers, services, worker code, or model properties.
  - [x] Use the document owner's `user_id` from the `Document` row, never from extraction output.

- [x] Task 5 - Align the `HealthValue` model and schemas with story requirements (AC: 1, 3, 4)
  - [x] Update `healthcabinet/backend/app/health_data/models.py` so the ORM supports story requirements:
    - [x] `confidence` column
    - [x] low-confidence review flag field aligned with future UI/admin flows
    - [x] canonical biomarker name field naming consistent with repo conventions
  - [x] Preserve immutability intent for extracted values unless replacement is explicitly document-scoped.
  - [x] Create or update `healthcabinet/backend/app/health_data/schemas.py` for API-safe response models the later stories can reuse.
  - [x] If a migration is required, add a new Alembic migration instead of editing old ones.

- [x] Task 6 - Upgrade worker orchestration from stubbed sleeps to real extraction flow (AC: 1, 2, 3, 5, 6)
  - [x] Refactor `healthcabinet/backend/app/processing/worker.py` so the existing stage events remain intact but actual work happens between them.
  - [x] Recommended order:
    - [x] publish `document.upload_started`
    - [x] set document status to `processing`
    - [x] publish `document.reading`
    - [x] fetch document metadata + object bytes
    - [x] publish `document.extracting`
    - [x] run extractor + normalization + confidence evaluation
    - [x] atomically persist health values
    - [x] publish `document.generating`
    - [x] determine terminal document status: `completed`, `partial`, or `failed`
    - [x] publish matching terminal SSE event
  - [x] If zero usable values are produced, mark the document `failed`.
  - [x] If any saved value has confidence below threshold, mark the document `partial`.
  - [x] If all saved values meet threshold, mark the document `completed`.

- [x] Task 7 - Fetch source files from object storage safely (AC: 1, 5)
  - [x] Extend the documents storage/service layer with a read path for worker use.
  - [x] Reuse the encrypted `s3_key` storage pattern already established in `documents/repository.py`.
  - [x] Keep ownership checks at the document lookup boundary; worker-internal file fetch may use the internal repository function because the worker already operates on a single trusted document ID.
  - [x] Avoid loading or exposing unrelated user files during processing.

- [x] Task 8 - LangSmith observability wiring (AC: 6)
  - [x] Add explicit tracing around the extraction pipeline, keyed by `document_id`.
  - [x] Use environment-driven tracing so the feature can be enabled in deployed environments without code changes.
  - [x] Tag traces with safe metadata such as `document_id`, `document_type`, and pipeline stage.
  - [x] Do not send raw document bytes or unnecessary PHI into trace metadata.

- [x] Task 9 - Surface saved values through health-data routes needed by current frontend cache invalidation (AC: 4)
  - [x] Implement the minimal backend route/service/repository path needed so the invalidated `['health_values']` query key has a real API to hit in upcoming work.
  - [x] Keep scope minimal: Story 2.3 is about extraction and persistence, not the full document detail UI from Story 2.4.
  - [x] If a route already exists as a placeholder, flesh it out instead of creating a duplicate API surface.

- [x] Task 10 - Backend tests (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add focused tests under `healthcabinet/backend/tests/processing/` for:
    - [x] successful extraction persists values and emits `document.completed`
    - [x] low-confidence values persist and emit `document.partial`
    - [x] zero-usable-value extraction emits `document.failed`
    - [x] worker status progression remains `processing -> completed|partial|failed`
    - [x] extractor failures roll back writes and do not leave partial DB state
  - [x] Add repository tests under `healthcabinet/backend/tests/health_data/` for:
    - [x] encrypted value round-trip
    - [x] atomic batch save semantics
    - [x] user isolation on timeline queries
    - [x] canonical biomarker grouping across multiple documents
  - [x] Mock Anthropic and storage access; never hit external APIs in tests.

- [x] Task 11 - Guardrail cleanup for placeholders and integration points (AC: 1, 2, 4)
  - [x] Remove or replace placeholder comments in `processing/extractor.py`, `processing/normalizer.py`, `health_data/repository.py`, and `health_data/schemas.py`.
  - [x] Register any newly functional health-data router endpoints in `healthcabinet/backend/app/main.py` if not already present.
  - [x] Keep story scope away from AI interpretation generation; the `document.generating` stage remains part of the existing pipeline contract, but interpretation content is a later story concern.

## Dev Notes

### Story Scope and Boundaries

- Story 2.2 already built the SSE transport, latest-event cache, and stage sequencing. Preserve those contracts.
- Story 2.3 replaces the worker's stubbed `asyncio.sleep()` extraction stages with real document reading, extraction, normalization, and persistence.
- Do not implement the document cabinet UI from Story 2.4, the re-upload UX from Story 2.5, or user flagging UI from Story 2.6 here.
- Do not redesign authentication, upload flow, or SSE auth. Those are already implemented and tested.

### Current Codebase Reality

- `healthcabinet/backend/app/processing/worker.py` is the current orchestration entrypoint and still uses sleeps as placeholders.
- `healthcabinet/backend/app/processing/extractor.py` and `healthcabinet/backend/app/processing/normalizer.py` are placeholders.
- `healthcabinet/backend/app/health_data/repository.py` and `healthcabinet/backend/app/health_data/schemas.py` are placeholders.
- `healthcabinet/backend/app/health_data/models.py` currently lacks required fields like `confidence` and low-confidence review state, so Story 2.3 must close that gap.
- Frontend upload flow already transitions through `DocumentUploadZone` to `ProcessingPipeline` and handles `completed`, `partial`, and `failed` terminal states.

### Architecture Compliance

- Backend stays FastAPI + SQLAlchemy 2.0 async + ARQ + Redis.
- Layer boundaries remain strict:
  - `router.py` for HTTP only
  - `service.py` for orchestration/business logic
  - `repository.py` for all DB reads and writes
  - encryption only in repository layer
- Use `Mapped[...]` and `mapped_column()` only.
- Use async DB access throughout. No sync SQLAlchemy patterns.
- Document processing must remain non-blocking from the user's perspective and continue publishing SSE stages through the existing route.

### Database and Persistence Guardrails

- All extracted values for one document must be written in one transaction.
- Never trust extracted `user_id`; derive ownership from the source `Document`.
- Timeline support depends on canonical biomarker naming. Normalize names before write, not only at query time.
- Partial extraction is a document terminal state, not a silent soft warning.
- If the write transaction fails, do not leave the document in `completed` or `partial`.

### Confidence Rules

- Confidence threshold is `0.7` per the epic.
- Treat confidence as a persisted data attribute, not a transient UI-only value.
- A document becomes `partial` if one or more persisted values are below threshold, even if other values are good.
- Low-confidence values should be explicitly marked for review so Stories 2.4, 2.5, and 6.2 can build on stored state instead of recomputing it.

### Extraction Pipeline Shape

- Keep orchestration simple and explicit. A full `graph.py` and node folder do not yet exist in the repo, so do not create an overbuilt framework unless it materially helps this story.
- A pragmatic implementation is acceptable:
  - extractor boundary for model call
  - normalizer boundary for canonicalization
  - repository boundary for atomic save
  - worker orchestration for status and error handling
- If you introduce LangGraph primitives now, keep them small and story-focused so later AI stories can extend them instead of replacing them.

### Storage and File Handling

- Uploaded files live in MinIO and the encrypted object key already exists in `documents`.
- The worker needs a read path from MinIO or compatible storage helper code.
- Support both `application/pdf` and image uploads already accepted by Story 2.1.
- Do not assume a single-page document.

### Frontend and API Implications

- The current upload page at `healthcabinet/frontend/src/routes/(app)/documents/upload/+page.svelte` already reacts correctly to `completed`, `partial`, and `failed`.
- The current cache invalidation targets `['documents']` and `['health_values']`, so Story 2.3 should make backend `health_values` retrieval viable for follow-on UI work.
- Avoid changing the SSE event names or stage order unless a failing test proves it necessary.

### Testing Requirements

- Start with small, story-local tests first:
  - extractor unit tests with mocked client responses
  - normalizer unit tests for canonical names and unit conversion
  - repository tests for encryption and atomic save semantics
  - worker tests for terminal-state branching
- Then run the relevant backend processing and health-data suites.
- Existing processing router tests are a regression boundary. Do not break Story 2.2 behavior.

### Previous Story Intelligence

- Story 2.2 established the canonical SSE sequence and already documents the exact transport contract.
- It also introduced `document.partial` as a valid terminal event even though the worker currently never emits it in practice.
- Reuse the Redis pub/sub and cached latest-event pattern from Story 2.2; do not invent a second progress transport.
- Keep the existing timeout and heartbeats in `processing/router.py` untouched unless extraction duration proves they need coordinated adjustment.

### Git Intelligence Summary

- Recent commits show the current branch focus is still Epic 2 pipeline work:
  - `713cecd feat: implement real-time document processing status with SSE and error handling`
  - `0b32d91 feat: enhance document processing flow with error handling and state management`
- Inference: Story 2.3 should extend the established processing path rather than refactor it wholesale.

### Latest Technical Information

- As of March 23, 2026, LangGraph official docs show `v1.x` is available. The repo architecture document still references `LangGraph 0.2`, so keep this story compatible with the installed project dependencies rather than silently upgrading framework versions. Source: https://docs.langchain.com/oss/python/langgraph
- LangChain official docs indicate provider-native structured output is supported for Anthropic models. Prefer validated structured output for extraction responses instead of parsing free-form prose. Source: https://docs.langchain.com/oss/python/langchain/structured-output
- Anthropic official docs state Claude vision supports image inputs, recommends images no larger than 1568 px on the long edge for latency efficiency, and caps standard request payloads at 32MB. Source: https://docs.anthropic.com/en/docs/build-with-claude/vision
- Anthropic official docs also state PDF support is available through document content blocks and subject to 32MB total request size and 100-page limits. Source: https://docs.anthropic.com/en/docs/build-with-claude/pdf-support
- LangSmith official docs state tracing is enabled via environment variables such as `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, and optional project naming. Source: https://docs.langchain.com/oss/python/langgraph/observability

### Project Context Reference

- Backend rules and patterns: `_bmad-output/project-context.md`
- Planning sources:
  - `_bmad-output/planning-artifacts/epics.md`
  - `_bmad-output/planning-artifacts/architecture.md`
  - `_bmad-output/planning-artifacts/prd.md`
  - `_bmad-output/planning-artifacts/ux-design-specification.md`
- Prior implementation context:
  - `_bmad-output/implementation-artifacts/2-2-real-time-processing-pipeline-status.md`

### Completion Status

- Story context created from epic, PRD, architecture, UX, project context, previous story, current codebase state, git history, and current official docs.
- Ultimate context engine analysis completed - comprehensive developer guide created.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Verified Anthropic Claude model naming and LangSmith tracing env controls against official docs before wiring the extractor defaults and tracing hooks.
- Added `ANTHROPIC_EXTRACTION_MODEL`, `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, and `LANGSMITH_PROJECT` config knobs; tracing is environment-driven and logs safe metadata only.
- Implemented internal document object-key read access in `documents/repository.py` and a storage read helper in `documents/storage.py` so the worker can fetch only the trusted document payload it is processing.
- Replaced all remaining Story 2.3 placeholders across `processing/extractor.py`, `processing/normalizer.py`, `health_data/repository.py`, `health_data/schemas.py`, `health_data/service.py`, and `health_data/router.py`.
- Added `004_health_values.py` because the existing migrations never created the `health_values` table.
- Full backend suite was run three times in validation. One run exposed a stale logout test assumption, which was corrected to include the required access token. One run hit transient asyncpg connection-reset errors while creating the shared test DB. The final rerun passed cleanly.

### Completion Notes

- Implemented a real document-processing pipeline in `processing/worker.py`: worker now reads the stored object, calls the Claude-backed extractor, normalizes biomarker values, persists them atomically, computes terminal status (`completed`, `partial`, `failed`), and publishes the existing SSE stage events unchanged.
- Added strict extraction and processing schemas in `processing/schemas.py`, including bounded confidence values and a separate processing-state model that is distinct from SSE payload models.
- Implemented pure biomarker/unit normalization in `processing/normalizer.py` with canonical biomarker aliases, deterministic safe unit normalization, and confidence downgrades when normalization certainty is limited.
- Built the health-data persistence and API path: updated `HealthValue` ORM fields, added encrypted repository writes and timeline reads, created response schemas, exposed `/api/v1/health-values` and `/api/v1/health-values/timeline/{canonical_biomarker_name}`, and registered the router in `app/main.py`.
- Added focused Story 2.3 backend coverage for extractor, normalizer, worker status branching, encrypted repository behavior, user isolation, and timeline grouping.
- Validation completed:
  - `uv run ruff check ...` on touched backend files passed.
  - `uv run mypy app/documents/storage.py app/processing/extractor.py app/processing/worker.py app/health_data/repository.py app/health_data/router.py app/health_data/schemas.py app/health_data/service.py app/processing/normalizer.py app/processing/schemas.py app/health_data/models.py app/core/security.py` passed.
  - `uv run pytest tests/processing/test_events.py tests/processing/test_worker.py tests/processing/test_normalizer.py tests/processing/test_extractor.py tests/health_data/test_repository.py tests/health_data/test_router.py` passed: 22 tests.
  - `uv run pytest tests/processing/test_router.py tests/documents/test_repository.py tests/documents/test_router.py` passed: 25 tests.
  - `uv run pytest` passed: 100 tests.
- **Review findings resolved (2026-03-23):**
  - ✅ Resolved review finding [Patch]: Stale health values on reprocessing — added `delete_document_health_values()` to repository, worker now calls it unconditionally before the has_values branch.
  - ✅ Resolved review finding [Patch]: AC 6 LangSmith tracing — replaced structlog-only `_pipeline_trace` with real `langsmith.trace` SDK integration; added `langsmith>=0.3.0` dependency.
  - ✅ Resolved review finding [Patch]: Document-owner invariant — `replace_document_health_values` now fetches the Document and asserts `doc.user_id == user_id` before writing.
  - Added 5 new tests: 2 for LangSmith tracing (enabled/disabled), 3 for repository (owner mismatch, nonexistent doc, stale value cleanup). Updated 3 existing worker tests to verify `delete_document_health_values` is called.
  - All 53 unit tests pass. Lint and mypy clean.

## File List

- `healthcabinet/backend/alembic/versions/004_health_values.py`
- `healthcabinet/backend/app/core/config.py`
- `healthcabinet/backend/app/core/security.py`
- `healthcabinet/backend/app/documents/repository.py`
- `healthcabinet/backend/app/documents/storage.py`
- `healthcabinet/backend/app/health_data/models.py`
- `healthcabinet/backend/app/health_data/repository.py`
- `healthcabinet/backend/app/health_data/router.py`
- `healthcabinet/backend/app/health_data/schemas.py`
- `healthcabinet/backend/app/health_data/service.py`
- `healthcabinet/backend/app/main.py`
- `healthcabinet/backend/app/processing/extractor.py`
- `healthcabinet/backend/app/processing/normalizer.py`
- `healthcabinet/backend/app/processing/schemas.py`
- `healthcabinet/backend/app/processing/worker.py`
- `healthcabinet/backend/pyproject.toml`
- `healthcabinet/backend/tests/auth/test_router.py`
- `healthcabinet/backend/tests/health_data/__init__.py`
- `healthcabinet/backend/tests/health_data/test_repository.py`
- `healthcabinet/backend/tests/health_data/test_router.py`
- `healthcabinet/backend/tests/processing/test_extractor.py`
- `healthcabinet/backend/tests/processing/test_normalizer.py`
- `healthcabinet/backend/tests/processing/test_worker.py`

## Change Log

- 2026-03-23: Story moved to `in-progress` for implementation.
- 2026-03-23: Implemented Story 2.3 backend extraction pipeline, health-data persistence/API, migration, and focused backend tests.
- 2026-03-23: Added backend validation fixes during final regression pass, including auth logout test alignment with the route’s access-token requirement.
- 2026-03-23: Addressed code review findings — 3 items resolved:
  - Fixed stale health values on failed/empty reprocessing: worker now calls `delete_document_health_values` before persisting new values.
  - Implemented real LangSmith tracing (AC 6): replaced structlog-only `_pipeline_trace` with `langsmith.trace` SDK integration; added `langsmith>=0.3.0` to dependencies.
  - Enforced document-owner invariant at repository boundary: `replace_document_health_values` now verifies `document.user_id == user_id` before writing.

### Review Findings

- [x] [Review][Patch] Unit normalization converts biomarker values without converting the accompanying reference ranges [healthcabinet/backend/app/processing/normalizer.py:72]
- [x] [Review][Patch] Timeline endpoint requires callers to know the internal canonical biomarker key instead of normalizing input server-side [healthcabinet/backend/app/health_data/router.py:21]
- [x] [Review][Patch] Extractor relies on prompt-only JSON output and brittle `json.loads` parsing instead of provider-structured output [healthcabinet/backend/app/processing/extractor.py:79]
- [x] [Review][Patch] Worker/storage path reads the full object into memory without a server-side size guard [healthcabinet/backend/app/documents/storage.py:45]
- [x] [Review][Patch] A single undecryptable stored health value can fail the entire health-values read path [healthcabinet/backend/app/health_data/repository.py:34]
- [x] [Review][Patch] Backend entrypoint runs `alembic upgrade head` on every container start, creating a migration race across replicas [healthcabinet/backend/entrypoint.sh:4]
- [x] [Review][Patch] Failed or empty reprocessing leaves stale health values attached to the document [healthcabinet/backend/app/processing/worker.py:113]
- [x] [Review][Patch] AC 6 is not actually implemented; `_pipeline_trace()` adds logs, not LangSmith tracing [healthcabinet/backend/app/processing/worker.py:40]
- [x] [Review][Patch] Health-value persistence does not enforce the document-owner invariant at the repository boundary [healthcabinet/backend/app/health_data/repository.py:67]
