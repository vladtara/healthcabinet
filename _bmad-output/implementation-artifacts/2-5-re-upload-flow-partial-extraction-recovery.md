# Story 2.5: Re-Upload Flow & Partial Extraction Recovery

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a registered user,
I want clear guidance and a smooth re-upload path when my document produces a partial or failed extraction,
so that I can recover gracefully without losing my progress or feeling frustrated.

## Acceptance Criteria

1. Given a document processing completes with `status="partial"` (some values below confidence threshold), when the user views the document result, then a `PartialExtractionCard` is shown displaying the successfully extracted values alongside a "We couldn't read everything clearly" message, and a 3-tip photo guide is shown: good lighting, flat surface, no shadows.
2. Given a document processing completes with `status="failed"` (extraction produced no usable values), when the user views the result, then a clear failure message is shown with the same 3-tip photo guide and a prominent re-upload CTA.
3. Given a user clicks re-upload for a partial or failed document, when they select a new file, then the new upload replaces the previous attempt for that document slot with no duplicate document records created, and any previously extracted partial values from the original attempt are preserved until the new extraction succeeds.
4. Given a user decides the partial extraction is acceptable, when they choose "Keep partial results", then the partial values are retained as-is and the re-upload prompt is dismissed for that document on subsequent reloads.
5. Given a re-upload completes successfully, when the new extraction finishes, then the document `status` is updated to `completed` and the full set of values replaces the partial set.

## Tasks / Subtasks

- [x] Task 1 - Extend backend upload API for retrying an existing document slot (AC: 3, 4, 5)
  - [x] Add a dedicated owner-scoped retry endpoint, preferred shape: `POST /api/v1/documents/{document_id}/reupload-url`. Do not overload the existing create-upload endpoint because it currently guarantees a fresh document row.
  - [x] Add a dedicated owner-scoped endpoint to persist "Keep partial results", preferred shape: `POST /api/v1/documents/{document_id}/keep-partial`.
  - [x] Restrict retry to authenticated owners of documents in `partial` or `failed` status; reject retry attempts for `completed`, `pending`, or `processing` documents unless the implementation deliberately adds a new status and updates all consumers.
  - [x] Keep `user_id` sourced only from `Depends(get_current_user)` and preserve RFC 7807 error responses for invalid ownership or invalid retry state.
  - [x] Return the same `document_id` for a retry path so SSE and cabinet/detail UI stay scoped to one document slot.
  - [x] Decide retry quota policy explicitly: retries consume the same `rate_limit_upload` quota as fresh uploads (enforced via `Depends(rate_limit_upload)` on the retry endpoint).

- [x] Task 2 - Add document retry preparation logic in the documents service/repository layers (AC: 3, 4, 5)
  - [x] Add repository support for preparing an existing document row for re-upload without creating a second `documents` row.
  - [x] Persist enough document-level state to support both prompt dismissal and in-flight replacement semantics. Added `keep_partial` nullable boolean field via Alembic migration 005.
  - [x] Keep the current document metadata and visible extracted values authoritative until a replacement run reaches `completed`; do not overwrite active fields too early.
  - [x] Reset job state cleanly before enqueueing processing for the retry, including `arq_job_id` / `keep_partial` that would otherwise block the new run or hide recovery UI incorrectly.
  - [x] Prevent MinIO object leaks when the replacement filename changes. Old object is deleted best-effort after the DB row is updated with the new s3_key.

- [x] Task 3 - Preserve partial results until replacement succeeds in the processing pipeline (AC: 3, 5)
  - [x] Refactor `app/processing/worker.py` so it does not unconditionally delete prior `health_values` before knowing the retry succeeded.
  - [x] Keep existing partial values visible while the retry is in progress and if the retry fails again.
  - [x] Define retry-failure status semantics explicitly: if a document had preserved partial values before the retry and the new retry fails, the authoritative document status reverts to `partial` rather than remain `failed`.
  - [x] Replace old values atomically only inside the same transaction that persists the newly extracted values on a successful retry (via `replace_document_health_values`).
  - [x] Preserve the first-time upload behavior for brand-new documents so Story 2.1 through 2.4 flows do not regress.

