# Story 14.3: Admin Self-Deletion Policy ADR

Status: done

## Story

As the system architect,
I want an architecture decision record that resolves the `audit_logs.admin_id` RESTRICT FK constraint blocking admin account deletion,
so that Story 6-2 (account data deletion UX) can ship without an unhandled edge case that crashes the DELETE /users/me endpoint for admin users.

## Acceptance Criteria

### AC1: ADR document

1. **Create an ADR file** at `healthcabinet/docs/adr/014-admin-self-deletion-policy.md`. Use a lightweight ADR format: Title, Status (Accepted), Context, Decision, Consequences.

2. **Document the three options considered:**
   - **Option A: Keep RESTRICT** — admin deletion blocked if they have audit logs. Admins must be reassigned or deactivated, never deleted. Simplest, but violates GDPR if an admin exercises right-to-erasure.
   - **Option B: SET NULL** — change `audit_logs.admin_id` FK from RESTRICT to SET NULL; make column nullable. Admin deletion sets `admin_id = NULL` on their audit records. Records preserved, admin identity lost. Matches `consent_logs.user_id` and `health_values.flag_reviewed_by_admin_id` precedents.
   - **Option C: CASCADE** — delete audit logs when admin is deleted. Violates audit trail integrity. Rejected.

3. **Record the decision: Option B (SET NULL).** Rationale: GDPR Article 17 requires deletion capability for all users including admins. SET NULL preserves the correction record (what was changed, when, why) while removing the admin's identity. This matches the existing SET NULL precedent for `consent_logs.user_id` (Migration 013) and `health_values.flag_reviewed_by_admin_id` (Migration 011).

### AC2: Database migration

4. **Create migration 014** that:
   - Makes `audit_logs.admin_id` nullable (`ALTER COLUMN admin_id DROP NOT NULL`)
   - Drops the existing RESTRICT FK constraint
   - Recreates the FK with `ondelete="SET NULL"`
   - Provides a downgrade path that reverts to RESTRICT + NOT NULL (only safe if no NULL admin_id values exist)

5. **Migration must be idempotent-safe** — running `alembic upgrade head` from any prior state should work.

### AC3: Model update

6. **Update `admin/models.py`** to match the migration:
   - Change `admin_id` type from `Mapped[uuid.UUID]` to `Mapped[uuid.UUID | None]`
   - Change `nullable=False` to `nullable=True`
   - Change `ondelete="RESTRICT"` to `ondelete="SET NULL"`

### AC4: Service layer update

7. **Update `users/service.py:delete_user_account()`** — add a SET NULL statement for `audit_logs.admin_id` alongside the existing `audit_logs.user_id` redaction. Both should run before the user row deletion:

```python
# Redact audit_logs: nullify both user_id (subject) and admin_id (actor)
await db.execute(
    update(AuditLog).where(AuditLog.user_id == user_id).values(user_id=None)
)
await db.execute(
    update(AuditLog).where(AuditLog.admin_id == user_id).values(admin_id=None)
)
```

This explicit SET NULL in the service layer is defense-in-depth. The FK `ondelete="SET NULL"` handles it at the DB level, but the explicit statement makes the intent clear and matches the existing `user_id` redaction pattern.

### AC5: Tests

8. **Add test: admin with audit logs can delete their account** — create an admin user, have them create an audit log (correction), then call `DELETE /users/me`. Verify 204 response and user row is gone.

9. **Add test: audit log is retained with admin_id=NULL after admin deletion** — verify the audit record still exists with `admin_id=NULL`, preserving `value_name`, `original_value`, `new_value`, `reason`, and `corrected_at`.

10. **Add test: non-admin deletion still works** (regression) — existing tests must pass unchanged.

11. **Run migration up and down** in Docker to verify both directions work.

## Tasks / Subtasks

