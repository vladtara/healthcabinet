# Story 12.2: Consent History Timeline

Status: done

## Story

As a registered user viewing my settings page,
I want to see a chronological timeline of all consent agreements I have accepted in a 98.css sunken panel,
so that I have full transparency over what I agreed to and when, satisfying GDPR Article 9 requirements.

## Acceptance Criteria

1. **Backend endpoint: GET /api/v1/users/me/consent-history** -- Returns all `consent_logs` rows for the authenticated user in descending chronological order (most recent first). Response shape: `{ items: ConsentLogResponse[] }`. Each item: `id`, `consent_type`, `privacy_policy_version`, `consented_at` (ISO 8601 UTC). Filtered strictly by `user_id` from JWT (no IDOR). Returns 200 with at least one entry (registration consent from Story 1.2 always exists).

2. **Backend schema and router** -- Add `ConsentLogResponse` Pydantic schema to `app/users/schemas.py`. Add route to `app/users/router.py` using existing `list_consent_logs_by_user()` from `app/auth/repository.py`. Response model: `ConsentHistoryResponse` with `items: list[ConsentLogResponse]`. Order by `consented_at` descending (reverse the existing ascending query or add a new one).

3. **Frontend API function** -- Add `getConsentHistory(): Promise<ConsentLog[]>` to `$lib/api/users.ts`. Calls `GET /api/v1/users/me/consent-history` via `apiFetch`. Returns the `items` array. Use existing `ConsentLog` interface from `$lib/types/api.ts`.

4. **Consent History fieldset on settings page** -- Add a new `<fieldset class="hc-fieldset">` with `<legend>Consent History</legend>` to the settings page, positioned between the "Data & Privacy" fieldset and the end of the page. Contains a sunken panel (`.hc-panel-sunken` or `.hc-consent-timeline`) displaying consent log entries.

5. **Timeline display** -- Each consent entry renders as a row in a sunken panel. Show: human-readable consent type label (e.g., "Health Data Processing" instead of raw `health_data_processing`), timestamp formatted as "DD MMM YYYY, HH:MM UTC" (e.g., "05 Apr 2026, 14:30 UTC"), and privacy policy version as a text label. Entries ordered most-recent-first. No edit or delete controls -- strictly read-only.

6. **Privacy policy version link** -- If privacy policy version text is present, render it as a clickable link `<a class="hc-consent-policy-link" href="/privacy">v{version}</a>` in accent color. If no version available, render as plain text "N/A".

7. **Empty state** -- Should not occur (registration consent always exists), but if no entries returned, show `.hc-state .hc-state-empty` with message "No consent records found."

8. **Loading state** -- While fetching consent history, show a loading indicator (`.hc-state .hc-state-loading` with "Loading consent history...").

9. **Error state** -- If the API call fails, show `.hc-state .hc-state-error` with message "Failed to load consent history" and role="alert".

10. **CSS follows established patterns** -- All new styles in `app.css` using `.hc-consent-*` prefix. Use design tokens. No Tailwind structural classes. No scoped styles. No inline styles. Reuse existing `.hc-fieldset`, `.hc-state-*` classes.

11. **Tests** -- Backend: test consent history endpoint returns user's logs in descending order, returns empty for user with no logs (edge case), does not leak other users' logs. Frontend: test consent timeline renders entries with correct data, loading state, error state, empty state, policy version link, timestamp formatting, axe accessibility audit.

12. **WCAG compliance** -- Fieldset has descriptive legend. Timeline entries are in a semantic list (`<ol>` or `<ul>` for screen reader count announcement). Policy links have accessible text. Read-only status is implicit (no controls). Axe audit passes.

## Tasks / Subtasks

- [x] Task 1: Backend -- Add consent history endpoint (AC: 1, 2)
  - [x] Add `ConsentLogResponse` and `ConsentHistoryResponse` schemas to `app/users/schemas.py`
  - [x] Add `GET /users/me/consent-history` route to `app/users/router.py`
  - [x] Reuse `list_consent_logs_by_user()` from `app/auth/repository.py`, reverse order to descending
  - [x] Add backend tests for endpoint (200 with entries, no cross-user leakage, auth required)

