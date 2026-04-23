# Story 2.6: Value Flagging

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a registered user,
I want to flag an extracted health value that looks incorrect,
so that I can signal potential extraction errors for admin review without losing my other results.

## Acceptance Criteria

1. Given an authenticated user is viewing extracted health values for a document, when they hover over or focus on a value card, then a flag button appears inline next to the value.
2. Given a user clicks the flag button on a value, when the flag action is submitted, then the `health_values` row is updated so the flagged state is persisted, a visible indicator shows the value is now flagged, and the value remains visible in the dashboard and document detail view.
3. Given a flagged value, when the future admin extraction-error queue is implemented, then the queue can surface the value name, document ID, and flag timestamp from persisted data without recomputing state.
4. Given a user flags a value using keyboard navigation, then the flag button is reachable via Tab, activatable via Enter and Space, and the state change is announced through an `aria-live` region.

## Tasks / Subtasks

- [x] Task 1 - Add persisted user-flag state to `health_values` (AC: 2, 3)
  - [x] Add the missing ORM fields to `healthcabinet/backend/app/health_data/models.py`: `is_flagged` boolean default `False` and `flagged_at` nullable UTC timestamp.
  - [x] Create a new Alembic migration instead of editing prior migrations. The migration should backfill existing rows with `is_flagged=false` and preserve existing data.
  - [x] Keep naming aligned with repo conventions and architecture docs: `snake_case`, SQLAlchemy 2.0 `Mapped[...]`, `mapped_column(...)`.

- [x] Task 2 - Extend health-data repository/service layers for owner-scoped flagging (AC: 2, 3)
  - [x] Add a repository method that updates exactly one `health_values` row owned by the authenticated user and returns the updated record.
  - [x] Persist `flagged_at` only on first flag transition so later admin queue ordering can use a stable timestamp.
  - [x] Keep encryption boundaries unchanged: no value encryption/decryption logic may move out of `repository.py`.
  - [x] Preserve owner isolation with `user_id` supplied only from `Depends(get_current_user)`, never from request body.

- [x] Task 3 - Expose a dedicated API contract for flagging values (AC: 2, 4)
  - [x] Add a dedicated owner-scoped route in `healthcabinet/backend/app/health_data/router.py`. Preferred shape: `PUT /api/v1/health-values/{health_value_id}/flag`.
  - [x] Return a typed response model that includes at least `id`, `is_flagged`, and `flagged_at`, plus any fields needed for immediate UI refresh.
  - [x] Keep errors in RFC 7807 shape for not-found, forbidden ownership, and invalid repeat-flag cases if the implementation treats duplicate flagging as a no-op or conflict.

- [x] Task 4 - Surface flagged state in API schemas used by document detail and future dashboard views (AC: 2, 3)
  - [x] Extend `healthcabinet/backend/app/health_data/schemas.py` response models with `is_flagged` and `flagged_at`.
  - [x] Extend `healthcabinet/backend/app/documents/schemas.py` nested `HealthValueItem` payload so document detail consumers receive the same fields without a parallel data shape.
  - [x] Keep JSON fields `snake_case`; do not add a transformation layer in TypeScript.

- [x] Task 5 - Add frontend API helpers and types for value flagging (AC: 2, 4)
  - [x] Extend `healthcabinet/frontend/src/lib/types/api.ts` with `is_flagged` and `flagged_at` on `HealthValueItem`, plus a response type for the flag endpoint if needed.
  - [x] Add a dedicated API helper in `healthcabinet/frontend/src/lib/api/health-values.ts` if the repo already prefers domain-specific clients; otherwise add the helper in the smallest existing API module that keeps ownership clear.
  - [x] Reuse `apiFetch<T>()`, existing auth/refresh behavior, and existing query keys. Do not introduce direct `fetch()` calls for authenticated backend traffic.

- [x] Task 6 - Upgrade the document detail value UI to support hover/focus flag affordances (AC: 1, 2, 4)
  - [x] Refactor the inline health-value row in `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` into a reusable component if that materially simplifies hover, focus, and flagged-state styling; otherwise keep the change local.
  - [x] Show the flag action only on hover and keyboard focus, but keep it accessible for touch by preserving a 44x44px minimum target.
  - [x] Once flagged, show a persistent visual indicator on the value and prevent the action from hiding the value or collapsing the card.
  - [x] Add an `aria-live` announcement using UX-approved copy: `Thanks — we'll review this value`.
  - [x] Preserve existing partial/failure recovery UI from Story 2.5 and delete flow from Story 2.4.

