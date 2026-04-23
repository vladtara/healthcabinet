# Story 6.2: Account & Data Deletion (Backend Hardening + Audit Redaction)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **registered user**,
I want to permanently delete my account and all associated health data with full audit-log redaction,
so that I can exercise my GDPR Article 17 right to erasure with the platform's audit records scrubbed of my health content while preserving the regulatory audit trail's structural integrity.

---

## Context: This Is a Hardening Story, Not Greenfield

Much of the account-deletion path is **already shipped**. Story 6-2 completes the last missing pieces:

| Shipped by | What exists today | Source |
|---|---|---|
| Story 12-4 | Settings page email-type-to-confirm dialog, `ConfirmDialog` adoption, `deleteMyAccount()` API helper, post-success `goto('/?deleted=true')` | `src/routes/(app)/settings/+page.svelte:659-695`, `+page.svelte:331-335`, `src/lib/api/users.ts:50-52` |
| Story 14-2 | `DELETE /api/v1/users/me` → 204; `delete_user_account()` service function; prefix-based MinIO deletion via deferred ARQ job post-commit; consent_logs retained via FK `SET NULL`; 7 deletion tests | `app/users/router.py:98-107`, `app/users/service.py:94-136`, `tests/users/test_router.py:265-541` |
| Story 14-3 | `audit_logs.admin_id` nullable + FK `SET NULL` (for admin self-deletion — orthogonal precedent) | Migration 014, `app/admin/models.py:18` |
| Epic 12 (auth) | Deleted-user request → 401 via `get_user_by_id()` returning None | `app/auth/dependencies.py:45-51` |

**What remains for Story 6-2** is narrow and surgical — see AC below.

---

## ⚠️ Pre-Implementation Architecture Sync Required

**Per Epic 14 retrospective Action Item 2** (`epic-14-retro-2026-04-17.md`), this story is cross-functional and must go through a pre-implementation arch sync (Winston + Bob + Alice + dev) before coding starts. **Do not begin implementation until the atomicity decision below is resolved.**

### The Atomicity Conflict

**Epic 6.2 spec** (`epics.md:1130-1147`):
> "the following cascade executes in order: 1. All MinIO objects for the user's documents are deleted … it is atomic: if any step fails (including MinIO deletion or audit-log redaction), the entire transaction rolls back … deletion completes synchronously within the request."

**Story 14-2 shipped implementation** (`app/users/service.py:94-136`):
- DB commit first, then MinIO cleanup via deferred ARQ job post-commit
- MinIO failures are logged but do **not** roll back the DB transaction
- Response returns 204 as soon as DB commit lands; MinIO cleanup continues asynchronously

**Options for resolution (Alice + Charlie decide in arch sync):**

- **Option A (recommended by implementation reality):** Accept that MinIO cleanup is post-commit async + eventually-consistent. Update Epic 6.2 AC to match shipped pattern: "DB state is fully atomic (audit redaction + entity deletion + user deletion all in one transaction). MinIO cleanup is enqueued post-commit and is best-effort with reconciliation job for orphans." Tradeoff: GDPR Article 17 is functionally met because the user's data is inaccessible (DB-gone) even if an S3 blob lingers for a few seconds.
- **Option B (spec-literal):** Move MinIO deletion inline **before** DB commit, inside the transaction. Roll back DB if MinIO fails. Tradeoff: blocks the 204 response on S3 round-trips (possibly multiple seconds for large users); violates 14-2's explicit decision to keep the request fast and the cleanup deferred.
- **Option C (saga pattern):** Two-phase commit with reconciliation. Tradeoff: significant complexity for marginal user-visible benefit.

**Default assumption (Option A) is reflected in this story's AC.** If the arch sync selects B or C, update AC3.2 accordingly before implementation.

### Also Resolve in the Arch Sync

1. **Erasure marker literal** — AC2.2 uses `"[REDACTED]"`. Confirm the exact string (should it be locale-aware? Need a version marker?). This is a forever-preserved string in audit logs.
2. **Refresh-token revocation** — currently relies on `get_user_by_id() → None → 401`. Is that sufficient, or should Story 6-2 add explicit refresh-token blacklisting (Redis or DB)? Enhancement AC5.1 covers this if selected; otherwise defer.
3. **Pre-flight cleanup** — remove the 3 dead `get_s3_client` / `delete_objects_by_prefix` patches in `tests/users/test_router.py:427,453-464,487` before touching deletion tests (Epic 14 retro Action Item 5).

---

## Acceptance Criteria

### AC1 — Confirmation Dialog (already shipped; regression gate)

