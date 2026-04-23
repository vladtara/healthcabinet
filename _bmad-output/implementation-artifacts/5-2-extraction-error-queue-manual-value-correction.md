# Story 5.2: Extraction Error Queue & Manual Value Correction

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **admin**,
I want to view documents with extraction problems and manually correct wrong values with a logged reason,
so that users get accurate health data even when the AI pipeline makes mistakes.

## Acceptance Criteria

1. **Given** an admin views the extraction queue
   **When** the page loads
   **Then** all documents with `status='failed'`, `status='partial'`, any value with `confidence < 0.7`, or any value with `is_flagged=true` are listed
   **And** each entry shows: document ID, user ID (not name), upload date, status, and flag reason if applicable

2. **Given** an admin selects a document from the queue
   **When** they view its extracted values
   **Then** each value is shown with its current value, unit, confidence score, and a correction form

3. **Given** an admin submits a corrected value
   **When** the correction is saved
   **Then** an `audit_logs` row is written (immutable, append-only) with: `admin_id` (from JWT, never from request body), `document_id`, `health_value_id`, `value_name`, `original_value`, `new_value`, `reason`, `corrected_at` (UTC)
   **And** the `health_values` row is updated with the corrected value (re-encrypted)
   **And** the corrected value is immediately visible in the user's dashboard

4. **Given** an admin corrects a value
   **Then** no indicator is shown to the user that the value was admin-corrected (correction is transparent to user experience at MVP)

5. **Given** an admin attempts to submit a correction without a reason
   **When** the form is validated
   **Then** the submission is blocked and "Correction reason is required" is shown

## Tasks / Subtasks

### Backend — Database & Models

- [x] Task 1: Create `AuditLog` model in `app/admin/models.py` (AC: 3)
  - [x] Replace placeholder comment with ORM model
  - [x] Fields: `id` (UUID PK), `admin_id` (UUID FK → users.id, NOT NULL), `document_id` (UUID FK → documents.id ON DELETE SET NULL, nullable), `health_value_id` (UUID FK → health_values.id ON DELETE SET NULL, nullable), `value_name` (Text, NOT NULL), `original_value` (Text, NOT NULL — stored as plaintext string of decrypted numeric value), `new_value` (Text, NOT NULL), `reason` (Text, NOT NULL), `corrected_at` (TimestampTZ, server_default=func.now())
  - [x] `__tablename__ = "audit_logs"`
  - [x] Indexes: `idx_audit_logs_admin_id`, `idx_audit_logs_document_id`, `idx_audit_logs_health_value_id`
  - [x] Table is append-only — no UPDATE or DELETE operations ever exposed

- [x] Task 2: Create Alembic migration `010_audit_logs.py` (AC: 3)
  - [x] `revision = "010"`, `down_revision = "009"`
  - [x] Create `audit_logs` table matching the model
  - [x] Add index `idx_health_values_is_flagged` on `health_values.is_flagged` (action item A4 from Epic 4 retro — required before Story 5.2 queries)
  - [x] Add index `idx_health_values_confidence` on `health_values.confidence` (for `< 0.7` queue filter)

### Backend — Schemas

- [x] Task 3: Add queue and correction Pydantic schemas to `app/admin/schemas.py` (AC: 1, 2, 3, 5)
  - [x] `ErrorQueueItem(BaseModel)`: `document_id: UUID`, `user_id: UUID`, `filename: str`, `upload_date: datetime`, `status: str`, `value_count: int`, `low_confidence_count: int`, `flagged_count: int`, `failed: bool`
  - [x] `ErrorQueueResponse(BaseModel)`: `items: list[ErrorQueueItem]`, `total: int`
  - [x] `DocumentHealthValueDetail(BaseModel)`: `id: UUID`, `biomarker_name: str`, `canonical_biomarker_name: str`, `value: float`, `unit: str | None`, `reference_range_low: float | None`, `reference_range_high: float | None`, `confidence: float`, `needs_review: bool`, `is_flagged: bool`, `flagged_at: datetime | None`
  - [x] `DocumentQueueDetail(BaseModel)`: `document_id: UUID`, `user_id: UUID`, `filename: str`, `upload_date: datetime`, `status: str`, `values: list[DocumentHealthValueDetail]`
  - [x] `CorrectionRequest(BaseModel)`: `new_value: float`, `reason: str = Field(..., min_length=1, max_length=1000)` — reason is required (non-empty string)
  - [x] `CorrectionResponse(BaseModel)`: `audit_log_id: UUID`, `health_value_id: UUID`, `value_name: str`, `original_value: float`, `new_value: float`, `corrected_at: datetime`
  - [x] Keep existing `PlatformMetricsResponse` unchanged

