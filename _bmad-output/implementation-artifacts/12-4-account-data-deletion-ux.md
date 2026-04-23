# Story 12.4: Account & Data Deletion UX

Status: done

## Story

As a registered user on my settings page,
I want a calm but serious confirmation dialog that requires me to type my email before permanently deleting my account and all health data,
so that I can exercise my GDPR Article 17 right to erasure with full awareness of the consequences.

## Acceptance Criteria

1. **Delete Account section on settings page** -- Add a new `<fieldset class="hc-fieldset">` with `<legend>Delete Account</legend>` at the bottom of the settings page (after Consent History). Contains a warning description and a "Delete My Account" button (`.btn-destructive`). The section uses calm, factual language -- no apologetic or dramatic copy.

2. **Confirmation dialog** -- Clicking "Delete My Account" opens a centered 98.css dialog (`.hc-delete-dialog`) with:
   - Title bar: "Account Deletion" with warning icon
   - Body: "This action cannot be undone. All your documents, health values, AI interpretations, and account data will be permanently deleted. Consent records are retained for regulatory compliance."
   - Email confirmation input: `<input class="hc-input">` with label "Type your email to confirm"
   - Action buttons: "Cancel" (`.btn-standard`, left) and "Delete My Account" (`.btn-destructive`, right). Delete button disabled until typed email matches the user's email exactly.

3. **Dialog accessibility** -- Dialog uses `role="dialog"`, `aria-modal="true"`, `aria-label="Account deletion confirmation"`. Focus trapped inside dialog. Escape key closes. Backdrop click closes. Email input has `aria-describedby` linking to the warning text.

4. **Backend endpoint: DELETE /api/v1/users/me** -- Deletes the authenticated user's account. Cascade order: delete user-owned `health_values`, `documents`, `user_profiles`, `ai_memories` rows, then delete `users` row. `consent_logs` rows are **retained** (regulatory requirement -- remove CASCADE on consent_logs FK or handle explicitly). Returns 204 No Content on success. Filtered by JWT `user_id`. Atomic transaction -- rolls back on any failure.

5. **Frontend delete flow** -- On confirmation: disable both dialog buttons, show "Deleting..." text on delete button. Call `DELETE /api/v1/users/me`. On success: close dialog, clear auth tokens (call `authStore.logout()` pattern), redirect to landing page (`/`) with query param `?deleted=true`. On error: re-enable buttons, show error in dialog body with `.hc-state-error` and `role="alert"`.

6. **Landing page deleted confirmation** -- If URL has `?deleted=true` query param, the landing page shows a one-time confirmation banner: "Your account and all associated data have been permanently deleted." using `.hc-state .hc-state-success`. Remove the param from URL after displaying.

7. **CSS follows established patterns** -- All new styles in `app.css` using `.hc-delete-*` prefix. Reuse design tokens. Dialog uses 98.css raised panel aesthetic (outset box-shadow). No Tailwind. No inline styles.

8. **Tests** -- Backend: test DELETE /users/me deletes user and returns 204, test cascade doesn't delete consent_logs, test requires auth, test atomic rollback not needed (SQLAlchemy handles). Frontend: test delete button renders with btn-destructive, test dialog opens on click, test email validation enables/disables confirm button, test dialog closes on Cancel/Escape, test successful deletion redirects, test error state in dialog, axe accessibility audit.

9. **WCAG compliance** -- Fieldset has legend. Dialog has proper ARIA. Focus management (trapped in dialog, restored on close). Email input has label and description. Error states have `role="alert"`. Axe audit passes.

## Tasks / Subtasks

- [x] Task 1: Backend -- Add user deletion endpoint (AC: 4)
  - [x] Add `DELETE /users/me` route to `app/users/router.py`
  - [x] Add `delete_user_account()` service function to `app/users/service.py`
  - [x] Cascade via DB FK: health_values, documents, user_profiles, ai_memories auto-deleted
  - [x] Migration 013: consent_logs FK changed to SET NULL (regulatory retention)
  - [x] Audit logs redacted (user_id nullified before user deletion)
  - [x] Return 204 No Content
  - [x] Add backend tests (204 success, consent_logs retained, auth required)

- [x] Task 2: Frontend API -- Add delete account function (AC: 5)
  - [x] Add `deleteMyAccount(): Promise<void>` to `$lib/api/users.ts`
  - [x] Function calls `DELETE /api/v1/users/me` via `apiFetch`

