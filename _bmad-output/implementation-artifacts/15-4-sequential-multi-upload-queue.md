# Story 15.4: Sequential Multi-Upload Queue

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user importing multiple files**,
I want to select or drop several files and see each file processed independently in a controlled queue,
So that I can import a batch without repeating the upload flow one file at a time.

## Acceptance Criteria

1. **Multi-select and multi-drop upload UI** — The upload page (`/documents/upload`) accepts multiple files via file picker (`multiple` attribute) and multi-file drag-and-drop. Each file is immediately queued and the queue is visible to the user so they know what's pending.

2. **Client queue tracks per-file states** — A queue data structure (array) tracks every file with its current state: `queued | uploading | processing | completed | partial | failed`. State transitions are driven by the existing single-file upload flow for each file. The queue UI shows the aggregate state (how many completed / partial / failed) and individual file status.

3. **Existing single-file endpoint reused per file** — Each queued file calls the existing `uploadDocument(file)` helper and `streamDocumentStatus(docId, ...)` SSE stream independently. No changes to the backend contract. Sequential execution means one file is "active" at a time; the queue waits for the previous file's SSE to reach a terminal status (`completed | partial | failed`) before advancing.

4. **Sequential queue execution** — The queue processes files one at a time (not parallel). This preserves the existing backend rate-limit enforcement (one upload at a time per user) and prevents SSE stream congestion. The "active" file shows the `ProcessingPipeline` component; files ahead of it show their state; files behind it wait.

5. **Retry mode stays single-file** — When `retryDocumentId` is present in the URL, the page renders in single-file retry mode (Story 2.5) and does NOT enter the multi-upload queue flow. The retry entry point bypasses the queue entirely.

6. **End-of-batch summary** — When every queued file reaches a terminal status, the queue transitions to a summary state showing: completed count, partial count, failed count, and per-file "View result" links for completed/partial files. The summary uses the existing 98.css state pattern. "Upload another batch" resets the queue to idle.

7. **Dashboard cache invalidation per file** — As each file's SSE reaches a terminal non-failed status, the dashboard `['ai_dashboard_interpretation']` query is invalidated (same pattern as Story 15.3). Failed uploads do NOT trigger invalidation (no AiMemory row is created for them). The dashboard shows updated results after the batch completes.

8. **Empty / single-file fallbacks work unchanged** — When the user picks exactly one file or drags exactly one file, the flow behaves exactly like the pre-15.4 single-file upload (queue of one, immediately processed, summary shows one result). When the user picks zero files and closes the picker, nothing happens (no empty queue state shown).

## Tasks / Subtasks

- [x] Task 1: Queue data model and state machine (AC: 2, 3, 4)
  - [x] Define `UploadQueueEntry` type: `{ id, file: File, status: 'queued'|'uploading'|'processing'|'completed'|'partial'|'failed', documentId?: string, error?: string }`
  - [x] Implement `createUploadQueue(files: File[]): UploadQueueEntry[]` factory
  - [x] Implement `advanceQueue(queue: UploadQueueEntry[]): UploadQueueEntry[]` which returns the queue with the first non-terminal entry promoted to active (uploading → processing)
  - [x] Implement `terminalStatuses: Set<string>` constant (`{'completed', 'partial', 'failed'}`) for guard checks

- [x] Task 2: Refactor page state from single-file to queue-aware (AC: 1, 4, 5, 8)
  - [x] Replace `uploadState: UploadState` and `documentId: string | null` page-level state with `queue: UploadQueueEntry[]`
  - [x] Derive `activeFile: UploadQueueEntry | undefined` from `queue.find(e => e.status === 'uploading' || e.status === 'processing')`
  - [x] Derive `queueStatus: 'idle'|'active'|'summary'` from queue state
  - [x] Guard `retryDocumentId` entry → single-file mode: render the existing single-file flow (do NOT merge retry into queue)
  - [x] `queuedCount`, `completedCount`, `partialCount`, `failedCount` derived from queue

