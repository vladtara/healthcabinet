# Story 15.7: Regression Gate for Stabilized Flows

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the **delivery team**,
I want automated regression coverage for the stabilized flows,
So that the fixes from Epic 15 stay reliable across backend and frontend refactors.

## Acceptance Criteria

1. **Backend coverage** exists for: document classification (`document_kind`), yearless-date persistence (measured_at stays `null`, partial text stored), year confirmation endpoint (validates, updates values + AI, correct 4xx paths), and dashboard AI rebuild behavior — specifically after **upload completion**, **reupload**, and **year confirmation** (not only after delete cascade).

2. **Frontend coverage** exists for: auth restore race (no redirect while `unknown`/`restoring`), multi-upload queue sequential processing, retry mode single-file guard (reupload URL param disables batch), filter invalidation on completed upload, locale persistence and bootstrap order, and chat scroll behavior.

3. **E2E acceptance coverage** verifies the full end-to-end scenarios from the fix plan: hard reload keeps authenticated session, multi-file sequential upload queue, year confirmation full flow (upload yearless → confirm year → values updated), and dashboard filter-empty state after document removal.

## Tasks / Subtasks

- [x] Task 1: Backend — Dashboard AI rebuild after upload, reupload, and year confirmation (AC: 1)
  - [x] In `tests/ai/test_router.py`, add `test_get_dashboard_interpretation_rebuilds_after_new_upload`: seed user with no AiMemory rows; simulate new document completing and AiMemory row being inserted; assert next `GET /api/v1/ai/dashboard/interpretation?document_kind=analysis` returns that new document_id in `source_document_ids`
  - [x] In `tests/ai/test_router.py`, add `test_get_dashboard_interpretation_rebuilds_after_reupload`: seed user with 1 AiMemory; replace it with a new AiMemory row (same document, refreshed content, new `interpreted_at`); assert next call reflects updated context text
  - [x] In `tests/ai/test_router.py`, add `test_get_dashboard_interpretation_rebuilds_after_year_confirmation`: seed user with AiMemory for an analysis; call `POST /api/v1/documents/{id}/confirm-date-year`; assert AI interpretation is invalidated at the document level; verify the subsequent dashboard call aggregates the remaining valid context
  - [x] Reuse `_seed_user_with_kinded_ai_memories` helper or extract a shared seeding utility; follow `make_user` + `make_document` factory pattern from `tests/conftest.py`

- [x] Task 2: Frontend — Upload queue retry mode single-file guard (AC: 2)
  - [x] In `src/routes/(app)/documents/upload/page.test.ts`, within the `Upload page multi-file queue` describe block, add: `'retry mode: file input multiple is false when retryDocumentId URL param is present'` — render the page with `retryDocumentId` prop set, assert `fileInput.multiple === false` and that `mockReuploadDocument` is called (not `mockUploadDocument`) when a file is selected
  - [x] File location: `healthcabinet/frontend/src/routes/(app)/documents/upload/page.test.ts`

- [x] Task 3: Frontend — Filter invalidation edge case (AC: 2)
  - [x] In `src/routes/(app)/dashboard/page.test.ts`, verify (or add if missing) a test: when the active dashboard filter is `analysis` and the last analysis document is deleted, the filter-empty state renders the kind-specific copy ("No analyses found") rather than the first-time empty state
  - [x] File location: `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts`

- [x] Task 4: E2E — Hard reload keeps authenticated session (AC: 3)
  - [x] In `tests/auth.spec.ts`, add a test inside the `Login` describe: `'hard reload on protected route keeps authenticated user on page'` — login → navigate to `/dashboard` → call `page.reload()` → assert user remains on `/dashboard` (not redirected to `/login`)
  - [x] Use the existing `setupAuth` helper from `tests/helpers/auth.ts`; mock `/api/v1/auth/refresh` to return 200 with a fresh token
  - [x] File location: `healthcabinet/frontend/tests/auth.spec.ts`