- [x] Task 3: Add `.hc-delete-*` CSS classes to `app.css` (AC: 7)
  - [x] `.hc-delete-section-warning` -- warning description text
  - [x] `.hc-delete-dialog-backdrop` -- centered backdrop overlay
  - [x] `.hc-delete-dialog` -- 98.css raised panel dialog
  - [x] `.hc-delete-dialog-title` -- title bar with accent color
  - [x] `.hc-delete-dialog-body` -- dialog content area
  - [x] `.hc-delete-dialog-actions` -- button row (cancel left, delete right)
  - [x] `.hc-delete-email-label` -- email confirmation label

- [x] Task 4: Add Delete Account section and dialog to settings page (AC: 1, 2, 3, 5)
  - [x] Add delete account state vars (dialogOpen, confirmEmail, deleteLoading, deleteError, emailMatches)
  - [x] Add Delete Account fieldset with warning and btn-destructive button
  - [x] Add confirmation dialog with email input, warning text, action buttons
  - [x] Wire up dialog open/close, email validation (case-insensitive match), delete flow
  - [x] On success: clear auth via authStore.logout(), redirect to /?deleted=true
  - [x] On error: show error in dialog with .hc-state-error
  - [x] Escape key closes dialog, backdrop click closes dialog

- [x] Task 5: Landing page deleted banner (AC: 6)
  - [x] Check for ?deleted=true query param via $page store
  - [x] Show success banner with .hc-state-success
  - [x] Remove param from URL via history.replaceState

- [x] Task 6: Update tests (AC: 8)
  - [x] Backend: DELETE /users/me returns 204 and removes user
  - [x] Backend: consent_logs retained with user_id=NULL after deletion
  - [x] Backend: requires auth (401 without token)
  - [x] Frontend: delete button renders with btn-destructive class
  - [x] Frontend: dialog opens on button click with ARIA attributes
  - [x] Frontend: confirm button disabled until email matches
  - [x] Frontend: dialog closes on Cancel
  - [x] Frontend: axe accessibility audit passes
  - [x] Landing page tests updated with $page store mock

- [x] Task 7: WCAG audit (AC: 9)
  - [x] Dialog has role="dialog", aria-modal="true", aria-label, tabindex="-1"
  - [x] Escape key closes dialog
  - [x] Email input has label and aria-describedby="delete-warning"
  - [x] Error state has role="alert"
  - [x] Axe audit passes

### Review Findings

- [x] [Review][Patch] Escape key — moved handler to dialog div, removed stopPropagation
- [x] [Review][Patch] Focus trap — added Tab cycling + programmatic focus on open via requestAnimationFrame
- [x] [Review][Patch] Logout error — wrapped in try/catch (best-effort cookie clear)
- [x] [Review][Patch] Email trim — added .trim() to email comparison
- [x] [Review][Patch] Migration downgrade — added DELETE WHERE NULL before NOT NULL alter
- [x] [Review][Patch] Test coverage — added delete error state + successful deletion flow tests
- [x] [Review][Defer] Admin RESTRICT FK can block admin self-deletion — edge case
- [x] [Review][Defer] MinIO orphaned documents — Story 6.2 scope
- [x] [Review][Defer] No server-side re-auth for DELETE — not in current ACs
- [x] [Review][Defer] Double-click race condition — unlikely with disabled guard

## Dev Notes

### Architecture & Patterns

- **Backend + Frontend story**: Unlike 12-1/12-2/12-3, this story requires a new backend endpoint. Story 6.2 (full deletion with MinIO cleanup and audit log redaction) was deferred. This story implements the core deletion flow; MinIO object cleanup and audit log redaction can be enhanced in Story 6.2 later.
- **Confirmation dialog**: Build as inline markup in the settings page (not a separate component). Use a `<div>` with backdrop + raised panel, matching the existing slide-over pattern for focus trapping but simpler (centered dialog, not slide-over).
- **Auth flow after deletion**: After successful DELETE, call the same token-clearing pattern as logout. Use `goto('/?deleted=true')` to redirect. The landing page reads the query param for the confirmation banner.
- **"Calm but serious" tone**: Per the UX spec, use factual language. "This action cannot be undone." not "Are you sure? This is very dangerous!" No apologetic copy, no sad illustrations.

