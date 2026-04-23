# Story 6.1: Full Data Export

Status: done

## Story

As a **registered user**,
I want to download a complete export of all data held about me,
So that I can exercise my GDPR Article 20 right to data portability.

## Acceptance Criteria

1. **Given** an authenticated user requests a data export **When** `POST /api/v1/users/me/export` is called **Then** a ZIP file is streamed back containing:
   - `documents/` — all uploaded documents (decrypted from MinIO)
   - `health_values.csv` — all extracted values (decrypted) with columns: `document_id, biomarker_name, canonical_biomarker_name, value, unit, reference_low, reference_high, confidence, needs_review, is_flagged, flagged_at, flag_reviewed_at, extracted_at`
   - `ai_interpretations.csv` — all AI interpretation texts (decrypted from `ai_memories`) with `document_id` and `created_at`
   - `admin_corrections.csv` — all admin correction records linked to the user's documents or health values at export time with columns: `document_id, value_name, original_value, new_value, reason, corrected_at`
   - `consent_log.csv` — full consent history with `consent_type, consented_at, privacy_policy_version`
   - `summary.txt` — human-readable account summary including registration date, `account_status`, and `last_login_at`

2. **Given** the export is generated **When** it is streamed **Then** all encrypted values are decrypted at the repository layer before inclusion **And** `user_id` is taken from the authenticated JWT (never from the request body) **And** no page reload is required (download initiates directly from the browser).

3. **Given** a user has no uploaded documents **When** they request an export **Then** a valid ZIP is returned containing only `consent_log.csv` and `summary.txt` (no empty error).

## Tasks / Subtasks

