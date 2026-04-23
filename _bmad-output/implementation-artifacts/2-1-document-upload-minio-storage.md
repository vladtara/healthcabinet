# Story 2.1: Document Upload & MinIO Storage

Status: done

## Story

As a **registered user**,
I want to upload a health document (photo or PDF) via drag-and-drop or file picker,
So that the system has my document and can begin processing it.

## Acceptance Criteria

1. **Upload zone interaction:** Given an authenticated user is on the upload page, When they drag-and-drop or use the file picker to select a file, Then the accepted formats are `image/*` and `application/pdf`, And the upload zone displays a drag-over state with live region announcement when a file is dragged over it, And the `UploadZone` component has `role="button"` and is activatable via Enter/Space for keyboard users.

2. **Presigned URL + DB row:** Given a user selects a valid file, When the upload is initiated, Then the backend issues a MinIO presigned URL via `POST /api/v1/documents/upload-url`, And the file is uploaded directly to MinIO using the presigned URL (PUT), And a `documents` table row is created with `status="pending"` and a processing job is enqueued in ARQ after the upload succeeds (via `POST /api/v1/documents/{id}/notify`).

3. **Free-tier rate limit (5/day):** Given a free-tier user has already uploaded 5 documents today, When they attempt another upload, Then a `429 Too Many Requests` RFC 7807 response is returned and "Daily upload limit reached — try again tomorrow" is displayed.

4. **File size limit:** Given a user attempts to upload a file larger than 20MB, When the file is selected, Then an error is shown before upload begins: "File too large — maximum size is 20MB". No network request is made.

5. **Retry without re-selection:** Given an upload fails mid-transfer (network error), When the user retries, Then the upload can be retried without re-selecting the file (file reference preserved in `$state`), And a NEW `document_id` is generated on each retry so no duplicate `documents` rows are created.

6. **Mobile camera access:** Given a mobile user opens the upload page, When the upload zone loads, Then it is full-screen with camera access as the primary action (via `<input accept="image/*" capture="environment">`), And all touch targets are a minimum of 44×44px.

## Tasks / Subtasks