- [x] Task 5: E2E — Year confirmation full flow (AC: 3)
  - [x] In `tests/document-detail.spec.ts`, add: `'yearless analysis shows confirmation banner and updates dashboard after year confirmed'` — mock `GET /documents/{id}` with `needs_date_confirmation: true, partial_measured_at_text: "03.12"`; assert the year confirmation banner is rendered; click confirm with year 2025; mock `POST /documents/{id}/confirm-date-year` returning 200; assert the banner disappears
  - [x] File location: `healthcabinet/frontend/tests/document-detail.spec.ts`

- [x] Task 6: E2E — Multi-file sequential upload queue (AC: 3)
  - [x] In `tests/document-processing.spec.ts`, add: `'multi-file sequential queue processes files one at a time and shows batch summary'` — mock file input with 2 files; assert only 1 upload call is in-flight at a time; mock SSE streams completing both; assert batch summary shows "1 complete, 1 partial"
  - [x] File location: `healthcabinet/frontend/tests/document-processing.spec.ts`

- [x] Task 7: E2E — Dashboard filter behavior after document removal (AC: 3)
  - [x] In `tests/dashboard.spec.ts`, add: `'switching to analysis filter after only plain documents remain shows filter-empty state'` — mock health_values for `analysis` filter returning empty array while `all` filter returns rows; assert filter-empty state renders with kind-specific copy, not the first-time empty CTA
  - [x] File location: `healthcabinet/frontend/tests/dashboard.spec.ts`

- [x] Task 8: Verify full test suite stays green (AC: 1, 2, 3)
  - [x] Run `docker compose exec backend uv run pytest` — 463 passed (3 new + 460 existing)
  - [x] Run `docker compose exec frontend npm run test:unit` — 791 passed (2 new + 789 existing)
  - [x] Run `npm run test:e2e -- --project=chromium` — 4/4 new E2E tests pass; see Completion Notes for pre-existing E2E baseline (SSE-mock drift from Story 14.1)

## Dev Notes

### Existing Coverage (Do NOT duplicate)

The following is already covered — check before writing new tests to avoid redundancy:

**Backend — already green:**
- `tests/processing/test_finalize_document.py`: classification (analysis/document/unknown), yearless-date → `partial` status + `needs_date_confirmation=True` + `partial_measured_at_text` stored, classification recomputed on reprocess
- `tests/documents/test_partial_date_parser.py`: fragment parsing matrix
- `tests/documents/test_router.py`: 12 year-confirmation tests (happy path, auth, ownership, validation, AI regeneration failure, boundary years, calendar validation, future year rejection)
- `tests/ai/test_router.py`: dashboard AI rebuild **after delete cascade** (`test_get_dashboard_interpretation_rebuilds_after_document_delete_cascade`) — this is the model for the new upload/reupload/year-confirm rebuild tests

**Frontend — already green:**
- `src/lib/stores/auth.svelte.test.ts`: bootstrap states `unknown → restoring → authenticated/anonymous`, concurrent deduplicate, `setAccessToken` race guard
- `src/routes/(app)/layout.test.ts`: no redirect while bootstrap is `unknown` or `restoring`
- `src/lib/upload-queue.test.ts`: queue data model, advanceQueue, processNextInQueue, applyTerminalStatus (dashboard cache invalidation for completed/partial; no-op for failed)
- `src/routes/(app)/documents/upload/page.test.ts`: multi-file queue sequential processing + batch summary (2-file test), auth error abort
- `src/lib/stores/locale.svelte.test.ts`: bootstrap order (saved → browser → `en`), invalid storage fallback, persistence, `_resetForTests()`
- `src/lib/components/health/ai-chat-scroll.test.ts` + `AIChatWindow.test.ts`: `isNearBottom` logic, auto-scroll only when near bottom, overflow in minimized/maximized modes

**E2E — already green:**
- `tests/auth.spec.ts`: registration + login flows
- `tests/dashboard.spec.ts`: empty state, active state, filter radio, error state
- `tests/document-processing.spec.ts`: single-file upload + SSE stream

### The Real Gaps This Story Closes

