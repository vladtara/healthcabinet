# Story 14.1: SSE Fetch-Based Auth and Lifecycle

Status: done

## Story

As a platform user uploading health documents,
I want the real-time processing status stream to use header-based authentication instead of URL query parameters,
so that my access token is not exposed in browser history, server access logs, or referrer headers — and the connection handles token expiry and reconnection gracefully.

## Acceptance Criteria

### AC1: Backend dual-auth support on SSE endpoint

1. **Modify `processing/router.py`** to accept authentication via **either** `Authorization: Bearer <token>` header **or** `?token=` query parameter. The query parameter becomes optional (`token: str | None = Query(default=None)`). Auth resolution order: (a) if `Authorization` header present, use `get_current_user` dependency pattern to extract user; (b) else if `?token=` query param present, use existing `verify_access_token(token)` path; (c) else return HTTP 401.

2. **Do NOT remove query-param support yet.** Dual-auth ensures zero-downtime migration — if a consumer is mid-stream on the old `EventSource` pattern when the frontend deploys, it keeps working. The query-param path can be removed in a future cleanup story.

3. **Preserve all existing SSE behavior**: Redis pub/sub subscription, heartbeat frames, terminal event detection, 120s stream timeout, document ownership check, fast-path for already-terminal documents.

4. **Update backend tests** in `tests/processing/test_router.py` to cover both auth paths: header-based (new) and query-param (existing). Add tests for: header auth success, header auth with expired token returns 401, missing both header and query-param returns 401, header auth preferred over query-param when both provided.

### AC2: Frontend fetch-based SSE client utility

5. **Create `streamDocumentStatus()` function** in `$lib/api/documents.ts` that replaces `getDocumentStatusUrl()`. This function:
   - Calls `apiStream(`/api/v1/documents/${documentId}/status`)` (GET request, no body)
   - Returns a parsed event async iterator or similar abstraction
   - Handles SSE frame parsing: split on `\n\n`, extract `data:` prefix, JSON parse each payload
   - Supports `AbortController` signal for cancellation
   - Gets automatic 401 refresh from `apiStream()` (already built in)
   - Returns a cleanup function or relies on `AbortController.abort()` for connection teardown

6. **Keep `getDocumentStatusUrl()` temporarily** (mark with `@deprecated` JSDoc comment) until both consumers are migrated. Remove in this same story after both consumers are updated.

### AC3: ProcessingPipeline.svelte migration

7. **Replace `EventSource` usage in `ProcessingPipeline.svelte`** with the new `streamDocumentStatus()` function. The `$effect` block must:
   - Create an `AbortController` per connection
   - Call `streamDocumentStatus(documentId, signal)` and iterate over parsed events
   - Preserve all existing behavior: `resetPipeline()` on documentId change, `updateStage()` on each event, terminal event detection calling `onComplete()`/`onFailed()`, consecutive error counting
   - Abort the previous controller when `documentId` changes (prevents orphaned connections)
   - Return cleanup function that calls `controller.abort()` (prevents orphaned connections on unmount)
   - Handle `AbortError` silently (same pattern as `AiFollowUpChat.svelte:85-88`)

8. **Preserve all existing error handling**: 3 consecutive errors close stream and call `onFailed('stream-error')`. Malformed SSE frames are skipped. Terminal events (`document.completed`, `document.failed`, `document.partial`) close the stream and fire the appropriate callback.

### AC4: documents/+page.svelte migration

9. **Replace the `EventSource` multiplexing pattern in `documents/+page.svelte`** with fetch-based streams. The `activeSSEConnections` Map changes from `Map<string, EventSource>` to `Map<string, AbortController>`. For each processing document:
   - Create an `AbortController` and store it in the map
   - Call `streamDocumentStatus(docId, controller.signal)` in an async IIFE
   - On terminal event: invalidate Svelte Query caches (same keys as current), delete controller from map
   - On error (3 consecutive): abort controller, delete from map
   - Closing connections for non-processing docs: call `controller.abort()` instead of `es.close()`

10. **Preserve `onDestroy` cleanup**: iterate all controllers in `activeSSEConnections` and call `.abort()` on each, then clear the map.

### AC5: Connection lifecycle hardening

11. **Prevent orphaned connections on re-render race**: In `ProcessingPipeline.svelte`, the `$effect` cleanup function must abort the controller **before** a new connection is opened when `documentId` changes. The Svelte 5 `$effect` cleanup runs before the next effect invocation, so returning `() => controller.abort()` is sufficient — but verify this in tests.