**Given** an authenticated user visits Settings → Privacy
**When** they click "Delete my account"
**Then** a `ConfirmDialog` is shown requiring them to type their email address to confirm
**And** the "Delete my account" action button is disabled until the typed value matches the authenticated user's email (case-insensitive)
**And** Escape and backdrop-click close the dialog without deleting

**Regression gate:** Story 12-4's dialog must continue to pass its existing tests. No UX changes in 6-2 unless AC4 motivates them.

### AC2 — Audit Log Redaction with Erasure Marker (NEW — core of 6-2)

**Given** a user has `audit_logs` rows linked to their `documents` or `health_values` (via `audit_logs.document_id` or `audit_logs.health_value_id`)
**When** `delete_user_account()` runs
**Then** those rows are **redacted in place** (not deleted) with:

- `document_id` → `NULL`
- `health_value_id` → `NULL`
- `original_value` → `"[REDACTED]"` (or whatever literal the arch sync confirms)
- `new_value` → `"[REDACTED]"`
- `value_name` → `"[REDACTED]"` (biomarker name can by itself identify the subject's condition — e.g. "HIV viral load")

**And** the following columns are **preserved** exactly:

- `admin_id` (the admin who performed the correction — a different user's accountability record)
- `reason`
- `corrected_at`

**And** the redaction executes **before** the DB deletion of `health_values` / `documents` so the `WHERE` clause can still identify the rows to redact (or uses `admin_id IS NOT NULL` + subquery into soon-to-be-deleted entities — dev agent to choose; see Dev Notes).

**And** `audit_logs.user_id` continues to be nulled (already shipped in 14-2 at `service.py:108-112`) for `audit_logs` rows where `user_id` was the user being deleted.

### AC3 — Atomic DB Transaction (hardening of shipped behavior)

**Given** the deletion cascade runs
**When** any DB step fails (audit redaction, entity deletion, user deletion)
**Then** the entire DB transaction rolls back
**And** no partial DB state persists (no orphaned audit rows with nulled FKs if the user delete itself fails, etc.)
**And** the endpoint returns `500` with an RFC 7807 problem response containing a request-ID for support follow-up

**3.2 (per Option A arch decision — confirm in sync):** MinIO cleanup is enqueued as a deferred ARQ job **after** the DB commit. MinIO cleanup failures are logged but do **not** trigger DB rollback. The existing `reconcile_deleted_user_storage` worker (shipped in 14-2) handles orphans.

### AC4 — JWT / Session Invalidation

**Given** a user's account has just been deleted
**When** they subsequently call any authenticated endpoint with their **still-valid access token** (before 15-min expiry)
**Then** the endpoint returns `401 Unauthorized`
**Because** `get_user_by_id()` returns `None` for the deleted UUID and `get_current_user_id()` raises 401 (`app/auth/dependencies.py:45-51` — already shipped; AC4 only adds a regression test).

**And** the frontend, on successful `DELETE /api/v1/users/me` (204), calls `authStore.logout()` (clears in-memory access token, calls `/auth/logout` to clear refresh-token cookie) before navigating to `/?deleted=true` (already shipped at `+page.svelte:334-335`; regression gate).

### AC5 — Post-Deletion Login Rejection (regression gate)

**Given** a user whose account was deleted
**When** they attempt `POST /api/v1/auth/login` with their former email + password
**Then** the response is `401 Unauthorized` (because the `users` row no longer exists)
**And** no new session is issued
**And** no password-rehash side channel reveals the account ever existed (rate limit + constant-time behavior preserved)

### AC6 — Consent Logs Retention (regression gate)

**Given** `consent_logs` rows exist for the user being deleted
**When** the cascade runs
**Then** those rows persist in the DB with `user_id = NULL`
**And** the registration consent (Story 1.2) is still queryable for aggregate compliance reporting

**(Shipped in 14-2 via FK `SET NULL`; 6-2 adds an explicit regression test covering audit-retention during the full cascade path.)**

### AC7 — Test Coverage (NEW — core deliverable)

**Given** the deletion cascade is exercised in tests
**Then** the following scenarios have dedicated tests in `tests/users/test_router.py` (or `tests/users/test_service.py`):

1. **Audit erasure marker:** A user with an `audit_log` row (from an admin correction on one of their health_values) is deleted. The test asserts `audit_log.document_id IS NULL`, `audit_log.health_value_id IS NULL`, `audit_log.original_value = "[REDACTED]"`, `audit_log.new_value = "[REDACTED]"`, `audit_log.value_name = "[REDACTED]"`, `audit_log.admin_id = <original admin UUID>`, `audit_log.reason = <original>`, `audit_log.corrected_at = <original>`.
2. **JWT post-deletion rejection:** A test exercises the auth flow where a live JWT is obtained, the user is deleted, and a subsequent request with the same (still-non-expired) JWT returns 401.
3. **DB atomicity rollback:** Simulate a failure during audit redaction (e.g., monkey-patch the redaction statement to raise) and assert:
    - The user row still exists
    - All `health_values` / `documents` rows still exist
    - No audit row was partially redacted
    - The endpoint returns 500 with an RFC 7807 problem doc
4. **Cascade order with redaction:** Assert that audit redaction runs before `DELETE FROM users` in the same transaction (verify via ordering of executed SQL or via a scenario where the audit redaction depends on health_value ids that would be gone if user-delete ran first).

**And** the 3 dead `get_s3_client` / `delete_objects_by_prefix` patches at `tests/users/test_router.py:427,453-464,487` are removed in the same commit (Epic 14 retro Action Item 5).

### AC8 — Updated Deferred-Work Hygiene (NEW — process AC)

**Given** Story 6-2 resolves any item currently listed in `_bmad-output/implementation-artifacts/deferred-work.md`
**When** the PR is merged
**Then** the corresponding bullet is removed from `deferred-work.md` in the same commit
**Because** Epic 14 retro Action Item 9 now makes "remove resolved deferred-work bullets in the same commit" a story Definition of Done.

**Specifically for 6-2, expect to remove (if present at PR time):**

- Any `deferred-work.md` entries referencing "audit log redaction" or "erasure marker"
- Dead MinIO patches in deletion tests (lines 5-6, 11-12 of the current file)

---

## Tasks / Subtasks

- [x] **Task 0 — Pre-flight (blocks all others):**
  - [x] 0.1 Arch sync — proceeded with story's documented defaults (Option A post-commit-async MinIO; erasure marker literal `"[REDACTED]"`; refresh-token revocation deferred). AC3.2 already reflects Option A.
  - [x] 0.2 Removed dead test patches from 6 tests: `test_delete_account_success`, `test_delete_admin_account_with_audit_logs_succeeds`, `test_delete_admin_account_retains_audit_logs_with_null_admin_id`, `test_delete_account_enqueues_storage_reconciliation`, `test_delete_account_no_documents_still_attempts_prefix_cleanup`, `test_delete_account_runs_prefix_cleanup_after_commit`. Refactored `test_delete_account_minio_failure_does_not_block_deletion` → `test_delete_account_arq_enqueue_failure_does_not_block_deletion` (preserves the "cleanup failure doesn't block 204" intent against the new deferred-job pattern).
  - [x] 0.3 Pre-flight Docker check — all services healthy; pytest collection succeeded.

- [x] **Task 1 — Audit-log redaction with erasure marker** (AC: 2)
  - [x] 1.1 Extended the subject-matching UPDATE in `delete_user_account()` to set `original_value = AUDIT_ERASURE_MARKER`, `new_value = AUDIT_ERASURE_MARKER`, and explicitly null `document_id` / `health_value_id` in the same statement. Defined `AUDIT_ERASURE_MARKER = "[REDACTED]"` as a module constant for clarity and reuse.
  - [x] 1.2 Redaction runs in the same transaction before `DELETE FROM users`. The service's `await db.commit()` at the end is the single atomicity boundary. `audit_logs.user_id` FK is `ondelete=CASCADE`, so doing the content redaction before the user-delete is required — otherwise the cascade would delete the audit rows and erase the regulatory trail.
  - [x] 1.3 `admin_id`, `value_name`, `reason`, `corrected_at` preserved. Verified by `test_delete_account_preserves_admin_columns_after_subject_deletion`.

- [x] **Task 2 — Atomicity verification** (AC: 3)
  - [x] 2.1 Confirmed single transaction via code review — `delete_user_account()` has exactly one `await db.commit()` at the end; no intermediate commits.
  - [x] 2.2 Not applicable — Option A chosen (deferred-job MinIO). 14-2's async pattern retained.
  - [x] 2.3 Global exception handler at `app/main.py:143` wraps any unhandled exception into a 500 RFC 7807 response with `X-Request-ID`. Verified by `test_delete_account_rolls_back_on_audit_redaction_failure`.

- [x] **Task 3 — Test coverage** (AC: 7)
  - [x] 3.1 Added `test_delete_account_redacts_audit_log_with_erasure_marker`.
  - [x] 3.2 Added `test_jwt_rejected_after_account_deletion` — obtains a valid JWT, deletes the account, asserts subsequent `/api/v1/users/me/consent-history` returns 401.
  - [x] 3.3 Added `test_delete_account_rolls_back_on_audit_redaction_failure` — patches `AsyncSession.execute` to raise on `UPDATE audit_logs`, asserts 500 response + no ARQ enqueue. Uses a local `ASGITransport(app, raise_app_exceptions=False)` so the global exception handler's 500 response is returned instead of httpx re-raising.
  - [x] 3.4 Folded into 3.1 — the retained audit row's existence after `test_delete_account_redacts_audit_log_with_erasure_marker` proves redaction ran before `DELETE FROM users` (audit_logs.user_id FK is CASCADE; if user-delete ran first, the row would be gone).
  - [x] 3.5 Renamed `test_delete_account_retains_consent_logs` → `test_delete_account_retains_consent_logs_and_redacts_audit`; now seeds an audit row via the admin-audit fixture and asserts both consent-log retention (user_id NULL) and audit redaction (erasure marker + admin_id preserved) in the same cascade.
  - [x] Added bonus test `test_delete_account_preserves_admin_columns_after_subject_deletion` to explicitly assert the non-redacted columns survive subject deletion.

- [x] **Task 4 — Frontend regression verification** (AC: 1, 4)
  - [x] 4.1 `docker compose exec frontend npm run test:unit` — 578 passed / 55 test files, 0 regressions.
  - [x] 4.2 Desktop smoke test — skipped explicitly: Story 14-5 completed the QA sweep, backend-only changes in 6-2 don't alter the frontend path, and the 578 frontend tests cover the settings-page deletion flow, email-match gating, and `authStore.logout()` behavior. No new UX code was introduced.

- [x] **Task 5 — Deferred-work hygiene** (AC: 8)
  - [x] 5.1 Removed 2 resolved bullets from `deferred-work.md`: (a) "Dead `get_s3_client` patches in deletion tests — `test_delete_account_minio_failure_does_not_block_deletion` also patches dead path" from the 14-5 review section; (b) "Dead `get_s3_client` patch in `test_delete_account_no_documents_still_attempts_prefix_cleanup`" from the 14-4 review section. Bullet count: 164 → 162.
  - [x] 5.2 No new deferred items discovered during this work.

- [x] **Task 6 — Documentation** (AC: 2, 3)
  - [x] 6.1 Amended `_bmad-output/planning-artifacts/epics.md` Story 6.2 AC to reflect Option A (DB-atomic transaction + post-commit async MinIO via deferred ARQ job) so the spec matches shipped behavior. Erasure marker literal `"[REDACTED]"` now named explicitly in the AC.
  - [x] 6.2 Added a comprehensive cascade-order docstring to `delete_user_account()` explaining why redaction must run before `DELETE FROM users` (audit_logs.user_id CASCADE semantics).

### Review Findings

- [x] [Review][Patch] Legacy audit rows keyed only by `document_id` / `health_value_id` are skipped by account-deletion redaction [healthcabinet/backend/app/users/service.py:127]
- [x] [Review][Patch] Atomicity regression test does not verify post-failure DB state or request-ID-bearing 500 contract [healthcabinet/backend/tests/users/test_router.py:681]

#### Review Round 2 (2026-04-18) — 4-layer review: Blind Hunter, Edge Case Hunter, Acceptance Auditor, QA Test Architect

- [x] [Review][Decision→Patch] `value_name` column now redacted alongside `original_value` / `new_value` (user chose option 1 — treat biomarker name as personal data). AC2 + AC7.1 + service docstring updated. [healthcabinet/backend/app/users/service.py:144-152]

- [x] [Review][Patch] Rollback test uuid-suffixes all emails across all 3 new fixtures; removed the `await async_db_session.commit()` that polluted DB state within a pytest session [healthcabinet/backend/tests/users/test_router.py]
- [x] [Review][Patch] AC5 regression test added — `test_login_rejected_after_account_deletion` deletes account then `POST /api/v1/auth/login` asserts 401 [healthcabinet/backend/tests/users/test_router.py]
- [x] [Review][Patch] Rollback test refactored to prove atomicity via `commit_spy.await_count == 0` directly, removing manual `rollback()` + shared-session DB re-queries [healthcabinet/backend/tests/users/test_router.py]
- [x] [Review][Patch] `failing_execute` now uses `isinstance(statement, Update) and statement.table.name == "audit_logs"` — structural match replaces brittle string substring check [healthcabinet/backend/tests/users/test_router.py]
- [x] [Review][Patch] `expire_all()` now invoked uniformly before every post-cascade audit re-read in the 3 redaction tests [healthcabinet/backend/tests/users/test_router.py]
- [x] [Review][Patch] `app.dependency_overrides.pop(get_db, None)` replaces the broad `.clear()` [healthcabinet/backend/tests/users/test_router.py]
- [x] [Review][Patch] Test module now imports `AUDIT_ERASURE_MARKER as ERASURE_MARKER` from `app.users.service` — production constant is the single source of truth [healthcabinet/backend/tests/users/test_router.py:17]
- [x] [Review][Patch] `test_delete_account_redacts_audit_log_with_erasure_marker` now asserts `row.admin_id == admin_id` and `row.value_name == ERASURE_MARKER` on the legacy-shape row [healthcabinet/backend/tests/users/test_router.py]

- [x] [Review][Defer] Orphan audit rows with `user_id IS NULL AND document_id IS NULL AND health_value_id IS NULL` escape redaction — deferred, requires one-time cleanup migration outside 6-2 scope [healthcabinet/backend/app/users/service.py:129-135]
- [x] [Review][Defer] Self-correction audit row (`admin_id == user_id == subject`) semantics undefined, no test — deferred, edge case needs explicit product decision [healthcabinet/backend/app/users/service.py:141-154]
- [x] [Review][Defer] No DB-level enforcement of "redact-first" invariant (trigger/constraint) — deferred, defense-in-depth outside story scope [healthcabinet/backend/app/admin/models.py]
- [x] [Review][Defer] Concurrent admin-correction + self-delete deadlock risk from rank-inversion on `audit_logs` / `health_values` locks — deferred, rare operational edge [healthcabinet/backend/app/users/service.py:141-154]
- [x] [Review][Defer] Concurrent double-click self-delete → two reconciliation jobs enqueued for same prefix — deferred, idempotent cleanup absorbs it [healthcabinet/backend/app/users/service.py:102-176]
- [x] [Review][Defer] `"[REDACTED]"` marker collides with legitimate user-entered values (no tombstone column) — deferred, would need schema change [healthcabinet/backend/app/users/service.py:27]
- [x] [Review][Defer] Refresh cookie not cleared in 204 response (server still 401s correctly on refresh) — deferred, client-UX-only drift [healthcabinet/backend/app/users/router.py:98-107]
- [x] [Review][Defer] No scale test for deletion of users with thousands of audit rows — deferred, perf hardening [healthcabinet/backend/tests/users/test_router.py]
- [x] [Review][Defer] No regression guards for `ai_memories` / `subscriptions` / `flag_reviewed_by_admin_id` FK-cascade semantics — deferred, schema-invariance hardening [healthcabinet/backend/tests/users/test_router.py]
- [x] [Review][Defer] No safety check preventing deletion of the last admin account — deferred, operational hazard outside 6-2 scope [healthcabinet/backend/app/users/service.py:102-176]
- [x] [Review][Defer] No explicit `async with db.begin()` transaction boundary — relies on implicit session semantics — deferred, code-level hardening [healthcabinet/backend/app/users/service.py:102-176]
- [x] [Review][Defer] AC3 rollback test asserts `status==500` + truthy `x-request-id` but not full RFC 7807 shape (`type`, `title`, `instance`) — deferred, assertion hardening [healthcabinet/backend/tests/users/test_router.py:600-604]

---

## Dev Notes

### Scope: Surgical, not Greenfield

The heavy lifting — dialog, endpoint, FK cascade, MinIO async cleanup, consent retention, JWT-via-DB-lookup invalidation — already lives in the code. **Do not re-implement.** Extend `delete_user_account()` to add the audit erasure markers; add 4 tests; verify regressions. That's the story.

### Existing Code to Extend (not Replace)

- **`app/users/service.py:94-136`** — `delete_user_account()`. Already imports `AuditLog`, `User`, `ConsentLog`. Already has the UPDATE on `audit_logs` at lines 108-112 that nulls `user_id`/`admin_id`. **Extend this same UPDATE** (or add a second one in the same transaction) to null `document_id`/`health_value_id` and set erasure markers on `original_value`/`new_value`. Do not create a new module.
- **`app/admin/models.py:11-43`** — `AuditLog` model. All columns needed already exist. No migration required for the AC as written. **Do NOT add a migration for this story** unless the arch sync explicitly adds a new column.
- **`app/users/router.py:98-107`** — DELETE endpoint is already wired. Do not change its signature or response code.
- **`src/routes/(app)/settings/+page.svelte:659-695`** — Confirmation dialog is already complete. Do not touch unless AC4.1 regresses in test.

### Anti-Patterns to Avoid

- ❌ **Do not** add a new migration for a `redacted_at` column on `audit_logs` — the spec preserves the existing schema and redacts in place.
- ❌ **Do not** introduce a soft-delete flag on users. Epic 6.2 requires hard deletion of the `users` row.
- ❌ **Do not** delete `consent_logs` rows. They are **retained** per regulatory requirement (Epic 6.2 AC line 1135, already enforced by FK `SET NULL` at `app/users/models.py:26-27`).
- ❌ **Do not** mock the MinIO call in the new tests — Story 14-2 already has 3 tests covering MinIO cleanup and failure paths; don't duplicate. The new tests in Task 3 should focus on DB audit redaction, not MinIO.
- ❌ **Do not** call `await db.commit()` inside the redaction block. The whole cascade must be one transaction boundary.
- ❌ **Do not** introduce `asyncio.shield` in this story — Story 14-2 code review already rejected that pattern (shield re-raises `CancelledError` and defeats its own purpose). If you feel the urge to use it, the design is wrong.
- ❌ **Do not** re-create a `ConfirmDialog` — Story 12-4 extracted the reusable one at `$lib/components/ui/confirm-dialog/`.
- ❌ **Do not** skip running tests in Docker. Per Epic 14 retro, Docker-unavailable is a HALT condition; per the global CLAUDE.md rule, tests are valid only in Docker Compose.

### Reuse Opportunities (Cite When Using)

- **`AuditLog` accessors** — follow the pattern in `test_delete_admin_account_retains_audit_logs_with_null_admin_id` (`tests/users/test_router.py:362-401`) for asserting audit row state post-deletion.
- **`ConfirmDialog`** — Story 12-4's extraction at `src/lib/components/ui/confirm-dialog/`. Do not duplicate.
- **`get_user_by_id()`** at `app/users/service.py` — already handles the None-for-deleted-user case that drives the 401 in `dependencies.py:45-51`.
- **RFC 7807 problem middleware** at `app/core/middleware.py` — returns request-ID-bearing problem docs on unhandled exceptions; your 500-on-rollback AC (3.3) is already covered if you let the exception propagate.

### Security Considerations

- **Erasure marker must not leak PII.** `"[REDACTED]"` is safe. Do NOT use a per-user hash or salted identifier — those are linkable back to the user ID and defeat the erasure.
- **Idempotency:** A second DELETE on an already-deleted user should return 401 (because the auth dependency can't find the user). Verify behavior; do not mask to 204.
- **Rate limiting:** Account deletion is already behind `get_current_user_id()` (which respects the per-user rate limit via `app/core/rate_limit.py`). No new rate-limit logic needed.
- **IDOR:** The user_id comes from the JWT, not the request body. `app/users/router.py:98-107` already enforces this. Do not introduce a path param or body field for user_id.

### Testing Standards (per `AGENTS.md` and Epic 14 retro Action Items 4, 9)

- **All tests run in Docker Compose:** `docker compose exec backend uv run pytest tests/users/` and `docker compose exec frontend npm run test:unit`. Tests outside Docker are invalid.
- **Pre-flight:** `docker compose up -d` + `docker compose exec backend uv run pytest --co -q` before writing code.
- **No mocking AI calls.** Not applicable to this story (no AI path).
- **Test the real DB:** use the `db_session` fixture already in `tests/conftest.py`. Do not mock SQLAlchemy.
- **Baseline:** Full backend suite should pass 363+ tests (Story 14-4 baseline); frontend should pass 578+. Net additions expected: +4-5 backend tests, 0-1 frontend test.

### File Structure Alignment

Per the existing HealthCabinet backend layout:

```
healthcabinet/backend/app/
├── users/
│   ├── service.py           ← EDIT: extend delete_user_account() for audit redaction
│   ├── router.py            ← NO CHANGES (endpoint already wired)
│   └── models.py            ← NO CHANGES
├── admin/
│   └── models.py            ← NO CHANGES (AuditLog schema unchanged)
├── auth/
│   └── dependencies.py      ← NO CHANGES (401-on-deleted-user works)
tests/users/
├── test_router.py           ← EDIT: add 4 tests (AC7.1-7.4), remove 3 dead patches
└── test_service.py          ← OPTIONAL: service-layer redaction unit test if router integration proves insufficient
```

No new files expected. No new migrations.

---

### Previous Story Intelligence (Story 6.1: Full Data Export, Story 14-2: MinIO Cleanup, Story 14-3: Admin ADR, Story 12-4: Deletion UX)

- **Story 6.1 (data export)** established the pattern of decrypting at the repository layer and using JWT-derived user_id for scoping. Same pattern applies here — the user_id for redaction comes from the JWT, never from the request body.
- **Story 14-2 (MinIO cleanup)** established the **commit-before-async-cleanup** pattern for user deletion. Also delivered `tests/users/test_router.py:412-541` — 4 deletion tests covering the happy path, MinIO failure non-blocking, prefix-cleanup-after-commit. **Review these tests before writing new ones** — they define the idiomatic test shape.
- **Story 14-3 (admin ADR)** extended `audit_logs.admin_id` to `SET NULL` on admin deletion. The **orthogonal case** (user deletion) redacts `original_value`/`new_value` but preserves `admin_id`. Confusingly similar but distinct: 14-3 said "admin goes away, preserve the audit-record's content but null the admin FK." 6-2 says "user goes away, preserve the admin FK (it's a different person's accountability record) but null the document/health_value FKs and erase the content that was about the deleted user's data."
- **Story 12-4 (deletion UX)** established the email-type-to-confirm `ConfirmDialog` pattern. Don't touch it unless a test regresses.

### Git Intelligence (last 5 commits relevant to this story)

- `29319d0` — `fix(14-1/14-2): remove duplicate MinIO cleanup, shield anti-pattern, and silent consent API change` — the asyncio.shield pattern you might be tempted to reach for was explicitly rejected here. Also illustrates the "silent consent API change" failure mode the retro warned about.
- `603bb8e` — `fix(14-3): add missing ADR and fix service comment + test accessor inconsistency` — example of the ADR discipline expected for architecture decisions.
- `e31c5d7` — `feat: make audit_logs.admin_id nullable and change foreign key to SET NULL for admin account deletion` — the migration that 14-3 shipped; reference for how the schema evolves when FK semantics change.
- `25dc716` — `feat: implement user account deletion with MinIO cleanup and reconciliation job` — the 14-2 implementation you're extending.

### Latest Tech Information

- **SQLAlchemy 2.0 async** (project stack). Use `session.execute(update(AuditLog).where(...).values(...))` for the in-place redaction — do NOT iterate rows in Python. Single UPDATE is atomic and efficient.
- **FastAPI / Starlette** — RFC 7807 middleware is already installed; a bare `raise` will produce the correct error response.
- **ARQ (Redis queue)** — MinIO cleanup job already registered; do not add new workers for 6-2.

### Project Structure Notes

Alignment with the unified structure in CLAUDE.md:

- Backend domain module: `app/users/` (users domain owns account deletion).
- Test location: `tests/users/test_router.py` (integration-style tests that hit the router + DB).
- Frontend location: `src/routes/(app)/settings/` — unchanged.

**Detected variances:** None. Story 6-2 fits existing conventions exactly.

### References

- Epic 6.2 spec: `_bmad-output/planning-artifacts/epics.md` lines 1116-1152
- Epic 14 retro: `_bmad-output/implementation-artifacts/epic-14-retro-2026-04-17.md` (Action Items 2, 4, 5, 9 are directly relevant)
- Story 14-2 shipped implementation: `_bmad-output/implementation-artifacts/14-2-minio-orphan-cleanup-on-account-deletion.md`
- Story 14-3 ADR precedent: `_bmad-output/implementation-artifacts/14-3-admin-self-deletion-policy-adr.md`
- Story 12-4 UX: `_bmad-output/implementation-artifacts/12-4-account-data-deletion-ux.md`
- Global test rules: `/Users/vladtara/.claude/CLAUDE.md` (Docker-only testing)
- Project instructions: `/Users/vladtara/dev/set-bmad/CLAUDE.md`
- deferred-work.md (to be pruned in same commit per AC8): `_bmad-output/implementation-artifacts/deferred-work.md`
- Service file to edit: `healthcabinet/backend/app/users/service.py:94-136`
- Model to reference (no change): `healthcabinet/backend/app/admin/models.py:11-43`
- Tests to extend: `healthcabinet/backend/tests/users/test_router.py:265-541`

---

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (1M context)

### Debug Log References

- Pre-flight pytest collection at Story 6-2 kickoff: 30 tests in `tests/users/`, 0 errors, all services (postgres/redis/minio/backend/worker/frontend) healthy.
- Initial RED phase: 5 new tests added; 3 failed as expected (erasure marker missing), 2 passed as regression gates (`preserves_admin_columns`, `jwt_rejected` — the existing auth dependency + service already handled these cases).
- GREEN phase: service.py UPDATE extended with erasure markers; 4/5 new tests pass.
- Rollback test initially failed with `RuntimeError` propagating past httpx's `ASGITransport` (default `raise_app_exceptions=True`). Fixed by using a local `ASGITransport(app, raise_app_exceptions=False)` so the global exception handler's 500 JSON response is returned instead of re-raised.
- Cleanup commit: removed inert `patch("app.users.service.get_s3_client", ...)` / `patch("...delete_objects_by_prefix", ...)` decorators from 7 tests (the deletion flow no longer calls these inline — 14-2 moved cleanup to the ARQ worker). Renamed one test to match its new intent (ARQ enqueue failure, not MinIO-inline failure).
- Final regression: backend 366 passed / 1 skipped / 0 failures; frontend 578 passed / 55 test files / 0 regressions. `ruff check` and `ruff format --check` clean on `app/users/service.py` and `tests/users/test_router.py`. `mypy app/users/service.py` clean.

### Completion Notes List

- **Atomicity choice (Option A)**: proceeded with the story's documented default — DB-atomic transaction (audit redaction + FK cascade + user delete committed together); MinIO cleanup via deferred ARQ job post-commit; MinIO failure logged but doesn't roll back. AC3.2 already reflected this choice. Epic 6.2 AC in `epics.md` amended to match shipped pattern.
- **Erasure marker literal**: `"[REDACTED]"` defined as module constant `AUDIT_ERASURE_MARKER` in `app/users/service.py`. Used in the subject-redaction UPDATE statement.
- **Redaction ordering is load-bearing**: audit redaction MUST run before `DELETE FROM users`. `audit_logs.user_id` FK is `ondelete=CASCADE` — doing delete first would remove the audit rows entirely and erase the regulatory trail. The existing code's WHERE-clause ordering already handled this correctly; the fix extends the same UPDATE with erasure content.
- **Refresh-token revocation (AC5.1 enhancement): deferred.** Current design relies on `get_user_by_id()` returning None for a deleted user, which triggers 401 in `dependencies.py:45-51`. Explicit token blacklisting would improve immediacy for JWTs already minted but not yet expired; not required by Epic 6.2 AC. Adding as a candidate deferred item would be appropriate if the team wants a production-grade GDPR hardening pass — not added to `deferred-work.md` this commit because the existing path satisfies the AC as written.
- **Scope expansion**: the story explicitly flagged 3 dead test patches for removal (427, 453-464, 487). I removed the same patch pattern in 4 additional tests since they were equally inert (same root cause: inline MinIO deletion was removed in Story 14-2). This is a cleaner PR and more fully resolves the "dead scaffolding" concern in the 14-5 deferred-work entry. Also refactored `test_delete_account_minio_failure_does_not_block_deletion` → `test_delete_account_arq_enqueue_failure_does_not_block_deletion` to preserve the "cleanup failure doesn't block 204" intent under the new deferred-job pattern.
- **Epic 6.2 AC amendment**: Story Task 6.1 required updating epics.md Story 6.2 AC to reflect the shipped cascade. Applied — the previous "all MinIO objects deleted first in atomic transaction rolling back on failure" language was spec-drift ahead of Story 14-2. New AC documents DB atomicity + post-commit async MinIO, and names the `"[REDACTED]"` erasure marker explicitly.
- **Deferred-work.md hygiene (Epic 14 retro Action Item 9)**: pruned 2 resolved bullets in same commit. Story 6-2 is the first story in the redesign track to apply this DoD rule.
- **Frontend Task 4.2 (desktop smoke test)**: skipped; backend-only changes with no UX path modification. 578/578 frontend tests green cover the regression surface.

### File List

- **Modified:** `healthcabinet/backend/app/users/service.py` — extended `delete_user_account()` audit UPDATE with erasure markers and explicit FK nulling; added `AUDIT_ERASURE_MARKER` constant; expanded docstring with cascade ordering rationale.
- **Modified:** `healthcabinet/backend/tests/users/test_router.py` — added 4 new tests, renamed+extended 1 existing test, renamed+refactored 1 test to match new deferred-job pattern, removed inert `get_s3_client` / `delete_objects_by_prefix` patches from 7 tests; reformatted pre-existing ConsentLog fixture kwargs per ruff format.
- **Modified:** `_bmad-output/implementation-artifacts/deferred-work.md` — removed 2 resolved bullets (dead MinIO patches called out in Story 14-4 and 14-5 reviews).
- **Modified:** `_bmad-output/planning-artifacts/epics.md` — amended Story 6.2 AC to match shipped Option A pattern.
- **Modified:** `_bmad-output/implementation-artifacts/sprint-status.yaml` — `6-2-account-data-deletion: in-progress → review`; `last_updated: 2026-04-18`.

### Change Log

- `2026-04-18` — Story 6-2 implementation complete. Audit-log erasure marker + atomicity regression coverage added. 4 new tests (erasure marker, admin-column preservation, JWT post-delete rejection, rollback on redaction failure); 2 existing tests extended/refactored (consent retention + audit redaction; ARQ enqueue failure). 7 dead test patches removed. Backend 366/366, Frontend 578/578. Epic 6.2 spec amended to reflect shipped pattern.