- [x] Task 4 - Surface partial and failed recovery UI in the document detail experience (AC: 1, 2, 4, 5)
  - [x] Add a dedicated partial/failure recovery component `PartialExtractionCard.svelte` under `frontend/src/lib/components/health/`.
  - [x] Show the 3-tip photo guide in both partial and failed states with copy aligned to the UX spec: good lighting, flat surface, no shadows.
  - [x] Add a prominent re-upload CTA that targets the current document slot instead of creating a new document.
  - [x] Add a "Keep partial results" action for `partial` documents that persists prompt dismissal without deleting or mutating the current extracted values.
  - [x] Treat re-upload as the primary CTA and "Keep partial results" as a secondary action so the recovery card does not violate the UX rule against two primary buttons on one screen.

- [x] Task 5 - Reuse the upload route and page state for retry-aware flows (AC: 3, 5)
  - [x] Update `$lib/api/documents.ts` and `frontend/src/lib/types/api.ts` to support retry requests while keeping API payloads snake_case.
  - [x] Add explicit retry-context plumbing on `src/routes/(app)/documents/upload/+page.svelte` so the route accepts the target `document_id` via `?retryDocumentId=<id>` query param and passes that context into the retry API call.
  - [x] Update `DocumentUploadZone.svelte` so retries from Story 2.5 target an existing document slot instead of always requesting a fresh document row.
  - [x] Preserve the existing upload constraints: PDF/image only, 20MB max, presigned PUT to MinIO, and `notify` after upload succeeds.
  - [x] Reuse the existing processing SSE flow and query invalidation pattern rather than introducing polling or a second status transport.
  - [x] Cover the post-upload terminal path explicitly: when processing ends in `partial` or `failed` on the upload route, `PartialExtractionCard` is rendered inline with recovery affordances.

- [x] Task 6 - Make document cabinet and detail views reflect retry state transitions safely (AC: 1, 2, 3, 5)
  - [x] Ensure the document cabinet continues to show exactly one card for the document being retried (same document_id returned by retry endpoint).
  - [x] Confirm the detail panel can show prior partial values while a retry is pending or processing (worker preserves values until replacement succeeds).
  - [x] On successful retry, refresh `['documents']` and `['health_values']` so status and extracted values swap to the completed result (existing SSE invalidation reused).
  - [x] On failed retry, keep the recovery UI actionable and keep prior partial values available to the user (worker reverts to `partial` status).

- [x] Task 7 - Add backend tests for retry semantics and regression coverage (AC: 3, 4, 5)
  - [x] Add router/service tests covering owner-only retry, invalid retry states, same-document retry behavior, and no duplicate `documents` rows.
  - [x] Add worker tests proving retry success replaces prior values atomically.
  - [x] Add worker tests proving retry failure preserves prior partial values rather than deleting them.
  - [x] Keep or update existing tests that codify current one-shot processing semantics so the story documents the intended behavior change explicitly.

- [x] Task 8 - Add frontend tests for recovery UX and retry path wiring (AC: 1, 2, 3, 4, 5)
  - [x] Add route/component tests for the partial recovery card, failed recovery card, 3-tip photo guidance, re-upload CTA, and keep-partial-results dismissal.
  - [x] Add tests showing the retry flow keeps one document slot instead of creating a duplicate document card.
  - [x] Add tests proving the upload route can receive retry context and still uses the existing upload/notify/SSE sequence.
  - [x] Preserve accessibility expectations: keyboard activation, `aria-live` updates, dialog dismissal behavior, and 44x44px touch targets.

### Review Follow-ups (AI)

- [x] [AI-Review] Finding 1 (High) — Defer authoritative document metadata replacement until notify completes: add `pending_*` columns (migration 006), move metadata in notify, clean up abandoned pending key on repeat retry-url calls.
- [x] [AI-Review] Finding 2 (High) — Align all retry failure paths (unexpected exceptions) with partial preservation: hoist `prior_values_existed` before outer try, use it in outer except handler for status and event.
- [x] [AI-Review] Finding 3 (Med) — Immediate keep-partial UI dismissal: add detail cache optimistic update (`['documents', docId]`) in `keepPartialMutation.onSuccess`.
- [x] [AI-Review] Finding 4 (Med) — Prefix-based cleanup fallback when old key is corrupted: implement prefix delete in `generate_reupload_url()` when `old_s3_key is None`.

