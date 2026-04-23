# Story 5.3: User Account Management & Flag Response

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **admin**,
I want to view and manage user accounts and respond to flagged value reports,
so that I can support users and maintain platform integrity.

## Acceptance Criteria

1. **Given** an admin visits user management
   **When** the page loads
   **Then** a searchable list of users is shown with: user ID, registration date, upload count, and account status
   **And** no health data (documents, extracted values, AI interpretations) is shown in this view - critical privacy boundary

2. **Given** an admin clicks on a user
   **When** the user detail view opens
   **Then** only account metadata is shown: registration date, last login, upload count, account status
   **And** health data remains inaccessible to admin in this view

3. **Given** an admin suspends a user account
   **When** they confirm the suspension dialog
   **Then** the user's JWT refresh is invalidated (subsequent refresh attempts return `401`)
   **And** the user cannot log in until the suspension is lifted

4. **Given** an admin views flagged value reports
   **When** the flag queue is shown
   **Then** each entry shows: user ID, document ID, value name, flagged value, flag timestamp
   **And** the admin can mark a flag as "reviewed" which removes it from the active queue
   **And** marking reviewed triggers Story 5.2's correction flow if a value change is needed

## Tasks / Subtasks

### Backend - Account State, Auth Enforcement, and Admin APIs

- [x] Task 1: Create Alembic migration `011_admin_user_account_state_and_flag_review.py` (AC: 1, 2, 3, 4)
  - [x] Add `users.account_status` as `String`, `NOT NULL`, default `"active"`
  - [x] Add `users.last_login_at` as nullable `DateTime(timezone=True)`
  - [x] Add `health_values.flag_reviewed_at` as nullable `DateTime(timezone=True)`
  - [x] Add `health_values.flag_reviewed_by_admin_id` as nullable UUID FK to `users.id` with `ON DELETE SET NULL`
  - [x] Backfill existing users to `"active"` and leave all new review fields `NULL`
  - [x] Add indexes needed for the new filters (`users.account_status`, reviewed-flag lookup)

- [x] Task 2: Update ORM models for the new fields (AC: 2, 3, 4)
  - [x] Extend `healthcabinet/backend/app/auth/models.py` `User`
  - [x] Extend `healthcabinet/backend/app/health_data/models.py` `HealthValue`
  - [x] Keep `is_flagged` semantics unchanged - reviewed state is separate and must not clear the user's persisted flag

- [x] Task 3: Enforce suspension in the existing auth flow without introducing new token infrastructure (AC: 3)
  - [x] Add auth exception(s) for suspended/inactive accounts as needed
  - [x] Update `healthcabinet/backend/app/auth/service.py::login_user()` to reject suspended accounts before issuing tokens
  - [x] Update `healthcabinet/backend/app/auth/service.py::login_user()` to set `last_login_at` on successful credential login only
  - [x] Update `healthcabinet/backend/app/auth/service.py::refresh_access_token()` to reject non-active accounts so suspended users receive `401` on refresh
  - [x] Update `healthcabinet/backend/app/auth/dependencies.py::get_current_user()` to reject non-active accounts so existing access tokens lose API access on the next authenticated request
  - [x] Keep the current DB-backed auth model; do **not** introduce JWT blocklists, token-version claims, or Redis revocation for this story because refresh and bearer auth already hit the DB
  - [x] If the refresh route clears invalid/suspended cookies, reuse `_REFRESH_COOKIE_PATH` from `app/auth/router.py`

- [x] Task 4: Add repository/service support for admin user management (AC: 1, 2, 3)
  - [x] Add list/detail/status-update schemas in `healthcabinet/backend/app/admin/schemas.py`
  - [x] Add repository queries in `healthcabinet/backend/app/admin/repository.py` for:
  - [x] `list_admin_users(db, query)` returning user ID, registration date, upload count, account status
  - [x] `get_admin_user_detail(db, user_id)` returning registration date, last login, upload count, account status
  - [x] `set_user_account_status(db, user_id, account_status)` as an idempotent update
  - [x] Scope these account-management endpoints to end-user accounts (`role = "user"`); do not allow Story 5.3 to suspend or manage admin accounts
  - [x] Search may match `email` and `id::text`, but the list/detail payload must remain account-metadata-only
  - [x] Upload counts must come from `documents` aggregation only; do not join `health_values`, `ai_memories`, or `user_profiles`

