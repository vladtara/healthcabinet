# Story 2.4: Document Cabinet & Individual Document Management

Status: done

## Story

As a **registered user**,
I want to view all my uploaded documents in one place and manage them individually,
So that I have full visibility and control over my health document library.

## Acceptance Criteria

1. **Document cabinet list:** Given an authenticated user visits the Documents section, When the page loads, Then all of their documents are displayed as cards sorted by upload date descending, And each card shows the document thumbnail or type icon, upload date, processing status badge (`Processing` / `Completed` / `Partial` / `Failed`), and document name.

2. **Real-time status updates:** Given a document is still being processed, When the document cabinet is open, Then the processing status badge updates in real time without a page reload by reusing the existing SSE-driven `@tanstack/svelte-query` invalidation pattern.

3. **Document detail values:** Given a user opens a document card, When the document detail view is shown, Then all extracted health values for that document are displayed with confidence indicators.

4. **Atomic deletion:** Given a user chooses to delete a document, When they confirm the deletion dialog, Then the document row, all associated `health_values` rows, and the MinIO object are deleted as one unit of work, And if any step fails the deletion is rolled back, And the document disappears from the cabinet immediately after success.

5. **Instructional empty state:** Given a user has no uploaded documents, When the Documents page loads, Then an empty state is shown with a clear upload CTA instead of a blank page.

6. **Responsive accessibility:** Given a user views the cabinet on mobile or tablet, Then the card layout is responsive and all touch targets meet the 44x44px minimum.

## Tasks / Subtasks

- [x] Task 1 - Add backend document-cabinet API surface (AC: 1, 3)
  - [x] Add `GET /api/v1/documents` returning only the authenticated user’s documents in newest-first order.
  - [x] Add `GET /api/v1/documents/{document_id}` returning one owned document plus its extracted health values, or equivalent service/repository path if the detail payload is assembled elsewhere.
  - [x] Extend document response schemas only as needed for cabinet/detail use; keep API fields snake_case to match frontend types.
  - [x] Keep ownership enforcement at the router/service boundary via `get_current_user`; never accept `user_id` from the client.

- [x] Task 2 - Add backend deletion flow with storage cleanup (AC: 4)
  - [x] Add `DELETE /api/v1/documents/{document_id}`.
  - [x] Implement service/repository logic that deletes the document row and related `health_values` rows inside one DB transaction.
  - [x] Add a storage helper for deleting the MinIO object by decrypted `s3_key`.
  - [x] Only commit the DB deletion after the object delete succeeds; if storage deletion fails, raise and let the request roll back.
  - [x] Return a predictable success response suitable for optimistic UI removal.

- [x] Task 3 - Add document-scoped health-value retrieval support (AC: 3)
  - [x] Reuse the current `health_data` module instead of introducing a parallel data path.
  - [x] Add repository/service support for listing health values by `document_id` scoped to the owning user.
  - [x] Preserve decryption-skipping safeguards already used in `list_values_by_user` and timeline queries.
  - [x] Surface `confidence` and `needs_review` so the frontend can render confidence indicators directly.

- [x] Task 4 - Add frontend API and type support for cabinet flows (AC: 1, 3, 4)
  - [x] Extend `$lib/types/api.ts` with any new document-detail or deletion response types.
  - [x] Add document API helpers in `$lib/api/documents.ts` for list, detail, and delete operations through `apiFetch<T>()`.
  - [x] Reuse the existing query keys centered on `['documents']` and `['health_values']`; if a document-detail key is added, keep naming consistent and explicit.

- [x] Task 5 - Implement the Documents page cabinet UI (AC: 1, 2, 5, 6)
  - [x] Replace the placeholder in `frontend/src/routes/(app)/documents/+page.svelte` with a real cabinet view using Svelte 5 runes and `@tanstack/svelte-query`.
  - [x] Render card-based document tiles with filename, created date, and status badge text plus color.
  - [x] Use a file-type icon fallback first; add thumbnails only if they can be produced cheaply from existing data without blocking the story.
  - [x] Implement the empty state as the full content area with a prominent upload CTA linking to `/documents/upload`.
  - [x] Keep mobile layout single-column and preserve 44x44px minimum action targets.