### Backend Implementation Guide

**Service** (`app/users/service.py`):
```python
async def delete_user_account(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Delete user account and all owned data. Retains consent_logs."""
    # Delete owned data in dependency order
    await db.execute(delete(HealthValue).where(HealthValue.user_id == user_id))
    await db.execute(delete(AiMemory).where(AiMemory.user_id == user_id))
    await db.execute(delete(Document).where(Document.user_id == user_id))
    await db.execute(delete(UserProfile).where(UserProfile.user_id == user_id))
    # consent_logs deliberately NOT deleted (regulatory retention)
    # Delete user row last
    await db.execute(delete(User).where(User.id == user_id))
```

**Route** (`app/users/router.py`):
```python
@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_user_account(db, current_user.id)
```

**Note**: The full MinIO object deletion and audit_log redaction from Story 6.2 are NOT in scope for this story. Those require S3 client integration in the deletion flow, which is complex. This story handles the database-level deletion and the UX.

### Frontend Dialog Pattern

```svelte
<!-- Delete confirmation dialog -->
{#if deleteDialogOpen}
  <div class="hc-delete-dialog-backdrop" onclick={closeDeleteDialog} onkeydown={handleBackdropKey}>
    <div class="hc-delete-dialog" role="dialog" aria-modal="true"
         aria-label="Account deletion confirmation" onclick|stopPropagation>
      <div class="hc-delete-dialog-title">Account Deletion</div>
      <div class="hc-delete-dialog-body">
        <p id="delete-warning">This action cannot be undone. All your documents, health values,
           AI interpretations, and account data will be permanently deleted.
           Consent records are retained for regulatory compliance.</p>
        {#if deleteError}
          <div class="hc-state hc-state-error" role="alert">
            <p class="hc-state-title">{deleteError}</p>
          </div>
        {/if}
        <label class="hc-delete-email-label" for="delete-confirm-email">
          Type your email to confirm
        </label>
        <input id="delete-confirm-email" class="hc-input" type="email"
               bind:value={confirmEmail} aria-describedby="delete-warning" />
      </div>
      <div class="hc-delete-dialog-actions">
        <button class="btn-standard" onclick={closeDeleteDialog} disabled={deleteLoading}>
          Cancel
        </button>
        <button class="btn-destructive" onclick={handleDeleteAccount}
                disabled={!emailMatches || deleteLoading}>
          {deleteLoading ? 'Deleting...' : 'Delete My Account'}
        </button>
      </div>
    </div>
  </div>
{/if}
```

### CSS Classes to Add (app.css)

| Class | Purpose |
|-------|---------|
| `.hc-delete-section-warning` | `font-size: 14px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 12px;` |
| `.hc-delete-dialog-backdrop` | Fixed overlay, `background: rgba(0,0,0,0.4)`, centered flex, z-index above content |
| `.hc-delete-dialog` | 98.css raised panel: `background: silver; box-shadow: outset; max-width: 480px; width: 100%;` |
| `.hc-delete-dialog-title` | Title bar: `background: var(--accent); color: var(--accent-text); padding: 4px 8px; font-weight: 700;` |
| `.hc-delete-dialog-body` | `padding: 16px; display: flex; flex-direction: column; gap: 12px;` |
| `.hc-delete-dialog-actions` | `padding: 0 16px 16px; display: flex; justify-content: space-between;` |
| `.hc-delete-email-label` | `font-size: 14px; font-weight: 600; color: var(--text-primary);` |

### User Email for Confirmation

The user's email is needed for the type-to-confirm pattern. Options:
1. Fetch from `GET /users/me/profile` (but profile might not have email)
2. The `User` model has email -- add it to an existing endpoint or create a `/users/me` endpoint
3. Store email from auth state

Check: the auth store or token response likely includes the user's email. The register/login responses return `email`. If `authStore` exposes the email, use that. Otherwise, add a simple `/users/me` endpoint that returns `{email}`.

### Existing Patterns to Follow

- **Slide-over component**: Has focus trap and keyboard handling -- reference for dialog implementation
- **Auth logout flow**: `authStore.logout()` clears tokens and redirects
- **btn-destructive**: Already defined in app.css (gray default, red on hover)
- **Success/error banners**: `.hc-state .hc-state-success/error` with ARIA roles