- [x] Task 7 - Query invalidation and optimistic UI behavior (AC: 2, 4)
  - [x] Invalidate or update `['documents', documentId]` detail cache immediately after a successful flag so the visible state changes without a reload.
  - [x] Also invalidate `['health_values']` because later dashboard and timeline surfaces depend on the same records.
  - [x] Avoid introducing polling or a second real-time transport; this is a direct mutation, not an SSE workflow.

- [x] Task 8 - Backend tests for flagging behavior and regression safety (AC: 2, 3, 4)
  - [x] Add router/service/repository tests under `healthcabinet/backend/tests/health_data/` for owner-only flagging, unknown ID handling, first-flag timestamp persistence, and schema serialization.
  - [x] Verify the flag mutation does not change encrypted numeric values, confidence, `needs_review`, or document visibility.
  - [x] Verify the document detail payload still includes flagged values and now surfaces `is_flagged` and `flagged_at`.

- [x] Task 9 - Frontend tests for interaction, accessibility, and cache updates (AC: 1, 2, 4)
  - [x] Add tests near the documents page for hover/focus visibility of the flag action, keyboard activation, `aria-live` announcement, and persistent flagged badge/state.
  - [x] Add API/helper tests proving the client calls the exact flag endpoint and preserves snake_case payload contracts.
  - [x] Add tests showing successful flagging updates the current detail panel without hiding the value and invalidates the relevant query keys.

### Review Findings

- [x] [Review][Patch] Flag action is hidden from touch users [`healthcabinet/frontend/src/lib/components/health/HealthValueRow.svelte:49`] — The button is rendered with base `opacity-0` and is only revealed by `group-hover` or `group-focus-within`. On touch devices there is no hover state, and users cannot reliably discover an invisible control, which violates the story's requirement to keep the action accessible on touch while preserving a 44x44 target.
- [x] [Review][Patch] `flagged_at` is not stable under concurrent flag requests [`healthcabinet/backend/app/health_data/repository.py:235`] — The repository does a plain read followed by an in-memory `if not row.is_flagged` update. Two requests racing in separate transactions can both observe `is_flagged = false` and write different timestamps, so the persisted `flagged_at` is no longer guaranteed to reflect the first flag transition as required for future admin-queue ordering.
- [x] [Review][Patch] Misleading migration comment describes unused two-phase strategy [`healthcabinet/backend/alembic/versions/007_health_values_flagging.py:34-35`] — Comment says "Add as nullable first… then backfill and constrain" but the code adds is_flagged as NOT NULL with server_default in a single step. The comment describes a multi-phase approach that was never implemented.
- [x] [Review][Patch] isFlagged local state desyncs from server after query refetch [`healthcabinet/frontend/src/lib/components/health/HealthValueRow.svelte:13-16`] — isFlagged is initialized once from hv.is_flagged at mount and never updated from props again. After TanStack Query refetch the parent re-renders with updated data but the component ignores it. Fix: use $derived(hv.is_flagged || locallyFlagged) where locallyFlagged is the optimistic flag set in onSuccess.
- [x] [Review][Patch] No onError handler on flag mutation — silent failure for user [`healthcabinet/frontend/src/lib/components/health/HealthValueRow.svelte:19-27`] — The createMutation config defines onSuccess but no onError. If the flag API call fails, the user receives zero feedback. Add onError handler with an aria-live announcement.
- [x] [Review][Defer] No index on is_flagged column for future admin queue queries [`healthcabinet/backend/app/health_data/models.py:32`] — deferred, pre-existing — admin queue story (5-2) should add the index when needed

#### Review Round 2 (2026-03-25)

- [x] [Review][Patch] Service layer raises HTTPException — violates layering [`healthcabinet/backend/app/health_data/service.py:82-91`] — The service catches `HealthValueNotFoundError` and raises `HTTPException` directly. This couples the service to FastAPI. The project pattern (see `main.py` lines 169+) registers domain exception handlers globally. Either register `HealthValueNotFoundError` in `main.py` or move the try/except to the router.
- [x] [Review][Patch] Row lock test inspects SQLAlchemy private attribute [`healthcabinet/backend/tests/health_data/test_repository.py:465-498`] — `test_flag_health_value_uses_row_lock_for_first_flag_transition` asserts on `_for_update_arg`, an undocumented SQLAlchemy internal. Will break silently on SQLAlchemy upgrades. Fix: compile the statement and assert `"FOR UPDATE"` in the SQL string.
- [x] [Review][Defer] No unflag/undo mechanism — deferred, out of story scope (story only specifies flagging)
- [x] [Review][Defer] No rate limiting on flag endpoint — deferred, cross-cutting concern for a future security hardening pass
- [x] [Review][Defer] No index on is_flagged column — deferred (already captured in R1, admin queue story 5-2)
- [x] [Review][Defer] No DB check constraint for is_flagged/flagged_at invariant — deferred, invariant enforced in application code; DB constraint is defense-in-depth
- [x] [Review][Defer] Partial reference range hidden when only one bound is null — deferred, pre-existing behavior from original inline rendering