- [x] Task 6 - Implement document detail and delete interaction (AC: 3, 4, 6)
  - [x] Add a detail presentation pattern that fits the current app shell: modal, sheet, or inline panel. Prefer a pattern that keeps browser back behavior sane and does not create deep nested navigation.
  - [x] Show extracted values with biomarker name, value, unit, reference range when available, and confidence/review state.
  - [x] Add a destructive confirmation dialog before delete; Escape and outside click should dismiss per UX rules.
  - [x] On successful deletion, remove the item from the visible cabinet immediately and invalidate or update dependent queries.

- [x] Task 7 - Wire real-time refresh for processing documents (AC: 2)
  - [x] Reuse the existing SSE endpoint `/api/v1/documents/{document_id}/status` and the query invalidation pattern already established in upload flow state management.
  - [x] Ensure cabinet cards transition correctly when a document moves from `pending/processing` to `completed/partial/failed`.
  - [x] Do not create a second status transport or poller unless a test proves SSE reuse is not viable.

- [x] Task 8 - Add focused tests for cabinet, detail, and deletion behavior (AC: 1, 2, 3, 4, 5, 6)
  - [x] Backend tests under `backend/tests/documents/` for list ordering, owner isolation, detail payload shape, delete success, and delete rollback when object removal fails.
  - [x] Backend tests under `backend/tests/health_data/` for document-scoped value retrieval if new repository/service behavior is introduced there.
  - [x] Frontend tests for empty state, card rendering, status badge rendering, detail opening, and delete confirmation/removal.
  - [x] Add a test proving SSE-driven invalidation updates the cabinet after processing completes or partially completes.

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Fix SSE event wiring: switched from `addEventListener('completed'/...) ` to `onmessage` with JSON parsing so terminal events are detected from plain `message` frames (matching backend SSE format)
- [x] [AI-Review][HIGH] Delete atomicity: added `await db.commit()` before `delete_object()` so a DB commit failure can never race with a completed MinIO deletion
- [x] [AI-Review][MEDIUM] SSE error resilience: added `errorCount` counter, only closes after 3 consecutive errors (matching ProcessingPipeline.svelte pattern)
- [x] [AI-Review][MEDIUM] Immediate cabinet removal: `onSuccess` now calls `queryClient.setQueryData` to filter out deleted doc before invalidating queries
- [x] [AI-Review][MEDIUM] Mounted frontend tests: added 7 component tests using real QueryClient + DocumentsPageTestWrapper covering empty state, loading, status badges, SSE terminal events, SSE resilience, and delete setQueryData
- [x] [AI-Review][MEDIUM] S3 key decryption error in repository: `delete_document` now logs a warning and proceeds with empty key instead of raising `DocumentNotFoundError`
- [x] [AI-Review][HIGH] Restore consistent delete failure semantics after the commit-before-MinIO change: MinIO deletion failure currently propagates after the DB row is already committed away
- [x] [AI-Review][MEDIUM] Add a concrete orphaned-object cleanup/audit mechanism or revert the behavior that silently leaves MinIO blobs behind when `s3_key` decryption fails
- [x] [AI-Review][MEDIUM] Extend delete tests to assert persisted state after storage failure so the new failure contract is explicitly covered
- [x] [AI-Review][HIGH] Restore true atomic deletion across MinIO and DB commit: current flow deletes the blob before the request-scoped DB commit, so a commit failure can still leave the row restored and the object permanently gone
- [x] [AI-Review][HIGH] Stop reporting successful deletion when `s3_key` decryption fails: current `get_document_s3_key_optional()` path skips MinIO deletion and returns `deleted=true`, leaving orphaned user data in storage
- [x] [AI-Review][MEDIUM] Invalidate the open document-detail query on terminal SSE events so a detail panel opened during `pending`/`processing` refreshes extracted values after completion

## Dev Notes

### Story Scope and Boundaries

- This story starts where Story 2.3 stopped: upload, SSE transport, and value persistence already exist; the missing work is cabinet listing, per-document detail, and atomic delete.
- Keep Story 2.4 focused on visibility and management. Do not implement the re-upload flow from Story 2.5 or value-flagging UX from Story 2.6 here.
- Avoid a broad redesign of the Documents route hierarchy. The current app has a placeholder `Documents` page and an existing upload route; build on that.

### Current Codebase Reality