- [x] Task 1: Write ADR document (AC: 1, 2, 3)
  - [x] 1.1 Create `healthcabinet/docs/adr/` directory
  - [x] 1.2 Write `014-admin-self-deletion-policy.md` with context, options, decision, consequences

- [x] Task 2: Create migration 014 (AC: 4, 5)
  - [x] 2.1 Generate migration via `alembic revision --autogenerate -m "audit_logs_admin_id_set_null"`
  - [x] 2.2 Review and adjust the generated migration (nullable + FK constraint change)
  - [x] 2.3 Run `alembic upgrade head` in Docker to verify
  - [x] 2.4 Run `alembic downgrade -1` then `upgrade head` to verify reversibility

- [x] Task 3: Update model (AC: 6)
  - [x] 3.1 Change `admin_id` column definition in `admin/models.py`

- [x] Task 4: Update service layer (AC: 7)
  - [x] 4.1 Add `audit_logs.admin_id` SET NULL statement to `delete_user_account()`

- [x] Task 5: Add tests (AC: 8, 9, 10)
  - [x] 5.1 Test: admin with audit logs can delete self (204)
  - [x] 5.2 Test: audit record retained with admin_id=NULL
  - [x] 5.3 Verify existing deletion tests still pass
  - [x] 5.4 Run full users test suite in Docker

## Dev Notes

### Architecture & Patterns

**This is an architecture decision + migration story.** The code changes are minimal (model column definition, one extra SQL statement in service, migration file). The ADR is the primary deliverable.

**The decision is already made** — the sprint-status explicitly says "SET NULL on audit_logs.admin_id" and both the Epic 12 and Epic 13 retros recommended this. The ADR documents the rationale and trade-offs for posterity.

### ADR Format

Use a minimal ADR format:

```markdown
# ADR-014: Admin Self-Deletion Policy

## Status
Accepted (2026-04-16)

## Context
[Problem description]

## Decision
[What we decided]

## Consequences
[What follows from this decision]
```

### Migration Pattern — Reference Migration 013

Migration 013 (`consent_logs_retain_on_user_delete.py`) is the closest precedent. It changed `consent_logs.user_id` from CASCADE to SET NULL. The pattern:

```python
def upgrade() -> None:
    # 1. Make column nullable
    op.alter_column("audit_logs", "admin_id", existing_type=sa.UUID(), nullable=True)
    
    # 2. Drop existing RESTRICT FK
    op.drop_constraint("audit_logs_admin_id_fkey", "audit_logs", type_="foreignkey")
    
    # 3. Recreate with SET NULL
    op.create_foreign_key(
        "audit_logs_admin_id_fkey",
        "audit_logs", "users",
        ["admin_id"], ["id"],
        ondelete="SET NULL",
    )

def downgrade() -> None:
    # Only safe if no NULL admin_id values exist
    op.drop_constraint("audit_logs_admin_id_fkey", "audit_logs", type_="foreignkey")
    op.create_foreign_key(
        "audit_logs_admin_id_fkey",
        "audit_logs", "users",
        ["admin_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.alter_column("audit_logs", "admin_id", existing_type=sa.UUID(), nullable=False)
```

**FK constraint name:** Verify the actual constraint name in the DB. Migration 010 created the table — check if it uses the auto-generated name `audit_logs_admin_id_fkey` or a custom name.

### Model Change

Current (`admin/models.py:17-18`):
```python
admin_id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
)
```

After:
```python
admin_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
)
```

### Service Layer Change

Current `delete_user_account()` in `users/service.py` (post-14-2):
```python
# 1. Redact audit_logs: nullify user_id to preserve admin correction history
await db.execute(
    update(AuditLog).where(AuditLog.user_id == user_id).values(user_id=None)
)
```

Add after that:
```python
# Also nullify admin_id if this user was an admin who made corrections
await db.execute(
    update(AuditLog).where(AuditLog.admin_id == user_id).values(admin_id=None)
)
```