### Review Findings

- [x] [Review][Patch] Pending retry promotion drops zero-byte file sizes because `commit_pending_retry_metadata()` uses `or` fallback semantics for `pending_file_size_bytes`, so a staged value of `0` leaves the old authoritative size in place instead of promoting the new metadata [healthcabinet/backend/app/documents/repository.py:329]

## Dev Notes

### Story Scope and Boundaries

- This story builds directly on Story 2.4's document cabinet and detail view. The missing work is recovery UX plus backend retry semantics, not a redesign of uploads or the cabinet.
- Keep Story 2.5 focused on retry and recovery. Do not pull in Story 2.6 value-flagging or Epic 3 dashboard/trend work.
- "Keep partial results" is a UX decision in this story, not a separate data-migration project. Prefer preserving the current `documents`/`health_values` model unless implementation proves an audit trail is required.

### Story Intelligence From Prior Work

- Story 2.4 established the cabinet/detail panel, status badge mapping, and SSE-driven query invalidation around `['documents']` and `['health_values']`. Reuse those contracts instead of inventing a new fetch path. [Source: /Users/vladtara/dev/set-bmad/_bmad-output/implementation-artifacts/2-4-document-cabinet-individual-management.md]
- Current frontend upload code still assumes every upload request creates a fresh document row. Story 2.5 must reverse that assumption for retries triggered from partial/failed results. [Source: /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/lib/components/health/DocumentUploadZone.svelte]
- The most recent implementation commit was `b4c52da feat(documents): implement document listing, detail retrieval, and deletion`, so this story should preserve the document list/detail/delete contracts and extend them carefully rather than refactoring the whole module. [Source: git log --oneline -5]

### Backend Guardrails