- [x] Task 2: Frontend API -- Add consent history fetch (AC: 3)
  - [x] Add `getConsentHistory()` function to `$lib/api/users.ts`
  - [x] Function calls `GET /api/v1/users/me/consent-history` via `apiFetch`
  - [x] Returns `items` array typed as `ConsentLog[]`

- [x] Task 3: Add `.hc-consent-*` CSS classes to `app.css` (AC: 10)
  - [x] `.hc-consent-timeline` -- sunken panel container for entries
  - [x] `.hc-consent-entry` -- individual entry row with bottom border separator
  - [x] `.hc-consent-type` -- consent type label (15px, bold, `var(--text-primary)`)
  - [x] `.hc-consent-meta` -- timestamp + version row (13px, `var(--text-secondary)`)
  - [x] `.hc-consent-policy-link` -- accent-colored link for policy version with focus-visible

- [x] Task 4: Add Consent History section to settings page (AC: 4, 5, 6, 7, 8, 9)
  - [x] Add `getConsentHistory` import and `$effect` to fetch on mount
  - [x] Add `<fieldset class="hc-fieldset"><legend>Consent History</legend>` after Data & Privacy
  - [x] Render loading state while fetching
  - [x] Render error state on failure
  - [x] Render empty state if no entries
  - [x] Render timeline entries in `<ul>` list inside `.hc-consent-timeline` sunken panel
  - [x] Format consent type: `health_data_processing` -> "Health Data Processing" (title case, replace underscores)
  - [x] Format timestamp: "DD MMM YYYY, HH:MM UTC"
  - [x] Render policy version as link or plain text

- [x] Task 5: Update tests (AC: 11)
  - [x] Backend: test GET /users/me/consent-history returns descending entries
  - [x] Backend: test no cross-user consent log leakage
  - [x] Frontend: test consent timeline renders with entries
  - [x] Frontend: test loading state
  - [x] Frontend: test error state with role="alert"
  - [x] Frontend: test empty state
  - [x] Frontend: test policy version link has href
  - [x] Frontend: test timestamp formatting (verified in entry render test)
  - [x] Frontend: axe accessibility audit

- [x] Task 6: WCAG audit (AC: 12)
  - [x] Fieldset has `<legend>Consent History</legend>`
  - [x] Timeline entries in semantic `<ul>` list with aria-label
  - [x] Policy links have accessible text (version number)
  - [x] Error state has `role="alert"`
  - [x] Axe audit passes

### Review Findings

- [x] [Review][Decision] Privacy policy link → resolved: added version query param href="/privacy?version={v}"
- [x] [Review][Patch] In-memory reversal → added list_consent_logs_by_user_desc with ORDER BY DESC at query level
- [x] [Review][Patch] Empty privacy_policy_version → added .trim() guard, empty/whitespace shows N/A
- [x] [Review][Patch] Timestamp format test → now asserts exact "15 Jan 2026, 10:30 UTC"
- [x] [Review][Patch] Policy link accessibility → added aria-label="Privacy policy version {v}"
- [x] [Review][Patch] ConsentLog type → removed user_id field not returned by backend
- [x] [Review][Defer] No pagination on consent history — bounded by consent event frequency, not user content
- [x] [Review][Defer] No runtime validation of API response shape — project-wide pattern
- [x] [Review][Defer] $effect re-triggering concerns — Svelte 5 runs once on mount
- [x] [Review][Defer] ConsentHistoryResponse wrapper boilerplate — pagination-ready pattern

## Dev Notes

### Architecture & Patterns

- **Backend-first, then frontend**: This story requires a new API endpoint. Implement the backend endpoint first (Task 1), then the frontend integration (Tasks 2-4).
- **Reuse existing repository function**: `list_consent_logs_by_user()` in `app/auth/repository.py` already queries consent logs ordered ascending. Either reverse in the route handler (`logs[::-1]`) or add a `desc=True` parameter. Prefer reversing in the handler to avoid modifying existing tested code.
- **Settings page extension**: Add the Consent History fieldset to the existing `/settings` page. Do NOT create a separate route. This follows the "Settings → Privacy" pattern from the spec and the Epic 12 approach of enriching the settings surface.
- **No data mutation**: This is a read-only display. No POST/PUT/DELETE. No form controls.