#### Review Round 3 (2026-03-25)

- [x] [Review][Patch] Router-to-repository coupling; register global handler in main.py [`healthcabinet/backend/app/health_data/router.py:52-58`] — Decision: register `HealthValueNotFoundError` as a global exception handler in `main.py` (matching `DocumentNotFoundError` pattern). Remove the try/except from the router and the `repository` import.
- [x] [Review][Defer] HealthValueDecryptionError not caught in flag endpoint [`healthcabinet/backend/app/health_data/router.py:52-58`] — deferred, pre-existing — if `_to_record` raises `HealthValueDecryptionError` during flag operation it escapes as unhandled 500; not introduced by this change
- [x] [Review][Defer] No structured logging on exception catch-and-rewrap [`healthcabinet/backend/app/health_data/router.py:52-58`] — deferred, pre-existing pattern — router catches and re-raises with no structured log entry
- [x] [Review][Defer] RFC 7807 instance field inconsistency between handler patterns [`healthcabinet/backend/app/main.py`] — deferred, pre-existing — HTTPException handler uses full URL for `instance`; domain handlers use path only

## Dev Notes

### Story Scope and Boundaries

- This story builds on Story 2.4 document detail rendering and Story 2.5 partial-recovery behavior. Do not redesign the Documents page or replace the current detail panel.
- Keep scope on user-submitted extraction-error signaling. Do not implement the admin queue itself here.
- The epic currently references the admin queue as "Story 6.2", but the actual queue story in `epics.md` is Epic 5 Story 5.2: `5-2-extraction-error-queue-manual-value-correction`. Implement persistence for that future dependency, not the mislabeled reference.

### Current Codebase Reality

- `healthcabinet/backend/app/health_data/models.py` currently does not include the architecture-documented `is_flagged` field yet, so this story needs both migration and ORM updates.
- `healthcabinet/backend/app/health_data/router.py` currently exposes only list and timeline endpoints; no mutation endpoint exists.
- `healthcabinet/backend/app/health_data/service.py` currently only maps read models into `HealthValueResponse`, so flagging logic should be added there instead of in the router.
- `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` currently renders extracted values inline as plain blocks with confidence labels and optional reference ranges; there is no reusable biomarker card component in use on this page yet.
- `healthcabinet/frontend/src/lib/types/api.ts` `HealthValueItem` currently lacks any flag-specific fields, so document detail UI cannot persist or display flagged state yet.

### Technical Requirements

- Backend stays layered: router -> service -> repository, with all DB access in `repository.py` only.
- `user_id` must come from `Depends(get_current_user)` only.
- Keep all datetimes ISO 8601 UTC; no formatted timestamps in the API layer.
- Continue using RFC 7807 error responses.
- Preserve repository-only encryption/decryption boundaries for stored health values.
- Use a fresh Alembic migration for schema changes.

### Architecture Compliance

- Align with the architecture mapping that places health-value APIs in `app/health_data/` and document UI under `(app)/documents/`.
- Follow `snake_case` in DB, Python, API, and TypeScript payloads.
- Do not create a documents-specific flag endpoint when the mutation belongs to `health_values`.
- Persisted flag state must remain on the `health_values` row so later admin/reporting workflows can query it directly.

### File Structure Requirements

- Backend likely touch points:
  - `healthcabinet/backend/alembic/versions/` new migration for health-value flag fields
  - `healthcabinet/backend/app/health_data/models.py`
  - `healthcabinet/backend/app/health_data/repository.py`
  - `healthcabinet/backend/app/health_data/service.py`
  - `healthcabinet/backend/app/health_data/router.py`
  - `healthcabinet/backend/app/health_data/schemas.py`
  - `healthcabinet/backend/app/documents/schemas.py`
  - `healthcabinet/backend/tests/health_data/test_router.py`
  - `healthcabinet/backend/tests/health_data/test_repository.py`