- [x] Task 3: Multi-file `DocumentUploadZone` integration (AC: 1, 8)
  - [x] Pass `multiple` attribute to the file input in `DocumentUploadZone` (or create a `MultiDocumentUploadZone` variant)
  - [x] `onFilesSelected(files: File[])` callback that calls a parent `enqueueFiles(files)` handler
  - [x] `onDrop` handler captures `e.dataTransfer.files` as an array (not just `files[0]`)
  - [x] Drag-over visual feedback for multi-file drop
  - [x] Single-file drop still works (files array of length 1 → single-file queue of one → same behavior as before)

- [x] Task 4: Per-file upload + SSE pipeline (AC: 3, 4, 7)
  - [x] `processNextInQueue(queryClient, queue)` async function:
    - Finds first `queued` entry
    - Calls `uploadDocument(file)` → stores returned `documentId` on entry → transitions to `uploading`
    - Calls `streamDocumentStatus(documentId, signal, ...)` with per-file callbacks:
      - `onEvent` → transition entry to `processing` when first non-terminal SSE event arrives
      - `onFailed(reason)` → `handleProcessingFailure` style: transition to `partial` or `failed`, invalidate dashboard cache for `partial`, skip for `failed`
      - `onComplete` → `handleProcessingComplete` style: transition to `completed`, invalidate dashboard cache
    - On SSE terminal status, calls `advanceQueue` recursively to process the next file
  - [x] Each file gets its own `AbortSignal`; when advancing to next file, the previous signal is cancelled
  - [x] On any unrecoverable error (non-401/stream-error), transition the active file to `failed` and advance
  - [x] 401 error on SSE: per Story 14.1 behavior — abort queue and surface auth error

- [x] Task 5: Queue UI — pending files list (AC: 1, 2)
  - [x] `UploadQueuePanel` component showing all queued/processing/completed/partial/failed entries
  - [x] Each entry row: file icon, filename, file size, status badge, per-status color
  - [x] Status badges use existing `HealthStatusBadge` patterns or 98.css badge styling: `Queued` (gray), `Uploading` (blue/processing), `Processing` (blue/processing), `Completed` (green/Optimal), `Partial` (yellow/Borderline), `Failed` (red/Concerning)
  - [x] Active file (first non-terminal) is visually distinct (highlighted row) — the one driving the `ProcessingPipeline`
  - [x] Completed/partial entries show a "View result" link to `/documents/{documentId}`
  - [x] Failed entries show the error message and a "Retry this file" action (re-opens the file picker for that entry only, replaces the file in place — same documentId is NOT reused; a new documentId is created)
  - [x] Keyboard accessible: Tab through queue entries, Enter/Space on "View result" / "Retry"

- [x] Task 6: Queue UI — active file ProcessingPipeline (AC: 4)
  - [x] When `activeFile` exists, render `<ProcessingPipeline documentId={activeFile.documentId} ...>` inline in the queue panel
  - [x] ProcessingPipeline transitions (`Uploading → Reading → Extracting → Generating → Completed`) drive the active entry's status

- [x] Task 7: End-of-batch summary state (AC: 6)
  - [x] `queueStatus === 'summary'` renders `<UploadBatchSummary>` component when all entries are terminal
  - [x] Summary shows: `{completedCount} completed`, `{partialCount} partial`, `{failedCount} failed`
  - [x] Per-completed/partial file: "View result" link to `/documents/{documentId}`
  - [x] "Upload another batch" button → resets queue to `[]`, returns to idle state
  - [x] Uses existing 98.css empty/success/warning state styling patterns from the codebase

- [x] Task 8: Page layout integration (AC: 1)
  - [x] The upload page (`/documents/upload`) adapts its layout based on `queueStatus`:
    - `idle`: single-file upload zone (same as current) OR queue-empty welcome state
    - `active`: queue panel + active ProcessingPipeline
    - `summary`: batch summary
  - [x] The 98.css dialog chrome (`hc-import-dialog`, `hc-dash-section`) wraps all three states

- [x] Task 9: Dashboard cache invalidation integration (AC: 7)
  - [x] In `processNextInQueue`, on `completed` terminal status → `queryClient.invalidateQueries({ queryKey: ['ai_dashboard_interpretation'] })`
  - [x] On `partial` terminal status → same invalidation
  - [x] On `failed` terminal status → no invalidation
  - [x] Pattern matches Story 15.3 `handleProcessingComplete` / `handleProcessingFailure` style