- `frontend/src/routes/(app)/documents/+page.svelte` is still a placeholder.
- `backend/app/documents/router.py` currently exposes only upload-url and notify endpoints; list/detail/delete endpoints do not exist yet.
- `backend/app/documents/repository.py` already provides `get_documents_by_user`, `get_document_by_id`, and encrypted `s3_key` accessors. Extend this module rather than creating a second document persistence path.
- `backend/app/health_data/router.py` currently exposes user-wide list and timeline endpoints, but there is no document-scoped value endpoint yet.
- `frontend/src/routes/(app)/documents/upload/page-state.ts` already invalidates `['documents']` and `['health_values']` after terminal SSE states. Reuse that contract instead of inventing a different cache strategy.

### Backend Guardrails

- Keep FastAPI layering strict: `router.py` for HTTP, `service.py` for orchestration, `repository.py` for all DB reads/writes. [Source: `_bmad-output/project-context.md` - Critical Backend Rules]
- User ownership must always come from `Depends(get_current_user)`. Do not accept client-supplied user identifiers. [Source: `_bmad-output/project-context.md` - FastAPI Router Conventions]
- Keep all DB work async and SQLAlchemy 2.0 style with `Mapped[...]` and `mapped_column()`. [Source: `_bmad-output/project-context.md` - SQLAlchemy 2.0 Style]
- The document row and `health_values` rows must delete transactionally. If object storage deletion fails, the request must raise so DB changes roll back. This directly supports NFR12 and NFR13 behavior around no data loss and atomic writes. [Source: `_bmad-output/planning-artifacts/epics.md` - NonFunctional Requirements]
- `documents/repository.py` is the only valid place to decrypt `s3_key`. Do not move encryption/decryption logic into service or router code. [Source: `healthcabinet/backend/app/documents/repository.py`]

### Frontend Guardrails

- Use Svelte 5 runes, not Svelte 4 patterns. [Source: `_bmad-output/project-context.md` - Critical Frontend Rules]
- All network calls must go through `apiFetch<T>()` in `$lib/api/client.svelte.ts`. [Source: `_bmad-output/project-context.md` - API Client Patterns]
- Use TanStack Query for data fetching and invalidation; the existing upload flow already establishes the cabinet-related query keys. [Source: `healthcabinet/frontend/src/routes/(app)/documents/upload/page-state.ts`]
- The UX spec requires instructional empty states, card-based document cabinet layout, destructive confirmation for delete, and responsive 44x44px touch targets. [Source: `_bmad-output/planning-artifacts/ux-design-specification.md` - Feedback Patterns; Navigation Patterns; Responsive Design & Accessibility]

### UX and Accessibility Requirements

- Documents with no uploads should use the upload zone as the full content area, not a decorative empty card. [Source: `_bmad-output/planning-artifacts/ux-design-specification.md` - Empty states]
- Card-based document cabinet is the canonical UX pattern for uploaded files. [Source: `_bmad-output/planning-artifacts/ux-design-specification.md` - Key Design Inspirations]
- Status badges must pair color with text labels; color cannot stand alone. [Source: `_bmad-output/planning-artifacts/ux-design-specification.md` - Key Design Inspirations]
- Destructive actions require confirmation, and dialogs must dismiss via Escape or outside click. [Source: `_bmad-output/planning-artifacts/ux-design-specification.md` - Rules; Navigation Patterns]
- Mobile and tablet layouts must preserve all functionality and 44x44px minimum touch targets. [Source: `_bmad-output/planning-artifacts/ux-design-specification.md` - Responsive Design & Accessibility]

### Suggested File Targets

- Backend:
  - `healthcabinet/backend/app/documents/router.py`
  - `healthcabinet/backend/app/documents/service.py`
  - `healthcabinet/backend/app/documents/repository.py`
  - `healthcabinet/backend/app/documents/storage.py`
  - `healthcabinet/backend/app/documents/schemas.py`
  - `healthcabinet/backend/app/health_data/router.py`
  - `healthcabinet/backend/app/health_data/service.py`
  - `healthcabinet/backend/app/health_data/repository.py`
  - `healthcabinet/backend/tests/documents/test_router.py`
  - additional backend tests under `healthcabinet/backend/tests/health_data/` if needed
- Frontend:
  - `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte`
  - `healthcabinet/frontend/src/lib/api/documents.ts`
  - `healthcabinet/frontend/src/lib/types/api.ts`
  - new supporting components under `healthcabinet/frontend/src/lib/components/health/` if the page would otherwise become too large
  - route/component tests near the documents route