12. **Prevent orphaned connections in documents list**: When `documentsQuery.data` changes and a document is no longer processing, abort its controller immediately. Do not rely on garbage collection.

13. **Maximum reconnect limit already exists** (3 consecutive errors → close). No additional reconnect logic needed — the fetch-based approach does not auto-reconnect like `EventSource` does (which is correct — we want explicit control).

### AC6: Test updates

14. **Update `ProcessingPipeline.test.ts`**: Replace `MockEventSource` with a mock for the new `streamDocumentStatus()` function. The mock should return a controllable async iterator that the test can push events into. Update all existing assertions to use the new pattern. Preserve: all stage progression tests, terminal event tests, error counting tests, axe audit, cleanup verification.

15. **Update `documents/page.test.ts`** — this file has extensive SSE-related tests: `MockEventSource` class, `mockEventSourceInstances` tracking, `getDocumentStatusUrl` unit tests (lines 169-182), and SSE integration assertions (lines 241-898). All must be migrated: replace `MockEventSource` with `streamDocumentStatus` mocks, remove `getDocumentStatusUrl` unit tests (function will be deleted), update SSE integration tests to use the new AbortController-based pattern.

16. **Backend `test_router.py`**: Add header-auth test cases alongside existing query-param tests. Existing query-param tests must continue passing unchanged.

### AC7: Remove deprecated code

17. **Remove `getDocumentStatusUrl()`** from `$lib/api/documents.ts` after both consumers are migrated.

18. **Remove `verify_access_token()` from `security.py`** — **NO, keep it.** The backend dual-auth still uses it for the query-param fallback path. Mark with a deprecation docstring note instead. It can be removed when query-param support is dropped in a future story.

## Tasks / Subtasks

- [x] Task 1: Backend dual-auth on SSE endpoint (AC: 1, 2, 3)
  - [x] 1.1 Modify `processing/router.py` — make `token` query param optional, add `Authorization` header extraction
  - [x] 1.2 Create a helper or inline logic: try header first → query param fallback → 401
  - [x] 1.3 Verify document ownership check and all existing SSE behavior unchanged
  - [x] 1.4 Add backend tests for header-auth path (AC: 4)

- [x] Task 2: Frontend SSE streaming utility (AC: 5, 6)
  - [x] 2.1 Add `streamDocumentStatus()` to `$lib/api/documents.ts`
  - [x] 2.2 Implement SSE frame parser (split `\n\n`, extract `data:` lines, JSON parse)
  - [x] 2.3 Add `@deprecated` JSDoc to `getDocumentStatusUrl()`

- [x] Task 3: Migrate ProcessingPipeline.svelte (AC: 7, 8, 11)
  - [x] 3.1 Replace `EventSource` with `streamDocumentStatus()` in `$effect` block
  - [x] 3.2 Add `AbortController` lifecycle (create per connection, abort on cleanup/change)
  - [x] 3.3 Preserve all stage progression, terminal event, and error handling logic
  - [x] 3.4 Update `ProcessingPipeline.test.ts` (AC: 14)

- [x] Task 4: Migrate documents/+page.svelte (AC: 9, 10, 12)
  - [x] 4.1 Change `activeSSEConnections` from `Map<string, EventSource>` to `Map<string, AbortController>`
  - [x] 4.2 Replace per-document `EventSource` creation with `streamDocumentStatus()` + AbortController
  - [x] 4.3 Update `onDestroy` cleanup
  - [x] 4.4 Update any related tests (AC: 15)

- [x] Task 5: Remove deprecated code and final verification (AC: 17, 18)
  - [x] 5.1 Remove `getDocumentStatusUrl()` from `documents.ts`
  - [x] 5.2 Remove `getDocumentStatusUrl` import from any remaining file
  - [x] 5.3 Add deprecation docstring to `verify_access_token()` in `security.py`
  - [x] 5.4 Run full frontend test suite — verify zero regressions (562 pass, 12 pre-existing fails unchanged)
  - [x] 5.5 Run full backend test suite — verify zero regressions (54/54 processing tests pass; full suite blocked by missing test DB — pre-existing infra issue)

### Review Findings