**Gap 1 — Backend rebuild after upload/reupload/year-confirm (AC1):**
The only covered rebuild scenario is cascade delete. The fix plan (Story 15.3 AC4) states: "Dashboard AI context is rebuilt from remaining persisted data after delete, upload, reupload, and year confirmation." The delete case has a test; the other three do not. Story 15.7 adds the missing three.

**Gap 2 — Frontend retry-mode single-file guard (AC2):**
The multi-file queue tests verify the new batch flow. But Story 15.4 AC5 states "Retry mode stays single-file when `retryDocumentId` is present." The current tests do not verify that the file input `multiple` attribute is false in retry mode, nor that `reuploadDocument` is called instead of `uploadDocument`.

**Gap 3 — E2E hard reload (AC3):**
The auth unit tests cover the bootstrap state machine in isolation. The Playwright `auth.spec.ts` covers login/registration, but not the "hard reload on `/dashboard` keeps user signed in" scenario. This is the most user-facing regression in Epic 15 (Story 15.1) and needs E2E verification.

**Gap 4 — E2E year confirmation and dashboard filter (AC3):**
The year confirmation endpoint has deep backend unit coverage, but no E2E test verifies the full user flow: upload a yearless document → see the confirmation banner → confirm → banner disappears. Similarly, dashboard filter behavior after document state changes has unit coverage but no E2E scenario.

### Project Structure Notes

- Backend test placement: `tests/<domain>/test_*.py` mirroring `app/`; `tests/conftest.py` provides `async_db_session`, `make_user`, `make_document` factories
- Frontend unit tests: co-located `*.test.ts` alongside source files
- Frontend E2E tests: `healthcabinet/frontend/tests/*.spec.ts` with Playwright; helpers in `tests/helpers/`
- SSE testing (backend): `httpx.AsyncClient(stream=True)` — assert full event sequence, not terminal state
- Backend async test pattern: `@pytest.mark.asyncio`, `AsyncClient` from `httpx`, `AsyncSession` from SQLAlchemy 2.0 async
- Frontend mock pattern for API: `vi.mock('$lib/api/documents', ...)` at top; `vi.mocked(fn)` for typed mocks; `vi.clearAllMocks()` in `beforeEach`
- Frontend Svelte 5 runes: use `$state`, `$derived`, `$effect` — not Svelte 4 stores
- TanStack Query invalidation: `queryClient.invalidateQueries({ queryKey: [...] })` — assert via spy on `invalidateQueries` or via re-rendered data

### AiMemory Seeding Pattern (for backend tests)

The existing rebuild-after-delete test uses `_seed_user_with_kinded_ai_memories`. Reuse this private helper or replicate its pattern:

```python
# from tests/ai/test_router.py — internal helper
user, a_doc_a, a_doc_b, d_doc, _ = await _seed_user_with_kinded_ai_memories(
    async_db_session, make_user, make_document, email="unique@example.com"
)
# Then call GET /api/v1/ai/dashboard/interpretation?document_kind=analysis
# and assert source_document_ids matches the a_doc IDs
```

For the **new upload rebuild test**, insert a new AiMemory row after the initial call to verify the next call widens `source_document_ids`.

For the **reupload rebuild test**, update the existing AiMemory row's `interpreted_at` and `context_text` to simulate a refresh, then assert the endpoint reflects the new content.

For the **year-confirmation rebuild test**: call `POST /api/v1/documents/{id}/confirm-date-year` (which invalidates document-level AI), then call the dashboard endpoint and assert the aggregation still works (reduced to the remaining valid context).

### Auth Headers for Backend Tests

```python
def auth_headers(user) -> dict:
    from app.core.security import create_access_token
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}
```

### E2E Playwright Patterns

```typescript
// From tests/helpers/auth.ts — use setupAuth for authenticated test context
import { setupAuth } from './helpers/auth';

// Hard reload test pattern
await page.goto('/dashboard');
await page.reload();
await expect(page).toHaveURL('/dashboard');  // not /login

// Mock API route for refresh endpoint
await page.route('**/api/v1/auth/refresh', async route => {
  await route.fulfill({ status: 200, contentType: 'application/json',
    body: JSON.stringify({ access_token: 'new-token' }) });
});
```