### Backend — Repository

- [x] Task 4: Add error queue repository functions to `app/admin/repository.py` (AC: 1, 2)
  - [x] `get_error_queue_documents(db: AsyncSession) -> list[dict]`
    - Query documents WHERE `status IN ('failed', 'partial')` OR document has any health_value with `confidence < 0.7` OR `is_flagged = true`
    - Use `SELECT DISTINCT documents.id` with LEFT JOIN to health_values
    - For each document: aggregate `value_count`, `low_confidence_count` (confidence < 0.7), `flagged_count` (is_flagged = true)
    - Order by: failed first, then partial, then by `created_at DESC`
    - Do NOT decrypt any health values in this query — only aggregate counts
  - [x] `get_document_values_for_correction(db: AsyncSession, document_id: UUID) -> tuple[Document, list[HealthValue]]`
    - Load document + all its health_values
    - Return raw ORM objects — decryption happens in service layer via `_to_record` pattern from health_data/repository.py
  - [x] Keep existing `get_platform_metrics()` unchanged

- [x] Task 5: Add audit log repository functions to `app/admin/repository.py` (AC: 3)
  - [x] `create_audit_log(db: AsyncSession, *, admin_id: UUID, document_id: UUID, health_value_id: UUID, value_name: str, original_value: str, new_value: str, reason: str) -> AuditLog`
    - INSERT only — never UPDATE or DELETE
  - [x] `update_health_value_encrypted(db: AsyncSession, *, health_value_id: UUID, new_value_encrypted: bytes) -> None`
    - UPDATE health_values SET value_encrypted = new_value_encrypted WHERE id = health_value_id
    - Use `with_for_update()` to prevent concurrent modification
    - Call `await db.refresh(row)` after update per project-context rules

### Backend — Service

- [x] Task 6: Implement admin queue service in `app/admin/service.py` (AC: 1, 2, 3, 5)
  - [x] `get_error_queue(db: AsyncSession) -> ErrorQueueResponse`
    - Delegate to repository, map to schema
  - [x] `get_document_for_correction(db: AsyncSession, document_id: UUID) -> DocumentQueueDetail`
    - Load document + values from repository
    - Decrypt values using `_decrypt_numeric_value` from health_data/repository.py (import the helper)
    - Return decrypted values in response schema
  - [x] `submit_correction(db: AsyncSession, *, admin_id: UUID, health_value_id: UUID, request: CorrectionRequest) -> CorrectionResponse`
    - Load the HealthValue row (verify it exists → 404 if not)
    - Decrypt original value for audit log
    - Encrypt new value using `_encrypt_numeric_value` from health_data/repository.py
    - In a single transaction: (1) update health_values row with new encrypted value, (2) insert audit_log row
    - admin_id comes from `Depends(require_admin)` — NEVER from request body
    - Return `CorrectionResponse` with audit details
  - [x] Keep existing `fetch_platform_metrics()` unchanged

### Backend — Router

- [x] Task 7: Add queue and correction endpoints to `app/admin/router.py` (AC: 1, 2, 3, 5)
  - [x] `GET /admin/queue` → `ErrorQueueResponse` (requires `require_admin`)
    - Returns list of documents with extraction problems
  - [x] `GET /admin/queue/{document_id}` → `DocumentQueueDetail` (requires `require_admin`)
    - Returns document + all decrypted health values for correction
  - [x] `POST /admin/queue/{document_id}/values/{health_value_id}/correct` → `CorrectionResponse` (requires `require_admin`)
    - Body: `CorrectionRequest` (new_value + reason)
    - admin_id extracted from `current_user.id` via `Depends(require_admin)`
  - [x] Keep existing `GET /admin/metrics` unchanged
  - [x] No changes to `app/main.py` — admin router is already registered

### Backend — Tests