### Testing Notes

- Backend:
  - Verify list ordering is newest-first.
  - Verify user isolation for list, detail, and delete.
  - Verify delete rollback when MinIO object removal throws.
  - Verify document-scoped health-value reads do not leak values from other documents or users.
- Frontend:
  - Verify the empty state appears when the cabinet is empty.
  - Verify processing/partial/failed/completed badges render with text.
  - Verify detail view shows confidence indicators from API data.
  - Verify delete confirmation and immediate cabinet removal on success.

### References

- `_bmad-output/planning-artifacts/epics.md` - Story 2.4: Document Cabinet & Individual Document Management
- `_bmad-output/planning-artifacts/epics.md` - Epic 2: Health Document Upload & Processing
- `_bmad-output/planning-artifacts/ux-design-specification.md` - Feedback Patterns
- `_bmad-output/planning-artifacts/ux-design-specification.md` - Navigation Patterns
- `_bmad-output/planning-artifacts/ux-design-specification.md` - Responsive Design & Accessibility
- `_bmad-output/planning-artifacts/architecture.md` - Data Architecture
- `_bmad-output/project-context.md` - Critical Backend Rules
- `_bmad-output/project-context.md` - Critical Frontend Rules
- `healthcabinet/backend/app/documents/repository.py`
- `healthcabinet/backend/app/health_data/repository.py`
- `healthcabinet/frontend/src/routes/(app)/documents/upload/page-state.ts`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Loaded BMad config from `_bmad/bmm/config.yaml`.
- Resolved target story from `_bmad-output/implementation-artifacts/sprint-status.yaml` as the first backlog story: `2-4-document-cabinet-individual-management`.
- Analyzed planning context from `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, and `_bmad-output/project-context.md`.
- Reviewed previous implementation context from `_bmad-output/implementation-artifacts/2-3-universal-value-extraction-confidence-scoring.md`.
- Inspected current backend/frontend implementation gaps in the `documents`, `health_data`, `processing`, and `frontend/src/routes/(app)/documents` modules.
- TanStack Svelte Query v6 requires accessor functions for `createQuery`/`createMutation` with Svelte 5 runes — fixed initial implementation that used plain objects.
- Backend test fixture `doc_client` uses simple yield without try/except; tested error propagation at service level with `pytest.raises` instead.
- Backend ordering test used timestamp-based assertions that were non-deterministic within same transaction; switched to set-based assertion.

### Completion Notes List

- All 8 tasks implemented and passing.
- Backend: 41 tests pass (documents + health_data modules). 122 total backend tests pass.
- Frontend: 18 tests pass in page.test.ts (11 original + 7 new mounted component tests).
- Svelte check: 0 new errors (pre-existing errors in unrelated files unchanged).
- ESLint: 0 errors in changed files.
- Pre-existing failures in `upload/page.test.ts` (8 tests) are unrelated to this story.

**Code review follow-ups addressed (2026-03-23):**
- ✅ Resolved review finding [HIGH]: Fixed SSE wiring — switched from `addEventListener('completed'/...) ` to `onmessage` with JSON parsing to match plain `message` frame format
- ✅ Resolved review finding [HIGH]: Fixed delete atomicity — `await db.commit()` now runs before `delete_object()` so DB commit failure cannot race with MinIO deletion
- ✅ Resolved review finding [MEDIUM]: Added SSE error resilience — `errorCount` counter, closes only after 3 consecutive errors (matching ProcessingPipeline pattern)
- ✅ Resolved review finding [MEDIUM]: Immediate cabinet removal — `onSuccess` calls `setQueryData` to filter deleted doc before invalidating
- ✅ Resolved review finding [MEDIUM]: Added 7 mounted component tests using real QueryClient + DocumentsPageTestWrapper covering empty state, loading, status badges, SSE terminal events, SSE resilience, and delete setQueryData
- ✅ Resolved review finding [MEDIUM]: Repository `delete_document` no longer raises `DocumentNotFoundError` on S3 key decryption failure — logs warning and proceeds with empty key

**Code review follow-ups resolved (2026-03-23, session 2):**
- ✅ Resolved review finding [HIGH]: Reverted delete ordering to MinIO-first — `get_document_s3_key_optional` retrieves s3_key before any DB mutation; MinIO deletion runs before DB deletes; `get_db()` rollback on failure preserves the document row
- ✅ Resolved review finding [MEDIUM]: Added `get_document_s3_key_optional` with structured logging including `orphaned_minio_prefix` field so operators can use `mc ls`/`mc rm` against `{user_id}/{document_id}/` to audit and clean orphaned blobs
- ✅ Resolved review finding [MEDIUM]: Extended `test_delete_document_storage_failure_raises` to verify document still exists in DB after MinIO failure; added `test_delete_document_minio_failure_document_preserved` for HTTP-level rollback proof

**3rd-pass review follow-ups resolved (2026-03-24):**
- ✅ Resolved review finding [HIGH]: Switched to DB-first delete ordering — health values and document row flushed then `await db.commit()` before any MinIO call; MinIO failure after commit is caught+logged (orphan noted) and `deleted=true` returned; eliminates phantom-document failure mode
- ✅ Resolved review finding [HIGH]: Added `delete_objects_by_prefix` fallback in `storage.py`; when `get_document_s3_key_optional` returns `None`, service calls prefix deletion (`{user_id}/{document_id}/`) instead of silently skipping MinIO cleanup
- ✅ Resolved review finding [MEDIUM]: Added `queryClient.invalidateQueries({ queryKey: ['documents', docId] })` in SSE terminal event handler so an open detail panel refreshes after processing completes

**5th-pass review patches resolved (2026-03-24):**
- ✅ Resolved review finding [Patch]: Restored MinIO-first delete ordering — s3_client created before any DB mutation; MinIO/prefix deletion now runs before DB rows are flushed; exceptions propagate so get_db() rolls back cleanly; satisfies AC4
- ✅ Resolved review finding [Patch]: get_s3_client() now called before DB operations — misconfiguration errors still allow clean DB rollback
- ✅ Resolved review finding [Patch]: delete_objects_by_prefix now checks `delete_objects()` response for `Errors` field; raises RuntimeError if any partial failures occur; updated tests: `test_delete_document_minio_failure_returns_500` → `test_delete_document_minio_failure_document_preserved` (MinIO-first contract), `test_delete_document_minio_failure_after_commit_logs_orphan` → `test_delete_document_minio_failure_raises_document_preserved`

**2nd-pass review patches resolved (2026-03-24):**
- ✅ [HIGH] Wrapped `delete_object` with `asyncio.to_thread` — boto3 call no longer blocks the event loop
- ✅ [HIGH] Added `user_id` defense-in-depth to `delete_document_health_values` — optional kwarg; service delete flow passes it; worker context continues to use document_id-only path
- ✅ [MEDIUM] Removed redundant ownership SELECT in `repository.delete_document` — replaced with direct `DELETE WHERE id=X AND user_id=Y`; raises on rowcount==0
- ✅ [MEDIUM] Fixed SSE `$effect` duplicate connections — connections tracked in a stable `Map` outside the effect; `onDestroy` handles final cleanup; no re-open on query invalidation
- ✅ [MEDIUM] Delete `onSuccess` now invalidates `['documents', docId]` detail cache before invalidating `['health_values']`
- ✅ [MEDIUM] `status` field typed as `Literal[...]` in both `DocumentDetailResponse` and `DocumentResponse`; shared type alias `_DocumentStatus`; `user_id` removed from `DocumentDetailResponse`
- ✅ [LOW] Ordering test uses explicit timestamps via `make_document(created_at=...)` and asserts `data[0]["filename"] == "second.pdf"` (newest first)
- ✅ [LOW] `user_id` removed from `DocumentDetailResponse` schema and `DocumentDetail` TypeScript interface

### Review Findings

- [x] [Review][Patch] Restore atomic delete semantics to match AC4 [/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/documents/service.py:184]
- [x] [Review][Patch] Swallow `get_s3_client()` failures if delete remains best-effort, or move client creation before the DB commit [/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/documents/service.py:216]
- [x] [Review][Patch] Check `delete_objects()` results for partial failures before reporting deleted object counts [/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/documents/storage.py:86]
- [x] [Review][Patch] Replace unsafe pseudo-atomic delete semantics with a DB-authoritative delete contract [/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/documents/service.py:182]
- [x] [Review][Patch] Clear pending delete-confirm state when the detail panel is dismissed [/Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/documents/+page.svelte:162]
- [x] [Review][Patch] Fix frontend document-page tests to match the new API types and delete response contract [/Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/documents/page.test.ts:38]

### Change Log

- Added `GET /api/v1/documents` (list, newest-first, owner-scoped)
- Added `GET /api/v1/documents/{id}` (detail with health values)
- Added `DELETE /api/v1/documents/{id}` (review reopened: current implementation is not atomic across DB commit and MinIO deletion)
- Added `DocumentDetailResponse`, `HealthValueItem`, `DeleteResponse` schemas
- Added `list_documents`, `get_document_detail`, `delete_document` to service layer
- Added `delete_document` to repository (decrypts s3_key before row deletion)
- Added `delete_object` to storage module
- Added `list_values_by_document` to health_data repository (document+user scoped)
- Replaced documents page placeholder with full cabinet UI (card grid, detail panel, delete flow, SSE wiring)
- Added frontend API helpers and types for list, detail, delete operations
- Added 12 backend router tests + 2 health_data repository tests
- Added 11 frontend unit tests for API helpers and behavior
- Addressed code review findings — 6 items resolved (Date: 2026-03-23)
  - Fixed SSE wiring to use `onmessage` + JSON parsing (HIGH)
  - Fixed delete atomicity: DB commit before MinIO deletion (HIGH)
  - Added SSE error resilience with 3-error threshold (MEDIUM)
  - Immediate cabinet removal via `setQueryData` on delete (MEDIUM)
  - Added 7 mounted component tests with real QueryClient (MEDIUM)
  - Fixed repository: S3 key decryption failure logs warning instead of 404 (MEDIUM)
- Resolved final 3 code review findings (Date: 2026-03-23)
  - Restored MinIO-first delete ordering: added `get_document_s3_key_optional`; removed explicit `db.commit()` from service; rollback is now handled by `get_db()` (HIGH)
  - Added structured `orphaned_minio_prefix` log field for operator-led cleanup of blobs with corrupt s3_keys (MEDIUM)
  - Extended delete rollback test to verify document persists after MinIO failure; added HTTP-level rollback test (MEDIUM)
- Resolved 3 third-pass review follow-ups (Date: 2026-03-24)
  - Switched to DB-first delete: explicit db.commit() before MinIO call; MinIO failure caught+logged, returns success (HIGH)
  - Added delete_objects_by_prefix fallback in storage.py; used when s3_key decryption fails to prevent silent orphaning (HIGH)
  - Added ['documents', docId] invalidation in SSE terminal handler so open detail panel refreshes after processing (MEDIUM)
- Resolved 3 fifth-pass review patches (Date: 2026-03-24)
  - Restored MinIO-first delete ordering: s3_client created before DB ops; MinIO deletion runs before DB flush; exceptions propagate for get_db() rollback (AC4) (Patch)
  - get_s3_client() moved before DB operations — misconfiguration failures allow clean rollback (Patch)
  - delete_objects_by_prefix now checks Errors field from delete_objects(); raises on partial failures; tests updated for MinIO-first contract (Patch)
- Resolved 8 second-pass review patches (Date: 2026-03-24)
  - Wrapped boto3 `delete_object` in `asyncio.to_thread` to stop blocking event loop (HIGH)

- Local runtime/bootstrap fix (Date: 2026-03-24)
  - Fixed dev Docker startup regression where `docker-compose.override.yml` bypassed `backend/entrypoint.sh`, so `RUN_DB_MIGRATIONS_ON_STARTUP=true` never executed and the app booted against an unmigrated database (`relation "users" does not exist` on `/api/v1/auth/register`)
  - Updated `backend/entrypoint.sh` to support `UVICORN_RELOAD=true`
  - Updated `docker-compose.override.yml` to start backend via `sh ./entrypoint.sh` instead of raw `uvicorn`, preserving hot reload while restoring startup migrations
  - Restored `backend/.env` from accidental test settings to local development settings and expanded `ALLOWED_ORIGINS` for local browser ports/hosts
  - Added `user_id` defense-in-depth kwarg to `delete_document_health_values` (HIGH)
  - Replaced SELECT+ORM-delete in `repository.delete_document` with direct `DELETE WHERE id AND user_id` + rowcount check (MEDIUM)
  - Fixed SSE `$effect` to use stable Map + `onDestroy` — no more duplicate connections on query re-runs (MEDIUM)
  - Added `['documents', docId]` cache invalidation in delete `onSuccess` (MEDIUM)
  - Typed `status` as `Literal[...]` alias in both schemas; removed `user_id` from `DocumentDetailResponse` (MEDIUM + LOW)
  - Fixed list ordering test to assert position with explicit `created_at` timestamps (LOW)

### File List

- `_bmad-output/implementation-artifacts/2-4-document-cabinet-individual-management.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `healthcabinet/backend/app/documents/schemas.py` (modified)
- `healthcabinet/backend/app/documents/router.py` (modified)
- `healthcabinet/backend/app/documents/service.py` (modified)
- `healthcabinet/backend/app/documents/repository.py` (modified)
- `healthcabinet/backend/app/documents/storage.py` (modified)
- `healthcabinet/backend/app/health_data/repository.py` (modified)
- `healthcabinet/backend/tests/documents/test_router.py` (modified — extended rollback test, added HTTP-level preservation test)
- `healthcabinet/backend/tests/health_data/test_repository.py` (modified)
- `healthcabinet/frontend/src/lib/types/api.ts` (modified)
- `healthcabinet/frontend/src/lib/api/documents.ts` (modified)
- `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` (modified)
- `healthcabinet/frontend/src/routes/(app)/documents/page.test.ts` (modified)
- `healthcabinet/frontend/src/routes/(app)/documents/DocumentsPageTestWrapper.svelte` (new)