### Key Files to Touch

| Task | File |
|------|------|
| Task 1 | `healthcabinet/backend/tests/ai/test_router.py` |
| Task 2 | `healthcabinet/frontend/src/routes/(app)/documents/upload/page.test.ts` |
| Task 3 | `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts` |
| Task 4 | `healthcabinet/frontend/tests/auth.spec.ts` |
| Task 5 | `healthcabinet/frontend/tests/document-detail.spec.ts` |
| Task 6 | `healthcabinet/frontend/tests/document-processing.spec.ts` |
| Task 7 | `healthcabinet/frontend/tests/dashboard.spec.ts` |

### Architecture Compliance

- **Never** add DB calls in `router.py` — all DB through `service.py` → `repository.py`
- **Never** inline user_id from body — always `Depends(get_current_user)`
- **Encryption/decryption in `repository.py` only** — never in service or router
- ISO 8601 UTC for all datetimes
- RFC 7807 error shape always
- Test files use `snake_case` for Python, `camelCase`/`PascalCase` for TypeScript per project conventions

### References

- Epic 15 story sequence and ACs: [Source: `_bmad-output/planning-artifacts/flow-stabilization-epic-15.md`]
- Architecture testing patterns: [Source: `_bmad-output/planning-artifacts/architecture.md#Test placement`, `#SSE testing`]
- Dashboard AI rebuild (delete cascade model): [Source: `healthcabinet/backend/tests/ai/test_router.py:780`]
- Year confirmation tests (12 tests, model for auth/validation patterns): [Source: `healthcabinet/backend/tests/documents/test_router.py:868`]
- Auth bootstrap state machine tests: [Source: `healthcabinet/frontend/src/lib/stores/auth.svelte.test.ts:147`]
- Multi-upload queue tests: [Source: `healthcabinet/frontend/src/routes/(app)/documents/upload/page.test.ts:385`]
- Dashboard filter store test model: [Source: `healthcabinet/frontend/src/lib/stores/dashboard-filter.svelte.test.ts`]
- E2E auth helpers: [Source: `healthcabinet/frontend/tests/helpers/auth.ts`]
- conftest.py factories: [Source: `healthcabinet/backend/tests/conftest.py`]
- Project context rules: [Source: `_bmad-output/project-context.md`]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context), via `/bmad-dev-story` slash command on 2026-04-22.

### Debug Log References

- Initial E2E run in the `frontend` Docker container failed — container is Alpine-based (`node:20-alpine`), Playwright's Ubuntu Chromium build and `apk`-installed Chromium are both out of scope for that image. Per project operator direction, **E2E runs on the host** (browser binaries in `~/Library/Caches/ms-playwright`); Docker-based testing rule applies to backend + unit only. `.github/workflows/frontend-ci.yml` already runs E2E on `ubuntu-latest`, which matches this split.
- `document-processing.spec.ts` existing SSE helpers (`setupSSEMock`, `dispatchSSEEvents`, `triggerSSEErrors`) stub `window.EventSource`, but the production code migrated to fetch-based streaming via `apiStream` in Story 14.1. Old SSE-based specs fail on `waitForFunction(__eventSources.length === 1)`. The new Task 6 test uses fetch-stream route mocks (`text/event-stream` body) instead; it does not touch the dead helper.
- `DocumentDetailPanel.svelte` — the component that renders the year-confirmation banner — lives on `/documents` (list + right-pane panel), NOT on `/documents/{id}` (the simpler detail route). Task 5 navigates to `/documents`, selects the yearless row, then interacts with the banner.
- `AiMemory` model has no `context_text` column (story prose referenced one); real columns are `interpretation_encrypted: bytes`, `model_version`, `safety_validated`, `updated_at`. The reupload test updates `interpretation_encrypted` in place and asserts rebuild via `call_model_text.call_args` prompt inspection.
- Upload page retry mode is detected via `$page.url.searchParams.get('retryDocumentId')`, not via a prop; Task 2 replaced the existing `vi.mock('$app/stores', ...)` with a `vi.hoisted`-backed writable so the URL is mutable per test.