- Frontend likely touch points:
  - `healthcabinet/frontend/src/lib/types/api.ts`
  - `healthcabinet/frontend/src/lib/api/health-values.ts` or existing domain API module
  - `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte`
  - `healthcabinet/frontend/src/routes/(app)/documents/page.test.ts`
  - Optional new value-row component under `healthcabinet/frontend/src/lib/components/health/` if extracting the UI is cleaner than growing the page file further

### Testing Requirements

- Backend:
  - Verify only the owner can flag a value.
  - Verify flagging an unknown or non-owned value returns the correct RFC 7807 response.
  - Verify first flag sets `is_flagged=true` and `flagged_at`.
  - Verify repeated flag submissions do not corrupt timestamps or other fields.
  - Verify document detail responses now surface `is_flagged` and `flagged_at`.
- Frontend:
  - Verify the flag button appears on hover and keyboard focus.
  - Verify keyboard activation with Enter and Space.
  - Verify `aria-live` feedback after success.
  - Verify the flagged value remains visible after mutation.
  - Verify query invalidation or optimistic updates refresh the visible detail state without a page reload.

### Previous Story Intelligence

- Story 2.4 established the current document cabinet/detail panel, `['documents']` and `['health_values']` query-key conventions, and the documents page test harness. Build on those paths instead of creating a second detail experience.
- Story 2.5 added `PartialExtractionCard`, retry helpers, and detail-cache optimistic updates around partial recovery. Reuse the same mutation/invalidation patterns rather than inventing a new state-management path.
- Story 2.3 already persists `needs_review` for low-confidence extraction. Do not overload that field for user flagging; user-generated flagging must be a separate persisted concept.

### Git Intelligence Summary

- Recent Epic 2 work has consistently extended existing document/detail flows instead of branching into new routes:
  - `ddc2d9a feat: implement retry and keep partial results functionality for document uploads`
  - `0763796 feat: update document deletion process to MinIO-first ordering and enhance error handling`
  - `7155dbf fix(documents): resolve 8 second-pass review patches for story 2-4`
- Inference: Story 2.6 should be implemented as a focused extension of the current documents detail surface and health-data API, not a broader UI rewrite.

### Latest Technical Information

- Svelte 5 official docs continue to use runes such as `$state(...)` for component-local state. Follow repo rules and avoid legacy store/reactive-block patterns in new UI work. Source: https://svelte.dev/docs/svelte/$state
- TanStack Query Svelte docs still center mutations and cache invalidation in the framework package rather than custom state containers. Reuse `createMutation` and query invalidation/update patterns already present in the repo. Source: https://tanstack.com/query/latest/docs/framework/svelte
- FastAPI route decorators continue to support explicit `response_model` and `status_code` configuration; keep the new flag endpoint typed the same way as the existing health-data routes. Source: https://fastapi.tiangolo.com/tutorial/path-operation-configuration/

### Project Context Reference

- Backend/frontend/testing rules: `/Users/vladtara/dev/set-bmad/_bmad-output/project-context.md`
- Planning sources:
  - `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/epics.md`
  - `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/prd.md`
  - `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/architecture.md`
  - `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/ux-design-specification.md`
- Previous implementation context:
  - `/Users/vladtara/dev/set-bmad/_bmad-output/implementation-artifacts/2-3-universal-value-extraction-confidence-scoring.md`
  - `/Users/vladtara/dev/set-bmad/_bmad-output/implementation-artifacts/2-4-document-cabinet-individual-management.md`
  - `/Users/vladtara/dev/set-bmad/_bmad-output/implementation-artifacts/2-5-re-upload-flow-partial-extraction-recovery.md`

### References

- `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/epics.md` - Story 2.6 acceptance criteria and Epic 2 context
- `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/epics.md` - Epic 5 flagged-value admin queue context (`5-2-extraction-error-queue-manual-value-correction`)
- `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/prd.md` - FR38 flagged-value admin response requirement
- `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/architecture.md` - `health_values` schema, `app/health_data/` ownership, and layering rules
- `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/ux-design-specification.md` - BiomarkerValueCard flagged state, button hierarchy, feedback patterns, and accessibility rules
- `/Users/vladtara/dev/set-bmad/_bmad-output/project-context.md` - Svelte 5 runes, API client rules, Docker-only tests, backend layering
- `/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/health_data/models.py`
- `/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/health_data/router.py`
- `/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/health_data/service.py`
- `/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/health_data/repository.py`
- `/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/health_data/schemas.py`
- `/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/documents/schemas.py`
- `/Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/documents/+page.svelte`
- `/Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/documents/page.test.ts`
- `/Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/lib/types/api.ts`
- `/Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/lib/api/documents.ts`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4.6) — review follow-ups
Claude Sonnet 4.6 (claude-sonnet-4-6) — initial implementation