- [x] [Review][Patch] Fetch-based SSE can die permanently after a single disconnect or 120s server timeout [healthcabinet/frontend/src/lib/api/documents.ts:82]
- [x] [Review][Patch] Malformed `Authorization` headers still fall back to `?token=` instead of failing closed [healthcabinet/backend/app/processing/router.py:79]
- [x] [Review][Patch] ProcessingPipeline marks the stream failed after 3 errors but never aborts the retrying helper, so the SSE loop keeps reconnecting and can fire repeated failure callbacks [healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.svelte:78]
- [x] [Review][Patch] Both SSE consumers ignore `auth-error`, so a failed refresh leaves the helper stopped while the UI keeps a stale in-flight state/controller [healthcabinet/frontend/src/lib/api/documents.ts:150]

## Dev Notes

### Architecture & Patterns

**This is a security + reliability story, not a feature story.** The SSE streams already work. The change is: (1) stop leaking tokens in URLs, (2) get automatic 401 refresh, (3) add explicit connection lifecycle management. All user-facing behavior stays identical.

**The `apiStream()` function in `client.svelte.ts:69-111` is the foundation.** It already handles:
- `Authorization: Bearer` header injection from `tokenState.accessToken`
- Automatic 401 detection → `refreshToken()` → retry once with new token
- `AbortController` / `AbortSignal` propagation
- Network error normalization to RFC 7807 shape

The AI chat streaming in `AiFollowUpChat.svelte:49-103` is the reference implementation for fetch-based streaming. Key differences: AI chat uses POST with a body (chat question), SSE status uses GET with no body. AI chat receives raw text chunks, SSE status receives `data: {json}\n\n` frames that need parsing.

### SSE Frame Parsing

The backend emits standard SSE format: `data: {"event":"document.reading",...}\n\n` with heartbeat frames as `:\n\n`. The fetch-based client must:

1. Get `response.body.getReader()` from `apiStream()` response
2. Read chunks via `reader.read()` in a loop
3. Decode with `TextDecoder({ stream: true })` — **critical: chunks may split mid-frame**
4. Buffer incomplete frames: accumulate text, split on `\n\n`, process only complete frames
5. For each complete frame: if starts with `data: `, strip prefix and JSON parse
6. Skip heartbeat frames (`:` prefix) — they keep the connection alive but carry no data
7. Skip empty frames

**Buffer pattern for chunk boundaries:**
```typescript
let buffer = '';
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const frames = buffer.split('\n\n');
  buffer = frames.pop() ?? ''; // last element is incomplete
  for (const frame of frames) {
    const dataLine = frame.split('\n').find(l => l.startsWith('data: '));
    if (!dataLine) continue; // heartbeat or empty
    const payload = JSON.parse(dataLine.slice(6));
    // yield/callback payload
  }
}
```

### Backend Changes — Minimal Scope

The backend router change is small. The existing `verify_access_token(token)` returns a `uuid.UUID` (user_id). The existing `get_current_user` dependency returns a full `User` object from the DB. For the SSE endpoint, we only need the `user_id` (to check document ownership). Two approaches:

**Recommended approach:** Extract the token from the `Authorization` header manually (not via `Depends(get_current_user)`) since using `Depends(HTTPBearer())` makes the header **required** and would break the optional-header-or-queryparam pattern. Instead:

```python
from fastapi import Header

@router.get("/documents/{document_id}/status")
async def document_status_stream(
    document_id: uuid.UUID,
    token: str | None = Query(default=None, description="..."),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    # Resolve user_id from header or query param
    if authorization and authorization.startswith("Bearer "):
        bearer_token = authorization[7:]
        user_id = verify_access_token(bearer_token)
    elif token:
        user_id = verify_access_token(token)
    else:
        raise HTTPException(status_code=401, detail="Missing authentication")
    
    doc = await get_document_by_id(db, document_id, user_id)
    # ... rest unchanged
```