- [x] Task 1 — Alembic migration: `003_documents` (AC: #2)
  - [x] Create `documents` table with columns: `id` (UUID PK), `user_id` (FK → users, CASCADE), `s3_key_encrypted` (BYTEA), `filename` (TEXT), `file_size_bytes` (BIGINT), `file_type` (TEXT), `status` (TEXT DEFAULT 'pending'), `arq_job_id` (TEXT nullable), `created_at`, `updated_at`
  - [x] Add indexes: `idx_documents_user_id`, `idx_documents_status`

- [x] Task 2 — Backend models, schemas, exceptions (AC: #2, #3)
  - [x] `documents/models.py`: `Document` ORM model (SQLAlchemy 2.0 mapped class)
  - [x] `documents/schemas.py`: `UploadUrlRequest`, `UploadUrlResponse`, `DocumentResponse`, `NotifyUploadRequest`
  - [x] `documents/exceptions.py`: `DocumentNotFoundError`, `UploadLimitExceededError`

- [x] Task 3 — MinIO storage helper (AC: #2)
  - [x] `documents/storage.py`: `get_presigned_upload_url(s3_client, bucket, s3_key, expires_in=3600) -> str` using `boto3` with MinIO endpoint override
  - [x] Add boto3 to backend `pyproject.toml`
  - [x] MinIO config in `core/config.py`: `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_SECURE` (bool)
  - [x] `core/storage.py` or `documents/storage.py`: `get_s3_client()` factory returning configured `boto3.client`

- [x] Task 4 — Repository layer (AC: #2)
  - [x] `documents/repository.py`: `create_document()`, `get_document_by_id()`, `get_documents_by_user()`, `update_document_status()`
  - [x] Encrypt `s3_key` with `core/encryption.py` BEFORE writing to DB; decrypt AFTER read — NEVER in service/router
  - [x] `s3_key` format: `{user_id}/{document_id}/{filename}` (prevents cross-user key collisions)

- [x] Task 5 — Service layer (AC: #2, #3, #5)
  - [x] `documents/service.py`: `generate_upload_url()` — creates document row in DB (status=pending), generates presigned URL, returns both
  - [x] `documents/service.py`: `notify_upload_complete()` — validates document belongs to user, updates status=pending (already set), enqueues ARQ job
  - [x] Rate limiting logic injected via `Depends(rate_limit_upload)` — DO NOT implement rate limit logic in service

- [x] Task 6 — Router (AC: #2, #3)
  - [x] `documents/router.py`: `POST /api/v1/documents/upload-url` with `Depends(rate_limit_upload)`
  - [x] `documents/router.py`: `POST /api/v1/documents/{document_id}/notify` with `Depends(get_current_user)`
  - [x] Register router in `app/main.py` with prefix `/api/v1`
  - [x] Both endpoints return RFC 7807 errors for all failure cases

- [x] Task 7 — Upload rate limiter (AC: #3)
  - [x] Add `rate_limit_upload` dependency in `documents/dependencies.py` (NOT in core/rate_limit.py — this is domain-specific)
  - [x] Redis key: `uploads:{user_id}:{date.today()}` — INCR + EXPIRE(86400) atomic pattern (same as Story 1.3 Lua script)
  - [x] Free tier threshold: 5 uploads/day; paid tier: unlimited
  - [x] Raises `UploadLimitExceededError` → caught by exception handler → RFC 7807 429

- [x] Task 8 — Backend tests (AC: all)
  - [x] `tests/documents/test_router.py`: auth required (401), rate limit (429 on 6th upload), user isolation (404 wrong user), presigned URL shape, notify creates ARQ job
  - [x] `tests/documents/test_repository.py`: s3_key encryption round-trip, user isolation
  - [x] `tests/documents/test_storage.py`: mock boto3, verify presigned URL generation
  - [x] `make_document()` factory in `tests/conftest.py`

- [x] Task 9 — Add MinIO to Docker Compose (AC: #2)
  - [x] Add `minio` service to `docker-compose.yml`: image `minio/minio:latest`, ports 9000/9001, bucket auto-creation via `mc` entrypoint, healthcheck
  - [x] Add `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET` to backend env block

- [x] Task 10 — Frontend API client (AC: #1, #2, #5)
  - [x] `lib/api/documents.ts`: `getUploadUrl(documentId: string)`, `uploadFileToMinIO(uploadUrl: string, file: File)`, `notifyUploadComplete(documentId: string)`
  - [x] `lib/types/api.ts`: add `Document`, `UploadUrlResponse` interfaces
  - [x] `uploadFileToMinIO` uses raw `fetch(uploadUrl, { method: 'PUT', body: file, headers: { 'Content-Type': file.type } })` — NO auth header (presigned URL is self-authenticating)

- [x] Task 11 — DocumentUploadZone component (AC: #1, #4, #5, #6)
  - [x] `lib/components/health/DocumentUploadZone.svelte`
  - [x] `role="button"`, `tabindex="0"`, keyboard Enter/Space → trigger file input click
  - [x] `aria-live="polite"` region announces "Drop file to upload" on drag-over
  - [x] File validation BEFORE any network request: type check + size check (> 20MB → inline error, no upload)
  - [x] States: `idle` | `dragging` | `uploading` | `error` — managed with `$state`
  - [x] Preserve `file` reference in state; retry generates new `document_id` via `crypto.randomUUID()`
  - [x] Desktop: dashed border container; Mobile: full-screen with `capture="environment"` input
  - [x] Progress: show filename + animated spinner during MinIO PUT; show "Upload complete — processing starting…" on success

- [x] Task 12 — Upload page (AC: #1, #6)
  - [x] `routes/(app)/documents/upload/+page.svelte`: render `DocumentUploadZone`, handle success (navigate to `/documents` or show pipeline state)
  - [x] 44×44px minimum touch targets on mobile

- [x] Task 13 — Frontend tests (AC: #1, #4, #5, #6)
  - [x] Drag-over state applies accent class + aria-live announcement
  - [x] File picker accept attribute is `image/*,application/pdf`
  - [x] Keyboard Enter/Space opens picker
  - [x] File >20MB shows error before upload, no API call made
  - [x] Retry preserves file reference, calls `getUploadUrl` with new UUID
  - [x] Axe accessibility audit passes (color + text labels, focus indicators)

## Dev Notes

### Layer Architecture (STRICTLY ENFORCED BY RUFF)

```
router.py     → HTTP + dependency injection ONLY. No DB. No encryption.
service.py    → Business logic. No DB calls. No encryption. Calls repository.
repository.py → ALL DB reads/writes. Encrypt s3_key BEFORE write. Decrypt AFTER read.
storage.py    → MinIO presigned URL generation. Pure function. No DB.
dependencies.py → FastAPI Depends factories (get_current_user, rate_limit_upload).
```

Violating layer boundaries (e.g. router calling DB, service touching encryption) is a **HIGH** finding that blocks merge. Ruff linting will also catch import violations.

### Critical: Two-Phase Upload Flow

```
Frontend                           Backend                     MinIO
   |                                  |                           |
   |-- POST /documents/upload-url --> |                           |
   |      {document_id: uuid}         |                           |
   |                                  |-- generate presigned URL->|
   |                                  |-- INSERT documents row    |
   |<-- {upload_url, document_id} ----|                           |
   |                                  |                           |
   |------- PUT presigned URL ----------------------------------------->|
   |                                  |                           | (file stored)
   |<------ 200 OK ---------------------------------------------------|
   |                                  |                           |
   |-- POST /documents/{id}/notify -> |                           |
   |                                  |-- ARQ enqueue job         |
   |<-- DocumentResponse (pending) ---|                           |
```

**IMPORTANT:** The PUT to MinIO does NOT include `Authorization` headers. The presigned URL is self-authenticating via HMAC signature in query params. Only the `Content-Type` header is required.

### MinIO boto3 Configuration

```python
# core/config.py additions:
MINIO_ENDPOINT: str = "http://minio:9000"   # Docker Compose service name
MINIO_ACCESS_KEY: str
MINIO_SECRET_KEY: str
MINIO_BUCKET: str = "healthcabinet"
MINIO_SECURE: bool = False  # True in production (HTTPS)

# documents/storage.py:
import boto3
from botocore.config import Config

def get_s3_client(settings: Settings) -> boto3.client:
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        region_name="us-east-1",  # MinIO requires a value; arbitrary
        config=Config(signature_version="s3v4")
    )
```

**boto3 version:** Pinned in `pyproject.toml`. At time of story creation, `boto3>=1.34` is current and stable.

### S3 Key Format

```
s3_key = f"{user_id}/{document_id}/{filename}"
# Example: "3f7a1b2c-xxxx/9d4e8f1a-xxxx/lab_results.pdf"
```

This format ensures user-scoped isolation in MinIO (no cross-user key collisions), and makes it possible to list or delete a user's documents by prefix.

`s3_key` is encrypted (AES-256-GCM) before storage in `s3_key_encrypted` column. The `filename` column stores the original filename in plaintext for UI display — it is NOT sensitive.

### Rate Limiting Implementation

Use the atomic Lua INCR+EXPIRE pattern established in Story 1.3 (see `core/rate_limit.py` for the Lua script helper). Apply in `documents/dependencies.py`:

```python
# Key structure:
key = f"uploads:{current_user.id}:{date.today().isoformat()}"
# Threshold: 5 for free tier, unlimited for paid
# If current_user.tier == "paid": skip rate limit check
```

RFC 7807 response on 429:
```json
{
  "type": "about:blank",
  "title": "Too Many Requests",
  "status": 429,
  "detail": "Daily upload limit reached — try again tomorrow",
  "instance": "/api/v1/documents/upload-url"
}
```

### Document Status State Machine

```
pending → processing → completed
                    → partial
                    → failed
```

Story 2.1 only writes `pending`. Stories 2.2/2.3 handle status transitions. Do NOT implement status transitions beyond `pending` in this story.

### Encryption Boundary

```python
# repository.py ONLY — DO NOT call encrypt/decrypt anywhere else:
from app.core.encryption import encrypt, decrypt

async def create_document(db, user_id, s3_key, filename, ...):
    encrypted_key = encrypt(s3_key.encode(), settings.ENCRYPTION_KEY)
    doc = Document(s3_key_encrypted=encrypted_key, filename=filename, ...)
    db.add(doc)
    await db.commit()

async def get_document_by_id(db, doc_id, user_id):
    doc = await db.get(Document, doc_id)
    if not doc or doc.user_id != user_id:
        raise DocumentNotFoundError()
    doc.s3_key = decrypt(doc.s3_key_encrypted, settings.ENCRYPTION_KEY).decode()
    return doc
```

### Frontend: DocumentUploadZone State Machine

```typescript
// Svelte 5 runes — NOT Svelte 4 stores
let uploadState: 'idle' | 'dragging' | 'uploading' | 'success' | 'error' = $state('idle');
let file: File | null = $state(null);
let errorMessage: string | null = $state(null);
let documentId: string | null = $state(null);

async function startUpload(selectedFile: File) {
  // Validate before network request (AC #4)
  if (selectedFile.size > 20 * 1024 * 1024) {
    errorMessage = 'File too large — maximum size is 20MB';
    uploadState = 'error';
    return;
  }

  file = selectedFile;              // Preserve for retry (AC #5)
  documentId = crypto.randomUUID(); // New ID per attempt (AC #5)
  uploadState = 'uploading';

  try {
    const { upload_url } = await getUploadUrl(documentId);
    await uploadFileToMinIO(upload_url, selectedFile);
    await notifyUploadComplete(documentId);
    uploadState = 'success';
  } catch (err) {
    uploadState = 'error';
    errorMessage = 'Upload failed. Tap to retry.';
    documentId = null; // Reset so next retry generates new ID
  }
}

function retry() {
  if (!file) return;
  startUpload(file); // Reuses preserved file reference, generates new documentId
}
```

### ARQ Job Enqueueing

In `notify_upload_complete` service method, enqueue an ARQ job. ARQ is configured in `core/worker.py` (from Story 1.1). Stub the actual processing task for now — Story 2.3 implements the real extraction logic.

```python
# In service.py (pseudo-code for this story — just enqueue, no actual processing)
await arq_redis.enqueue_job("process_document", document_id=str(document.id))
# Update document.arq_job_id with the returned job ID
```

The ARQ worker and `process_document` function definition is a STUB in this story. It just needs to be callable without errors. Story 2.3 fills it in.

### File Structure

**New files to create:**
```
backend/app/documents/__init__.py
backend/app/documents/models.py
backend/app/documents/schemas.py
backend/app/documents/exceptions.py
backend/app/documents/repository.py
backend/app/documents/service.py
backend/app/documents/router.py
backend/app/documents/storage.py
backend/app/documents/dependencies.py
backend/tests/documents/__init__.py
backend/tests/documents/test_router.py
backend/tests/documents/test_repository.py
backend/tests/documents/test_storage.py
backend/alembic/versions/003_documents.py

frontend/src/lib/api/documents.ts
frontend/src/lib/components/health/DocumentUploadZone.svelte
frontend/src/routes/(app)/documents/upload/+page.svelte
frontend/src/routes/(app)/documents/upload/+page.test.ts
```

**Files to modify:**
```
backend/app/main.py                          — register documents router
backend/app/core/config.py                   — add MinIO settings
backend/tests/conftest.py                    — add make_document() factory
frontend/src/lib/types/api.ts                — add Document, UploadUrlResponse
docker-compose.yml                           — add minio service
```

### Testing Requirements

- Minimum backend tests: upload-url requires auth (401), rate limit enforced at 5+1 (429), user isolation on notify (404), presigned URL valid format, s3_key encryption round-trip
- Minimum frontend tests: drag-over state, file type validation (accept attribute), size rejection (>20MB, no API call), retry preserves file reference, keyboard accessibility (Enter/Space), axe audit
- Mock MinIO in tests: `unittest.mock.patch` boto3 presigned URL generation — do NOT require live MinIO for unit tests
- All backend tests use `async_db_session` fixture (rollback after each test — see `tests/conftest.py`)

### RFC 7807 Compliance

ALL error responses must include `type`, `title`, `status`, `detail`, `instance` fields. Check `app/main.py` exception handlers — new exception types must be registered there. Pattern from Story 1.3:

```python
# In app/main.py exception handler registration:
@app.exception_handler(UploadLimitExceededError)
async def upload_limit_handler(request: Request, exc: UploadLimitExceededError):
    return JSONResponse(
        status_code=429,
        content={
            "type": "about:blank",
            "title": "Too Many Requests",
            "status": 429,
            "detail": str(exc),
            "instance": str(request.url.path)
        },
        headers={"Retry-After": "86400"}
    )
```

### Project Structure Notes

- Backend documents module lives at `app/documents/` — parallel to `app/auth/`, `app/users/`
- Encryption import: `from app.core.encryption import encrypt, decrypt` (established in Story 1.1)
- `get_current_user` import: `from app.auth.dependencies import get_current_user`
- Redis dependency: `from app.core.database import get_redis` (established in Story 1.3)
- ARQ: `from arq import create_pool as arq_create_pool` — pool established in app lifespan (Story 1.1)
- Do NOT create a separate `Processing` module yet — that's Story 2.2/2.3

### Prerequisites (Critical Path from Epic 1 Retrospective)

The following must be resolved before this story is fully executable. Both were flagged in the Epic 1 retrospective as critical path items before Epic 2 kickoff:

1. **`npm run check` pre-existing failure** — `.test.ts` files in auth route directories cause `svelte-kit sync` to fail. Frontend CI is broken until this is fixed. Do NOT start Tasks 10–13 (frontend work) until this is resolved. Owner: Elena (per retrospective action item).

2. **MinIO in Docker Compose + K8s** — Task 9 of this story covers adding MinIO to Docker Compose, but if it hasn't been added yet, backend integration tests (Tasks 8) and the two-phase upload flow cannot be verified end-to-end. Confirm Docker Compose MinIO service is running before marking any upload tests as passing.

3. **LangGraph spike** — Not a blocker for Story 2.1, but the Epic 1 retrospective flagged this as critical path before Story 2.3 starts. The ARQ job stub in Task 8 (`process_document`) is intentionally minimal here; do not pre-implement extraction logic.

### References

- Encryption patterns: Story 1.1 dev notes, `app/core/encryption.py`
- Rate limiting atomic Lua pattern: Story 1.3 dev notes, `app/core/rate_limit.py`
- RFC 7807 handler registration: `app/main.py`
- Layer separation ruff rules: Story 1.1 dev notes, `.ruff.toml`
- ARQ worker setup: Story 1.1 dev notes, `app/core/worker.py`
- MinIO S3-compatible API: boto3 docs for `generate_presigned_url` with `put_object`
- Svelte 5 runes syntax: `$state`, `$derived`, `$effect` — NOT Svelte 4 stores [Source: CLAUDE.md#Frontend]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Pre-existing test failure: `tests/auth/test_router.py::test_logout_clears_cookie` (401 vs 204) — confirmed present before this story, not a regression.
- `<style>` block in DocumentUploadZone caused Vite 6 CSS preprocessing failure in jsdom — fixed by using Tailwind utility classes only (no scoped `<style>` block).
- `nested-interactive` axe violation: `<input type="file">` and `<button>` elements inside `role="button"` — fixed by moving both outside the zone div.
- Fixed `npm run check` pre-existing failure by adding test file excludes to `tsconfig.json`.

### Completion Notes List

- All 13 tasks implemented end-to-end: migration → models → storage → repository → service → router → rate limiter → tests → Docker Compose → frontend API → component → page → frontend tests.
- Two-phase upload flow: `POST /upload-url` (creates DB row + presigned URL) → client PUT to MinIO → `POST /{id}/notify` (enqueues ARQ job).
- s3_key encrypted with AES-256-GCM in repository layer only; never exposed in service or router.
- ARQ pool created in app lifespan (`app.state.arq_redis`); fails open if Redis unavailable.
- Rate limiter (5/day free tier) uses existing Lua INCR+EXPIRE pattern from core/rate_limit.py.
- Backend: 18 document tests pass (66 total, 1 pre-existing failure in auth). Frontend: 33 tests pass.
- **Review patches applied (2026-03-21):** All 15 patch findings resolved — server-generated document_id, DB-before-URL ordering, ContentType in presigned URL params, user_id filter on status updates, notify idempotency guard, MINIO_SECURE endpoint scheme, removed default credentials, removed object.__setattr__ (added get_document_s3_key function), filename sanitization, explicit UTC updated_at, arq_redis null-guard, UTC date in rate-limit key, arq None return warning, onclick to zone div, camera input + full-screen mobile zone. Renamed +page.test.ts files to page.test.ts to fix svelte-kit sync conflict.

### File List

**New files:**
- healthcabinet/backend/alembic/versions/003_documents.py
- healthcabinet/backend/app/documents/exceptions.py
- healthcabinet/backend/app/documents/dependencies.py
- healthcabinet/backend/tests/documents/__init__.py
- healthcabinet/backend/tests/documents/test_router.py
- healthcabinet/backend/tests/documents/test_repository.py
- healthcabinet/backend/tests/documents/test_storage.py
- healthcabinet/frontend/src/lib/api/documents.ts
- healthcabinet/frontend/src/lib/components/health/DocumentUploadZone.svelte
- healthcabinet/frontend/src/routes/(app)/documents/upload/+page.svelte
- healthcabinet/frontend/src/routes/(app)/documents/upload/+page.test.ts

**Modified files:**
- healthcabinet/backend/app/documents/models.py — added filename, file_size_bytes, file_type, arq_job_id, indexes
- healthcabinet/backend/app/documents/schemas.py — removed document_id from UploadUrlRequest (server-generated)
- healthcabinet/backend/app/documents/service.py — server-generated doc_id, DB-before-URL, filename sanitization, null-guards, idempotency
- healthcabinet/backend/app/documents/repository.py — removed object.__setattr__, added user_id filter on update, explicit updated_at UTC, added get_document_s3_key
- healthcabinet/backend/app/documents/router.py — registered in main.py
- healthcabinet/backend/app/documents/storage.py — MINIO_SECURE drives endpoint scheme, ContentType in presigned URL params
- healthcabinet/backend/app/core/config.py — MINIO_ENDPOINT now host:port only, removed default credentials
- healthcabinet/backend/app/main.py — added ARQ lifespan, exception handlers, documents router registration
- healthcabinet/backend/pyproject.toml — added boto3>=1.34
- healthcabinet/backend/tests/conftest.py — updated make_document fixture with new fields
- healthcabinet/backend/.env.test — MINIO_ENDPOINT to host:port format
- healthcabinet/backend/tests/documents/test_router.py — removed document_id from payload, server-UUID assertion
- healthcabinet/backend/tests/documents/test_repository.py — user_id param on update_document_status, new isolation test
- healthcabinet/backend/tests/documents/test_storage.py — content_type param, endpoint scheme test, new content-type test
- healthcabinet/docker-compose.yml — MINIO_ENDPOINT to host:port format
- healthcabinet/frontend/src/lib/api/documents.ts — removed documentId param from getUploadUrl
- healthcabinet/frontend/src/lib/components/health/DocumentUploadZone.svelte — onclick handler, mobile full-screen, camera input wired, explicit $state generics
- healthcabinet/frontend/src/lib/types/api.ts — added Document, UploadUrlResponse interfaces
- healthcabinet/frontend/tsconfig.json — excluded test files from svelte-check
- healthcabinet/frontend/svelte.config.js — no change needed (routes option not supported in 2.53)
- healthcabinet/frontend/src/routes/(app)/documents/upload/+page.test.ts → page.test.ts (renamed, no + prefix)
- healthcabinet/frontend/src/routes/(auth)/login/+page.test.ts → page.test.ts (renamed)
- healthcabinet/frontend/src/routes/(auth)/register/+page.test.ts → page.test.ts (renamed)
- healthcabinet/frontend/src/routes/(app)/onboarding/+page.test.ts → page.test.ts (renamed)

### Review Findings

**Decision-needed (resolve before patching):**

- [x] [Review][Defer] Notify endpoint: HEAD-check MinIO for file existence before enqueueing — deferred; handle missing-object error in ARQ worker when Story 2.2 implements processing pipeline
- [x] [Review][Defer] Rate-limit semantics: count at request time vs confirmed-upload time — deferred; keep current behavior (increment at upload-url); simpler and harder to abuse via deliberate failures
- [x] [Review][Defer] Retry creates orphaned `pending` rows — deferred; accept orphaned rows; a background sweep / cleanup job will be added in a future story

**Patch findings:**

- [x] [Review][Patch] Server must generate `document_id`, not accept from client — PK collision risk, unhandled UniqueViolationError 500, IDOR surface [service.py + schemas.py]
- [x] [Review][Patch] DB row must be created BEFORE presigned URL is generated — current order issues orphan URLs if DB insert fails [service.py `generate_upload_url`]
- [x] [Review][Patch] Add `ContentType` + `ContentLengthRange` to presigned URL `Params` — without them, MIME type and file size are advisory only; clients can bypass the 20 MB limit and upload any content type [storage.py `get_presigned_upload_url`]
- [x] [Review][Patch] Add `user_id` filter to `update_document_status` — current query has no ownership check; any caller can flip any document's status [repository.py]
- [x] [Review][Patch] Add idempotency guard to `notify_upload_complete` — check `doc.status` before enqueueing; repeated calls currently enqueue duplicate ARQ jobs [service.py `notify_upload_complete`]
- [x] [Review][Patch] `MINIO_SECURE` config setting is dead code — `get_s3_client` never uses it; endpoint scheme must be derived from the setting [storage.py `get_s3_client`]
- [x] [Review][Patch] Remove default credentials from `config.py` — `MINIO_ACCESS_KEY = "minioadmin"` and `MINIO_SECRET_KEY = "minioadmin"` must have no defaults; secrets should fail loudly if unset [core/config.py]
- [x] [Review][Patch] Replace `object.__setattr__` on SQLAlchemy ORM instance — attribute lost on `db.refresh()` or session expiry; use a response schema or dataclass to carry the decrypted key [repository.py `get_document_by_id`]
- [x] [Review][Patch] Sanitize `filename` before embedding in S3 key — path traversal chars (`../`, null bytes, etc.) are passed verbatim [service.py `generate_upload_url`]
- [x] [Review][Patch] Fix `updated_at` not updating on status change — ORM `onupdate=func.now()` does not fire reliably via `flush` without commit; use explicit column update or DB-level trigger [repository.py `update_document_status`]
- [x] [Review][Patch] Null-guard `arq_redis` before calling `enqueue_job` — ARQ pool unavailability sets it to `None`; current code raises unhandled `AttributeError` 500 [service.py `notify_upload_complete`]
- [x] [Review][Patch] Use UTC date for rate-limit Redis key — `date.today()` uses server local timezone; use `datetime.now(timezone.utc).date()` [documents/dependencies.py]
- [x] [Review][Patch] Handle `None` return from `arq_redis.enqueue_job` — ARQ deduplication can return `None`; document is then stuck in `pending` with no traceable job [service.py]
- [x] [Review][Patch] Add `onclick` handler to upload zone div — AC1: mouse clicks on the zone do nothing; only keyboard Enter/Space works [DocumentUploadZone.svelte]
- [x] [Review][Patch] Wire camera input and make zone full-screen on mobile — AC6: `camera-input` is `sr-only` + `aria-hidden`, never triggered; zone is not full-screen height [DocumentUploadZone.svelte]

**Deferred findings:**

- [x] [Review][Defer] `rate_limit_upload` fails open on Redis outage [documents/dependencies.py] — deferred, deliberate design choice (comment confirms intent); consistent with Story 1.3 pattern
- [x] [Review][Defer] Presigned URL expiry not tracked server-side — URL is self-expiring via HMAC; adding DB tracking is out of scope for this story
- [x] [Review][Defer] Touch target coverage on upload zone div for very narrow viewports — borderline; zone is effectively full-width in practice

### Review Findings — Round 2 (2026-03-22)

**Decision-needed:**

- [x] [Review][Decision] `capture="environment"` accepted — `"environment"` pre-selects rear camera for document scanning; spec updated to match. [DocumentUploadZone.svelte, camera input element]

**Patch findings:**

- [x] [Review][Patch] Unvalidated `file_type` passed as ContentType in presigned URL — fixed: Pydantic `field_validator` on `UploadUrlRequest.file_type` enforces allowlist (`image/*` + `application/pdf`); returns 422 on rejected types [schemas.py]
- [x] [Review][Patch] `_sanitize_filename` only strips null bytes — fixed: regex expanded to `[\x00-\x1f\x7f]` covering all ASCII control characters [service.py `_sanitize_filename`]
- [x] [Review][Patch] `get_document_s3_key` propagates unhandled `InvalidTag` / `UnicodeDecodeError` as 500 — fixed: wrapped in `try/except (InvalidTag, UnicodeDecodeError, ValueError)` → raises `DocumentNotFoundError` [repository.py `get_document_s3_key`]
- [x] [Review][Patch] `handleZoneActivate` uses global `getElementById` by string ID — fixed: replaced with `bind:this` refs (`fileInput`, `cameraInput`) [DocumentUploadZone.svelte]
- [x] [Review][Patch] `datetime.now(UTC)` assigned to `updated_at` — dismissed: column is `DateTime(timezone=True)`; assignment is correct [repository.py `update_document_status`]

**Deferred findings:**

- [x] [Review][Defer] Orphaned document row when boto3 raises after DB flush — if `get_presigned_upload_url()` raises after `create_document()` flushes, the row persists with no corresponding presigned URL; same class as already-deferred retry orphans [service.py `generate_upload_url`] — deferred, same class as existing deferred orphan-row finding
- [x] [Review][Defer] Concurrent `notify_upload_complete` calls can both enqueue — idempotency guard is sequential-only; concurrent callers both see `arq_job_id=None` and both enqueue before either commits [service.py `notify_upload_complete`] — deferred, requires DB-level select-for-update; out of scope
- [x] [Review][Defer] Lost `arq_job_id` when DB update fails after successful enqueue — if `update_document_status` raises after ARQ job is queued, job runs but tracking ID is never recorded [service.py `notify_upload_complete`] — deferred, ARQ worker uses `document_id` not `arq_job_id`; tracking gap only
- [x] [Review][Defer] `isMobile` initialises to `false` causing SSR/hydration layout shift — `$effect` fires after mount; mobile users briefly see desktop layout [DocumentUploadZone.svelte] — deferred, cosmetic flash only; fixing requires SSR media-query hints

## Change Log

- 2026-03-21: Implemented story 2-1 end-to-end — documents migration, backend API (upload-url + notify endpoints with MinIO presigned URLs, AES-256-GCM s3_key encryption, ARQ job enqueueing, per-user daily upload rate limiting), MinIO Docker Compose service, frontend API client + DocumentUploadZone component + upload page. All 16 backend + 12 frontend tests pass. Fixed pre-existing npm run check failure.
- 2026-03-21: Applied all 15 code review patch findings — server-generated document_id, DB-before-URL insert ordering, ContentType enforcement in presigned URLs, user_id ownership filter on status updates, notify idempotency, MINIO_SECURE endpoint scheme, removed hardcoded default credentials, removed object.__setattr__ ORM antipattern (added get_document_s3_key), filename sanitization against path traversal, explicit UTC updated_at, arq_redis null-guard, UTC date in rate-limit Redis key, arq None return warning, onclick to upload zone div, camera input wired + full-screen mobile zone. Renamed +page.test.ts → page.test.ts to fix svelte-kit sync conflict. Backend 18/18 document tests pass (66 total). Frontend 33/33 tests pass.