### Debug Log References

- Loaded BMad config, sprint-status (story `2-6-value-flagging` → in-progress), and all referenced source files.
- Inspected migration 006 to determine naming conventions; stamped DB base and re-applied all migrations to bring schema to 007.
- All 154 backend tests and 90 frontend tests pass with 0 regressions. `ruff check` clean.
- Svelte compile warning for `$state(hv.is_flagged)` resolved by wrapping initial read in a helper function.
- 4 frontend unhandled errors from background refetch after `invalidateQueries` fixed by extending mock to handle the detail URL in each affected test.
- Review follow-up: Touch accessibility — replaced `opacity-0` base with `[@media(hover:hover)]:opacity-0` so button is always visible on touch devices. Desktop retains hover-reveal behavior via `[@media(hover:hover)]:group-hover:opacity-100`.
- Review follow-up: Race condition — verified `with_for_update()` (SELECT FOR UPDATE) was already present on the flag query, preventing concurrent transactions from both reading `is_flagged=false`. PostgreSQL READ COMMITTED isolation ensures the second transaction sees the committed update after lock release.
- Review follow-up: Replaced one-shot local `isFlagged` state with `$derived(hv.is_flagged || locallyFlagged)` so refetched query data and optimistic UI stay in sync.
- Review follow-up: Added flag mutation `onError` handling with aria-live feedback and covered both the error path and prop-driven refetch sync with targeted frontend tests.
- Verified in Docker: `docker compose -f /Users/vladtara/dev/set-bmad/healthcabinet/docker-compose.yml exec frontend npm run test:unit -- src/routes/(app)/documents/page.test.ts` → 44 passed.
- Review follow-up: Moved `HealthValueNotFoundError` to the router boundary so `service.py` remains framework-agnostic and the router still returns RFC 7807 404 responses.
- Review follow-up: Reworked the row-lock regression test to compile the SQL statement with the PostgreSQL dialect and assert `FOR UPDATE` instead of reading SQLAlchemy's private `_for_update_arg`.
- Verified in Docker: `docker compose -f /Users/vladtara/dev/set-bmad/healthcabinet/docker-compose.yml exec backend uv run pytest tests/health_data/test_repository.py -k row_lock` → 1 passed.
- Verified in Docker: `docker compose -f /Users/vladtara/dev/set-bmad/healthcabinet/docker-compose.yml exec backend uv run pytest tests/health_data/test_router.py -k flag_health_value` → 5 passed.
- Verified in Docker: `docker compose -f /Users/vladtara/dev/set-bmad/healthcabinet/docker-compose.yml exec backend uv run pytest` → 155 passed, 2 warnings.
- Verified locally: `uv run ruff check app/health_data/service.py app/health_data/router.py tests/health_data/test_repository.py` → clean.

### Completion Notes List

