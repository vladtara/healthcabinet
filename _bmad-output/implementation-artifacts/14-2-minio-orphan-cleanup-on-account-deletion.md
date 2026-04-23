# Story 14.2: MinIO Orphan Cleanup on Account Deletion

Status: done

## Story

As a user exercising my GDPR Article 17 right to erasure,
I want all my uploaded health documents to be deleted from object storage when I delete my account,
so that no document blobs remain orphaned in MinIO after my data is erased from the database.

## Acceptance Criteria

### AC1: Collect S3 keys before DB deletion

1. **Before deleting the user row** in `users/service.py:delete_user_account()`, query all documents belonging to the user via `documents/repository.py:get_documents_by_user()`.

2. **Extract S3 keys** from each document's `s3_key_encrypted` field using `decrypt_bytes()`. Also extract `pending_s3_key_encrypted` (staged retry uploads). Use the safe decryption pattern from `get_document_s3_key_optional()` — return `None` on decryption failure, do not raise.

3. **Build the user-level prefix** `{user_id}/` for fallback. Since all S3 keys follow the format `{user_id}/{document_id}/{filename}`, this prefix covers all documents for the user and catches orphaned objects from prior failed cleanups.

### AC2: DB-first deletion (existing behavior preserved)

4. **Preserve the existing deletion order** in `delete_user_account()`: redact `audit_logs.user_id` → delete user row (CASCADE removes documents, health_values, user_profiles, ai_memories, subscriptions; SET NULL on consent_logs). The DB transaction commits before MinIO cleanup.

5. **No change to the DB transaction scope.** MinIO cleanup happens after the DB transaction commits successfully. If the DB transaction fails, no MinIO cleanup is attempted (correct — no data was deleted).

### AC3: Best-effort MinIO cleanup after DB commit

6. **After the DB transaction commits**, attempt to delete all collected S3 objects from MinIO. Use the prefix-based bulk deletion approach: `delete_objects_by_prefix(s3_client, bucket, f"{user_id}/")`. This is simpler and more reliable than per-key deletion because it catches all objects under the user's prefix regardless of decryption state.

7. **If prefix-based deletion fails**, log a structured warning with the orphaned prefix so operators can manually clean up via MinIO CLI (`mc rm --recursive --force myminio/healthcabinet/{user_id}/`). Do NOT re-raise the exception — the account deletion is already committed and must not appear to fail.

8. **Return normally** — the `DELETE /users/me` endpoint returns 204 regardless of MinIO cleanup outcome. The user's account is deleted from the DB, which is the authoritative state.

### AC4: Structured logging for operator auditability

9. **Log successful cleanup**: `structlog` info event `account_deletion.storage_cleanup_complete` with `user_id`, `deleted_object_count`, and `prefix`.

10. **Log failed cleanup**: `structlog` warning event `account_deletion.storage_cleanup_failed` with `user_id`, `orphaned_prefix`, and exception info. This is the same severity as `delete_document.storage_cleanup_failed` (existing pattern).

### AC5: Tests

11. **Add test: account deletion triggers MinIO cleanup** — verify that `delete_objects_by_prefix` is called with the correct prefix `{user_id}/` after the DB deletion commits.

12. **Add test: MinIO failure does not block account deletion** — verify that when `delete_objects_by_prefix` raises an exception, the endpoint still returns 204 and the user row is gone from the DB.

13. **Add test: account deletion with no documents skips MinIO cleanup** — verify that `delete_objects_by_prefix` is still called (to catch orphaned objects), or is skipped entirely if no documents exist and no prefix cleanup is needed.

14. **Existing tests must continue passing**: `test_delete_account_success`, `test_delete_account_retains_consent_logs`, and all other user router tests.

## Tasks / Subtasks