### Completion Notes List

**What was implemented**
- **3 new backend tests** in `tests/ai/test_router.py` mirroring the existing delete-cascade test (`test_get_dashboard_interpretation_rebuilds_after_document_delete_cascade`), covering the remaining three AC1 triggers: new upload, reupload, year-confirmation. Seeding reuses the file-local `_seed_user_with_kinded_ai_memories` helper; LLM boundary is patched via `app.ai.service.call_model_text`.
- **2 new frontend unit tests**: retry-mode single-file guard (`upload/page.test.ts`) and filter-empty kind-specific copy (`dashboard/page.test.ts`).
- **4 new E2E tests**: hard-reload keeps session (`auth.spec.ts`), yearless-analysis full flow (`document-detail.spec.ts`), multi-file sequential queue (`document-processing.spec.ts`), dashboard filter-empty with kind-specific copy (`dashboard.spec.ts`).
- **Review patch round (2026-04-23)**: fixed the year-confirmation dashboard invalidation keys, added a single-file drop guard for retry mode, and tightened the three Story 15.7 regression specs to cover the missing refresh/removal/ordering paths from code review.

**Verification results (2026-04-22)**
- Backend: `docker compose exec backend uv run pytest` → **463 passed**. All 4 rebuild tests in `tests/ai/test_router.py` green (1 existing + 3 new).
- Frontend unit: `docker compose exec frontend npm run test:unit` → **791 passed, 72 files**. New tests in `upload/page.test.ts` (22/22) and `dashboard/page.test.ts` (25/25) green.
- Frontend E2E (host-side): the 4 new tests all pass in < 1s each (`auth.spec.ts`, `document-detail.spec.ts`, `document-processing.spec.ts`, `dashboard.spec.ts`).

**Verification results (2026-04-23 review patches)**
- Frontend unit: `npm run test:unit -- src/lib/components/health/DocumentDetailPanel.test.ts 'src/routes/(app)/documents/upload/page.test.ts'` → **66 passed**.
- Frontend E2E (host-side, targeted): `npm run test:e2e -- tests/document-detail.spec.ts tests/document-processing.spec.ts tests/dashboard.spec.ts --project=chromium --grep 'yearless analysis shows confirmation banner and updates dashboard after year confirmed|multi-file sequential queue processes files one at a time and shows batch summary|switching to analysis filter after only plain documents remain shows filter-empty state'` → **3 passed**.

**Pre-existing E2E baseline — NOT introduced by this story**
The full E2E suite has 31 failing tests that existed before this story and are out of scope. Confirmed by diffing against `HEAD` (e.g. `dashboard.spec.ts:81` is byte-identical to HEAD and fails there for the same reason — the dashboard heading was renamed in a prior story without updating the spec). Failures cluster in two groups:
- `document-processing.spec.ts` SSE-based tests — depend on the `setupSSEMock`/`dispatchSSEEvents` helpers that were invalidated when Story 14.1 migrated to fetch-based streaming. This is documented drift, not a regression.
- `dashboard.spec.ts` static-heading / first-time-empty / try-again tests — reference copy or structure that has since changed.
Addressing this baseline is a separate remediation task (suggested: follow-up story for the Pre-GA Cleanup Sprint or a testarch test-review). This story closes the specified 7 regression gaps without touching the broken legacy tests.

**Operational note for future runs**
- Backend + frontend unit tests: run inside Docker Compose per CLAUDE.md. The backend container has no volume mount for source, so update its copy with `docker cp healthcabinet/backend/tests/ai/test_router.py healthcabinet-backend-1:/app/tests/ai/test_router.py` before running.
- Frontend E2E: the frontend container is Alpine and does not run Playwright Chromium. Run E2E from the host in `healthcabinet/frontend` with `npm run test:e2e -- --project=chromium`. CI handles this the same way (Ubuntu runner).

### File List