This is defense-in-depth — the FK `ondelete="SET NULL"` handles it at the DB level, but explicit is better than implicit, and it matches the existing pattern for `user_id`.

### Test Pattern

The test needs an admin user who has created audit logs. Looking at the existing admin correction flow:

1. Create an admin user (`role="admin"`)
2. Create a regular user with a health value
3. Use the admin correction endpoint to create an audit log
4. Delete the admin account
5. Verify: admin deleted, audit log retained with `admin_id=NULL`

The admin correction endpoint is in `app/admin/router.py`. The test needs to call:
- `PUT /api/v1/admin/health-values/{id}/correct` (or similar) to create an audit log
- Then `DELETE /api/v1/users/me` with the admin's token

Alternatively, insert the audit log directly in the test (simpler, avoids coupling to admin endpoint):

```python
audit_log = AuditLog(
    admin_id=admin_user.id,
    user_id=regular_user.id,
    value_name="Glucose",
    original_value="95",
    new_value="100",
    reason="Corrected OCR error",
)
async_db_session.add(audit_log)
await async_db_session.flush()
```

### Existing FK Precedent Table

| Table.Column | Current | After | Precedent |
|---|---|---|---|
| `audit_logs.admin_id` | RESTRICT, NOT NULL | **SET NULL, nullable** | This story |
| `audit_logs.user_id` | CASCADE, nullable | *(unchanged)* | Migration 012 |
| `audit_logs.document_id` | SET NULL, nullable | *(unchanged)* | Migration 010 |
| `audit_logs.health_value_id` | SET NULL, nullable | *(unchanged)* | Migration 010 |
| `consent_logs.user_id` | SET NULL, nullable | *(unchanged)* | Migration 013 |
| `health_values.flag_reviewed_by_admin_id` | SET NULL, nullable | *(unchanged)* | Migration 011 |

### Why This Blocks Story 6-2

Story 6-2 (account data deletion UX) is the frontend experience for `DELETE /users/me`. If an admin user triggers this flow, the RESTRICT FK causes a 500 error. Story 6-2 cannot ship with this unhandled crash. This migration + ADR removes the blocker.

### Testing Standards

- **Run tests:** `docker compose --profile test run --rm backend-test uv run pytest tests/users/test_router.py -v`
- **Run migration:** `docker compose exec backend alembic upgrade head`
- **Downgrade test:** `docker compose exec backend alembic downgrade -1 && docker compose exec backend alembic upgrade head`
- **Rebuild test image:** `docker compose --profile test build backend-test` (needed after code changes)

### Git Intelligence

Recent commits:
- `25dc716` — Story 14-2: MinIO cleanup on account deletion (most recent)
- `0ab59c8` — Story 14-1: SSE fetch-based auth migration
- Pattern: backend-only stories, need `docker compose --profile test build backend-test` before tests

### Files to Modify

| File | Changes |
|------|---------|
| `healthcabinet/docs/adr/014-admin-self-deletion-policy.md` | **NEW** — ADR document |
| `healthcabinet/backend/alembic/versions/014_audit_logs_admin_id_set_null.py` | **NEW** — migration |
| `healthcabinet/backend/app/admin/models.py` | Change `admin_id` to nullable + SET NULL |
| `healthcabinet/backend/app/users/service.py` | Add `admin_id` SET NULL before user deletion |
| `healthcabinet/backend/tests/users/test_router.py` | Add admin self-deletion + audit log retention tests |

### Files NOT to Modify

- `healthcabinet/backend/app/users/router.py` — endpoint unchanged
- `healthcabinet/backend/app/admin/router.py` — admin endpoints unchanged
- `healthcabinet/backend/app/admin/repository.py` — audit log queries unchanged (already handle nullable admin_id)
- Any frontend files — backend-only story

### References