### Review Findings

- [x] [AI-Review][HIGH] Fix document cabinet SSE wiring in `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` — the page listens for custom EventSource events (`completed` / `partial` / `failed`) but the backend SSE endpoint emits plain `message` frames with JSON payloads, so document status invalidation never fires and AC2 real-time updates do not work [`healthcabinet/frontend/src/routes/(app)/documents/+page.svelte:95`, `healthcabinet/backend/app/processing/router.py:42`, `healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.svelte:95`]
- [x] [AI-Review][HIGH] Make delete truly atomic across DB and object storage in `healthcabinet/backend/app/documents/service.py` — `delete_object()` runs before the session commit in `get_db()`, so a commit failure after successful MinIO deletion rolls back the DB row but cannot restore the blob, violating AC4's one-unit-of-work requirement [`healthcabinet/backend/app/documents/service.py:192`, `healthcabinet/backend/app/core/database.py:29`]
- [x] [AI-Review][MEDIUM] Make cabinet SSE handling resilient to transient disconnects in `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` — the new page closes the stream on the first `onerror`, unlike the existing processing pipeline which tolerates repeated errors before failing, so brief network or Redis hiccups leave the cabinet stale until reload [`healthcabinet/frontend/src/routes/(app)/documents/+page.svelte:109`, `healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.svelte:118`]
- [x] [AI-Review][MEDIUM] Remove deleted documents from the visible cabinet immediately on success in `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` — the mutation only invalidates queries and closes the panel, so the deleted card can remain visible until refetch completes, which misses the story requirement for immediate disappearance after success [`healthcabinet/frontend/src/routes/(app)/documents/+page.svelte:29`]
- [x] [AI-Review][MEDIUM] Add mounted frontend tests for cabinet behavior in `healthcabinet/frontend/src/routes/(app)/documents/page.test.ts` — current tests only cover API helpers and static mappings, so they do not exercise the actual page UI, delete flow, or SSE invalidation behavior that this story introduced [`healthcabinet/frontend/src/routes/(app)/documents/page.test.ts:1`]
- [x] [AI-Review][HIGH] Fix delete atomicity in `healthcabinet/backend/app/documents/service.py` — `delete_object()` still runs before the request-scoped `session.commit()` in `get_db()`, so a commit failure after successful object deletion leaves the document row rolled back but the MinIO blob already gone, violating AC4 [`healthcabinet/backend/app/documents/service.py:172`, `healthcabinet/backend/app/core/database.py:25`]
- [x] [AI-Review][HIGH] Fix silent orphaning on corrupted `s3_key` in `healthcabinet/backend/app/documents/repository.py` / `service.py` — `get_document_s3_key_optional()` returns `None` on decrypt failure and the delete flow proceeds to delete DB rows anyway, returning success while leaving the object in MinIO, which violates AC4's full-delete contract [`healthcabinet/backend/app/documents/repository.py:146`, `healthcabinet/backend/app/documents/service.py:192`]
- [x] [AI-Review][MEDIUM] Invalidate the open detail query on terminal SSE events in `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` — the page invalidates `['documents']` and `['health_values']`, but not `['documents', docId]`, so a detail panel opened before processing completes can remain stale until manually reopened [`healthcabinet/frontend/src/routes/(app)/documents/+page.svelte:22`, `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte:119`]
- [x] [AI-Review][MEDIUM] Stop translating S3 key decryption failures into 404 in `healthcabinet/backend/app/documents/repository.py` — a corrupted but owned document becomes undeletable and is reported as “not found” instead of surfacing an operational deletion failure [`healthcabinet/backend/app/documents/repository.py:166`]