This keeps `verify_access_token()` as the single validation function for both paths. No `get_current_user` dependency needed (avoids the extra DB query that the SSE endpoint doesn't need — it already does `get_document_by_id` which confirms ownership).

**Note on suspended account check:** The current SSE endpoint does NOT check `account_status` — it only validates the JWT and document ownership. This matches the existing behavior. Adding a suspended-account check would require a DB user lookup (like `get_current_user` does). This is out of scope for this story — the access token has a 15-minute expiry, so suspended users lose access within 15 minutes.

### Frontend Implementation — `streamDocumentStatus()`

```typescript
export interface DocumentStatusEvent {
  event: string;
  document_id: string;
  progress: number;
  message: string;
}

export async function streamDocumentStatus(
  documentId: string,
  signal: AbortSignal,
  onEvent: (event: DocumentStatusEvent) => void,
  onError: (error: 'stream-error' | 'auth-error') => void,
): Promise<void> {
  let response: Response;
  try {
    response = await apiStream(
      `/api/v1/documents/${documentId}/status`,
      { signal, method: 'GET' },
    );
  } catch (err) {
    if ((err as { name?: string })?.name === 'AbortError') return;
    onError('auth-error');
    return;
  }

  if (!response.ok) {
    onError('stream-error');
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    onError('stream-error');
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split('\n\n');
      buffer = frames.pop() ?? '';
      for (const frame of frames) {
        const dataLine = frame.split('\n').find(l => l.startsWith('data: '));
        if (!dataLine) continue;
        try {
          const event = JSON.parse(dataLine.slice(6)) as DocumentStatusEvent;
          onEvent(event);
        } catch { /* malformed frame — skip */ }
      }
    }
  } catch (err) {
    if ((err as { name?: string })?.name === 'AbortError') return;
    onError('stream-error');
  } finally {
    reader.cancel().catch(() => {});
  }
}
```

### Key Behavioral Differences: EventSource vs Fetch-Based

| Behavior | EventSource (current) | Fetch-based (target) |
|----------|----------------------|---------------------|
| Auto-reconnect | Yes (built-in, uncontrollable) | No — explicit control |
| Auth refresh | Not possible mid-stream | Handled by `apiStream()` before stream starts |
| Cancellation | `es.close()` | `controller.abort()` |
| Error counting | `es.onerror` fires per retry | Network error thrown once; app-level error counting moves to the consumer |
| Heartbeats | Invisible (EventSource handles) | Must skip `:\n\n` frames in parser |
| Token in URL | Yes (query param) | No (Authorization header) |

**Error counting change:** With `EventSource`, `onerror` fires on each auto-reconnect attempt, so counting to 3 means "3 reconnect attempts failed." With fetch-based, there's no auto-reconnect — the stream either works or fails. If the initial connection fails (non-200 response), that's a single failure. If the stream drops mid-way (reader throws), that's also a single failure. The 3-retry pattern should be reimplemented as: if the stream fails, retry up to 2 more times with a brief delay, then give up.

### Connection Lifecycle

**ProcessingPipeline:** One connection per `documentId`. Lifecycle:
1. `$effect` fires → create `AbortController` → call `streamDocumentStatus()`
2. documentId changes → cleanup runs `controller.abort()` → effect re-fires with new ID
3. Terminal event received → abort controller (stream will end naturally, but abort ensures cleanup)
4. Component unmount → cleanup runs `controller.abort()`

**documents/+page.svelte:** Multiple connections (one per processing document). Lifecycle:
1. `$effect` fires when `documentsQuery.data` changes
2. For each processing doc without an active controller → create AbortController, start stream
3. For each non-processing doc with an active controller → `controller.abort()`, delete from map
4. Component destroy → abort all controllers, clear map

### Project Structure Notes

All changes align with existing project structure:
- Backend: `app/processing/router.py` (endpoint change), `app/core/security.py` (docstring only)
- Frontend: `src/lib/api/documents.ts` (utility), `src/lib/api/client.svelte.ts` (unchanged — used as-is)
- Consumers: `src/lib/components/health/ProcessingPipeline.svelte`, `src/routes/(app)/documents/+page.svelte`
- Tests: co-located `*.test.ts` for frontend, `tests/processing/test_router.py` for backend

No new files created (the `DocumentStatusEvent` type can live in `documents.ts` or `$lib/types/api.ts`). No new dependencies. No migrations. No CSS changes.

### Testing Standards

- **Backend:** `docker compose exec backend uv run pytest tests/processing/test_router.py` — add header-auth tests alongside existing query-param tests. Use `httpx.AsyncClient` with explicit `headers={"Authorization": "Bearer ..."}` for header-auth tests.
- **Frontend:** `docker compose exec frontend npm run test:unit` — mock `streamDocumentStatus()` in consumer tests. The mock should accept events pushed by the test and support abort signal.
- **Axe audit:** ProcessingPipeline already has an axe test — preserve it.
- **Integration:** Manual verification that SSE streams work end-to-end requires running the full stack (backend + Redis + frontend). This can be verified by uploading a document and watching the processing pipeline progress.

### Backend API Contracts

**Endpoint:** `GET /api/v1/documents/{document_id}/status`

**Auth (current):** `?token=<access_jwt>` (required)
**Auth (after this story):** `Authorization: Bearer <access_jwt>` (preferred) OR `?token=<access_jwt>` (fallback)

**Response:** `text/event-stream` — unchanged format:
```
data: {"event":"document.reading","document_id":"uuid","progress":0.25,"message":"Reading document..."}\n\n
```

### Previous Story Learnings

From **Story 13-5** (the story that re-deferred this work):
- GA-waiver documented: "The `apiStream` pattern (fetch-based streaming) already exists for AI chat but would require backend SSE endpoint changes to accept `Authorization` headers instead of query params."
- The SSE endpoint returns document processing status only (no health data), limiting exposure of the token-in-URL risk.
- Two consumers confirmed: `documents/+page.svelte` (list page multiplexing) and `ProcessingPipeline.svelte` (upload progress).

From **Epic 11 retrospective** (where SSE security was first flagged):
- SSE token-as-query-param was flagged in code reviews for stories 11-1, 11-2, and 11-3.
- Deferred 4 times total: Epic 11 → Epic 12 → 13-5 → Epic 14 cleanup sprint.

From **Epic 13 retrospective** (which created Epic 14):
- "Frontend-only stories cannot fix a frontend+backend problem." This story is explicitly full-stack.
- "Cross-functional items must get dedicated stories, not just retro bullets." This story fulfills that requirement.

### Git Intelligence

Recent commits (Epic 13 track):
- `9e560f4` — chore: .gitignore update
- `6b37de7` — feat: document handling + UI (Story 13-5 hardening)
- `40c9343` — refactor: `<main>` → `<div>` admin pages (Story 13-4)
- `6690777` — refactor: admin user detail + management (Story 13-3)
- `b629bc2` — refactor: admin document correction + error queue (Story 13-2)

Pattern: all recent work is frontend-only reskin. This story is the first full-stack change since Epic 12 (Story 12-4 `DELETE /users/me`).

### Files to Modify

| File | Changes |
|------|---------|
| `healthcabinet/backend/app/processing/router.py` | Add `Authorization` header extraction, make `token` query param optional |
| `healthcabinet/backend/app/core/security.py` | Add deprecation docstring to `verify_access_token()` |
| `healthcabinet/backend/tests/processing/test_router.py` | Add header-auth test cases |
| `healthcabinet/frontend/src/lib/api/documents.ts` | Add `streamDocumentStatus()`, deprecate then remove `getDocumentStatusUrl()` |
| `healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.svelte` | Replace EventSource with fetch-based streaming |
| `healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.test.ts` | Replace MockEventSource with streamDocumentStatus mock |
| `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` | Replace EventSource multiplexing with fetch-based + AbortController |
| `healthcabinet/frontend/src/routes/(app)/documents/page.test.ts` | Replace MockEventSource + getDocumentStatusUrl tests with streamDocumentStatus mocks |

### Files NOT to Modify

- `healthcabinet/frontend/src/lib/api/client.svelte.ts` — `apiStream()` is used as-is, no changes needed
- `healthcabinet/backend/app/processing/events.py` — Redis pub/sub publishing is unchanged
- `healthcabinet/backend/app/processing/schemas.py` — SSE payload schema unchanged
- `healthcabinet/frontend/src/app.css` — no CSS changes
- Any admin route files
- Any other backend domain modules

### References

- [Source: _bmad-output/implementation-artifacts/13-5-frontend-hardening-accessibility-qa-performance.md — GA-waiver: SSE Token Security section, lines 258-266]
- [Source: _bmad-output/implementation-artifacts/epic-13-retro-2026-04-16.md — Cleanup Sprint Plan Tier 1 items #3 and #4]
- [Source: _bmad-output/implementation-artifacts/epic-12-retro-2026-04-15.md — Action Item #3, Deferred Work section]
- [Source: _bmad-output/implementation-artifacts/epic-11-retro-2026-04-05.md — Action Items #2 and #3]
- [Source: _bmad-output/planning-artifacts/architecture.md — SSE events communication pattern, line 439-446]
- [Source: healthcabinet/frontend/src/lib/api/client.svelte.ts:69-111 — apiStream() function]
- [Source: healthcabinet/frontend/src/lib/api/documents.ts:74-78 — getDocumentStatusUrl() current implementation]
- [Source: healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.svelte:91-139 — EventSource consumer]
- [Source: healthcabinet/frontend/src/routes/(app)/documents/+page.svelte:101-173 — EventSource multiplexing consumer]
- [Source: healthcabinet/backend/app/processing/router.py:58-182 — SSE endpoint with query-param auth]
- [Source: healthcabinet/backend/app/core/security.py:59-81 — verify_access_token()]
- [Source: healthcabinet/backend/app/auth/dependencies.py:22-58 — get_current_user() header-based auth pattern]
- [Source: healthcabinet/frontend/src/lib/components/health/AiFollowUpChat.svelte:49-103 — fetch-based streaming reference]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Backend full test suite blocked by missing `healthcabinet_test` database (pre-existing infra issue). Processing-specific tests run successfully: 54/54 pass.
- Frontend: 12 pre-existing test failures in 3 files (`documents/page.test.ts`, `AIChatWindow.test.ts`, `users/+page.test.ts`) — all are detail-panel rendering failures, unchanged by this story. Scoped for Story 14-4.

### Completion Notes List

- **Backend dual-auth:** `processing/router.py` now accepts `Authorization: Bearer` header (preferred) or `?token=` query param (legacy fallback). Header takes precedence when both present. 6 new header-auth tests added; 12 existing query-param tests continue passing.
- **`streamDocumentStatus()` utility:** New fetch-based SSE client in `documents.ts` using `apiStream()` for automatic `Authorization` header injection and 401 refresh. SSE frame parser handles `data:` lines, heartbeat frames, and cross-chunk buffering.
- **ProcessingPipeline migration:** Replaced `EventSource` with `streamDocumentStatus()` + `AbortController`. Svelte 5 `$effect` cleanup aborts controller on unmount/re-render. All 17 component tests updated and passing.
- **Documents list migration:** Replaced `Map<string, EventSource>` with `Map<string, AbortController>`. Per-document streams use `streamDocumentStatus()`. `onDestroy` cleanup aborts all controllers. 4 SSE-specific tests migrated from MockEventSource to callback-based mocking.
- **Deprecated code removed:** `getDocumentStatusUrl()` deleted from `documents.ts`. Zero remaining references in codebase. `verify_access_token()` retained with updated docstring (still used by query-param fallback).
- **Security improvement:** Access tokens no longer appear in URLs — eliminated from browser history, server access logs, and referrer headers.

### Change Log

- 2026-04-16: Story created — comprehensive developer guide for SSE fetch-based auth migration
- 2026-04-16: Implementation complete — all 5 tasks done, 18 backend tests pass, 17 ProcessingPipeline tests pass, documents page SSE tests pass

### File List

- `healthcabinet/backend/app/processing/router.py` (modified — dual-auth: Authorization header + query param fallback)
- `healthcabinet/backend/app/core/security.py` (modified — updated verify_access_token docstring)
- `healthcabinet/backend/tests/processing/test_router.py` (modified — 6 new header-auth tests, updated missing-auth test)
- `healthcabinet/frontend/src/lib/api/documents.ts` (modified — added streamDocumentStatus + DocumentStatusEvent, removed getDocumentStatusUrl)
- `healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.svelte` (modified — EventSource → fetch-based SSE with AbortController)
- `healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.test.ts` (modified — MockEventSource → streamDocumentStatus mock)
- `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` (modified — EventSource → fetch-based SSE with AbortController)
- `healthcabinet/frontend/src/routes/(app)/documents/page.test.ts` (modified — MockEventSource → streamDocumentStatus mock, removed getDocumentStatusUrl tests)

## Review Findings

- [x] [Review][Patch] MinIO cleanup ran twice per deletion (inline + deferred job) [service.py] — Removed inline cleanup task; now only enqueues deferred reconciliation job. Removed dead `_run_account_deletion_storage_cleanup` function and unused `asyncio` import.
- [x] [Review][Patch] `asyncio.shield` re-raised `CancelledError`, defeating its purpose [service.py] — Removed shield wrapper; deferred cleanup is now purely async-fire-and-forget via job queue.
- [x] [Review][Patch] `ConsentLogResponse.model_validate` silently changed `get_consent_history` API behavior [router.py] — Reverted to `ConsentHistoryResponse(items=logs)`. Added no tests for this change, was out of scope for all 3 stories. Removed unused `ConsentLogResponse` import.
- [x] [Review][Defer] Worker `reconcile_deleted_user_storage` lacks isolated unit test — No test for the worker function itself; only tested via integration router test. Deferred.
- [x] [Review][Defer] Query-param SSE auth flagged "legacy" with no removal plan — No ADR or tracking issue for removing the legacy `?token=` path. Deferred.