- **Task 1**: Added `is_flagged` (Boolean, NOT NULL, server_default=false) and `flagged_at` (DateTime, nullable) to `HealthValue` ORM model. Created migration `007_health_values_flagging.py` (down_revision=006) with server_default for safe NOT NULL addition without backfill SQL.
- **Task 2**: Extended `HealthValueRecord` dataclass and `_to_record` with `is_flagged`/`flagged_at`. Added `HealthValueNotFoundError` exception class. Added `flag_health_value()` repository function that updates is_flagged/flagged_at only on first transition (idempotent via `if not row.is_flagged`). Calls `session.refresh(row)` after flush per project rules.
- **Task 3**: Added `FlagValueResponse` Pydantic schema with `id`, `is_flagged`, `flagged_at`. Added `PUT /{health_value_id}/flag` route in router.py. Service catches `HealthValueNotFoundError` and raises HTTP 404 (with `from exc` chaining for B904). Both not-found and forbidden ownership return 404 to avoid ownership leakage.
- **Task 4**: Extended `HealthValueResponse` (health_data/schemas.py) and `HealthValueItem` (documents/schemas.py) with `is_flagged`/`flagged_at`. Updated `documents/service.py` `HealthValueItem` constructor to pass these fields from `HealthValueRecord`.
- **Task 5**: Added `is_flagged: boolean` and `flagged_at: string | null` to `HealthValueItem` in `api.ts`. Added `FlagValueResponse` interface. Created `health-values.ts` with `flagHealthValue()` using `apiFetch<FlagValueResponse>` with PUT method.
- **Task 6**: Extracted `HealthValueRow.svelte` component from the inline value block in `+page.svelte`. Component uses Tailwind `group-hover:opacity-100 group-focus-within:opacity-100` for CSS-only show/hide of flag button (opacity-0 base keeps button keyboard-accessible). Flag button has `min-h-[44px] min-w-[44px]` for touch targets. Flagged badge (`<span>Flagged</span>`) shown persistently when `isFlagged=true`. `aria-live="polite"` region updated with "Thanks — we'll review this value" on success. Removed `confidenceLabel` from `+page.svelte` (moved into component).
- **Task 7**: `flagMutation.onSuccess` calls `queryClient.invalidateQueries` for both `['documents', documentId]` and `['health_values']`. No polling or SSE introduced.
- **Task 8**: 13 new backend tests (5 repository + 8 router): owner-only flagging, 404 for unknown/other-user IDs, idempotent timestamps, no mutation of encrypted values, schema serialization, 401 for unauthenticated requests, `is_flagged`/`flagged_at` in list response.
- **Task 9**: 10 new frontend tests: flag button in DOM (keyboard accessible), keyboard activation, Flagged badge after click, aria-live announcement, value remains visible, pre-flagged value shows badge without button, query key invalidation, API helper snake_case contract, error propagation.
- ✅ Resolved review finding [Patch]: Touch accessibility — replaced `opacity-0` with `@media(hover:hover)` conditional opacity so flag button is visible on touch devices while preserving hover-reveal on desktop.
- ✅ Resolved review finding [Patch]: Race condition — verified `with_for_update()` row lock already prevents concurrent `flagged_at` corruption; no code change needed.
- ✅ Resolved review finding [Patch]: Migration comment now matches the actual single-step `server_default=false` implementation in revision 007.
- ✅ Resolved review finding [Patch]: HealthValueRow flagged state now stays aligned with refetched query props via derived state plus local optimistic state.
- ✅ Resolved review finding [Patch]: Flag mutation now reports failures through the aria-live region instead of failing silently.
- ✅ Resolved review finding [Patch]: Moved the `HealthValueNotFoundError` to HTTP 404 translation from `service.py` into `router.py`, preserving the router -> service -> repository layering.
- ✅ Resolved review finding [Patch]: Replaced the repository test's SQLAlchemy private-attribute assertion with a compiled PostgreSQL SQL assertion for `FOR UPDATE`.
- Full backend regression suite now passes in Docker: 155 tests green.

### Change Log

- 2026-03-25: Implemented Story 2.6 — value flagging. Backend: migration 007, model, repository, service, router, schemas (health_data + documents). Frontend: HealthValueRow component, health-values API helper, types. Tests: 13 backend + 10 frontend new tests.
- 2026-03-25: Addressed 2 code review findings — (1) Fixed touch accessibility: flag button now visible on touch devices via `@media(hover:hover)` conditional opacity. (2) Verified race condition fix: `with_for_update()` row lock already prevents concurrent `flagged_at` corruption.
- 2026-03-25: Addressed final 3 code review findings — aligned migration comment with actual implementation, fixed HealthValueRow refetch/state sync, and added mutation error feedback with regression tests.
- 2026-03-25: Addressed final 2 review-round-2 patch findings — restored service/router layering for not-found handling and replaced the private SQLAlchemy row-lock test assertion with a compiled SQL check; full backend regression re-run passed.

### File List

- healthcabinet/backend/alembic/versions/007_health_values_flagging.py
- healthcabinet/backend/app/health_data/models.py
- healthcabinet/backend/app/health_data/repository.py
- healthcabinet/backend/app/health_data/service.py
- healthcabinet/backend/app/health_data/router.py
- healthcabinet/backend/app/health_data/schemas.py
- healthcabinet/backend/app/documents/schemas.py
- healthcabinet/backend/app/documents/service.py
- healthcabinet/backend/tests/health_data/test_repository.py
- healthcabinet/backend/tests/health_data/test_router.py
- healthcabinet/frontend/src/lib/types/api.ts
- healthcabinet/frontend/src/lib/api/health-values.ts
- healthcabinet/frontend/src/lib/components/health/HealthValueRow.svelte
- healthcabinet/frontend/src/routes/(app)/documents/+page.svelte
- healthcabinet/frontend/src/routes/(app)/documents/page.test.ts
- _bmad-output/implementation-artifacts/2-6-value-flagging.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