- [x] Task 10: Unit tests (AC: all)
  - [x] `upload-queue.test.ts` — queue factory, terminal status guard, advanceQueue logic, derived counts
  - [x] `page-state.test.ts` — queue-aware `handleUploadSuccess`, `handleProcessingComplete`/`handleProcessingFailure` for queue entries (vs the old single-file signatures)
  - [x] `DocumentUploadZone.test.ts` — multi-file file-change handler, multi-file drop, single-file backwards compat
  - [x] `upload-page.test.ts` — multi-file flow end-to-end (3 files → sequential → summary), retry-mode bypass, single-file backwards compat, queue idle with zero files
  - [x] `upload-page-processing.test.ts` — per-file dashboard cache invalidation on completed/partial/failed

### Review Findings

- [x] [Review][Decision] Queue retry contract clarified: keep the current "new document row" behavior for failed-row retry. Queue retry intentionally clears the failed entry's `documentId`, requeues the replacement file, and lets the next attempt call `uploadDocument(file)` rather than `reuploadDocument(existingDocId, newFile)`.
- [x] [Review][Patch] SSE auth failures now abort the batch and surface re-auth instead of collapsing into generic stream failure advancement. `ProcessingPipeline` gained an opt-in `onAuthError` callback, and the queue path marks the active row failed, stops advancement, and shows an authentication-required banner. [healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.svelte:11] [healthcabinet/frontend/src/routes/(app)/documents/upload/+page.svelte:93]
- [x] [Review][Patch] Partial results now render with a distinct warning badge in both the live queue rows and the batch summary instead of reusing the in-progress token. [healthcabinet/frontend/src/lib/components/health/UploadQueueEntryRow.svelte:29] [healthcabinet/frontend/src/lib/components/health/UploadBatchSummary.svelte:36]
- [x] [Review][Patch] Route-level multi-file tests now cover sequential batch completion, summary/reset flow, and auth-error batch abort behavior on the mounted upload page. [healthcabinet/frontend/src/routes/(app)/documents/upload/page.test.ts:377]

## Dev Notes

### Story Scope and Boundaries

- **Story 15.4 is a pure frontend story.** The backend upload/reupload contract is unchanged. Each file in the queue calls `uploadDocument(file)` — the same API used by the existing single-file flow. No backend changes are required unless a bug is discovered during integration.
- **Do NOT merge retry mode into the queue.** `retryDocumentId` in the URL means "replace the content of this existing document slot." This is a single-file operation with a pre-existing `documentId`. The queue is for new uploads. Keep the paths separate — the retry entry point renders the existing single-file flow (unchanged) and does NOT invoke queue logic.
- **Sequential, not parallel.** This story explicitly specifies sequential queue execution. The existing backend contract does not support concurrent uploads per user (rate limiting). Parallel upload is out of scope for 15.4.
- **Do NOT touch the backend SSE endpoint.** Each file uses `streamDocumentStatus` independently. The SSE contract is unchanged. The only frontend SSE integration point is inside `processNextInQueue`.
- **Do NOT introduce new backend endpoints.** The multi-file UX is achieved by orchestrating repeated calls to the existing `uploadDocument` + `streamDocumentStatus` per file.
- **Do not change `page-state.ts` function signatures in a breaking way.** The existing `handleProcessingComplete` / `handleProcessingFailure` helpers in `page-state.ts` are used by the single-file retry flow. Refactor them to accept either a single-file model (`{ uploadState, documentId }`) or a queue-entry model (`UploadQueueEntry`). The safest approach: new queue-aware helpers that live in `upload-queue.ts`, keep `page-state.ts` helpers for the retry path.
- **Do not introduce a batch-upload backend endpoint.** Even if the backend later supports true batch upload, this story achieves the goal with the existing single-file API. A future story can add a batch endpoint for parallel/atomic batch upload if needed.
- **Story 15.7 (Regression Gate) will add tests for this story.** Ensure test coverage is complete here so 15.7 can verify it.