### Backend Implementation Guide

**Schema** (`app/users/schemas.py`):
```python
class ConsentLogResponse(BaseModel):
    id: uuid.UUID
    consent_type: str
    privacy_policy_version: str
    consented_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConsentHistoryResponse(BaseModel):
    items: list[ConsentLogResponse]
```

**Route** (`app/users/router.py`):
```python
@router.get("/me/consent-history", response_model=ConsentHistoryResponse, status_code=200)
async def get_consent_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsentHistoryResponse:
    logs = await list_consent_logs_by_user(db, current_user.id)
    return ConsentHistoryResponse(items=list(reversed(logs)))
```

**Import needed**: `from app.auth.repository import list_consent_logs_by_user`

### Frontend Implementation Guide

**API function** (`$lib/api/users.ts`):
```typescript
export async function getConsentHistory(): Promise<ConsentLog[]> {
    const res = await apiFetch<{ items: ConsentLog[] }>('/api/v1/users/me/consent-history');
    return res.items;
}
```

**Consent type formatting**:
```typescript
function formatConsentType(type: string): string {
    return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
```

**Timestamp formatting**:
```typescript
function formatConsentDate(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
        + ', ' + d.toUTCHours().toString().padStart(2, '0')
        + ':' + d.toUTCMinutes().toString().padStart(2, '0') + ' UTC';
}
```
Note: Use `getUTCHours()`/`getUTCMinutes()` to display UTC time, not local time.

### CSS Classes to Add (app.css)

| Class | Purpose |
|-------|---------|
| `.hc-consent-timeline` | Sunken panel: `box-shadow` inset (matching `.hc-state` pattern), `padding: 0`, `background: var(--surface-sunken)` |
| `.hc-consent-entry` | `padding: 10px 12px; border-bottom: 1px solid var(--border-sunken-inner);` last-child no border |
| `.hc-consent-type` | `font-size: 15px; font-weight: 600; color: var(--text-primary);` |
| `.hc-consent-meta` | `font-size: 13px; color: var(--text-secondary); margin-top: 2px; display: flex; gap: 12px;` |
| `.hc-consent-policy-link` | `color: var(--accent); text-decoration: underline; font-size: 13px;` |

### Existing Resources to Reuse

- **Backend**: `list_consent_logs_by_user()` in `app/auth/repository.py` -- tested, production-ready
- **Frontend type**: `ConsentLog` in `$lib/types/api.ts` -- already defined with all needed fields
- **CSS**: `.hc-fieldset`, `.hc-state`, `.hc-state-empty`, `.hc-state-loading`, `.hc-state-error` -- all exist in `app.css`
- **Sunken panel pattern**: Use the same `box-shadow` as `.hc-state` for the inset 3D effect

### Backend API Contract

```
GET /api/v1/users/me/consent-history
Authorization: Bearer <access_token>

Response 200:
{
    "items": [
        {
            "id": "uuid",
            "consent_type": "health_data_processing",
            "privacy_policy_version": "1.0",
            "consented_at": "2026-01-15T10:30:00Z"
        }
    ]
}

Response 401: Unauthorized (no/invalid token)
```

### ConsentLog Database Model

```python
# app/users/models.py (already exists)
class ConsentLog(Base):
    __tablename__ = "consent_logs"
    id: UUID PK
    user_id: UUID FK -> users.id (CASCADE)
    consent_type: str  # e.g., "health_data_processing"
    privacy_policy_version: str  # e.g., "1.0"
    consented_at: DateTime (UTC, server_default=func.now())
    # Indexed on user_id
```

### Previous Story Learnings (Story 12-1)