### Previous Story Learnings

- Use `.hc-*` CSS classes exclusively, no Tailwind, no inline styles
- Section-based CSS prefix (`.hc-delete-*` for this story)
- Reset 98.css button chrome on custom elements if needed
- Add `:focus-visible` on custom interactive elements
- Axe audit required
- 511 frontend tests currently pass

### Files to Create/Modify

| File | Changes |
|------|---------|
| `healthcabinet/backend/app/users/service.py` | Add `delete_user_account()` |
| `healthcabinet/backend/app/users/router.py` | Add `DELETE /me` route |
| `healthcabinet/backend/tests/users/test_router.py` | Add deletion tests |
| `healthcabinet/frontend/src/lib/api/users.ts` | Add `deleteMyAccount()` |
| `healthcabinet/frontend/src/app.css` | Add `.hc-delete-*` classes (~7 new classes) |
| `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` | Add delete section + dialog |
| `healthcabinet/frontend/src/routes/(app)/settings/page.test.ts` | Add deletion UX tests |
| `healthcabinet/frontend/src/routes/(marketing)/+page.svelte` | Add `?deleted=true` banner |

### References

- [Source: _bmad-output/planning-artifacts/epics.md -- Story 6.2 Account & Data Deletion full acceptance criteria]
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md -- FE Epic 6 Story 4: calm but serious dialog]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md -- Destructive action patterns, dialog specs, emotional design]
- [Source: _bmad-output/planning-artifacts/prd.md -- FR4, FR33 deletion requirements]
- [Source: _bmad-output/implementation-artifacts/12-3-data-export-ux.md -- CSS patterns, learnings]
- [Source: healthcabinet/frontend/src/lib/components/ui/slide-over/ -- Focus trap reference]
- [Source: healthcabinet/frontend/src/lib/stores/auth.svelte.ts -- Logout/redirect pattern]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Migration 013: Changed consent_logs FK from CASCADE to SET NULL + nullable (GDPR regulatory retention)
- Backend: delete_user_account() service function — redacts audit_logs.user_id, then deletes user (CASCADE handles child tables)
- Backend: DELETE /users/me endpoint returns 204, requires auth
- Backend: 3 new tests (success+user removed, consent_logs retained with NULL user_id, auth required)
- Frontend API: deleteMyAccount() function calling DELETE /api/v1/users/me
- Frontend CSS: 7 new .hc-delete-* classes (section-warning, dialog-backdrop, dialog, title, body, actions, email-label)
- Frontend: Delete Account fieldset with "calm but serious" warning text and btn-destructive button
- Frontend: Confirmation dialog with email type-to-confirm (case-insensitive), ARIA dialog attributes, Escape/backdrop close
- Frontend: On success → authStore.logout() → redirect to /?deleted=true
- Frontend: Landing page reads ?deleted=true param, shows confirmation banner, removes param from URL
- Frontend: 4 new deletion tests + landing page test mock updated
- 515/515 frontend tests pass, 13/13 backend user router tests pass, 0 regressions, 0 type errors

### Change Log

- 2026-04-05: Story implementation complete -- Account & Data Deletion UX
- 2026-04-05: Code review patches applied -- 6 fixes (Escape key, focus trap, logout error, email trim, migration safety, test coverage)

### File List

- `healthcabinet/backend/alembic/versions/013_consent_logs_retain_on_user_delete.py` (new -- migration)
- `healthcabinet/backend/app/users/models.py` (modified -- ConsentLog FK SET NULL + nullable)
- `healthcabinet/backend/app/users/service.py` (modified -- added delete_user_account)
- `healthcabinet/backend/app/users/router.py` (modified -- added DELETE /me route)
- `healthcabinet/backend/tests/users/test_router.py` (modified -- added 3 deletion tests)
- `healthcabinet/frontend/src/lib/api/users.ts` (modified -- added deleteMyAccount)
- `healthcabinet/frontend/src/app.css` (modified -- added .hc-delete-* CSS classes)
- `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` (modified -- added delete section + dialog)
- `healthcabinet/frontend/src/routes/(app)/settings/page.test.ts` (modified -- added 4 deletion tests)
- `healthcabinet/frontend/src/routes/+page.svelte` (modified -- added ?deleted=true banner)
- `healthcabinet/frontend/src/routes/page.test.ts` (modified -- added $page store mock)