- [x] Task 1: Add MinIO cleanup to `delete_user_account()` (AC: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
  - [x] 1.1 Modify `users/service.py:delete_user_account()` to accept or create S3 client
  - [x] 1.2 After DB commit, call `delete_objects_by_prefix(s3_client, bucket, f"{user_id}/")` in a try/except
  - [x] 1.3 Add structured logging for success and failure paths
  - [x] 1.4 Wrap MinIO call in `asyncio.to_thread()` since boto3 is synchronous (matches `delete_document()` pattern)

- [x] Task 2: Add backend tests (AC: 11, 12, 13, 14)
  - [x] 2.1 Test: MinIO prefix cleanup called on account deletion
  - [x] 2.2 Test: MinIO failure logged but 204 still returned
  - [x] 2.3 Test: existing deletion tests still pass (updated with MinIO mocks)
  - [x] 2.4 Run full users test suite in Docker (16/16 pass; 82/82 processing+users+export pass)

### Review Findings

- [x] [Review][Patch] Add a durable post-deletion reconciliation path so racing upload/reupload requests cannot recreate orphaned `user_id/...` objects after the initial sweep [`healthcabinet/backend/app/users/service.py:46`]
- [x] [Review][Patch] Ensure post-commit MinIO cleanup survives request cancellation or timeout [`healthcabinet/backend/app/users/service.py:52`]
- [x] [Review][Patch] Add regression coverage that proves MinIO cleanup runs only after the database commit [`healthcabinet/backend/tests/users/test_router.py:277`]
- [x] [Review][Patch] Fix Ruff violations in the touched user router test module (`I001` import order, `F401` unused import) [`healthcabinet/backend/tests/users/test_router.py:1`]

## Dev Notes

### Architecture & Patterns

**This is a backend-only GDPR compliance fix.** No frontend changes. No migrations. No new endpoints. The change is inside `delete_user_account()` in `users/service.py`.

**Follow the established pattern from `delete_document()` in `documents/service.py:333-386`.** That function does:
1. Resolve S3 key while row exists
2. Delete from DB, commit
3. Best-effort MinIO cleanup with structured logging on failure

The account deletion version is simpler because we use **prefix-based bulk deletion** (`{user_id}/`) instead of per-key deletion. This avoids:
- Iterating documents one-by-one
- Decrypting individual `s3_key_encrypted` values (which can fail)
- Missing `pending_s3_key_encrypted` values from staged retries
- Missing orphaned objects from prior failed cleanups

### Implementation — Recommended Approach

```python
# users/service.py

import asyncio
import structlog

from app.core.config import settings
from app.documents.storage import delete_objects_by_prefix, get_s3_client

logger = structlog.get_logger()

async def delete_user_account(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Delete user account and all associated data (GDPR Article 17).
    
    DB deletion is authoritative: commit first, then best-effort MinIO cleanup.
    MinIO failure is logged for operator intervention but does not block deletion.
    """
    # 1. Redact audit_logs: nullify user_id to preserve admin correction history
    await db.execute(
        update(AuditLog).where(AuditLog.user_id == user_id).values(user_id=None)
    )
    # 2. Delete user row — CASCADE handles documents, health_values, profiles,
    #    ai_memories, subscriptions. consent_logs.user_id set to NULL by FK.
    await db.execute(delete(User).where(User.id == user_id))

    # 3. Best-effort MinIO cleanup after DB commit.
    #    Prefix covers all objects: {user_id}/{document_id}/{filename}
    prefix = f"{user_id}/"
    try:
        s3_client = get_s3_client()
        deleted_count = await asyncio.to_thread(
            delete_objects_by_prefix, s3_client, settings.MINIO_BUCKET, prefix
        )
        logger.info(
            "account_deletion.storage_cleanup_complete",
            user_id=str(user_id),
            deleted_object_count=deleted_count,
            prefix=prefix,
        )
    except Exception:
        logger.warning(
            "account_deletion.storage_cleanup_failed",
            user_id=str(user_id),
            orphaned_prefix=prefix,
            exc_info=True,
        )
```

**Key decision: no per-document iteration needed.** The S3 key format `{user_id}/{document_id}/{filename}` means `{user_id}/` as prefix deletes ALL objects for the user. `delete_objects_by_prefix()` already handles pagination via S3 `list_objects_v2` paginator.

### Why Prefix-Based Over Per-Key Deletion

| Approach | Pros | Cons |
|----------|------|------|
| Per-key (decrypt each doc) | Precise; can track individual failures | Decryption can fail; misses pending keys; misses prior orphans |
| Prefix-based (`{user_id}/`) | Catches everything; no decryption needed; simpler code | Slightly less precise logging per object |

**Prefix-based is strictly better for bulk account deletion.** Per-key deletion is appropriate for single-document delete (where precision matters). For "delete everything," prefix is more reliable.

### Transaction Timing

The DB session auto-commits on success (per `get_db()` pattern in `core/database.py`). The `delete_user_account()` function is called inside a route handler that uses `Depends(get_db)`, which commits at the end of the dependency's scope. So the MinIO cleanup happens **after the session yields** — meaning after DB commit.

Wait — actually this needs verification. Let me check: does `delete_user_account()` explicitly commit, or does it rely on the session auto-commit?

Looking at the existing code:
```python
# users/service.py:28-36
async def delete_user_account(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(update(AuditLog)...)
    await db.execute(delete(User)...)
```

No explicit `await db.commit()`. The commit happens when the route handler's `get_db()` dependency exits its context (on successful response). This means the MinIO cleanup code runs **inside the same session scope** — if MinIO cleanup throws and the exception propagates, it could prevent the DB commit!

**Critical: must ensure MinIO exceptions are caught** so they don't prevent the DB session commit. The try/except in the recommended approach handles this, but the MinIO call must be placed AFTER the DB operations and the try/except must be airtight.

Actually, looking more carefully at `delete_document()` in documents/service.py:333-386, it explicitly calls `await db.commit()` before MinIO cleanup. The account deletion service function should follow the same pattern — add an explicit `await db.commit()` before MinIO cleanup, then the MinIO cleanup happens outside the transaction.

### Explicit Commit Required

```python
async def delete_user_account(db: AsyncSession, user_id: uuid.UUID) -> None:
    # DB operations
    await db.execute(update(AuditLog)...)
    await db.execute(delete(User)...)
    
    # Explicit commit — DB deletion is authoritative
    await db.commit()
    
    # MinIO cleanup — best effort, after commit
    prefix = f"{user_id}/"
    try:
        ...
    except Exception:
        ...
```

This matches the `delete_document()` pattern exactly. Without the explicit commit, an exception in MinIO cleanup could roll back the DB transaction.

### Current Files

| File | Current State |
|------|--------------|
| `healthcabinet/backend/app/users/service.py:28-36` | `delete_user_account()` — DB-only, no MinIO cleanup |
| `healthcabinet/backend/app/users/router.py:98-104` | `DELETE /users/me` → calls `delete_user_account()` |
| `healthcabinet/backend/app/documents/storage.py` | `delete_objects_by_prefix()` — already exists, handles pagination |
| `healthcabinet/backend/app/documents/service.py:333-386` | `delete_document()` — reference pattern for DB-first + MinIO |
| `healthcabinet/backend/app/core/config.py:54-59` | `MINIO_BUCKET`, `MINIO_ENDPOINT`, etc. |
| `healthcabinet/backend/tests/users/test_router.py:216-262` | Account deletion tests (DB-only, no MinIO assertions) |

### Testing Standards

- **Run tests:** `docker compose --profile test run --rm backend-test uv run pytest tests/users/test_router.py -v`
- **Mock pattern:** Patch `app.users.service.get_s3_client` and `app.users.service.delete_objects_by_prefix` (import into users/service module first)
- **Reference:** Document deletion tests in `tests/documents/test_router.py:306-425` show the established MinIO mocking pattern
- **Full backend test suite:** `docker compose --profile test run --rm backend-test uv run pytest tests/processing/ tests/users/ -v` (processing + users modules; full suite blocked by missing test DB)

### Backend API Contracts

**Endpoint:** `DELETE /api/v1/users/me`
**Auth:** `Authorization: Bearer <access_token>`
**Response:** 204 No Content (unchanged)
**Behavior change:** Now also deletes MinIO objects under `{user_id}/` prefix after DB commit. Response code and shape unchanged.

### Previous Story Learnings

From **Story 14-1** (just completed):
- Docker test profile requires image rebuild: `docker compose --profile test build backend-test`
- Backend processing tests pass (54/54); full suite blocked by missing `healthcabinet_test` DB
- Story pattern: implement → test → verify in Docker

From **Story 12-4** (which created the `DELETE /users/me` endpoint):
- Migration 013 changed consent_logs FK from CASCADE to SET NULL
- `audit_logs.user_id` explicitly set to NULL before user deletion
- MinIO cleanup was explicitly deferred: "deferred to Story 6.2 scope"

From **Epic 12 retro** (which flagged this issue):
- "MinIO orphan objects after account deletion — 12-4 backend deletes DB rows but not MinIO objects. Deferred to Story 6.2 scope. A user who exercises right-to-erasure today leaves document blobs in object storage. Regulatory risk."

From **Epic 13 retro** (which created Epic 14):
- Cleanup Sprint item #2: "MinIO orphaned object cleanup on account deletion"
- Action Item #4: "Deletion cascade architecture review — 10-min walkthrough of cascade order"

### Git Intelligence

Recent commits:
- `0ab59c8` — Story 14-1: SSE fetch-based auth migration (most recent)
- `6b37de7` — Story 13-5: frontend hardening
- Pattern: backend changes need `docker compose --profile test build backend-test` before running tests

### Files to Modify

| File | Changes |
|------|---------|
| `healthcabinet/backend/app/users/service.py` | Add MinIO cleanup after DB commit in `delete_user_account()` |
| `healthcabinet/backend/tests/users/test_router.py` | Add MinIO cleanup tests (called, failure logged, 204 preserved) |

### Files NOT to Modify

- `healthcabinet/backend/app/users/router.py` — endpoint unchanged (still calls `delete_user_account()`)
- `healthcabinet/backend/app/documents/storage.py` — `delete_objects_by_prefix()` already exists
- `healthcabinet/backend/app/documents/service.py` — single-document deletion unchanged
- `healthcabinet/backend/app/documents/models.py` — no schema changes
- `healthcabinet/backend/alembic/` — no migrations needed
- Any frontend files — backend-only story

### References

- [Source: healthcabinet/backend/app/users/service.py:28-36 — current delete_user_account() implementation]
- [Source: healthcabinet/backend/app/users/router.py:98-104 — DELETE /users/me endpoint]
- [Source: healthcabinet/backend/app/documents/service.py:333-386 — delete_document() DB-first + MinIO pattern]
- [Source: healthcabinet/backend/app/documents/storage.py — delete_object(), delete_objects_by_prefix() functions]
- [Source: healthcabinet/backend/app/documents/repository.py:147-185 — get_document_s3_key_optional() safe decryption]
- [Source: healthcabinet/backend/app/core/config.py:54-59 — MINIO_BUCKET, MINIO_ENDPOINT settings]
- [Source: healthcabinet/backend/tests/users/test_router.py:216-262 — existing account deletion tests]
- [Source: healthcabinet/backend/tests/documents/test_router.py:306-425 — document deletion + MinIO mock tests]
- [Source: _bmad-output/implementation-artifacts/epic-12-retro-2026-04-15.md — "MinIO orphan objects" flagged, deferred]
- [Source: _bmad-output/implementation-artifacts/epic-13-retro-2026-04-16.md — Cleanup Sprint item #2, Action Item #4]
- [Source: healthcabinet/backend/app/admin/models.py:11-42 — AuditLog model, admin_id RESTRICT FK]
- [Source: healthcabinet/backend/alembic/versions/013_consent_logs_retain_on_user_delete.py — consent_logs SET NULL migration]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Test DB `healthcabinet_test` had to be created (`CREATE DATABASE healthcabinet_test`) — pre-existing infra gap, same as Story 14-4 scope.
- All 82 tests pass across processing + users + export modules.

### Completion Notes List

- **MinIO prefix cleanup added to `delete_user_account()`:** After DB commit (explicit `await db.commit()`), calls `delete_objects_by_prefix(s3_client, bucket, f"{user_id}/")` via `asyncio.to_thread()`. Catches all objects under the user's S3 prefix regardless of encryption state.
- **DB-first pattern preserved:** Audit log redaction → user row deletion → commit → MinIO cleanup. Same pattern as `delete_document()`.
- **Best-effort with structured logging:** Success logs `account_deletion.storage_cleanup_complete` with count; failure logs `account_deletion.storage_cleanup_failed` with orphaned prefix for operator cleanup. MinIO failure never blocks the 204 response.
- **3 new tests added:** prefix cleanup called, MinIO failure swallowed, no-documents still runs prefix cleanup.
- **2 existing tests updated:** `test_delete_account_success` and `test_delete_account_retains_consent_logs` now mock `get_s3_client` and `delete_objects_by_prefix`.

### Change Log

- 2026-04-16: Story created — GDPR Article 17 MinIO orphan cleanup for account deletion
- 2026-04-16: Implementation complete — 2 files modified, 16/16 users tests pass, 82/82 combined tests pass

### File List

- `healthcabinet/backend/app/users/service.py` (modified — added MinIO prefix cleanup after DB commit)
- `healthcabinet/backend/tests/users/test_router.py` (modified — 3 new MinIO tests, 2 existing tests updated with MinIO mocks)

## Review Findings

- [x] [Review][Patch] MinIO cleanup ran twice per deletion (inline + deferred job) [service.py] — Inline cleanup removed; only deferred reconciliation job runs. Dead `_run_account_deletion_storage_cleanup` and `asyncio` import removed.
- [x] [Review][Defer] Worker `reconcile_deleted_user_storage` lacks isolated unit test — No test for the worker function itself; only tested via integration router test. Deferred.