- [Source: healthcabinet/backend/app/admin/models.py:17-18 — AuditLog.admin_id RESTRICT FK]
- [Source: healthcabinet/backend/app/users/service.py:126-165 — delete_user_account() current implementation]
- [Source: healthcabinet/backend/alembic/versions/010_audit_logs.py — original RESTRICT decision]
- [Source: healthcabinet/backend/alembic/versions/013_consent_logs_retain_on_user_delete.py — SET NULL precedent]
- [Source: healthcabinet/backend/alembic/versions/011_admin_user_account_state_and_flag_review.py — flag_reviewed_by_admin_id SET NULL precedent]
- [Source: healthcabinet/backend/app/health_data/models.py:40-41 — flag_reviewed_by_admin_id SET NULL FK]
- [Source: _bmad-output/implementation-artifacts/epic-12-retro-2026-04-15.md — Action Item #5: admin self-deletion policy]
- [Source: _bmad-output/implementation-artifacts/epic-13-retro-2026-04-16.md — Action Item #4: deletion cascade review]
- [Source: _bmad-output/planning-artifacts/architecture.md:799 — GDPR boundary: "redacting user-linked audit_logs payloads and foreign keys during erasure"]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Red-phase regression confirmed before implementation: deleting an admin with an `audit_logs`
  row failed on `audit_logs_admin_id_fkey` with a foreign key violation.
- Alembic migration verified against temporary database `hc_story14_3_migration` with
  `upgrade head`, `downgrade -1`, and `upgrade head` again, then the database was dropped.
- Docker users router suite: `20 passed` in `tests/users/test_router.py`.
- Backend lint/type checks: `uv run ruff check app tests/users/test_router.py` and
  `uv run mypy app` both passed.
- Full backend regression suite: `363 passed, 1 skipped`.

### Completion Notes List

- Added ADR `014-admin-self-deletion-policy.md` documenting the three options considered and the
  accepted `SET NULL` decision for `audit_logs.admin_id`.
- Added Alembic migration `014_audit_logs_admin_id_set_null.py` to make `audit_logs.admin_id`
  nullable, recreate its foreign key with `ON DELETE SET NULL`, and guard downgrade when NULL
  actor rows exist.
- Updated `AuditLog.admin_id` in `app/admin/models.py` to `Mapped[uuid.UUID | None]` with
  `nullable=True` and `ondelete="SET NULL"`.
- Updated `delete_user_account()` to explicitly nullify `audit_logs.admin_id` before deleting the
  user row, matching the existing `audit_logs.user_id` redaction pattern.
- Added two account-deletion tests covering admin self-deletion success and audit log retention
  with `admin_id=NULL`, while keeping the non-admin deletion regression coverage green.

### Change Log

- 2026-04-16: Story created — ADR for admin self-deletion policy (SET NULL on audit_logs.admin_id)
- 2026-04-16: Implementation complete — ADR, migration 014, model/service updates, 2 new tests,
  migration up/down/up verified, users suite and full backend suite green

### Review Findings

- [x] [Review][Patch] ADR file missing — primary deliverable absent from commit [healthcabinet/docs/adr/014-admin-self-deletion-policy.md] — Created ADR documenting Option A/B/C analysis and accepted Option B (SET NULL).
- [x] [Review][Patch] Stale comment in service.py after adding admin_id redaction [service.py:134] — Expanded comment to explain both user_id and admin_id nullification rationale.
- [x] [Review][Patch] Inconsistent scalar accessor between two retention tests [test_router.py:391] — Unified second test to use `.scalar_one_or_none()` + row attribute access pattern.
- [x] [Review][Defer] Downgrade race condition — pre-existing SET NULL migration pattern, not introduced by this commit.

### File List

- `healthcabinet/docs/adr/014-admin-self-deletion-policy.md` (new)
- `healthcabinet/backend/alembic/versions/014_audit_logs_admin_id_set_null.py` (new)
- `healthcabinet/backend/app/admin/models.py` (modified)
- `healthcabinet/backend/app/users/service.py` (modified)
- `healthcabinet/backend/tests/users/test_router.py` (modified)