**New/modified files**
- `healthcabinet/frontend/src/lib/components/health/DocumentDetailPanel.svelte` — corrected year-confirmation cache invalidation to hit `health_values` and `ai_dashboard_interpretation`
- `healthcabinet/frontend/src/lib/components/health/DocumentUploadZone.svelte` — rejects multi-file drops in single-file mode before any upload/reupload call
- `healthcabinet/frontend/src/lib/i18n/messages.ts` — added localized copy for the single-file drop guard error
- `healthcabinet/backend/tests/ai/test_router.py` — added 3 rebuild tests + Story 15.7 section header
- `healthcabinet/frontend/src/lib/components/health/DocumentDetailPanel.test.ts` — pinned year-confirmation POST payload and invalidation keys
- `healthcabinet/frontend/src/routes/(app)/documents/upload/page.test.ts` — added retry-mode single-file guard test; replaced `$app/stores` mock with `vi.hoisted`-backed writable + `setPageUrl` helper
- `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts` — added kind-specific filter-empty copy test
- `healthcabinet/frontend/tests/auth.spec.ts` — added hard-reload E2E
- `healthcabinet/frontend/tests/document-detail.spec.ts` — strengthened year-confirmation E2E to assert submitted year plus dashboard refresh
- `healthcabinet/frontend/tests/document-processing.spec.ts` — replaced timestamp-based queue ordering proof with a deterministic event log
- `healthcabinet/frontend/tests/dashboard.spec.ts` — rewrote the filter-empty E2E to exercise the real delete/invalidation flow via `/documents`
- `healthcabinet/frontend/test-results/.last-run.json` — restored passing Playwright metadata after review fixes

**Metadata**
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `15-7-regression-gate-for-stabilized-flows` transitioned `ready-for-dev → in-progress → review → done`
- `_bmad-output/implementation-artifacts/15-7-regression-gate-for-stabilized-flows.md` — task checkboxes, Dev Agent Record, File List, Change Log, Status

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-04-22 | Story moved to `in-progress`. Implementation started. | Dev Agent (Opus 4.7) |
| 2026-04-22 | Added 3 backend dashboard-AI rebuild tests (Task 1). | Dev Agent |
| 2026-04-22 | Added retry-mode single-file guard unit test (Task 2). | Dev Agent |
| 2026-04-22 | Added kind-specific filter-empty unit test (Task 3). | Dev Agent |
| 2026-04-22 | Added hard-reload session E2E (Task 4). | Dev Agent |
| 2026-04-22 | Added year-confirmation full-flow E2E (Task 5). | Dev Agent |
| 2026-04-22 | Added multi-file sequential queue E2E (Task 6). | Dev Agent |
| 2026-04-22 | Added dashboard filter-empty kind-specific E2E (Task 7). | Dev Agent |
| 2026-04-22 | Verified full backend (463) + frontend unit (791) + 4 new E2E suites green; documented pre-existing E2E drift (Task 8). Status → `review`. | Dev Agent |
| 2026-04-23 | Applied code-review patches: fixed dashboard invalidation keys, added single-file drop guard, strengthened 3 regression specs, restored Playwright artifacts. Status → `done`. | Codex |

### Review Findings

- [x] [Review][Patch] Year-confirmation E2E still misses dashboard/value refresh coverage [healthcabinet/frontend/tests/document-detail.spec.ts:226]
- [x] [Review][Patch] Dashboard filter-empty E2E does not exercise the removal/invalidation flow [healthcabinet/frontend/tests/dashboard.spec.ts:220]
- [x] [Review][Patch] Sequential queue E2E uses millisecond timestamps as its ordering proof [healthcabinet/frontend/tests/document-processing.spec.ts:184]
- [x] [Review][Patch] Retry-mode coverage misses the multi-file drop path in the single-file upload zone [healthcabinet/frontend/src/routes/(app)/documents/upload/page.test.ts:487]
- [x] [Review][Patch] Generated Playwright failure artifact is still in the tracked diff [healthcabinet/frontend/test-results/.last-run.json:1]