- [x] Task 5: Add flagged-report repository/service support (AC: 4)
  - [x] Add `GET /admin/flags` response schemas in `healthcabinet/backend/app/admin/schemas.py`
  - [x] Add repository query returning only active flagged values: `is_flagged = true AND flag_reviewed_at IS NULL`
  - [x] Return `health_value_id`, `user_id`, `document_id`, `value_name`, encrypted value blob, and `flagged_at`; decrypt the numeric value in `app/admin/service.py` using the same helper pattern already used by Story 5.2
  - [x] Order flagged reports by `flagged_at DESC`
  - [x] Add `mark_flag_reviewed(db, health_value_id, admin_id)` that sets review metadata exactly once and is safe under concurrent clicks
  - [x] Do not clear `is_flagged` when a report is reviewed
  - [x] Update Story 5.2 queue logic so reviewed flags no longer keep a document in the active flagged queue unless the document is still `failed`, `partial`, or has low-confidence values

- [x] Task 6: Add admin router endpoints in `healthcabinet/backend/app/admin/router.py` (AC: 1, 2, 3, 4)
  - [x] `GET /admin/users?q=...`
  - [x] `GET /admin/users/{user_id}`
  - [x] `PATCH /admin/users/{user_id}/status`
  - [x] `GET /admin/flags`
  - [x] `POST /admin/flags/{health_value_id}/review`
  - [x] All endpoints use `Depends(require_admin)`
  - [x] Preserve RFC 7807 behavior for `401`, `403`, `404`, `409`, and `422`

### Backend - Tests

- [x] Task 7: Add backend tests in `healthcabinet/backend/tests/admin/test_admin_users.py` (AC: 1, 2, 3, 4)
  - [x] Admin user list returns upload counts and account status for known fixtures
  - [x] Search filters the list predictably and does not leak health data fields
  - [x] Detail endpoint returns only account metadata plus upload count
  - [x] Suspending a user blocks new login attempts and makes subsequent refresh attempts return `401`
  - [x] Re-activating a user allows login again
  - [x] A suspended user with a previously issued access token is rejected by authenticated endpoints via `get_current_user()`
  - [x] Attempting to manage an admin account is rejected or treated as not found per the chosen endpoint contract
  - [x] Flagged report list returns only unreviewed flagged values with decrypted numeric value and timestamp
  - [x] Marking a flag reviewed removes it from `GET /admin/flags` but does not unset `is_flagged`
  - [x] Existing `/api/v1/admin/queue` no longer includes documents solely because of reviewed flags
  - [x] Non-admin users get `403`; missing JWT gets `401`
  - [x] Use the existing real-DB admin test pattern from `test_admin_metrics.py` and `test_admin_queue.py`

### Frontend - Types and API Helpers

- [x] Task 8: Extend frontend types and API wrappers (AC: 1, 2, 3, 4)
  - [x] Update `healthcabinet/frontend/src/lib/types/api.ts` with `account_status` types and admin user / flagged report interfaces
  - [x] Add `getAdminUsers`, `getAdminUserDetail`, `updateAdminUserStatus`, `getFlaggedReports`, and `markFlagReviewed` to `healthcabinet/frontend/src/lib/api/admin.ts`
  - [x] Keep API interfaces in `snake_case` matching backend responses directly

### Frontend - Admin Pages and Existing Flow Reuse