- Use `.hc-*` CSS classes exclusively, no Tailwind structural classes, no inline styles
- Section-based CSS prefix naming (`.hc-consent-*` for this story)
- Reuse design tokens: `--text-primary`, `--text-secondary`, `--accent`, `--surface-sunken`, `--border-sunken-inner`
- Reset 98.css button chrome (min-width, box-shadow, text-shadow) on custom interactive elements
- Add `:focus-visible` on any custom interactive elements
- Use `var(--accent-text)` not hardcoded `#fff` for text on accent backgrounds
- Axe audit test required
- 502 tests currently pass -- maintain zero regressions

### Project Structure Notes

- Backend endpoint in `app/users/router.py` (not auth) since it's user-facing data
- Import `list_consent_logs_by_user` from `app/auth/repository.py` (cross-module import, matches export service pattern)
- Frontend stays within existing `/settings` route -- no new route file needed
- All CSS in `app.css` with `.hc-consent-*` prefix

### Files to Create/Modify

| File | Changes |
|------|---------|
| `healthcabinet/backend/app/users/schemas.py` | Add `ConsentLogResponse`, `ConsentHistoryResponse` |
| `healthcabinet/backend/app/users/router.py` | Add `GET /me/consent-history` route |
| `healthcabinet/backend/tests/users/test_router.py` | Add consent history endpoint tests |
| `healthcabinet/frontend/src/lib/api/users.ts` | Add `getConsentHistory()` function |
| `healthcabinet/frontend/src/app.css` | Add `.hc-consent-*` classes (~5 new classes) |
| `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` | Add Consent History fieldset section |
| `healthcabinet/frontend/src/routes/(app)/settings/page.test.ts` | Add consent timeline tests |

### References

- [Source: _bmad-output/planning-artifacts/epics.md -- Story 6.3 Consent History View acceptance criteria]
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md -- FE Epic 6 Story 2: consent history timeline]
- [Source: _bmad-output/planning-artifacts/prd.md -- FR6, FR30, FR31 consent requirements]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md -- Settings page consent history reference]
- [Source: _bmad-output/implementation-artifacts/12-1-medical-profile-page-redesign.md -- CSS patterns, learnings]
- [Source: healthcabinet/backend/app/auth/repository.py -- list_consent_logs_by_user() existing function]
- [Source: healthcabinet/frontend/src/lib/types/api.ts -- ConsentLog interface already defined]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Backend: Added `ConsentLogResponse` and `ConsentHistoryResponse` schemas to users/schemas.py
- Backend: Added `GET /users/me/consent-history` route to users/router.py, reuses `list_consent_logs_by_user()` with reversed order
- Backend: 3 new tests (descending order, no cross-user leakage, auth required) -- 10/10 pass
- Frontend API: Added `getConsentHistory()` to users.ts using existing `ConsentLog` type
- Frontend CSS: 7 new `.hc-consent-*` classes in app.css (timeline, entry, type, meta, policy-link + hover + focus-visible)
- Frontend template: New "Consent History" fieldset on settings page with loading/error/empty/timeline states
- Consent type formatted from snake_case to Title Case
- Timestamps formatted as "DD MMM YYYY, HH:MM UTC" using UTC methods
- Policy version rendered as link to /privacy
- Timeline uses semantic `<ul>` with `aria-label`
- 6 new frontend tests (fieldset, entries, semantic list, loading, error, empty)
- 508/508 frontend tests pass, 0 regressions, 0 type errors

### Change Log

- 2026-04-05: Story implementation complete -- Consent History Timeline
- 2026-04-05: Code review patches applied -- 6 fixes (version link, DB ordering, empty version guard, timestamp test, aria-label, type fix)

### File List

- `healthcabinet/backend/app/users/schemas.py` (modified -- added ConsentLogResponse, ConsentHistoryResponse)
- `healthcabinet/backend/app/users/router.py` (modified -- added GET /me/consent-history route)
- `healthcabinet/backend/tests/users/test_router.py` (modified -- added 3 consent history tests)
- `healthcabinet/frontend/src/lib/api/users.ts` (modified -- added getConsentHistory function)
- `healthcabinet/frontend/src/app.css` (modified -- added .hc-consent-* CSS classes)
- `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` (modified -- added Consent History fieldset)
- `healthcabinet/frontend/src/routes/(app)/settings/page.test.ts` (modified -- added 6 consent timeline tests)