- [x] Task 8: Backend tests in `tests/admin/test_admin_queue.py` (AC: 1, 2, 3, 5)
  - [x] Test 1: Admin gets 200 with queue listing — fixture: 1 failed doc, 1 partial doc, 1 completed doc with a low-confidence value, 1 completed doc with a flagged value, 1 completed doc with all values OK → queue returns exactly 4 docs
  - [x] Test 2: Queue items have correct aggregate counts (value_count, low_confidence_count, flagged_count)
  - [x] Test 3: Admin gets 200 with document detail for correction — response contains decrypted health values
  - [x] Test 4: Admin submits correction — 200, audit_log row created with correct fields, health_value updated with new encrypted value that decrypts to new_value
  - [x] Test 5: Correction without reason → 422 validation error
  - [x] Test 6: Correction for non-existent health_value_id → 404
  - [x] Test 7: Non-admin user gets 403 on all queue endpoints
  - [x] Test 8: No JWT gets 401 on all queue endpoints
  - [x] Test 9: Empty queue returns `{ items: [], total: 0 }` when no problematic documents exist
  - [x] Use real DB (no mocks) following `tests/admin/test_admin_metrics.py` patterns
  - [x] Create fixtures: `make_document`, `make_health_value` helper functions (or reuse from conftest if they exist)

### Frontend — Types

- [x] Task 9: Add admin queue types to `src/lib/types/api.ts` (AC: 1, 2, 3)
  - [x] `ErrorQueueItem`: `document_id: string`, `user_id: string`, `filename: string`, `upload_date: string`, `status: string`, `value_count: number`, `low_confidence_count: number`, `flagged_count: number`, `failed: boolean`
  - [x] `ErrorQueueResponse`: `items: ErrorQueueItem[]`, `total: number`
  - [x] `DocumentHealthValueDetail`: mirror backend schema with snake_case
  - [x] `DocumentQueueDetail`: `document_id: string`, `user_id: string`, `filename: string`, `upload_date: string`, `status: string`, `values: DocumentHealthValueDetail[]`
  - [x] `CorrectionRequest`: `new_value: number`, `reason: string`
  - [x] `CorrectionResponse`: `audit_log_id: string`, `health_value_id: string`, `value_name: string`, `original_value: number`, `new_value: number`, `corrected_at: string`

### Frontend — API Functions

- [x] Task 10: Add admin queue API functions to `src/lib/api/admin.ts` (AC: 1, 2, 3)
  - [x] `getErrorQueue(): Promise<ErrorQueueResponse>` → `GET /api/v1/admin/queue`
  - [x] `getDocumentForCorrection(documentId: string): Promise<DocumentQueueDetail>` → `GET /api/v1/admin/queue/{documentId}`
  - [x] `submitCorrection(documentId: string, healthValueId: string, data: CorrectionRequest): Promise<CorrectionResponse>` → `POST /api/v1/admin/queue/{documentId}/values/{healthValueId}/correct`
  - [x] All use `apiFetch` from `$lib/api/client.svelte`

### Frontend — Error Queue Page