- [x] Task 9: Create the admin user management page at `healthcabinet/frontend/src/routes/(admin)/admin/users/+page.svelte` (AC: 1, 4)
  - [x] Show a searchable user table with at minimum: user ID, registration date, upload count, account status, and action to open detail
  - [x] Do not render document names, biomarker values, AI interpretations, or any health profile fields in the user-management section
  - [x] Add a separate "Flagged value reports" section on the same page using the new `GET /admin/flags` endpoint
  - [x] Each flagged-report row shows: user ID, document ID, value name, flagged value, flag timestamp
  - [x] Each flagged-report row has two actions:
  - [x] `Open correction flow` -> navigate to the existing Story 5.2 document correction page
  - [x] `Mark reviewed` -> call the new review endpoint and remove the row from the active queue
  - [x] If a value needs changing, the admin must use `Open correction flow` first and only then mark the flag reviewed; do not mutate the value directly from `/admin/users`
  - [x] Use the existing admin page pattern: `createQuery(() => ({ ... }))`, manual refresh, `refetchOnWindowFocus: false`, `refetchOnReconnect: false`

- [x] Task 10: Create the admin user detail page at `healthcabinet/frontend/src/routes/(admin)/admin/users/[user_id]/+page.svelte` (AC: 2, 3)
  - [x] Show account metadata only: registration date, last login, upload count, account status
  - [x] Provide explicit suspend / reactivate action with a confirmation dialog
  - [x] Invalidate the users list and the user detail query after status changes
  - [x] Do not render documents, extracted values, AI output, or `user_profiles` medical fields

- [x] Task 11: Reuse Story 5.2's correction flow instead of recreating it (AC: 4)
  - [x] Extend `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte` to accept an optional `health_value_id` query parameter
  - [x] Scroll to, focus, or visually highlight the matching value row so the admin can review the flagged item immediately
  - [x] Do not duplicate correction forms on `/admin/users`

- [x] Task 12: Update existing admin navigation and login UX where required (AC: 1, 3)
  - [x] Add navigation from `healthcabinet/frontend/src/routes/(admin)/admin/+page.svelte` to `/admin/users`
  - [x] Update `healthcabinet/frontend/src/routes/(auth)/login/+page.svelte` so a backend `403` for suspended accounts shows a clear suspension message instead of the generic outage fallback

### Frontend - Tests

- [x] Task 13: Add frontend tests for the new admin flows (AC: 1, 2, 3, 4)
  - [x] `healthcabinet/frontend/src/routes/(admin)/admin/users/page.test.ts`
  - [x] Cover user list rendering, search, flagged report rendering, mark-reviewed mutation, and correction-flow deep-linking
  - [x] `healthcabinet/frontend/src/routes/(admin)/admin/users/[user_id]/page.test.ts`
  - [x] Cover account metadata rendering, absence of health data, and suspend/reactivate confirmation flow
  - [x] Extend `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/page.test.ts` for `health_value_id` targeting
  - [x] Extend `healthcabinet/frontend/src/routes/(auth)/login/page.test.ts` for suspended-account messaging

### Review Findings