### Current Codebase Reality

**Existing single-file flow:**
- `routes/(app)/documents/upload/+page.svelte` owns the full upload page lifecycle.
- `page-state.ts` exports `handleUploadSuccess(doc) → { uploadState: 'success', documentId }`, `handleProcessingComplete` (invalidates `['documents']`, `['health_values']`, `['ai_dashboard_interpretation']`), and `handleProcessingFailure` (partial path invalidates dashboard key; failed path does not).
- `DocumentUploadZone.svelte` accepts one file at a time (`onFileChange` reads `input.files?.[0]`). Drop reads `e.dataTransfer.files[0]`. The `onSuccess` callback fires with the created `Document`.
- `uploadDocument(file)` in `lib/api/documents.ts` calls `POST /api/v1/documents/upload` with a `FormData` body. `reuploadDocument(docId, file)` calls `POST /api/v1/documents/{id}/reupload`.
- `streamDocumentStatus(docId, signal, onEvent, onError)` in `lib/api/documents.ts` implements SSE via fetch. Terminal events: `document.completed`, `document.partial`, `document.failed`. Non-terminal: `document.upload_started`, `document.reading`, `document.extracting`, `document.generating`.
- `ProcessingPipeline.svelte` takes `{ documentId, onComplete, onFailed }` and renders the 4-stage progress UI.
- `PartialExtractionCard.svelte` takes `{ status, documentId, onReupload }`.
- `lib/api/documents.ts::confirmDateYear` is the Story 15.2 contract helper (not yet called from any UI; UI consumption is deferred to future story or can be added here if the year-confirm entry point lands on the upload/retry page).

**Story 15.3 integration:**
- Dashboard cache invalidation on `completed`/`partial` terminal SSE events is already present in `page-state.ts` (`handleProcessingComplete` and the partial path in `handleProcessingFailure`). These helpers are reused in the queue flow.

**Story 14.1 integration (fetch-based SSE with token-in-header):**
- `streamDocumentStatus` uses `apiStream()` which attaches the access token via `Authorization: Bearer <token>` header. Token refresh is handled by `apiStream()`. The queue does NOT need to manage token refresh differently for sequential files.

### Implementation Guardrails