- [x] Task 11: Create admin error queue page at `src/routes/(admin)/admin/documents/+page.svelte` (AC: 1, 4)
  - [x] Route: `/admin/documents` (matches architecture: `(admin)/admin/documents/+page.svelte`)
  - [x] Use TanStack Query: `createQuery(() => ({ queryKey: ['admin', 'queue'], queryFn: getErrorQueue, refetchOnWindowFocus: false, refetchOnReconnect: false }))`
  - [x] Show loading skeleton while fetching (reuse Skeleton from shadcn-svelte)
  - [x] Show error state on failure
  - [x] Display table with columns: Document ID (truncated UUID), User ID (truncated UUID), Filename, Upload Date, Status (badge), Values, Low Confidence, Flagged
  - [x] Status badges: "failed" → Action red (#E05252), "partial" → Concerning orange (#F08430), "completed" → muted (document itself is OK but has flagged/low-confidence values)
  - [x] Each row links to correction detail page: `/admin/documents/{document_id}`
  - [x] Show "No documents requiring review" empty state when queue is empty
  - [x] Manual refresh button (same pattern as metrics page — `$queryClient.invalidateQueries`)

### Frontend — Document Correction Page

- [x] Task 12: Create document correction detail page at `src/routes/(admin)/admin/documents/[document_id]/+page.svelte` (AC: 2, 3, 5)
  - [x] Route: `/admin/documents/{document_id}`
  - [x] Use TanStack Query to fetch document detail
  - [x] Display document metadata: filename, status, user_id, upload date
  - [x] For each health value, show: biomarker name, current value + unit, confidence (with color: <0.7 → Concerning orange), is_flagged badge, reference range
  - [x] Inline correction form per value: text input for new value (numeric), text input for reason (required), Submit button
  - [x] On submit: call `submitCorrection`, show success toast/alert, invalidate query to refresh
  - [x] Validation: reason field required (non-empty), new_value must be numeric
  - [x] Disabled submit button until both fields valid
  - [x] Back link to queue page
  - [x] Svelte 5 runes: `$state`, `$derived` for form state — NOT Svelte 4 stores

### Frontend — Tests

- [x] Task 13: Frontend tests (AC: 1, 2, 3, 5)
  - [x] `src/routes/(admin)/admin/documents/page.test.ts`:
    - Mock `getErrorQueue`, assert table renders with correct columns and values
    - Test loading skeleton renders
    - Test error state renders
    - Test empty queue message renders when items is empty
  - [x] `src/routes/(admin)/admin/documents/[document_id]/page.test.ts`:
    - Mock `getDocumentForCorrection`, assert health values display with decrypted values
    - Mock `submitCorrection`, test form submission triggers API call with correct payload
    - Test reason-required validation prevents submission
  - [x] Follow `routes/(admin)/admin/page.test.ts` patterns for test setup

### Review Findings

- [x] [Review][Patch] Correction route ignores `document_id` and will update any `health_value_id`, even when it belongs to a different document [healthcabinet/backend/app/admin/router.py:63]
- [x] [Review][Patch] Whitespace-only correction reasons pass validation and get written into `audit_logs`, violating AC5's required-reason rule [healthcabinet/backend/app/admin/schemas.py:54]
- [x] [Review][Patch] Queue implementation omits the required flag-reason display for flagged documents (`User-flagged` per story note) [healthcabinet/frontend/src/routes/(admin)/admin/documents/+page.svelte:103]
- [x] [Review][Patch] Admin correction page fails `npm run check` because `documentId` remains `string | undefined` in query and mutation calls [healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte:13]
- [x] [Review][Patch] Admin backend fails `uv run mypy app/admin` due inaccurate repository return and collection typing [healthcabinet/backend/app/admin/repository.py:72]

## Dev Notes

### Endpoint Contracts (P3: Locked Before Implementation)

```
GET /api/v1/admin/queue
Authorization: Bearer <access_token>
Required: role=admin claim in JWT

Response 200 OK:
{
  "items": [
    {
      "document_id": "uuid",
      "user_id": "uuid",
      "filename": "blood_test.pdf",
      "upload_date": "2026-03-15T10:00:00Z",
      "status": "partial",
      "value_count": 12,
      "low_confidence_count": 3,
      "flagged_count": 1,
      "failed": false
    }
  ],
  "total": 1
}

Response 403: { "detail": "Admin access required" }
Response 401: (standard JWT error, headers: WWW-Authenticate: Bearer)
```

```
GET /api/v1/admin/queue/{document_id}
Authorization: Bearer <access_token>
Required: role=admin claim in JWT

Response 200 OK:
{
  "document_id": "uuid",
  "user_id": "uuid",
  "filename": "blood_test.pdf",
  "upload_date": "2026-03-15T10:00:00Z",
  "status": "partial",
  "values": [
    {
      "id": "uuid",
      "biomarker_name": "Cholesterol",
      "canonical_biomarker_name": "cholesterol_total",
      "value": 5.2,
      "unit": "mmol/L",
      "reference_range_low": 3.0,
      "reference_range_high": 5.0,
      "confidence": 0.45,
      "needs_review": true,
      "is_flagged": false,
      "flagged_at": null
    }
  ]
}

Response 404: { "detail": "Document not found" }
Response 403: { "detail": "Admin access required" }
Response 401: (standard JWT error)
```

```
POST /api/v1/admin/queue/{document_id}/values/{health_value_id}/correct
Authorization: Bearer <access_token>
Required: role=admin claim in JWT
Content-Type: application/json

Request Body:
{
  "new_value": 5.8,
  "reason": "Decimal misread by OCR — original lab shows 5.8 not 58"
}

Response 200 OK:
{
  "audit_log_id": "uuid",
  "health_value_id": "uuid",
  "value_name": "cholesterol_total",
  "original_value": 58.0,
  "new_value": 5.8,
  "corrected_at": "2026-04-01T12:00:00Z"
}

Response 404: { "detail": "Health value not found" }
Response 422: (Pydantic validation: reason required, new_value numeric)
Response 403: { "detail": "Admin access required" }
Response 401: (standard JWT error)
```

### Database — Existing Models Referenced

**Document** (`app/documents/models.py`):
- Status field: `String`, values: `"pending"`, `"processing"`, `"completed"`, `"partial"`, `"failed"`
- Has `idx_documents_status` index already
- FK: `user_id → users.id` with CASCADE delete

**HealthValue** (`app/health_data/models.py`):
- `value_encrypted: bytes` — AES-256-GCM encrypted numeric value
- `confidence: float` — 0.0–1.0, extraction confidence
- `is_flagged: bool` — set by user via `PUT /health-values/{id}/flag`
- `flagged_at: datetime | None` — idempotent, set on first flag only
- `needs_review: bool` — set by processing pipeline
- FK: `document_id → documents.id` with CASCADE delete
- FK: `user_id → users.id` with CASCADE delete
- **Column name is `biomarker_name` and `canonical_biomarker_name`** — NOT `name`
- **Column name is `value_encrypted`** — NOT `value`. Decryption happens in repository via `_decrypt_numeric_value()`
- **No `flag_reason` column** — epics mention "flag reason if applicable" but the model only has `is_flagged` + `flagged_at`; the queue display should show "User-flagged" as the reason text for flagged values

### Encryption — Critical Patterns

- `encrypt_bytes()` and `decrypt_bytes()` are in `app/core/encryption.py`
- **ONLY call from repository.py files** — never from service.py or router.py (enforced by Ruff)
- Health value encryption/decryption helpers are in `app/health_data/repository.py`:
  - `_encrypt_numeric_value(value: float) -> bytes`
  - `_decrypt_numeric_value(value_encrypted: bytes) -> float`
  - `_to_record(model: HealthValue) -> HealthValueRecord`
- For the correction flow: import these helpers into `app/admin/repository.py` (or re-implement — prefer import to avoid duplication)
- The correction endpoint must: (1) decrypt old value for audit log, (2) encrypt new value, (3) update row, (4) insert audit log — all in one transaction

### Audit Log Design

- **Append-only**: no UPDATE or DELETE operations exposed on audit_logs
- `admin_id` always from JWT `Depends(require_admin)` — NEVER from request body (project-wide security rule)
- `original_value` and `new_value` stored as plaintext strings in audit_logs — these are the decrypted numeric values, not encrypted blobs. This is intentional: the audit log must be human-readable for compliance
- `document_id` and `health_value_id` use `ON DELETE SET NULL` — audit records survive if the underlying data is deleted (GDPR delete removes health data but preserves admin audit trail)

### Auth Dependencies

- `require_admin` is in `app/auth/dependencies.py` — already exists and working
- Returns `User` model with `role='admin'` verified
- All three new endpoints use `Depends(require_admin)` for both auth and admin_id extraction

### Admin Router — Already Registered

The admin router is already registered in `app/main.py`:
```python
from app.admin.router import router as admin_router
app.include_router(admin_router, prefix="/api/v1")
```
No changes to `main.py` needed — new endpoints added to the existing router are automatically included.

### Frontend Patterns

**TanStack Query (Svelte 5 runes mode):**
- Use function form: `createQuery(() => ({ ... }))` — NOT plain object form (causes `options is not a function` error)
- Access data: `metricsQuery.data` — NOT `$metricsQuery.data` (rune-based, not Svelte 4 store)
- Invalidation: `queryClient.invalidateQueries({ queryKey: ['admin', 'queue'] })`
- Set `refetchOnWindowFocus: false` and `refetchOnReconnect: false` for admin pages (manual refresh only, matching Story 5.1 behavior)

**Svelte 5 Runes:**
- State: `let formValue = $state(0)` — NEVER `writable()`
- Derived: `let isValid = $derived(reason.length > 0 && !isNaN(newValue))` — NEVER `$: isValid = ...`
- Props: `const { documentId } = $props()` — NEVER `export let`
- Children: `{@render children()}` — NEVER `<slot />`

**Frontend types use snake_case** directly matching API — no transformation layer.

### Navigation — Admin Sidebar

Currently the admin layout uses the top-level app shell. The `/admin/documents` page needs to be navigable. Check if admin navigation exists in `routes/(admin)/+layout.svelte` or `routes/(admin)/admin/+page.svelte`. If there's no link to the documents queue page from the admin dashboard, add a link card or navigation item.

### Missing `is_flagged` Index (Epic 4 Retro Action Item A4)

The Epic 4 retrospective explicitly requires adding an `is_flagged` index before Story 5.2:
> "A4: Add `is_flagged` index on `health_values` table — Priority 🟡 High — Before Story 5.2"

This index MUST be in the migration. Also add a `confidence` index since the queue queries filter on `confidence < 0.7`.

### Testing Requirements

**Backend tests** (`tests/admin/test_admin_queue.py`):
- Use real database (same pattern as `tests/admin/test_admin_metrics.py`)
- No mocking DB queries
- Create fixture data with specific document statuses and health value confidence levels
- Assert exact values — not just lower bounds (lesson from Story 5.1 code review)
- Test 403 for non-admin, 401 for no token on all endpoints
- Verify audit_log row fields after correction (especially that admin_id matches the JWT user, not a request body field)

**Frontend tests** (Vitest):
- Mock API functions at module level
- Assert table columns and values render
- Test correction form validation (reason required)
- Run in Docker Compose: `docker compose exec frontend npm run test:unit`

**P1 rule (from Epic 4 retro):** Story does not close until tests pass in Docker Compose — no unknown test state.

### Epic 4 Learnings Applied

- **P3 principle**: All endpoint contracts locked above — do not deviate during implementation
- **Low patch count template (Story 4-3)**: Dev notes are exhaustive to minimize review patches
- **No architecture decisions in code review**: All schema, path, and type decisions are made above
- **Encryption boundary**: Repository-only — service and router never touch `encrypt_bytes`/`decrypt_bytes` directly

### Project Structure — Files to Create/Modify

**Backend (new files):**
- `healthcabinet/backend/alembic/versions/010_audit_logs.py` — migration
- `healthcabinet/backend/tests/admin/test_admin_queue.py` — test suite

**Backend (modified files):**
- `healthcabinet/backend/app/admin/models.py` — replace placeholder with AuditLog model
- `healthcabinet/backend/app/admin/schemas.py` — add queue + correction schemas (keep PlatformMetricsResponse)
- `healthcabinet/backend/app/admin/repository.py` — add queue + correction functions (keep get_platform_metrics)
- `healthcabinet/backend/app/admin/service.py` — add queue + correction functions (keep fetch_platform_metrics)
- `healthcabinet/backend/app/admin/router.py` — add 3 new endpoints (keep GET /metrics)

**Frontend (new files):**
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/+page.svelte` — error queue list
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte` — correction detail
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/page.test.ts` — queue page tests
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/page.test.ts` — correction page tests

**Frontend (modified files):**
- `healthcabinet/frontend/src/lib/types/api.ts` — add queue + correction types
- `healthcabinet/frontend/src/lib/api/admin.ts` — add queue + correction API functions

**No changes to:**
- `app/auth/dependencies.py` — `require_admin` already exists
- `app/main.py` — admin router already registered
- `app/health_data/models.py` — HealthValue model unchanged
- `app/documents/models.py` — Document model unchanged
- `routes/(admin)/+layout.svelte` — role guard already implemented
- Any Epic 1–4 domain files

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.2: Extraction Error Queue & Manual Value Correction]
- [Source: _bmad-output/planning-artifacts/prd.md#FR35, FR36 — Admin queue and manual correction]
- [Source: _bmad-output/planning-artifacts/architecture.md#Admin & Operations (FR34–FR38)]
- [Source: _bmad-output/planning-artifacts/architecture.md#Health Values Schema]
- [Source: _bmad-output/planning-artifacts/architecture.md#audit_logs in initial schema list]
- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md#Admin documents page — GET /api/v1/admin/queue]
- [Source: _bmad-output/implementation-artifacts/5-1-admin-platform-metrics-dashboard.md — admin router patterns, TanStack Query patterns, testing patterns]
- [Source: _bmad-output/implementation-artifacts/5-0-langchain-ai-migration.md — encryption boundary, recent git patterns]
- [Source: _bmad-output/implementation-artifacts/epic-4-retro-2026-03-30.md — P1/P2/P3 principles, action item A4 (is_flagged index)]
- [Source: _bmad-output/project-context.md — encryption rules, testing rules, SQLAlchemy patterns]
- [Source: healthcabinet/backend/app/health_data/models.py — HealthValue model with is_flagged, flagged_at, confidence, value_encrypted]
- [Source: healthcabinet/backend/app/health_data/repository.py — _encrypt_numeric_value, _decrypt_numeric_value, _to_record, flag_health_value]
- [Source: healthcabinet/backend/app/documents/models.py — Document model with status field]
- [Source: healthcabinet/backend/app/admin/router.py — existing GET /admin/metrics endpoint pattern]
- [Source: healthcabinet/backend/app/auth/dependencies.py — require_admin dependency]
- [Source: healthcabinet/backend/app/core/encryption.py — encrypt_bytes, decrypt_bytes (repository-only)]
- [Source: healthcabinet/frontend/src/lib/types/api.ts — HealthValueItem, Document, AdminMetrics types]
- [Source: healthcabinet/frontend/src/lib/api/admin.ts — getAdminMetrics using apiFetch pattern]

## Dev Agent Record

### Agent Model Used
claude-opus-4-6

### Debug Log References

### Completion Notes List

All 13 tasks completed. Backend: AuditLog model, migration 010 with indexes (is_flagged, confidence), schemas (ErrorQueueItem, ErrorQueueResponse, DocumentHealthValueDetail, DocumentQueueDetail, CorrectionRequest, CorrectionResponse), repository functions (get_error_queue_documents, get_document_values_for_correction, create_audit_log, update_health_value_encrypted), service functions (get_error_queue, get_document_for_correction, submit_correction), router endpoints (GET /admin/queue, GET /admin/queue/{id}, POST /admin/queue/{id}/values/{hv_id}/correct). Frontend: types added to api.ts, API functions in admin.ts, error queue page at /admin/documents, correction detail page at /admin/documents/{id}, tests passing (15 backend, 6 queue page, 6 correction page). Note: fix_func_case SQLAlchemy issue during implementation (case() vs func.case()). All tests pass in Docker Compose.

### File List

**Backend (new files):**
- `healthcabinet/backend/alembic/versions/010_audit_logs.py`
- `healthcabinet/backend/tests/admin/test_admin_queue.py`

**Backend (modified files):**
- `healthcabinet/backend/app/admin/models.py`
- `healthcabinet/backend/app/admin/schemas.py`
- `healthcabinet/backend/app/admin/repository.py`
- `healthcabinet/backend/app/admin/service.py`
- `healthcabinet/backend/app/admin/router.py`
- `healthcabinet/backend/tests/conftest.py` (added make_health_value fixture)

**Frontend (new files):**
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/+page.svelte`
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte`
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/page.test.ts`
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/page.test.ts`
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/AdminQueuePageTestWrapper.svelte`
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/AdminCorrectionPageTestWrapper.svelte`

**Frontend (modified files):**
- `healthcabinet/frontend/src/lib/types/api.ts`
- `healthcabinet/frontend/src/lib/api/admin.ts`
- `healthcabinet/frontend/src/routes/(admin)/admin/+page.svelte` (added navigation link to documents queue)

**No changes to:**
- `app/auth/dependencies.py` — `require_admin` already exists
- `app/main.py` — admin router already registered
- `app/health_data/models.py` — HealthValue model unchanged
- `app/documents/models.py` — Document model unchanged
- `routes/(admin)/+layout.svelte` — role guard already implemented

## Change Log
- Addressed code review findings - N/A (story just completed dev, no review yet)