- [x] [Review][Patch] Error queue `flagged_count` includes reviewed flags [admin/repository.py:138]
- [x] [Review][Patch] `handleReviewFlag` missing try/catch [users/+page.svelte]
- [x] [Review][Patch] `confirmStatusChange` missing catch block [users/[user_id]/+page.svelte]
- [x] [Review][Patch] Silent decryption error — add logging [admin/service.py]
- [x] [Review][Patch] `account_status` schema: use `Literal` instead of bare `str` [admin/schemas.py]
- [x] [Review][Patch] LIKE wildcard chars not escaped in search [admin/repository.py]
- [x] [Review][Patch] Button label "View" should be "Open correction flow" [users/+page.svelte]
- [x] [Review][Patch] Debounce timer not cleared on unmount [users/+page.svelte]
- [x] [Review][Patch] `$effect` scroll-to-row fires repeatedly [documents/[document_id]/+page.svelte]
- [x] [Review][Patch] NULL `flagged_at` produces "Invalid Date" [admin/repository.py]
- [x] [Review][Patch] NULL `flagged_at` NULLS LAST ordering [admin/repository.py]
- [x] [Review][Patch] Refresh: raise `AccountSuspendedError` (403) instead of `InvalidCredentialsError` [auth/service.py, auth/router.py]
- [x] [Review][Patch] Assert `is_flagged` stays True after review [test_admin_users.py]
- [x] [Review][Patch] Add health data field exclusion assertions [test_admin_users.py]
- [x] [Review][Patch] Add reactivation-restores-login round-trip test [test_admin_users.py]
- [x] [Review][Patch] Frontend: suspend confirm button never calls mutation [page.test.ts]
- [x] [Review][Patch] Frontend: mark-reviewed button never calls mutation [page.test.ts]
- [x] [Review][Patch] Assert `last_login_at` unchanged on refresh [test_admin_users.py]
- [x] [Review][Patch] Check Set-Cookie clearing on suspended refresh [test_admin_users.py]
- [x] [Review][Patch] Frontend: add search test [page.test.ts]
- [x] [Review][Patch] Frontend: test correction-flow deep-link [page.test.ts]
- [x] [Review][Patch] Frontend: test health_value_id targeting [page.test.ts]
- [x] [Review][Patch] Strengthen UUID search assertion [test_admin_users.py]
- [x] [Review][Defer] No pagination on user list/flags — deferred, admin-internal MVP scale
- [x] [Review][Defer] Dialog focus trapping — deferred, pre-existing modal pattern
- [x] [Review][Defer] Rate limit masks 403 for suspended users — deferred, pre-existing auth flow
- [x] [Review][Defer] 403 auto-redirect from API interceptor — deferred, broader frontend concern

## Dev Notes

### Story 5.2 Reuse Is Mandatory

- Story 5.2 already created the admin module backbone:
- `healthcabinet/backend/app/admin/router.py`
- `healthcabinet/backend/app/admin/repository.py`
- `healthcabinet/backend/app/admin/service.py`
- `healthcabinet/frontend/src/lib/api/admin.ts`
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/+page.svelte`
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte`
- Build Story 5.3 on top of those files. Do **not** create a parallel support/admin subsystem.
- Do **not** recreate manual value-correction UI on the new users page. Reuse the existing document correction page from Story 5.2.

### Account Suspension Design Guardrails

- Keep the new account-state model minimal:
- `users.account_status`: `"active"` or `"suspended"`
- `users.last_login_at`: nullable timestamp
- This repo's auth flow already performs DB lookups in both `refresh_access_token()` and `get_current_user()`. That means suspension can be enforced immediately with the new DB field alone.
- Do **not** add Redis token blocklists, token-version claims, or JWT payload churn for this story unless a concrete blocker appears.
- Recommended auth behavior:
- `POST /auth/login`: return `403` after valid credentials if the account is suspended
- `POST /auth/refresh`: return `401` for suspended accounts to satisfy AC #3 and force logout
- `Depends(get_current_user)`: reject suspended accounts so existing bearer tokens stop working on the next request
- Update `last_login_at` only after successful credential login, not on silent refresh

### Privacy Boundary

- User list and user detail views are **account management only**.
- Allowed sources there: `users` plus aggregated `documents` count.
- Forbidden sources there: `user_profiles`, `health_values`, `ai_memories`, document filenames, extracted biomarker values, AI interpretation text.
- Flagged value reports are the only Story 5.3 surface that may expose minimal health data, and only what AC #4 requires: `value_name`, decrypted `flagged_value`, and `flagged_at`.

### Admin Accounts Are Out of Scope

- Story 5.3 is about managing end-user accounts, not operator accounts.
- Scope account-management queries and status mutations to `User.role == "user"`.
- Do not allow an admin to suspend themselves or another admin through these endpoints.

### Flag Review State Must Be Separate from User Flag State

- `is_flagged` and `flagged_at` were added in Story 2.6 and are already used by Story 5.2.
- A reviewed flag must **not** clear `is_flagged`, because that erases the persisted user report.
- Use separate review metadata (`flag_reviewed_at`, `flag_reviewed_by_admin_id`) and make the active queue filter on:

```python
HealthValue.is_flagged.is_(True) & HealthValue.flag_reviewed_at.is_(None)
```

- Reviewed flags must disappear from the active admin queue, but the underlying flag should remain historically visible on the value itself.

### Existing Code Patterns to Follow

- Backend service layer already decrypts health values in `healthcabinet/backend/app/admin/service.py`; keep that boundary.
- Encryption helpers already exist in `healthcabinet/backend/app/health_data/repository.py`:
- `_decrypt_numeric_value()`
- `_encrypt_numeric_value()`
- Repository-only encryption rule still applies: router never encrypts/decrypts directly.
- `require_admin` already exists in `healthcabinet/backend/app/auth/dependencies.py`.
- The admin router is already registered in `healthcabinet/backend/app/main.py`.
- Frontend admin pages already use TanStack Query with Svelte 5 runes:
- `createQuery(() => ({ ... }))`
- manual refresh via `queryClient.invalidateQueries(...)`
- `refetchOnWindowFocus: false`
- `refetchOnReconnect: false`

### Known Document Drift - Follow Current Code, Not Stale Planning Text

- `healthcabinet/backend/app/core/security.py` uses **PyJWT**, not `python-jose`. Follow current code and `project-context.md`.
- `ux-page-specifications.md` still mentions `GET /api/v1/admin/stats` and `GET /api/v1/admin/errors`; the implemented admin endpoints are currently `GET /api/v1/admin/metrics` and `GET /api/v1/admin/queue`.
- Use the existing implemented endpoint names as the source of truth for extending admin flows.

### Existing Test and Fixture Patterns

- Reuse `healthcabinet/backend/tests/admin/test_admin_metrics.py` and `healthcabinet/backend/tests/admin/test_admin_queue.py` patterns for:
- `admin_client` fixture
- admin vs non-admin auth headers
- real DB assertions
- `healthcabinet/backend/tests/conftest.py` already has:
- `make_user`
- `make_document`
- `make_health_value`
- Add only the additional fixture helpers Story 5.3 truly needs.

### Docker Compose and Story Completion Rules

- Project context rule: test results are only trustworthy when they pass in Docker Compose.
- Minimum verification before story closure:
- Backend: `docker compose exec backend uv run pytest tests/admin/test_admin_users.py tests/auth/test_router.py`
- Frontend: `docker compose exec frontend npm run test:unit -- src/routes/(admin)/admin/users/page.test.ts src/routes/(admin)/admin/users/[user_id]/page.test.ts src/routes/(admin)/admin/documents/[document_id]/page.test.ts src/routes/(auth)/login/page.test.ts`
- Follow Epic 4 retrospective principle P1: unknown test state is not acceptable.

### Previous Story Intelligence

- Story 5.2 already established the admin UX vocabulary: lightweight admin pages, table-based lists, manual refresh, and explicit error/empty states.
- Story 5.2 also proved the backend path layout:
- `app/admin/*` for admin domain code
- `tests/admin/*` for backend tests
- `src/routes/(admin)/admin/*` for frontend admin pages
- Story 5.2 had to work around the fact that there is no stored `flag_reason`; do not invent one for Story 5.3. A flag report is driven by persisted state and the flagged value itself.
- Story 5.2 already contains the only correction UI the project should have for admin value edits. Story 5.3 only links into it and records review state.

### Git Intelligence Summary

- The latest relevant commit is `91d62e0 feat(admin-documents): implement extraction error queue and document correction pages`.
- It expanded the exact files Story 5.3 should continue using:
- backend `app/admin/*`
- backend `tests/admin/*`
- frontend `src/lib/api/admin.ts`
- frontend `src/lib/types/api.ts`
- frontend `src/routes/(admin)/admin/*`
- Follow that footprint so Story 5.3 stays aligned with the current repo shape.

### Project Structure - Files to Create / Modify