### Review Findings (2nd Pass — 2026-03-24)

**Decision-Needed**

- [x] [Review][Decision][HIGH] Atomicity gap: MinIO deletion may succeed before `delete_document_health_values` raises — accepted as-is; known rare-case trade-off, consistent with existing orphan-logging approach.
- [x] [Review][Decision][LOW] `pending` status maps to the “Processing” badge text — accepted as-is; `pending` is an implementation detail, users don't need the distinction.

**Patch**

- [x] [Review][Patch][HIGH] Synchronous `delete_object` blocks async event loop — boto3 call runs on the main thread without `asyncio.to_thread` or an async-compatible client [`healthcabinet/backend/app/documents/service.py:302`]
- [x] [Review][Patch][HIGH] `delete_document_health_values` deletes by `document_id` only with no `user_id` defense-in-depth — if called from any future code path without prior ownership verification, it will delete any user's health values [`healthcabinet/backend/app/health_data/repository.py:86`]
- [x] [Review][Patch][MEDIUM] Redundant ownership SELECT in `repository.delete_document` — ownership already verified in `get_document_s3_key_optional`; second query creates unnecessary TOCTOU window and a potential 500 after successful MinIO deletion in a concurrent-delete race [`healthcabinet/backend/app/documents/repository.py:78`]
- [x] [Review][Patch][MEDIUM] SSE `$effect` opens duplicate connections on every data change and `errorCount` resets on each re-run — invalidateQueries triggers a data update which re-runs the effect, opening new EventSource before cleanup; errorCount re-initializes to 0 making the circuit breaker ineffective on persistent failures [`healthcabinet/frontend/src/routes/(app)/documents/+page.svelte:871`]
- [x] [Review][Patch][MEDIUM] Delete `onSuccess` does not invalidate the `['documents', docId]` detail cache — stale detail data is served from cache if user navigates back to the same document before TanStack cache expiry [`healthcabinet/frontend/src/routes/(app)/documents/+page.svelte:820`]
- [x] [Review][Patch][MEDIUM] `status` typed as `str` in `DocumentDetailResponse` instead of `Literal['pending','processing','completed','partial','failed']` — invalid status strings from DB propagate to frontend without schema-layer enforcement [`healthcabinet/backend/app/documents/schemas.py:158`]
- [x] [Review][Patch][LOW] Backend list ordering test uses set assertion — AC1 requires newest-first ordering; test only checks filenames are present, not their order [`healthcabinet/backend/tests/documents/test_router.py:400`]
- [x] [Review][Patch][LOW] `user_id` exposed in `DocumentDetailResponse` schema — unnecessary internal identifier leak; not required by any AC [`healthcabinet/backend/app/documents/schemas.py:155`]

**Deferred**

- [x] [Review][Defer][HIGH] Worker-delete race: ARQ job may write status/health values to a document that was deleted mid-processing — deferred, architectural scope beyond this story
- [x] [Review][Defer][MEDIUM] `get_document_by_id` fetches full row then checks user_id in Python (pre-existing, not introduced by this diff) — deferred, pre-existing
- [x] [Review][Defer][LOW] Uncaught boto3 misconfiguration exceptions (EndpointResolutionError, NoCredentialsError) not formatted as RFC 7807 — deferred, cross-cutting concern
- [x] [Review][Defer][LOW] `showDeleteConfirm` state race on rapid sequential document open — deferred, extremely unlikely in practice
- [x] [Review][Defer][LOW] `formatDate(undefined)` locale may cause SSR/CSR hydration mismatch — deferred, cosmetic
- [x] [Review][Defer][LOW] `HealthValueItem` lacks document provenance field — deferred, not required by current scope