- [x] Task 1: Backend — export repository functions (AC: #1, #2)
  - [x] 1.1 Create `app/users/export_repository.py` with functions that collect all user data from each table, decrypting encrypted fields at the repository layer
  - [x] 1.2 Add `list_consent_logs_by_user()` to `app/auth/repository.py`
  - [x] 1.3 Add `list_audit_logs_by_user_documents()` to `app/admin/repository.py` (joins `audit_logs` through user's `document_id` and `health_value_id`)
  - [x] 1.4 Add `list_ai_memories_by_user()` to `app/ai/repository.py` with decrypted interpretation text
- [x] Task 2: Backend — export service and ZIP builder (AC: #1, #2, #3)
  - [x] 2.1 Create `app/users/export_service.py` with `build_export_zip()` that orchestrates data collection and writes ZIP to an in-memory buffer
  - [x] 2.2 Generate each CSV using Python `csv` module (not pandas) with explicit column headers
  - [x] 2.3 Generate `summary.txt` with account metadata (email, created_at, account_status, last_login_at)
  - [x] 2.4 For each document, fetch the actual file bytes from MinIO via `get_object_bytes()` and write to `documents/{filename}` in the ZIP
  - [x] 2.5 Handle empty-data case: if no documents exist, ZIP still contains `consent_log.csv` and `summary.txt`
- [x] Task 3: Backend — export endpoint (AC: #1, #2)
  - [x] 3.1 Add `POST /users/me/export` to `app/users/router.py` returning `StreamingResponse` with `application/zip` content type
  - [x] 3.2 Set `Content-Disposition: attachment; filename="healthcabinet-export-{date}.zip"`
  - [x] 3.3 Use `Depends(get_current_user)` for auth — user_id from JWT only
- [x] Task 4: Backend — tests (AC: #1, #2, #3)
  - [x] 4.1 Test export endpoint returns valid ZIP with all expected files
  - [x] 4.2 Test CSV contents have correct columns and decrypted values
  - [x] 4.3 Test empty-document user gets ZIP with only consent_log.csv and summary.txt
  - [x] 4.4 Test export is scoped to authenticated user only (no IDOR)
  - [x] 4.5 Test admin_corrections.csv includes correction records linked to user's documents
- [x] Task 5: Frontend — export button on settings page (AC: #2)
  - [x] 5.1 Add "Data & Privacy" section to `/settings` page with "Download My Data" button
  - [x] 5.2 Add `exportMyData()` to `src/lib/api/users.ts` that calls `POST /api/v1/users/me/export` and triggers browser download from the response blob
  - [x] 5.3 Show loading state during export generation, success toast on completion, error toast on failure
- [x] Task 6: Docker Compose validation
  - [x] 6.1 Run `docker compose exec backend uv run pytest tests/users/` — all pass
  - [x] 6.2 Run `docker compose exec frontend npm run test:unit` — all pass

## Dev Notes

### Architecture Compliance

- **Encryption boundary:** All decryption happens in repository layer only (`encrypt_bytes`/`decrypt_bytes` from `app/core/encryption.py`). Never decrypt in service or router. [Source: app/core/encryption.py, architecture enforcement rule]
- **User ID source:** Always from `Depends(get_current_user)` — never from request body/params. [Source: app/auth/dependencies.py]
- **Error format:** RFC 7807 responses. Follow existing exception handler pattern in `app/main.py`.
- **DB operations:** Async SQLAlchemy 2.0 only. Use `select()` style, not legacy Query API.

### Existing Code to Reuse (DO NOT reinvent)

| What | Where | How to use |
|------|-------|------------|
| Health value decryption | `app/health_data/repository.py:_to_record()` + `HealthValueRecord` dataclass | Reuse `list_values_by_user()` — already returns decrypted records with corrupt-record handling |
| Document listing | `app/documents/repository.py:get_documents_by_user()` | Returns all docs for user; use `get_document_s3_key()` to decrypt each S3 key |
| S3 file download | `app/documents/storage.py:get_object_bytes()` | Pass `get_s3_client()` + `settings.MINIO_BUCKET` + decrypted s3_key |
| AI interpretation decryption | `app/ai/repository.py:list_user_ai_context()` | Returns decrypted interpretation text; adapt to also return `created_at` |
| Consent log creation | `app/auth/repository.py:create_consent_log()` | Model is `app/users/models.py:ConsentLog`; need new list query |
| Auth dependency | `app/auth/dependencies.py:get_current_user` | Standard dependency injection for all user-scoped endpoints |

### Key Data Models (current schema)

**users** (`app/auth/models.py`): `id, email, hashed_password, role, tier, account_status, last_login_at, created_at, updated_at`

**documents** (`app/documents/models.py`): `id, user_id, s3_key_encrypted (bytes), filename, file_size_bytes, file_type, status, created_at, updated_at`

**health_values** (`app/health_data/models.py`): `id, user_id, document_id, biomarker_name, canonical_biomarker_name, value_encrypted (bytes), unit, reference_range_low, reference_range_high, measured_at, confidence, needs_review, is_flagged, flagged_at, flag_reviewed_at, flag_reviewed_by_admin_id, created_at`

**ai_memories** (`app/ai/models.py`): `id, user_id, document_id, context_json_encrypted, interpretation_encrypted, model_version, safety_validated, created_at, updated_at`

**audit_logs** (`app/admin/models.py`): `id, admin_id, user_id, document_id (SET NULL), health_value_id (SET NULL), value_name, original_value, new_value, reason, corrected_at` — `user_id` snapshots export attribution even after document/value deletion; legacy rows can still fall back through `document_id → documents.user_id` or `health_value_id → health_values.user_id`

**consent_logs** (`app/users/models.py`): `id, user_id, consent_type, privacy_policy_version, consented_at`

### Implementation Details

**ZIP assembly approach:** Build the ZIP in memory using `io.BytesIO` + `zipfile.ZipFile`. For large exports, this is acceptable at MVP scale (single user's data). Return via `StreamingResponse(buffer, media_type="application/zip")`.

**CSV generation:** Use `csv.writer` with `io.StringIO`. Columns must match the AC exactly. Write the StringIO content as UTF-8 bytes into the ZIP.

**Document file retrieval from MinIO:** For each document row, decrypt the s3_key via `get_document_s3_key()`, then fetch bytes via `get_object_bytes()` in a `asyncio.to_thread()` call (boto3 is synchronous). Handle decryption failures gracefully — skip the document file but log a warning, don't fail the entire export.

**Admin corrections query:** `audit_logs.user_id` is the primary export key so corrections remain attributable after `document_id` / `health_value_id` are later nulled by deletion flows. Query: select `audit_logs` where `audit_logs.user_id = current user`, with a legacy fallback to the old document/health-value joins for rows not yet backfilled.

**`summary.txt` content:**
```
HealthCabinet Data Export
=========================
Email: {user.email}
Account created: {user.created_at}
Account status: {user.account_status}
Last login: {user.last_login_at or "Never"}
Export generated: {datetime.now(UTC)}
Documents: {count}
Health values: {count}
AI interpretations: {count}
```

### Frontend Implementation

**Settings page location:** `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` — currently only has medical profile. Add a new "Data & Privacy" card section below the existing profile sections.

**API client pattern:** Follow existing pattern in `src/lib/api/users.ts`. For binary download, use:
```typescript
const response = await fetch(`${BASE_URL}/api/v1/users/me/export`, {
  method: 'POST',
  headers: authHeaders(),
});
const blob = await response.blob();
const url = URL.createObjectURL(blob);
// trigger download via hidden <a> element
```

**UI states:** Loading spinner on button during export → success toast "Export downloaded" → error toast on failure. Use Svelte 5 runes (`$state`) for loading state.

**Design tokens:** Follow dark-neutral theme. Button should be secondary style (not primary). Place in a card with heading "Data & Privacy" and description text about GDPR data portability rights. No modal — direct download.

### Testing Strategy

**Backend tests** go in `tests/users/test_export.py` (new file). Use existing test fixtures from `tests/conftest.py`: `async_db_session`, `make_user()`, `make_document()`. Mock MinIO calls with `unittest.mock.patch` on `get_object_bytes` and `get_s3_client`. Do NOT mock the database — use real async DB session.

**Frontend tests:** Add to `healthcabinet/frontend/src/routes/(app)/settings/page.test.ts` or create a new test file for the export button component.

**All tests run in Docker Compose:**
- Backend: `docker compose exec backend uv run pytest tests/users/test_export.py -v`
- Frontend: `docker compose exec frontend npm run test:unit`

### Project Structure Notes

- New files: `app/users/export_repository.py`, `app/users/export_service.py`, `tests/users/test_export.py`
- Modified files: `app/users/router.py`, `app/auth/repository.py`, `app/admin/repository.py` (new query function), `app/ai/repository.py` (new list function), `src/routes/(app)/settings/+page.svelte`, `src/lib/api/users.ts`
- No new migrations required — this story only reads existing data
- No new dependencies required — `zipfile`, `csv`, `io` are Python stdlib

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 6, Story 6.1]
- [Source: _bmad-output/planning-artifacts/architecture.md — GDPR boundary, users module structure]
- [Source: _bmad-output/planning-artifacts/prd.md — FR5, FR32, NFR21]
- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md — Settings page wireframe]
- [Source: _bmad-output/implementation-artifacts/epic-5-retro-2026-04-02.md — Epic 6 prep items, data inventory]

### Previous Story Intelligence

**From Epic 5 retrospective:** Epic 6 must account for Epic 5 data model additions: `users.account_status`, `users.last_login_at`, `health_values.flag_reviewed_at`, `health_values.flag_reviewed_by_admin_id`, and admin correction records in `audit_logs`. All of these are included in this story's export scope.

**From Story 5.4 (last completed story):**
- LangGraph processing graph is now in place — no impact on export, but `ai_memories` table structure is stable
- Test pattern: use `docker compose exec backend uv run pytest` for validation, rebuild `backend-test` if needed
- Code conventions: async SQLAlchemy 2.0, `select()` style, type hints, structlog for logging

**From deferred work:** No items directly block this story. The `upsert_ai_interpretation` TOCTOU race is a write-path issue; export is read-only.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (initial implementation), GPT-5 Codex (review patch follow-up)

### Debug Log References

- Backend tests: 331 passed, 1 skipped, 0 failures (`uv run pytest`)
- Export tests: 10/10 passed (`uv run pytest tests/users/test_export.py`)
- Backend static checks: `uv run mypy app/` passed, `uv run ruff check app/ tests/users/test_export.py` passed
- Frontend tests: 200 passed, 21 test files (`npm run test:unit`)
- Frontend targeted export/settings tests: 3/3 passed
- Frontend type check: `npm run check` passed with 2 pre-existing admin-page accessibility warnings
- Frontend lint tooling note: `npm run lint` is still blocked by pre-existing Prettier/build-output issues unrelated to Story 6.1

### Completion Notes List

- Extended `HealthValueRecord` dataclass with `flag_reviewed_at` field (required by AC but missing from the record)
- Created new `list_ai_memories_by_user()` in ai/repository.py returning `created_at` (AC requirement) instead of reusing `list_user_ai_context()` which returns `updated_at`
- Used `get_document_s3_key_optional()` for graceful S3 key decryption failure handling during export
- Frontend export now uses `apiStream()` so token refresh, auth redirect handling, and RFC 7807 parsing work for ZIP downloads
- All CSVs match AC column specifications exactly
- Empty-data case handled: ZIP contains consent_log.csv and summary.txt even with no documents
- IDOR prevention verified: export scoped to authenticated user via `Depends(get_current_user)`
- Review patch follow-up: export now includes unvalidated AI interpretations, sanitizes and deduplicates ZIP document filenames, quotes/sanitizes CSV output, and discloses skipped corrupt rows in `summary.txt`
- Review patch follow-up: concurrent document deletion no longer crashes export, S3 client is closed after ZIP creation, and blob URLs are revoked asynchronously after download starts
- Code review fix: `summary.txt` now counts only document files actually written into the ZIP and discloses skipped document retrievals
- Follow-up fix: audit logs now persist `user_id`, exports still include `admin_corrections.csv` after document deletion, and the migration backfills existing rows where attribution is still recoverable

### File List

**New files:**
- `healthcabinet/backend/app/users/export_repository.py`
- `healthcabinet/backend/app/users/export_service.py`
- `healthcabinet/backend/tests/users/test_export.py`
- `healthcabinet/frontend/src/lib/api/users.test.ts`

**Modified files:**
- `healthcabinet/backend/app/users/router.py` — added POST /me/export endpoint
- `healthcabinet/backend/app/health_data/repository.py` — added flag_reviewed_at to HealthValueRecord and _to_record
- `healthcabinet/backend/app/auth/repository.py` — added list_consent_logs_by_user()
- `healthcabinet/backend/app/admin/repository.py` — added list_audit_logs_by_user_documents(); later tightened type annotation during review patch follow-up
- `healthcabinet/backend/app/ai/repository.py` — added list_ai_memories_by_user()
- `healthcabinet/frontend/src/lib/api/users.ts` — added exportMyData(); later switched export download path to `apiStream()` with RFC 7807 parsing
- `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` — added Data & Privacy section and clearer export error handling

### Review Findings

- [x] [Review][Decision] AI interpretations filtered by `safety_validated == True` — AC1 says "all AI interpretation texts" but query excludes unvalidated records; GDPR Article 20 requires all data held about the user [ai/repository.py:list_ai_memories_by_user]
- [x] [Review][Decision] Empty-user export includes extra CSV files — AC3 says "only `consent_log.csv` and `summary.txt`" but implementation unconditionally writes header-only `health_values.csv`, `ai_interpretations.csv`, `admin_corrections.csv` [export_service.py:build_export_zip]
- [x] [Review][Fix] Orphaned audit logs invisible after SET NULL — added persistent `audit_logs.user_id`, export query fallback for legacy rows, and a regression test covering deleted-document export [admin/repository.py:list_audit_logs_by_user_documents]
- [x] [Review][Patch] ZIP Slip: unsanitized `doc.filename` used as ZIP entry path — path traversal if filename contains `../` [export_service.py:71]
- [x] [Review][Patch] Blob URL revoked before browser download completes — `URL.revokeObjectURL(url)` runs synchronously after `a.click()` which is async [frontend/src/lib/api/users.ts:exportMyData]
- [x] [Review][Patch] Raw `fetch` bypasses `apiFetch` token-refresh logic — expired 15-min access token causes 401 with no retry/refresh [frontend/src/lib/api/users.ts:exportMyData]
- [x] [Review][Patch] Filename collision: duplicate `doc.filename` silently overwrites earlier ZIP entries — user loses documents with no warning [export_service.py:71]
- [x] [Review][Patch] `DocumentNotFoundError` uncaught in `get_document_file_bytes` — concurrent document deletion between listing and download crashes entire export [export_repository.py:get_document_file_bytes]
- [x] [Review][Patch] CSV `created_at` for AI interpretations writes literal `"None"` — `entry.get("created_at", "")` finds key with `None` value, `str(None)` → `"None"` [export_service.py:ai_rows]
- [x] [Review][Patch] Corrupted health values silently dropped from export — `hv_result.skipped_corrupt_records` is ignored; GDPR export omits data with zero disclosure [export_service.py:build_export_zip]
- [x] [Review][Patch] Frontend error handling discards RFC 7807 body — throws `{ status }` without parsing error response body [frontend/src/lib/api/users.ts:exportMyData]
- [x] [Review][Patch] Misleading docstring — `export_repository.py` claims "All decryption happens at this layer" but actual decryption occurs in delegated repositories [export_repository.py:1]
- [x] [Review][Defer] Unbounded in-memory ZIP — no aggregate size cap on document bytes fetched into BytesIO buffer; acceptable at MVP scale per spec [export_service.py:build_export_zip] — deferred, pre-existing architectural choice
- [x] [Review][Defer] No rate limiting on export endpoint — expensive operation (N S3 downloads + ZIP compression) with no per-endpoint rate limiter [users/router.py:export_my_data] — deferred, pre-existing
- [x] [Review][Defer] Sequential data fetching — five independent DB queries awaited sequentially instead of `asyncio.gather()` [export_service.py:build_export_zip] — deferred, performance optimization

## Change Log

- 2026-04-02: Implemented full data export (Story 6.1) — GDPR Article 20 data portability endpoint and frontend UI
- 2026-04-02: Addressed review patch findings for export ZIP safety, AI export scope, corrupt-row disclosure, router cleanup, and frontend download/auth handling
- 2026-04-02: Fixed code review follow-up for `summary.txt` document counts when document retrieval is skipped

## Review Findings (2026-04-02)

### Patches (action items)
- [x] [Review][Patch] S3 client never closed — connection pool leak [router.py]
- [x] [Review][Patch] ZIP path traversal via unsanitized document filename [export_service.py]
- [x] [Review][Patch] CSV fields not quoted — embedded delimiters/newlines corrupt output [export_service.py]
- [x] [Review][Patch] Non-UTF-8 OCR bytes cause UnicodeEncodeError crash [export_service.py]
- [x] [Review][Patch] summary.txt AI count inaccurate when decryption silently skips records [export_service.py]
- [x] [Review][Patch] `summary.txt` can overcount exported documents when file retrieval is skipped [healthcabinet/backend/app/users/export_service.py:115]

### Deferred
- [x] [Review][Defer] GDPR audit logging (who requested export, when) — broader audit infrastructure needed [router.py]
- [x] [Review][Defer] No rate limiting on export endpoint — pre-existing gap across codebase [router.py]