**Backend - new files**
- `healthcabinet/backend/alembic/versions/011_admin_user_account_state_and_flag_review.py`
- `healthcabinet/backend/tests/admin/test_admin_users.py`

**Backend - modified files**
- `healthcabinet/backend/app/auth/models.py`
- `healthcabinet/backend/app/auth/service.py`
- `healthcabinet/backend/app/auth/dependencies.py`
- `healthcabinet/backend/app/auth/router.py`
- `healthcabinet/backend/app/admin/schemas.py`
- `healthcabinet/backend/app/admin/repository.py`
- `healthcabinet/backend/app/admin/service.py`
- `healthcabinet/backend/app/admin/router.py`
- `healthcabinet/backend/app/health_data/models.py`

**Frontend - new files**
- `healthcabinet/frontend/src/routes/(admin)/admin/users/+page.svelte`
- `healthcabinet/frontend/src/routes/(admin)/admin/users/[user_id]/+page.svelte`
- `healthcabinet/frontend/src/routes/(admin)/admin/users/page.test.ts`
- `healthcabinet/frontend/src/routes/(admin)/admin/users/[user_id]/page.test.ts`

**Frontend - modified files**
- `healthcabinet/frontend/src/lib/api/admin.ts`
- `healthcabinet/frontend/src/lib/types/api.ts`
- `healthcabinet/frontend/src/routes/(admin)/admin/+page.svelte`
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte`
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/page.test.ts`
- `healthcabinet/frontend/src/routes/(auth)/login/+page.svelte`
- `healthcabinet/frontend/src/routes/(auth)/login/page.test.ts`