- **Svelte 5 runes only.** Queue state should use `$state` rune. Derived values (`activeFile`, `queueStatus`, counts) use `$derived`. Side effects (SSE event handlers, file processing) use `$effect` or explicit async functions called imperatively.
- **TanStack Query invalidation.** Invalidate `['ai_dashboard_interpretation']` on `completed` and `partial` per file. Do NOT manually call dashboard AI rebuild — Story 15.3 established that the aggregate is computed on-demand; invalidation triggers the next GET. Use `queryClient.invalidateQueries({ queryKey: ['ai_dashboard_interpretation'] })` (prefix match covers all filter variants).
- **AbortSignal lifecycle.** Each file in the queue gets its own `AbortSignal`. When `processNextInQueue` is called for the next file, it must abort the previous file's SSE stream. Use `signal.abort()` on the previous signal before starting the next file's SSE. Ensure `handleProcessingComplete` / `handleProcessingFailure` in the SSE callbacks check whether the signal is still relevant (don't transition if already aborted).
- **Error resilience.** SSE `onError` receives `'stream-error' | 'auth-error'`. For `'stream-error'`, transition the active entry to `failed` and advance to the next file. For `'auth-error'`, abort the entire queue and surface the auth error (the user must re-authenticate before continuing).
- **No duplicate document rows.** Each call to `uploadDocument(file)` creates a new backend document row. On retry ("Retry this file" in the queue), call `reuploadDocument(existingDocId, newFile)` to replace the content of the existing slot — same pattern as the existing retry flow.
- **File size/type validation before enqueuing.** Validate each file before adding to the queue (same checks as `DocumentUploadZone::startUpload`). Files that fail validation are rejected immediately and not enqueued.
- **98.css chrome.** Queue panel, status badges, and summary use existing 98.css patterns from the codebase. Do not introduce new Tailwind structural styling. Status badges should match the existing health status color tokens.

### File Targets

**New files:**
- `healthcabinet/frontend/src/lib/upload-queue.ts` — queue data model, `createUploadQueue`, `advanceQueue`, `processNextInQueue`, `terminalStatuses`
- `healthcabinet/frontend/src/lib/components/health/UploadQueuePanel.svelte` — queue list UI
- `healthcabinet/frontend/src/lib/components/health/UploadBatchSummary.svelte` — end-of-batch summary
- `healthcabinet/frontend/src/lib/components/health/UploadQueueEntryRow.svelte` — individual queue entry row (file icon, name, size, status badge, actions)
- `healthcabinet/frontend/tests/upload-queue.test.ts` — queue logic unit tests
- `healthcabinet/frontend/tests/upload-page.test.ts` — (additions) multi-file flow, summary state, retry bypass

**Modified files:**
- `healthcabinet/frontend/src/lib/components/health/DocumentUploadZone.svelte` — `multiple` on input, `onFilesSelected(files: File[])`, array-based drop handler
- `healthcabinet/frontend/src/routes/(app)/documents/upload/+page.svelte` — queue state, queue panel rendering, summary state, retry guard
- `healthcabinet/frontend/src/routes/(app)/documents/upload/page-state.ts` — extend helpers for queue model (or add queue-aware variants)
- `healthcabinet/frontend/src/routes/(app)/documents/upload/upload-page-processing.test.ts` — (additions) per-file dashboard invalidation on completed/partial/failed

**Do NOT modify:**
- `healthcabinet/frontend/src/lib/api/documents.ts` — API helpers unchanged
- `healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.svelte` — unchanged
- `healthcabinet/frontend/src/lib/components/health/PartialExtractionCard.svelte` — unchanged
- `healthcabinet/backend/` — no backend changes (unless a bug surfaces during integration)

### Testing Requirements

- Follow the project rule: run tests inside Docker Compose — `docker compose exec backend uv run pytest` (if any backend tests added) and `docker compose exec frontend npm run test:unit`.
- **Queue logic tests** (`upload-queue.test.ts`): test `createUploadQueue` factory (empty, single, multiple), `terminalStatuses` guard, `advanceQueue` transitions (queued→uploading, completes don't advance, empty queue returns unchanged).
- **Multi-file page tests** (`upload-page.test.ts`): use `@testing-library/user-event` or Playwright for drag-drop and multi-select simulation. Test the full sequential flow: 3 files → each transitions through states → summary shows correct counts → "Upload another batch" resets.
- **Single-file regression** (`upload-page.test.ts`): drag single file → behaves identically to pre-15.4 flow (queue of one, immediately processed, summary shows one result).
- **Retry bypass** (`upload-page.test.ts`): navigate to `/documents/upload?retryDocumentId=xxx` → single-file mode, no queue panel, existing retry behavior.
- **Dashboard invalidation** (`upload-page-processing.test.ts`): simulate 3-file queue; assert `invalidateQueries` called N times for `completed`/`partial` files and 0 times for `failed` files.
- Run `npm run test:unit` inside Docker before opening PR. Do not run broader `npm run check` / lint sweeps unless touching shared types; rely on CI.

### Previous Story Intelligence

- **Story 15.1 (auth bootstrap restore guard):** Delivered explicit bootstrap state machine. The upload page is behind `(app)` auth guard. No special coordination with bootstrap state needed — the page renders a guarded placeholder while bootstrap is `unknown/restoring`.
- **Story 15.2 (document intelligence + year confirmation):** Persisted `document_kind` + `needs_date_confirmation` + `partial_measured_at_text`. Multi-upload files go through the same processing pipeline and will receive their `document_kind` classification automatically. The queue does not need to handle `needs_date_confirmation` specially — after processing completes, users see the year-confirm prompt if applicable (Story 15.2 UI consumption).
- **Story 15.3 (dashboard filter + aggregate AI):** Delivered dashboard filter state and the `['ai_dashboard_interpretation']` cache key. The queue invalidates this key on `completed`/`partial` per file. Default filter is `'analysis'` — after the batch, the user's dashboard reflects the new analyses immediately.
- **Story 2.1 (document upload):** Established single-file upload contract: `POST /api/v1/documents/upload` → MinIO presigned URL flow (backend proxies), `documents` table row with `status="pending"`, ARQ job enqueued. Story 15.4 reuses this per file. Rate limiting (5 docs/day) is enforced by the backend per `uploadDocument` call — the queue does not need to enforce it.
- **Story 2.5 (re-upload flow):** Established retry contract: `retryDocumentId` in URL → `reuploadDocument(docId, file)` → same documentId reused. The queue implements retry ("Retry this file" action) as calling `reuploadDocument` with the entry's `documentId` and a new file. This is already wired in `DocumentUploadZone` via the `retryDocumentId` prop.
- **Story 14.1 (SSE fetch-based auth):** `streamDocumentStatus` uses `apiStream()` with `Authorization: Bearer <token>` header and automatic token refresh. The queue uses this same function for each file. Token refresh during SSE is handled transparently — no queue-level change needed.

### Git Intelligence Summary

Recent commits across Epic 15 show a pattern of multi-round review cycles:

```
ae0a39f feat: update test cases to include document kind and date confirmation fields; enhance mock data for better coverage
8a0cbfb feat: enhance DocumentDetailPanel with result date and document kind display; add year confirmation functionality
945ef13 feat: implement dashboard mode for AI Clinical Note and related components
0dd0e00 fix(15-1): inline admin-loading style to avoid Svelte preprocessor error
97af0ce fix(15-3): update deferred work items from code review of 15-1 and 15-2
49cf308 fix(15-1): round-2 HIGH patches (login deadlock, admin blank, timer leak)
4389bfa fix(15-2): round-2 HIGH patches (invalidate unconditional, _bind_node stage-scoped clear)
```

Inference: expect 2–3 review rounds. The queue state machine and per-file SSE lifecycle are correctness-sensitive — edge cases (file rejected before upload, SSE error mid-file, auth error mid-batch, partial file with zero values) should be considered during implementation and covered by tests. Keep changes additive and narrowly scoped to the upload page and queue logic.

### Latest Technical Information

- **Svelte 5 runes for queue state:** Use `$state` for the `queue: UploadQueueEntry[]` array. `$derived` for computed values. `$effect` only for imperative side effects (SSE callbacks, file processing loop).
- **TanStack Query v5 invalidation by prefix:** `queryClient.invalidateQueries({ queryKey: ['ai_dashboard_interpretation'] })` matches by prefix by default (v5 behavior). This sweeps every filter variant (`all`, `analysis`, `document`) in one call.
- **AbortController per file:** `new AbortController()` creates a signal per file. Store it on the queue entry so it can be aborted when advancing to the next file. Pattern: `const controller = new AbortController()` → pass `controller.signal` to `streamDocumentStatus` → on next file, `controller.abort()`.
- **No new backend routes needed.** `POST /api/v1/documents/upload` and `POST /api/v1/documents/{id}/reupload` handle every file in the queue. SSE endpoint unchanged.

### Project Context Reference

- Project rules: `_bmad-output/project-context.md`
- Core planning sources:
  - `_bmad-output/planning-artifacts/prd.md` (FR7, FR8, FR23 cover upload + processing scope)
  - `_bmad-output/planning-artifacts/architecture.md`
  - `_bmad-output/planning-artifacts/ux-design-specification.md`
  - `_bmad-output/planning-artifacts/ux-page-specifications.md`
  - `_bmad-output/planning-artifacts/flow-stabilization-epic-15.md` (Story 15.4 scope and acceptance summary)
- Prior implementation context:
  - `_bmad-output/implementation-artifacts/2-1-document-upload-minio-storage.md`
  - `_bmad-output/implementation-artifacts/2-2-real-time-processing-pipeline-status.md`
  - `_bmad-output/implementation-artifacts/2-5-re-upload-flow-partial-extraction-recovery.md`
  - `_bmad-output/implementation-artifacts/14-1-sse-fetch-based-auth-and-lifecycle.md`
  - `_bmad-output/implementation-artifacts/15-1-auth-bootstrap-restore-guard.md`
  - `_bmad-output/implementation-artifacts/15-2-document-intelligence-and-year-confirmation-contract.md`
  - `_bmad-output/implementation-artifacts/15-3-dashboard-filter-and-aggregate-ai-context.md`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) via Claude Code.

### Debug Log References

- **Preprocessor-friendly styling.** A `<style>` block inside `+page.svelte` triggered the known Tailwind-v4/PostCSS preprocessor error (same class as fix `0dd0e00`). All styles in new components and the page body are inlined as `style="…"` attributes; no scoped `<style>` blocks in the upload route. Existing `hc-pipeline-stage-*` / `hc-recovery-btn-*` global classes are referenced for status badges and primary actions.
- **Test mock hoisting.** `vi.mock('$lib/api/documents', ...)` must not call `vi.importActual` because `$lib/api/documents` transitively imports `$lib/api/client.svelte.ts` → `$env/dynamic/public`, which is not available in jsdom. Both test files use flat `vi.mock` factories returning only the methods under test.
- **ProcessingPipeline gained one queue-only extension point.** The queue module still does not own the SSE stream. `processNextInQueue` uploads one file and promotes the entry to `processing`; then `<ProcessingPipeline>` rendered inside `UploadQueuePanel` takes over SSE. Review patching added an optional `onAuthError` callback so the queue can stop advancement on auth expiry without changing the existing single-file retry behavior.
- **Auth-error now aborts the batch.** Queue mode handles `onAuthError` by marking the active row failed, showing an authentication-required banner, and leaving later files queued until the user signs in again or starts a new batch. `stream-error` still marks the active row failed and advances to the next file.
- **Retry path untouched.** When `?retryDocumentId=…` is present, the page renders the exact pre-15.4 single-file flow (same `$state` variables, same `DocumentUploadZone` usage without `multiple`, same `ProcessingPipeline` wiring via `handleProcessingComplete` / `handleProcessingFailure`). The queue branch is behind an `isRetryMode` guard.

### Completion Notes List

- **AC1 (multi-select + multi-drop)**: `DocumentUploadZone` gains a `multiple` prop; when enabled the native `<input multiple>` attribute is set and both drop + file-picker handlers pass every selected file to the new `onFilesSelected(files: File[])` callback.
- **AC2 (client queue)**: `UploadQueueEntry` type + `createUploadQueue`, `advanceQueue`, `isTerminal`, `countByStatus`, `getActiveEntry`, `getQueueStatus` live in `src/lib/upload-queue.ts`. The new `UploadQueuePanel` renders per-file state and aggregate counts live.
- **AC3 (reuses single-file endpoint)**: `processNextInQueue` calls `uploadDocument(file)` per entry; `ProcessingPipeline` opens a fresh `streamDocumentStatus` per active entry. Zero backend changes.
- **AC4 (sequential execution)**: `processNextInQueue` is a no-op when an active entry exists; the queue only advances after the active entry reaches terminal status.
- **AC4 review patch (auth abort)**: queue mode now distinguishes `auth-error` from `stream-error`. Auth expiry stops the batch and surfaces a re-auth message; generic stream loss still fails that row and advances.
- **AC5 (retry stays single-file)**: `isRetryMode` branch renders the unchanged Story 2.5 flow — queue logic is never invoked.
- **AC6 (end-of-batch summary)**: `getQueueStatus(queue) === 'summary'` renders `UploadBatchSummary` with completed/partial/failed counts, per-file "View result" links, and an "Upload another batch" button that resets the queue.
- **AC7 (dashboard cache invalidation per file)**: `applyTerminalStatus` invalidates `['documents']`, `['health_values']`, `['ai_dashboard_interpretation']` on `completed`/`partial` and skips invalidation on `failed`. Test: `upload-queue.test.ts > applyTerminalStatus > 3-file batch per-file invalidation count` verifies 6 calls for 2 completed + 1 failed, with exactly 2 dashboard-key invalidations.
- **AC8 (single-file + zero-file fallbacks)**: `onFilesSelected([file])` creates a queue of one → summary shows one result. Empty picker selection is a no-op (`validateFilesForQueue` returns `{ accepted: [], rejected: [] }`). Existing `page.test.ts` section-header assertions still pass.
- **Review patch verification**: focused frontend rerun after review fixes passed `79/79` tests across `ProcessingPipeline.test.ts`, `upload-queue.test.ts`, `upload-page-processing.test.ts`, and `page.test.ts`. `npm run check` passed with `0` errors / `0` warnings.

Test counts:
- **New**: 32 queue-module tests (`src/lib/upload-queue.test.ts`) + 3 multi-file invalidation cases appended to `upload-page-processing.test.ts`.
- **Full suite**: frontend `npm run test:unit` → 703/703 pass (was 684 pre-15.4). backend `uv run pytest` → 460/460 pass. `svelte-check` → 0 errors / 0 warnings.

### File List

**New**

- `healthcabinet/frontend/src/lib/upload-queue.ts` — queue data model, pure transitions, `processNextInQueue` orchestrator, `applyTerminalStatus`, `markEntryProcessing`, `validateFilesForQueue` helper.
- `healthcabinet/frontend/src/lib/upload-queue.test.ts` — 32 unit tests (type model, `advanceQueue`, counts, derived status, `processNextInQueue`, terminal invalidation rules, validation partitioning).
- `healthcabinet/frontend/src/lib/components/health/UploadQueuePanel.svelte` — queue list wrapper that renders entry rows and the active `ProcessingPipeline`.
- `healthcabinet/frontend/src/lib/components/health/UploadQueueEntryRow.svelte` — per-entry row (icon, filename, size, status badge, "View result" / "Retry this file" actions).
- `healthcabinet/frontend/src/lib/components/health/UploadBatchSummary.svelte` — end-of-batch summary with success + failure groups and an "Upload another batch" reset.

**Modified**

- `healthcabinet/frontend/src/lib/components/health/DocumentUploadZone.svelte` — adds `multiple` + `onFilesSelected(File[])` props, native `<input multiple>`, array-based drop handler; single-file retry path unchanged.
- `healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.svelte` — adds optional `onAuthError` callback so queue mode can stop on SSE auth expiry while preserving single-file `onFailed` behavior.
- `healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.test.ts` — adds coverage for the queue-specific auth-error callback path.
- `healthcabinet/frontend/src/routes/(app)/documents/upload/+page.svelte` — gains `isRetryMode` guard wrapping the original single-file flow; new `queue` state + multi-file branch renders idle / active (via `UploadQueuePanel`) / summary (via `UploadBatchSummary`).
- `healthcabinet/frontend/src/routes/(app)/documents/upload/page.test.ts` — adds mounted route tests for sequential multi-file processing, summary reset, and auth-error batch abort behavior.
- `healthcabinet/frontend/src/routes/(app)/documents/upload/upload-page-processing.test.ts` — appends 3 tests covering per-file invalidation for multi-file batches (completed/partial/failed mix, all-failed, single-file back-compat).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `15-4-sequential-multi-upload-queue` → `done`; `last_updated` updated for the review-fix verification pass.

**Untouched (per story Dev Notes "Do NOT modify" list)**

- `healthcabinet/frontend/src/lib/api/documents.ts`
- `healthcabinet/frontend/src/lib/components/health/PartialExtractionCard.svelte`
- `healthcabinet/frontend/src/routes/(app)/documents/upload/page-state.ts` (retry path still consumes these helpers unchanged)
- `healthcabinet/backend/**`

### Change Log

| Date | Change | Notes |
|---|---|---|
| 2026-04-22 | Implemented Story 15.4 sequential multi-upload queue | Adds multi-file queue mode on `/documents/upload` while preserving Story 2.5 single-file retry flow. 32 queue-module tests + 3 page-level invalidation tests. Zero backend changes. 703/703 frontend, 460/460 backend, svelte-check clean. |
| 2026-04-22 | Applied review round fixes for Story 15.4 | Queue auth errors now abort the batch with a re-auth banner, partial rows use warning badges, route-level multi-file tests were added, and the retry contract was explicitly kept as "new document row". Focused frontend verification: 79/79 tests, svelte-check 0/0. |