- Keep the FastAPI layering strict: router for HTTP concerns, service for orchestration, repository for DB access, and encryption/decryption only inside repository code. [Source: /Users/vladtara/dev/set-bmad/_bmad-output/project-context.md#Critical Backend Rules]
- Current `documents` code has no retry primitive. `generate_upload_url()` always creates a new UUID and `notify_upload_complete()` only handles a brand-new or already-enqueued document. Story 2.5 must add an explicit retry path. [Source: /Users/vladtara/dev/set-bmad/healthcabinet/backend/app/documents/service.py]
- The worker currently deletes document health values before persisting new extraction output. That behavior is correct for one-shot processing but violates this story's requirement to preserve partial values until retry success. Treat `app/processing/worker.py` as a required change target. [Source: /Users/vladtara/dev/set-bmad/healthcabinet/backend/app/processing/worker.py]
- Prefer reusing `pending` and `processing` statuses for retry progress unless a new status is clearly needed. Adding a new status would force updates across backend schemas, frontend unions, status badges, and SSE handling. [Source: /Users/vladtara/dev/set-bmad/healthcabinet/backend/app/documents/repository.py; /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/lib/types/api.ts]
- If a retry started from a previously `partial` document fails again, keep the preserved values and restore the authoritative status to `partial` so API consumers do not see `failed` plus non-empty preserved results as contradictory state. [Source: /Users/vladtara/dev/set-bmad/healthcabinet/backend/app/processing/worker.py; /Users/vladtara/dev/set-bmad/healthcabinet/backend/app/documents/service.py]
- Because the current object key includes the filename, retrying with a different filename can orphan the superseded object unless the story enforces either stable retry keys or explicit cleanup of the old object after the new one wins. [Source: /Users/vladtara/dev/set-bmad/healthcabinet/backend/app/documents/service.py]
- The retry endpoint must make an explicit decision about whether retries count against the existing upload quota enforced by `Depends(rate_limit_upload)`. Do not leave that as an implementation-time product decision. [Source: /Users/vladtara/dev/set-bmad/healthcabinet/backend/app/documents/router.py]

### Frontend Guardrails

- Use Svelte 5 runes and TanStack Query patterns already present in the codebase. Existing queries correctly use the function form of `createQuery()` and `createMutation()`. [Source: /Users/vladtara/dev/set-bmad/_bmad-output/project-context.md#Critical Frontend Rules; /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/documents/+page.svelte]
- All network access must continue to flow through `$lib/api/client.svelte.ts`; do not call `fetch()` directly for authenticated backend requests. Presigned MinIO PUT remains the only direct upload exception. [Source: /Users/vladtara/dev/set-bmad/_bmad-output/project-context.md#Critical Frontend Rules; /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/lib/api/documents.ts]
- The documents detail panel in `src/routes/(app)/documents/+page.svelte` is already the user-visible result surface for partial/failed documents. Prefer extending that detail experience with a small dedicated recovery component rather than routing users to a brand-new result page. [Source: /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/documents/+page.svelte]
- Reuse the existing upload route `src/routes/(app)/documents/upload/+page.svelte` and `page-state.ts` to keep SSE status handling, query invalidation, and success/failure states consistent, but add explicit retry-context plumbing because the route currently has no built-in way to know which existing document slot is being retried. [Source: /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/documents/upload/+page.svelte; /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/documents/upload/page-state.ts]

### UX and Accessibility Requirements

- Partial extraction requires an inline actionable recovery surface, not a toast. The UX spec explicitly names `PartialExtractionCard` as the correct pattern. [Source: /Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/ux-design-specification.md#Feedback Patterns; /Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/epics.md]
- Failed extraction must show a clear failure state with the same three photo tips and a prominent retry action; do not hide the recovery path behind secondary copy or navigation. [Source: /Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/epics.md]
- The UX spec forbids two primary buttons on one screen. In the recovery card, re-upload is primary and "Keep partial results" must be visibly secondary. [Source: /Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/ux-design-specification.md]
- Preserve accessibility and responsiveness rules from Story 2.4: text plus color for status communication, keyboard-reachable actions, Escape/outside-click dismissal for dialogs, and 44x44px touch targets. [Source: /Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/ux-design-specification.md#Navigation Patterns; /Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/ux-design-specification.md#Responsive Design & Accessibility]

### Architecture Compliance

- SSE event transport is already defined as `document.upload_started -> document.reading -> document.extracting -> document.generating -> document.completed | document.failed | document.partial`. Story 2.5 should reuse this stream for retry progress unless a new event is proven necessary. [Source: /Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/architecture.md#Communication Patterns]
- Reliability requirements explicitly call for retryable uploads with no data loss and no silent extraction failures. This story is the concrete implementation of that architecture promise. [Source: /Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/architecture.md]
- Document management belongs in `app/documents/` and `frontend/src/routes/(app)/documents/`, while processing feedback belongs in `app/processing/`. Do not collapse worker logic into the documents router or service layer. [Source: /Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]

### Library and Framework Requirements

- FastAPI dependency injection remains the required pattern for auth, DB sessions, and rate limiting via `Depends(...)`; do not manually thread user identity or Redis into route bodies. [Source: /Users/vladtara/dev/set-bmad/_bmad-output/project-context.md#FastAPI Router Conventions]
- Svelte 5 runes remain mandatory for state and side effects. Avoid reintroducing Svelte 4 store/reactive syntax while implementing recovery UI. [Source: /Users/vladtara/dev/set-bmad/_bmad-output/project-context.md#Critical Frontend Rules]
- Keep query invalidation and cache usage aligned with the TanStack Query Svelte patterns already adopted in this repo. [Source: /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/documents/+page.svelte; /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/documents/upload/page-state.ts]

### File Structure Requirements

- Backend likely touch points:
  - `healthcabinet/backend/app/documents/router.py`
  - `healthcabinet/backend/app/documents/service.py`
  - `healthcabinet/backend/app/documents/repository.py`
  - `healthcabinet/backend/app/documents/schemas.py`
  - `healthcabinet/backend/app/processing/worker.py`
  - `healthcabinet/backend/tests/documents/test_router.py`
  - `healthcabinet/backend/tests/processing/test_worker.py`
- Frontend likely touch points:
  - `healthcabinet/frontend/src/lib/api/documents.ts`
  - `healthcabinet/frontend/src/lib/types/api.ts`
  - `healthcabinet/frontend/src/lib/components/health/DocumentUploadZone.svelte`
  - `healthcabinet/frontend/src/lib/components/health/` new recovery component(s)
  - `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte`
  - `healthcabinet/frontend/src/routes/(app)/documents/upload/+page.svelte`
  - `healthcabinet/frontend/src/routes/(app)/documents/upload/page-state.ts`
  - route/component tests near documents and upload flows

### Testing Requirements

- Backend:
  - Verify retrying a `partial` or `failed` document reuses the same `document_id`.
  - Verify no second document row is created during retry.
  - Verify retry is rejected for documents owned by another user or in non-retryable states.
  - Verify the chosen retry quota policy is enforced at the API layer.
  - Verify a failed retry of a previously partial document restores status `partial` and the detail endpoint still returns the preserved health values.
  - Verify retrying with a different filename does not leak the superseded object in MinIO.
  - Verify worker behavior for three distinct cases: first processing, successful retry replacement, failed retry preserving prior values.
- Frontend:
  - Verify partial result surfaces the recovery card and "Keep partial results" action.
  - Verify failed result surfaces the same photo guide and a retry CTA.
  - Verify retry context can be carried from the detail view into the upload route and then into the retry API call.
  - Verify the upload route's terminal `partial`/`failed` states either render the same recovery affordances or redirect into the detail surface that contains them.
  - Verify retry wiring targets the existing document slot and preserves a single cabinet card.
  - Verify SSE completion/failure still invalidates the correct query keys and updates the detail panel.

### Project Structure Notes

- The repo structure in `healthcabinet/` already matches the architecture boundaries for this story. No new top-level package or route namespace is needed.
- The current upload component tests contain stale selectors (`#file-input`, `#camera-input`) relative to the component markup. If those tests remain flaky during implementation, fix them as part of Story 2.5 only if the retry work touches that component anyway. [Source: /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/lib/components/health/DocumentUploadZone.svelte; /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/documents/upload/page.test.ts]

### References

- /Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/epics.md - Story 2.5: Re-Upload Flow & Partial Extraction Recovery
- /Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/epics.md - Epic 2: Health Document Upload & Processing
- /Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/prd.md - Graceful failure handling and re-upload prompt
- /Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/architecture.md - Reliability, communication patterns, and project boundaries
- /Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/ux-design-specification.md - Feedback patterns, navigation patterns, responsive design and accessibility
- /Users/vladtara/dev/set-bmad/_bmad-output/project-context.md - Critical backend rules, frontend rules, and testing rules
- /Users/vladtara/dev/set-bmad/_bmad-output/implementation-artifacts/2-4-document-cabinet-individual-management.md
- /Users/vladtara/dev/set-bmad/healthcabinet/backend/app/documents/router.py
- /Users/vladtara/dev/set-bmad/healthcabinet/backend/app/documents/service.py
- /Users/vladtara/dev/set-bmad/healthcabinet/backend/app/documents/repository.py
- /Users/vladtara/dev/set-bmad/healthcabinet/backend/app/processing/worker.py
- /Users/vladtara/dev/set-bmad/healthcabinet/backend/app/health_data/repository.py
- /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/documents/+page.svelte
- /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/lib/components/health/DocumentUploadZone.svelte
- /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/documents/upload/+page.svelte
- /Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/documents/upload/page-state.ts

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Loaded BMad config from `/Users/vladtara/dev/set-bmad/_bmad/bmm/config.yaml`.
- Identified `2-5-re-upload-flow-partial-extraction-recovery` as the next `ready-for-dev` story from sprint-status.yaml.
- Read all referenced backend source files: router, service, repository, schemas, models, worker, exceptions.
- Read all referenced frontend source files: documents API, types, +page.svelte, upload/+page.svelte, DocumentUploadZone, page-state.ts.
- Ran full backend test suite (139 tests, all passed) and frontend test suite (79 tests, all passed) inside Docker Compose.
- Ran `ruff check` on all modified backend modules — clean.

### Completion Notes List (Review Fix-up 2026-03-25)

- Added Alembic migration 005 for `keep_partial` nullable boolean column on `documents` table.
- Added `DocumentRetryNotAllowedError` exception + 409 handler in `main.py`.
- Added `POST /documents/{id}/reupload-url` and `POST /documents/{id}/keep-partial` endpoints to router, service, and repository.
- Updated `schemas.py` with `keep_partial` field on `DocumentResponse`/`DocumentDetailResponse`, and new `KeepPartialResponse`.
- Refactored `worker.py` to check for prior health values before deciding to delete/preserve. Retry failures with prior partial values now revert to `partial` status. The separate pre-delete call was removed; `replace_document_health_values` handles atomic delete+insert.
- Added `PartialExtractionCard.svelte` component with 3-tip photo guide, primary re-upload CTA, and secondary keep-partial action.
- Updated `documents.ts` API client with `getRetryUploadUrl` and `keepPartialResults` functions.
- Updated `DocumentUploadZone.svelte` with optional `retryDocumentId` prop that routes to retry endpoint.
- Updated upload `+page.svelte` to read `?retryDocumentId` query param and render `PartialExtractionCard` on terminal partial/failed states.
- Updated documents `+page.svelte` detail panel to show `PartialExtractionCard` for partial/failed documents and handle keep-partial mutation.
- Added 15 new backend router tests (retry endpoint ownership, status gating, arq reset, rate limit) + 3 new worker tests (retry success, retry failure preserves prior values, first-time failure).
- Added 11 new frontend tests (retry API helpers, recovery card visibility, 3-tip guide, keep-partial mutation, SSE completion after retry).
- Updated all 4 existing worker tests to include `has_document_health_values` mock and corrected `delete_values` assertion for success path.

**Review fix-up (2026-03-25) — 4 blocking findings resolved:**
- ✅ Resolved review finding [High]: Added `pending_s3_key_encrypted`, `pending_filename`, `pending_file_size_bytes`, `pending_file_type` columns via Alembic migration 006. `prepare_document_for_reupload()` now stages metadata in pending columns; `commit_pending_retry_metadata()` (new repo function) promotes them atomically in `notify_upload_complete()`. Also cleans up abandoned prior pending keys on repeated reupload-url calls.
- ✅ Resolved review finding [High]: Moved `has_document_health_values` check to the pre-extraction DB block so `prior_values_existed` is set before any exception-prone extraction code. Outer except handler uses `prior_values_existed` to publish `document.partial` (not `document.failed`) when prior values exist.
- ✅ Resolved review finding [Med]: Added `queryClient.setQueryData(['documents', docId], ...)` in `keepPartialMutation.onSuccess` to optimistically update the detail cache so the recovery card hides immediately without waiting for background refetch.
- ✅ Resolved review finding [Med]: Added prefix-based cleanup fallback in `generate_reupload_url()` when `old_s3_key is None` (decryption failure), mirroring the existing pattern in `delete_document()`.
- Added 4 new backend tests (3 router + 1 worker) and 1 new frontend test covering the 4 findings.
- Full regression: 143 backend tests pass, 80 frontend tests pass, ruff clean.

### File List

- _bmad-output/implementation-artifacts/2-5-re-upload-flow-partial-extraction-recovery.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- healthcabinet/backend/alembic/versions/005_documents_keep_partial.py (new)
- healthcabinet/backend/app/documents/models.py
- healthcabinet/backend/app/documents/exceptions.py
- healthcabinet/backend/app/documents/schemas.py
- healthcabinet/backend/app/documents/repository.py
- healthcabinet/backend/app/documents/service.py
- healthcabinet/backend/app/documents/router.py
- healthcabinet/backend/app/main.py
- healthcabinet/backend/app/processing/worker.py
- healthcabinet/backend/tests/documents/test_router.py
- healthcabinet/backend/tests/processing/test_worker.py
- healthcabinet/frontend/src/lib/types/api.ts
- healthcabinet/frontend/src/lib/api/documents.ts
- healthcabinet/frontend/src/lib/components/health/PartialExtractionCard.svelte (new)
- healthcabinet/frontend/src/lib/components/health/DocumentUploadZone.svelte
- healthcabinet/frontend/src/routes/(app)/documents/+page.svelte
- healthcabinet/frontend/src/routes/(app)/documents/upload/+page.svelte
- healthcabinet/frontend/src/routes/(app)/documents/page.test.ts
- healthcabinet/frontend/src/routes/(app)/documents/upload/upload-page-processing.test.ts
- healthcabinet/backend/alembic/versions/006_documents_pending_retry_metadata.py (new)

## Change Log

- 2026-03-24: Story 2.5 implemented — re-upload flow and partial extraction recovery. Added retry backend endpoints, `keep_partial` DB field with Alembic migration, worker partial-value preservation, PartialExtractionCard frontend component, retry-aware upload route/zone, and comprehensive test coverage (15 new backend + 11 new frontend tests).
- 2026-03-25: Code review completed with blocking findings. Story moved back to `in-progress` pending fixes for retry metadata consistency, retry failure status preservation on unexpected worker exceptions, immediate keep-partial UI dismissal, and re-upload orphaned-object cleanup fallback.
- 2026-03-25: All 4 blocking review findings resolved. Migration 006 added (pending retry metadata columns). Worker exception handler fixed. Detail cache optimistic update added. Prefix cleanup fallback implemented. 4 new tests added. Story status → review.

## Review Concerns

### Blocking Findings From Code Review (2026-03-25)

1. Retry metadata is overwritten before the replacement upload succeeds.
   - Current implementation updates the authoritative document row with the new `s3_key`, filename, size, and MIME type as soon as `/reupload-url` is requested.
   - If the client never completes the PUT or never calls `/notify`, the document can remain in `partial` or `failed` state with old extracted values but new file metadata.
   - This violates the story note that current metadata and visible values must remain authoritative until the replacement run succeeds.
   - Impact: user-visible inconsistency, misleading audit trail, and ambiguity about which file produced the stored values.

2. Retry-failure preservation semantics do not hold for unexpected worker errors.
   - The worker correctly restores `partial` when a retry finishes with no extracted values and preserved prior values exist.
   - However, the outer exception handler still forces `failed` for any unexpected exception during retry processing.
   - This creates contradictory state: preserved partial values may still exist while the document status becomes `failed`.
   - Impact: AC 3/5 behavior is only partially implemented and can regress on real failure paths outside the nominal no-values branch.

3. "Keep partial results" does not dismiss the recovery card immediately in the detail panel.
   - The mutation currently updates the list cache and invalidates the detail query, but it does not optimistically update the selected document detail cache that drives the visible recovery card.
   - On slow refetches, the card remains onscreen and appears still actionable despite the mutation succeeding.
   - Impact: UI behavior does not match the intended immediate dismissal flow from AC 4.

4. Re-upload cleanup fallback for corrupted prior object keys is documented but not implemented.
   - Repository code comments say the caller will fall back to prefix-based cleanup when decrypting the old key fails.
   - Service code only attempts cleanup when `old_s3_key` is present, so the corrupted-key path skips cleanup entirely.
   - Impact: superseded MinIO objects can leak indefinitely for retry flows that start from a document with a corrupt encrypted key.

### Follow-Up Expectations Before Returning To Review

- Defer authoritative document metadata replacement until the retry upload and processing lifecycle reaches a safe point, or persist pending-retry metadata separately so old extracted values cannot be misattributed.
- Align all retry failure paths, including unexpected exceptions, with the story rule that documents with preserved prior values revert to `partial`.
- Update the documents detail cache optimistically when `keep_partial` succeeds so the recovery card hides immediately.
- Implement and test the documented prefix-based cleanup fallback for re-upload when the previous object key cannot be decrypted.