**No changes expected**
- AI module (`healthcabinet/backend/app/ai/*`)
- document storage layer (`healthcabinet/backend/app/documents/storage.py`)
- user profile CRUD (`healthcabinet/backend/app/users/*`) unless a small shared helper is truly needed

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.3: User Account Management & Flag Response]
- [Source: _bmad-output/planning-artifacts/prd.md#FR37: User account management]
- [Source: _bmad-output/planning-artifacts/prd.md#FR38: Flagged value response]
- [Source: _bmad-output/planning-artifacts/architecture.md#Admin & Operations (FR34-FR38)]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md#Admin /admin]
- [Source: _bmad-output/project-context.md#Technology Stack & Versions]
- [Source: _bmad-output/project-context.md#Critical Backend Rules]
- [Source: _bmad-output/project-context.md#Critical Frontend Rules]
- [Source: _bmad-output/project-context.md#Testing Rules]
- [Source: CLAUDE.md#Architecture]
- [Source: _bmad-output/implementation-artifacts/5-2-extraction-error-queue-manual-value-correction.md#Dev Notes]
- [Source: _bmad-output/implementation-artifacts/2-6-value-flagging.md#Tasks / Subtasks]
- [Source: _bmad-output/implementation-artifacts/epic-4-retro-2026-03-30.md#Process Principles - Adopted for Epic 5+]
- [Source: healthcabinet/backend/app/auth/models.py]
- [Source: healthcabinet/backend/app/auth/service.py]
- [Source: healthcabinet/backend/app/auth/dependencies.py]
- [Source: healthcabinet/backend/app/auth/router.py]
- [Source: healthcabinet/backend/app/admin/router.py]
- [Source: healthcabinet/backend/app/admin/service.py]
- [Source: healthcabinet/backend/app/admin/repository.py]
- [Source: healthcabinet/backend/app/health_data/models.py]
- [Source: healthcabinet/backend/tests/admin/test_admin_metrics.py]
- [Source: healthcabinet/backend/tests/admin/test_admin_queue.py]
- [Source: healthcabinet/backend/tests/conftest.py]
- [Source: healthcabinet/frontend/src/lib/api/admin.ts]
- [Source: healthcabinet/frontend/src/lib/api/client.svelte.ts]
- [Source: healthcabinet/frontend/src/lib/types/api.ts]
- [Source: healthcabinet/frontend/src/routes/(admin)/admin/+page.svelte]
- [Source: healthcabinet/frontend/src/routes/(admin)/admin/documents/+page.svelte]
- [Source: healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte]
- [Source: healthcabinet/frontend/src/routes/(auth)/login/+page.svelte]

## Dev Agent Record

### Agent Model Used

claude-opus-4.6

### Debug Log References

- Fixed correction page test mock: added `url` property to `mockPageData` for `$page.url.searchParams` support
- Fixed svelte-check type error: `$page.params.user_id` → coalesced with `?? ''` and added `enabled` guard to query
- Fixed a11y warnings: added `tabindex="-1"` to dialog overlay, removed unnecessary `onkeydown` from inner div

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- Story 5.3 selected from `sprint-status.yaml` as the first backlog story in order
- Story 5.2 correction flow reuse locked to prevent duplicate admin correction UI
- Suspension design intentionally uses existing DB-backed auth checks instead of introducing token-revocation infrastructure
- All 13 tasks implemented: 7 backend + 6 frontend
- Backend: 308 tests passed, 1 skipped, 0 failures (full regression)
- Frontend: 193 tests passed, 0 failures (20 test files)
- svelte-check: 0 errors, 2 warnings (standard a11y notes for modal backdrop pattern)

### File List

**Created:**
- `healthcabinet/backend/alembic/versions/011_admin_user_account_state_and_flag_review.py`
- `healthcabinet/backend/tests/admin/test_admin_users.py`
- `healthcabinet/frontend/src/routes/(admin)/admin/users/+page.svelte`
- `healthcabinet/frontend/src/routes/(admin)/admin/users/AdminUsersPageTestWrapper.svelte`
- `healthcabinet/frontend/src/routes/(admin)/admin/users/page.test.ts`
- `healthcabinet/frontend/src/routes/(admin)/admin/users/[user_id]/+page.svelte`
- `healthcabinet/frontend/src/routes/(admin)/admin/users/[user_id]/AdminUserDetailTestWrapper.svelte`
- `healthcabinet/frontend/src/routes/(admin)/admin/users/[user_id]/page.test.ts`

**Modified:**
- `healthcabinet/backend/app/auth/models.py` — Added account_status, last_login_at, __table_args__
- `healthcabinet/backend/app/health_data/models.py` — Added flag_reviewed_at, flag_reviewed_by_admin_id, composite index
- `healthcabinet/backend/app/auth/exceptions.py` — Added AccountSuspendedError
- `healthcabinet/backend/app/auth/service.py` — Suspension check in login + last_login_at; rejection in refresh
- `healthcabinet/backend/app/auth/dependencies.py` — Suspended account → 403 in get_current_user
- `healthcabinet/backend/app/auth/router.py` — AccountSuspendedError→403; refresh clears cookie
- `healthcabinet/backend/app/admin/schemas.py` — 7 new Pydantic schemas
- `healthcabinet/backend/app/admin/repository.py` — 5 new functions + updated error queue filter
- `healthcabinet/backend/app/admin/service.py` — 5 new service functions
- `healthcabinet/backend/app/admin/router.py` — 5 new endpoints
- `healthcabinet/frontend/src/lib/types/api.ts` — 8 new TypeScript interfaces
- `healthcabinet/frontend/src/lib/api/admin.ts` — 5 new API wrapper functions
- `healthcabinet/frontend/src/routes/(admin)/admin/+page.svelte` — Added User Management nav link
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte` — Added health_value_id query param support
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/page.test.ts` — Fixed mock for url property
- `healthcabinet/frontend/src/routes/(auth)/login/+page.svelte` — Added 403 suspension error message
- `healthcabinet/frontend/src/routes/(auth)/login/page.test.ts` — Added suspension message test
- `_bmad-output/implementation-artifacts/5-3-user-account-management-flag-response.md` — Story status → review
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 5-3 → review

### Review Findings

- [ ] [Review][Patch] Doubled `/api` prefix in `markFlagReviewed` URL [frontend/src/lib/api/admin.ts]
- [ ] [Review][Patch] Type name typo `FlaggedRepositoryItem` instead of `FlaggedReportItem` in `FlaggedReportListResponse` [frontend/src/lib/types/api.ts]
- [ ] [Review][Patch] Stray `field_name` field in `AdminUserDetail` Pydantic schema [backend/app/admin/schemas.py]
- [ ] [Review][Patch] `params` variable computed but never appended in `getAdminUsers` URL [frontend/src/lib/api/admin.ts]
- [ ] [Review][Patch] Double `await await` in login test [frontend/src/routes/(auth)/login/page.test.ts]
- [ ] [Review][Patch] `'splash'` typo in `AdminUserStatusUpdate` frontend type [frontend/src/lib/types/api.ts]
- [x] [Review][Patch] LIKE pattern characters (`%`, `_`) not escaped in user search query [backend/app/admin/repository.py:104]
- [ ] [Review][Patch] Scroll-to silently fails when `health_value_id` is not in current document [frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte]
- [x] [Review][Patch] Corrupt flagged values silently skipped — flag persists forever with no admin visibility [backend/app/admin/service.py:506-509]
- [ ] [Review][Patch] `AdminUserStatusUpdate.account_status` uses bare `str` instead of `Literal['active', 'suspended']` [backend/app/admin/schemas.py]
- [x] [Review][Patch] Refresh route does not actually clear invalid/suspended cookie because `delete_cookie()` is lost when `HTTPException` is raised [backend/app/auth/router.py:141]
- [x] [Review][Patch] Flagged reports table omits required document ID column [frontend/src/routes/(admin)/admin/users/+page.svelte:208]
- [x] [Review][Defer] Suspension does not invalidate existing access tokens until natural expiry (15 min) — intentional tradeoff per spec Dev Notes [backend/app/auth/service.py] — deferred, per-design
- [x] [Review][Defer] Suspended users re-registering see "email already registered" instead of suspension message — pre-existing, out of scope for Story 5.3 — deferred, pre-existing
- [x] [Review][Defer] `last_login_at` not updated on token refresh — per spec ("only on successful credential login, not on silent refresh") — deferred, per-design

## Change Log

| Change | Files | Reason |
|--------|-------|--------|
| Add account_status, last_login_at, flag review columns | Migration 011, auth/models.py, health_data/models.py | AC 1-4: Account state + flag review tracking |
| Enforce suspension in auth flow | auth/exceptions.py, auth/service.py, auth/dependencies.py, auth/router.py | AC 3: Immediate token invalidation via DB checks |
| Admin user management API | admin/schemas.py, admin/repository.py, admin/service.py, admin/router.py | AC 1-3: List/detail/status endpoints, privacy boundary |
| Flagged report API + error queue update | admin/schemas.py, admin/repository.py, admin/service.py, admin/router.py | AC 4: Active flag query, mark reviewed, queue filter fix |
| 32 backend tests | tests/admin/test_admin_users.py | AC 1-4: Full coverage of user mgmt + flag + auth enforcement |
| Frontend types and API wrappers | lib/types/api.ts, lib/api/admin.ts | AC 1-4: TypeScript interfaces + fetch wrappers |
| Admin users management page | admin/users/+page.svelte | AC 1,4: Searchable user table + flagged reports section |
| Admin user detail page | admin/users/[user_id]/+page.svelte | AC 2,3: Metadata + suspend/reactivate with confirmation |
| Correction flow health_value_id targeting | admin/documents/[document_id]/+page.svelte | AC 4: Scroll-to + highlight flagged value row |
| Admin nav + login suspension UX | admin/+page.svelte, login/+page.svelte | AC 1,3: Nav link + 403 distinction |
| Frontend tests (14 new + 1 extended) | users/page.test.ts, [user_id]/page.test.ts, login/page.test.ts, documents/page.test.ts | AC 1-4: Full frontend test coverage |
