# Story 13.3: User Management & User Detail Redesign

Status: done

## Story

As a platform admin working with user accounts and flagged value reports,
I want `/admin/users` and `/admin/users/[user_id]` restyled to 98.css with the same chrome and dialog contract as the rest of the admin console,
so that user triage, suspension, and flag review feel native to the operations console rather than leftover Tailwind scaffolds.

## Scope

Two routes, both fully reskinned in this story:

- **`/admin/users`** — Searchable user list + "Flagged Value Reports" section (two tables on one page)
- **`/admin/users/[user_id]`** — Per-user account-metadata detail page with Suspend / Reactivate action + confirmation dialog

**Reskin only.** Do NOT change API surface, query behavior, privacy boundaries, or business logic. Same discipline as Stories 11-1, 12-1, 13-1, 13-2.

## Acceptance Criteria

### Shared constraints

1. **No behavior change** — All queries (`getAdminUsers`, `getAdminUserDetail`, `getFlaggedReports`), mutations (`updateAdminUserStatus`, `markFlagReviewed`), debounced search, navigation targets (`goto('/admin/users/{id}')`, `goto('/admin/documents/{id}?health_value_id={hvid}')`), and privacy boundary (no health data in list/detail) are preserved exactly. Reskin only.

2. **All Tailwind structural classes removed** from both `+page.svelte` files. Replace with `.hc-admin-users-*` (list page) and `.hc-admin-user-detail-*` (detail page) prefixed classes in `app.css`. No scoped `<style>`, no inline Tailwind colors/spacing/layout, no `className` prop passing utility classes.

3. **Design-token discipline** — Use CSS variables (`--text-primary`, `--text-secondary`, `--surface-sunken`, `--border-sunken-outer`, `--accent`, `--accent-text`, `--status-concerning`, `--status-action`, `--status-optimal`). No hardcoded colors, no raw `#fff`.

4. **No `$lib/components/ui/button|input|label|textarea` imports** in either page. Use `.btn-*`, `.hc-input`, native `<label>` + `.hc-admin-*` label classes directly — same pattern 13-1/13-2 enforced. Import-guard regex test asserts this.

5. **Page container is `<main class="hc-admin-users-page">` / `<main class="hc-admin-user-detail-page">`** — parity with 13-1 and 13-2, which use `<main>` despite the nested-main concern. Project-wide nested-main fix lives in Story 13-5 per 13-1 retro deferral.

### Users list page (`/admin/users/+page.svelte`)

6. **Header layout** — `<header class="hc-admin-users-header">` containing title "User Management" (left, `.hc-admin-users-title`), subtitle "View accounts, manage suspension, and review flagged values" (`.hc-admin-users-subtitle`), Refresh button (right). Refresh button uses `.btn-standard`, keeps `aria-label="Refresh user list"`, still invalidates BOTH `['admin', 'users']` and `['admin', 'flags']` queries (matches existing behavior).

7. **Search input** — Replace the Tailwind `rounded-md border border-border` input with `<input class="hc-input hc-admin-users-search" ...>`. Preserve `placeholder="Search by email or user ID…"`, the `aria-label="Search users"`, the 300ms debounce (`debounceTimer`, `debouncedQuery` state), and the `onDestroy(clearTimeout)`. Wrap in `<label class="hc-admin-users-search-label">` with visually-hidden text "Search users" so the control has a programmatic label beyond `aria-label` (WCAG 1.3.1 parity with 13-2 input labeling fix).

8. **Use `DataTable` primitive for the user table** — Replace the inline `<table>` with `<DataTable columns={...} rows={...} onRowClick={(row) => goto(`/admin/users/${row.user_id}`)}>` from `$lib/components/ui/data-table`. Columns: `email` (sortable), `user_id` (sortable), `registration_date` (sortable), `upload_count` (sortable, align: center), `account_status` (sortable). Render cells via the `children` snippet: `user_id` → `truncateId()`, `registration_date` → `formatDate()`, `upload_count` → `.hc-admin-users-count-cell` tabular-nums, `account_status` → `<Badge variant={accountStatusVariant(status)}>{accountStatusLabel(status)}</Badge>`. Remove the inline `role="button"` / `tabindex="0"` / `onclick` / `onkeydown` wiring from rows — `DataTable` handles it.

9. **User list states**
   - **Loading:** `<div class="hc-admin-users-skeleton" role="status" aria-label="Loading users">` with 5 `.hc-admin-users-skeleton-row` children. No Tailwind `animate-pulse`; pulse animation lives in CSS keyframes (mirror `hc-admin-queue-skeleton-pulse` from 13-2).
   - **Error:** `<div class="hc-state hc-state-error" role="alert">` with title "Unable to load user list", body, and `.btn-standard` "Try again" button that calls `handleRefresh`.
   - **Empty (no search):** `.hc-admin-users-empty-panel` wrapping `.hc-state .hc-state-empty` with title "No users found" and body "Users will appear here after registration."
   - **Empty (search no match):** Same panel, title "No users match your search" and body "Try a different search term."
   - **Footer count:** `<p class="hc-admin-users-footer-count">Showing N user(s)</p>` after the table (plural-safe).

### Flagged Reports section (same `/admin/users/+page.svelte`)

10. **Section wrapper** — Wrap the flagged-reports block in a `<section class="hc-admin-users-flags-section">` with a heading `<h2 class="hc-admin-users-section-title">Flagged Value Reports</h2>`. No `mt-10` Tailwind margin; section-level spacing comes from the `.hc-admin-users-flags-section` class.

11. **Review error banner** — The `reviewError` banner uses `.hc-state .hc-state-error` with `role="alert"` and `.hc-state-title` for the message. No Tailwind destructive classes.

12. **Flags table** — Keep as a `<table>` wrapped in `.hc-admin-users-flags-table` (since `DataTable` row-click would conflict with per-row action buttons; an explicit table keeps the two-action-buttons-per-row pattern straightforward). Columns: Biomarker, Flagged Value, User ID, Document ID, Flagged At, Actions. Table headers use 98.css sunken chrome matching `.hc-data-table` style but scoped under `.hc-admin-users-flags-table`. Rows alternate optional.

13. **Flagged value column emphasis** — Use `.hc-admin-users-flag-value` (color: `var(--status-action)`; tabular-nums) on the flagged numeric value cell. No inline Tailwind `text-action` class.

14. **User-ID link** — The truncated user ID in the flagged-reports table must remain an interactive link that calls `goto('/admin/users/{user_id}')`. Use a `<button type="button" class="hc-admin-users-flag-userlink">` styled as an inline accent-colored link (underline on hover, `:focus-visible` ring). Do NOT render a raw `<button>` without a class — it must look like an inline text link, not a filled 98.css button.

15. **Action buttons per flag row** — Two buttons:
    - **"Open correction flow"** → `.btn-standard`; `goto('/admin/documents/${flag.document_id}?health_value_id=${flag.health_value_id}')` (query-param handoff to Story 13-2's highlight-row effect).
    - **"Mark Reviewed"** → `.btn-primary`; calls `handleReviewFlag(flag.health_value_id)` which invokes `markFlagReviewed`, then invalidates BOTH `['admin', 'flags']` AND `['admin', 'queue']` (matches existing behavior — reviewed flags may no longer keep a document in the queue).
    - Layout: `.hc-admin-users-flag-actions` flex row, `gap: 8px`, right-aligned.

16. **Flags states**
    - **Loading:** `.hc-admin-users-flags-skeleton` with `role="status"` + `aria-label="Loading flagged reports"`. 3 skeleton rows.
    - **Error:** `.hc-state .hc-state-error` with `role="alert"`, title "Unable to load flagged reports". No "Try again" button on this section — preserve existing behavior (refresh via page-level Refresh button).
    - **Empty:** `.hc-admin-users-flags-empty` wrapping `.hc-state .hc-state-empty` with body "No unreviewed flagged values."
    - **Footer count:** `<p class="hc-admin-users-flags-footer-count">{total} unreviewed flag(s)</p>`, plural-safe.

### User detail page (`/admin/users/[user_id]/+page.svelte`)

17. **Back button** — Replace the inline `<svg>` arrow + Tailwind hover classes with `<button type="button" class="btn-standard hc-admin-user-detail-back" onclick={() => goto('/admin/users')}>← Back to users</button>`. No SVG icons.

18. **Page header** — `<header class="hc-admin-user-detail-header">` with email as the page title (`<h1 class="hc-admin-user-detail-title">{user.email}</h1>`), the full UUID as `<p class="hc-admin-user-detail-id">{user.user_id}</p>` (monospace, muted), and Refresh button (right, `.btn-standard`, `aria-label="Refresh user details"`, invalidates `['admin', 'users', userId]`).

19. **Account metadata** — Wrap the 4-field `<dl>` inside `<fieldset class="hc-fieldset"><legend>Account Information</legend>` with `.hc-admin-user-detail-meta-grid` (3-column grid using `<dl>`, `<dt>`, `<dd>` semantics preserved). Fields (in order): Status (Badge), Registered, Last Login, Documents Uploaded. `dt` uses `.hc-admin-user-detail-meta-label` (secondary text); `dd` uses `.hc-admin-user-detail-meta-value` (primary text, tabular-nums for Documents Uploaded). The "Never" fallback for `last_login === null` is preserved via `formatDate()`.

20. **Status badge** — Still via `<Badge variant={accountStatusVariant(user.account_status)}>{accountStatusLabel(user.account_status)}</Badge>`. No CSS changes — the primitive already handles 98.css tokens.

21. **Update error banner** — When `updateError` is set, render `<div class="hc-state hc-state-error" role="alert"><p class="hc-state-title">{updateError}</p></div>` above the action-button row. Remove the Tailwind destructive banner.

22. **Action row** — `<div class="hc-admin-user-detail-actions">` (left-aligned) containing either:
    - **Suspend button** (when `user.account_status === 'active'`): `<button type="button" class="btn-destructive" onclick={() => promptStatusChange('suspended')}>Suspend Account</button>`
    - **Reactivate button** (when `'suspended'`): `<button type="button" class="btn-primary" onclick={() => promptStatusChange('active')}>Reactivate Account</button>`

    Replace the inline Tailwind `bg-action/10 text-action` / `bg-optimal/10 text-optimal` buttons with proper `.btn-destructive` / `.btn-primary` primitives. Keep `promptStatusChange(newStatus)` exactly.

23. **Confirmation dialog — use `ConfirmDialog` primitive** — Replace the inline `<div class="fixed inset-0 z-50…">` modal markup entirely with `<ConfirmDialog>` from `$lib/components/ui/confirm-dialog`:

    ```svelte
    <ConfirmDialog
      bind:open={showConfirmDialog}
      title={pendingStatus === 'suspended' ? 'Suspend Account?' : 'Reactivate Account?'}
      confirmLabel={pendingStatus === 'suspended' ? 'Suspend' : 'Reactivate'}
      confirmVariant={pendingStatus === 'suspended' ? 'destructive' : 'primary'}
      loading={isUpdating}
      loadingLabel="Updating…"
      onConfirm={confirmStatusChange}
    >
      {#if pendingStatus === 'suspended'}
        <p>This will immediately prevent the user from logging in or accessing the platform. Existing sessions will be terminated on their next API call.</p>
      {:else}
        <p>This will restore the user's access to the platform. They can log in normally.</p>
      {/if}
    </ConfirmDialog>
    ```

    **Remove entirely:** the hand-rolled backdrop div, panel div, `onclick={() => showConfirmDialog = false}`, the `svelte-ignore` comments, the manual Cancel/Confirm button markup. `ConfirmDialog` owns focus trap, Escape handling, backdrop click (while not loading), and button rendering.

    **Satisfies epic-12 retro Action Item 1:** "ConfirmDialog used by both settings deletion and at least one admin flow" — user suspension is the admin flow.

24. **Detail page states**
    - **Loading:** `.hc-admin-user-detail-skeleton` with `role="status"` + `aria-label="Loading user details"`. Skeleton approximates title-bar + metadata-fieldset shape.
    - **Error:** `.hc-state .hc-state-error` with `role="alert"`, title "Unable to load user details", body "The user may not exist or you may not have permission.", `.btn-standard` "Try again" button calling `handleRefresh`.

### Privacy / Data-model guardrails (MUST NOT violate)

25. **No health data is rendered on either page.** Do NOT add any field to the user table or detail view beyond: `email`, `user_id`, `registration_date`, `last_login` (detail only), `upload_count`, `account_status`. The existing API responses (`AdminUserListItem`, `AdminUserDetail` in `$lib/types/api.ts`) enforce this contract — do not accidentally destructure or fetch additional fields. Health data (documents, extracted values, AI interpretations) is intentionally inaccessible from this admin surface per Story 5.3 AC1/AC2.

26. **Admin-account scope preserved.** The backend's `list_admin_users` / `get_admin_user_detail` repository queries already exclude `role = "admin"` accounts (Story 5.3 Task 4). The frontend must not surface the notion of managing admin accounts (no "role" column, no role filter, no admin-specific empty-state copy). If the user is not found (404), the existing error state is the correct UX.

### Testing and a11y

27. **Tests updated** — Both `(admin)/admin/users/page.test.ts` and `(admin)/admin/users/[user_id]/page.test.ts`:
    - CSS class assertions for page containers, DataTable usage (list), fieldset legend (detail metadata), `.hc-admin-users-skeleton` / `.hc-admin-user-detail-skeleton` classes, `.hc-state-error` for error states, `.btn-destructive` / `.btn-primary` for action buttons.
    - Axe audit passes both pages (zero violations). Mock resolved data so the table renders.
    - Import-guard regex test (same pattern as 13-2, using terminators — NOT substring):
      ```ts
      expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/button['/]/);
      expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/input['/]/);
      expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/label['/]/);
      expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/textarea['/]/);
      ```
    - List page: row click navigates to `/admin/users/{user_id}` (spy `goto`); empty state renders; empty-search state renders the "No users match" copy; refresh invalidates BOTH `['admin', 'users']` AND `['admin', 'flags']`; Mark-Reviewed invalidates BOTH `['admin', 'flags']` AND `['admin', 'queue']`; Open-correction-flow navigates with `?health_value_id=` param; search debounces at 300ms.
    - Detail page: back button calls `goto('/admin/users')`; Suspend button visible for active user; Reactivate for suspended; clicking Suspend opens `<ConfirmDialog>` (assert via `role="dialog"` query); confirming calls `updateAdminUserStatus(userId, 'suspended')`; dialog `aria-label` matches title; Escape closes dialog (use `fireEvent.keyDown(dialogPanel, { key: 'Escape' })`); backdrop click closes when not loading; confirm button is `.btn-destructive` for suspend, `.btn-primary` for reactivate.
    - All existing tests in both files must continue to pass. Test counts should only grow.

28. **WCAG compliance** — Search input has a proper `<label>` (visible or `.sr-only`); the flags-section heading is `<h2>` (heading hierarchy `<h1>` page → `<h2>` section); user-ID link button has focus-visible ring; Suspend/Reactivate buttons announce state via visible label (no aria-live needed since button text changes drive the update); error banners `role="alert"`; loading states `role="status"` + `aria-label`; axe passes both pages.

## Tasks / Subtasks

- [x] Task 1: Add `.hc-admin-users-*` CSS classes to `app.css` (AC: 6, 7, 9, 10, 11, 12, 13, 14, 15, 16)
  - [x] `.hc-admin-users-page` — container layout (`max-width: 1400px; padding: 24px;`)
  - [x] `.hc-admin-users-header` + `-title` + `-subtitle` — flex row, title block
  - [x] `.hc-admin-users-search-label` + `-search` — label (visually-hidden) + input width (`max-width: 28rem`)
  - [x] `.hc-admin-users-count-cell` — `text-align: center; font-variant-numeric: tabular-nums;`
  - [x] `.hc-admin-users-empty-panel` — sunken-panel wrapper for empty-state centering
  - [x] `.hc-admin-users-skeleton` + `-skeleton-row` + keyframe (reuse `hc-pulse` or add `hc-admin-users-skeleton-pulse`)
  - [x] `.hc-admin-users-footer-count` — small secondary text
  - [x] `.hc-admin-users-flags-section` + `-section-title` — section wrapper + h2 style
  - [x] `.hc-admin-users-flags-table` — table chrome (sunken border, header styling) scoped for the inline `<table>`
  - [x] `.hc-admin-users-flag-value` — `color: var(--status-action); font-variant-numeric: tabular-nums;`
  - [x] `.hc-admin-users-flag-userlink` — inline accent-colored link button (reset 98.css button base: `background: none; border: none; padding: 0; box-shadow: none; text-shadow: none; color: var(--accent); cursor: pointer;` + `:hover` underline + `:focus-visible` ring)
  - [x] `.hc-admin-users-flag-actions` — flex row, `gap: 8px; justify-content: flex-end;`
  - [x] `.hc-admin-users-flags-skeleton` + keyframe
  - [x] `.hc-admin-users-flags-empty` + `.hc-admin-users-flags-footer-count`

- [x] Task 2: Add `.hc-admin-user-detail-*` CSS classes to `app.css` (AC: 18, 19, 22, 24)
  - [x] `.hc-admin-user-detail-page` — container layout
  - [x] `.hc-admin-user-detail-back` — margin-bottom on back button (to space from header)
  - [x] `.hc-admin-user-detail-header` — flex row with title-block (left) + refresh button (right)
  - [x] `.hc-admin-user-detail-title` — 18px bold, `color: var(--text-primary)`
  - [x] `.hc-admin-user-detail-id` — monospace, secondary text
  - [x] `.hc-admin-user-detail-meta-grid` — `display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px 24px;` inside fieldset
  - [x] `.hc-admin-user-detail-meta-label` — dt styling (secondary, small)
  - [x] `.hc-admin-user-detail-meta-value` — dd styling (primary), `&--numeric` variant with tabular-nums
  - [x] `.hc-admin-user-detail-actions` — flex row, left-aligned, `margin-top: 16px`
  - [x] `.hc-admin-user-detail-skeleton` + `-skeleton-title` + `-skeleton-panel` + keyframe

- [x] Task 3: Rewrite `/admin/users/+page.svelte` (AC: 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)
  - [x] Import `DataTable`, `type { Column }` from `$lib/components/ui/data-table`
  - [x] Define `columns: Column[]` for the user table (5 columns)
  - [x] Map `usersQuery.data.items` → rows with pre-formatted cells (truncate IDs, format date)
  - [x] Replace user table markup with `<DataTable>` + `children` snippet (mirror `/admin/documents/+page.svelte` pattern from 13-2)
  - [x] Replace search input with `.hc-input.hc-admin-users-search` inside `.hc-admin-users-search-label`
  - [x] Replace all `rounded-md border border-border …` Tailwind with `.hc-admin-users-*`
  - [x] Swap Refresh button to `.btn-standard`
  - [x] Swap Mark-Reviewed to `.btn-primary`, Open-correction-flow to `.btn-standard`
  - [x] Keep flagged-reports as an explicit `<table>` wrapped in `.hc-admin-users-flags-table` (two action buttons per row rule out DataTable row-click)
  - [x] Preserve `handleSearch`, `handleRefresh`, `handleReviewFlag`, `truncateId`, `formatDate`, `onDestroy(clearTimeout)`, the two `createQuery` configs, the `queryClient.invalidateQueries` calls (both `['admin', 'users']` on Refresh + `['admin', 'flags']` on Refresh and Mark-Reviewed; plus `['admin', 'queue']` on Mark-Reviewed)
  - [x] Remove `role="button" tabindex="0"` from user rows (DataTable handles it)

- [x] Task 4: Rewrite `/admin/users/[user_id]/+page.svelte` (AC: 1, 2, 4, 5, 17, 18, 19, 20, 21, 22, 23, 24)
  - [x] Import `ConfirmDialog` from `$lib/components/ui/confirm-dialog`
  - [x] Replace back-button markup: remove `<svg>`, use `.btn-standard.hc-admin-user-detail-back` with plain "←" prefix
  - [x] Replace page header with `.hc-admin-user-detail-title` / `-id` / refresh button (`.btn-standard`)
  - [x] Wrap account metadata in `<fieldset class="hc-fieldset"><legend>Account Information</legend>` using `<dl class="hc-admin-user-detail-meta-grid">` semantics
  - [x] Replace inline Tailwind Suspend/Reactivate buttons with `.btn-destructive` / `.btn-primary`
  - [x] Replace entire inline modal (`<div class="fixed inset-0 z-50…">` through `</div>`) with `<ConfirmDialog>` (see AC23)
  - [x] Delete the `svelte-ignore` comments for dialog a11y (no longer needed)
  - [x] Preserve `promptStatusChange`, `confirmStatusChange`, `handleRefresh`, `formatDate`, `isUpdating`, `updateError`, `pendingStatus`, `showConfirmDialog` state exactly
  - [x] Ensure `ConfirmDialog` receives `bind:open={showConfirmDialog}` so it closes correctly after success (existing `showConfirmDialog = false` in the `finally` block keeps working)

- [x] Task 5: Update tests (AC: 27)
  - [x] `(admin)/admin/users/page.test.ts`:
    - [x] Assert `.hc-admin-users-page` on container
    - [x] Assert `DataTable` rendered (query by role=table, verify columns)
    - [x] Row click test: click an `.hc-row-interactive` (or by email text) → `goto('/admin/users/{id}')`
    - [x] Empty state test: both "No users found" (no query) and "No users match your search" (with query) variants
    - [x] Refresh test: click refresh → both `['admin', 'users']` AND `['admin', 'flags']` invalidated (spy on `queryClient.invalidateQueries`)
    - [x] Mark-Reviewed test already exists — extend to assert both `['admin', 'flags']` AND `['admin', 'queue']` invalidated
    - [x] Open-correction-flow test already exists — keep
    - [x] Search debounce test already exists — keep
    - [x] `.hc-admin-users-flag-value` styling assertion on flagged value cell
    - [x] Axe audit test
    - [x] Import-guard regex test (all 4 shadcn primitives)
  - [x] `(admin)/admin/users/[user_id]/page.test.ts`:
    - [x] Assert `.hc-admin-user-detail-page` on container
    - [x] Assert back button is `.btn-standard`, clicking calls `goto('/admin/users')`
    - [x] Fieldset `<legend>Account Information</legend>` present
    - [x] Suspend button class is `.btn-destructive` for active user
    - [x] Reactivate button class is `.btn-primary` for suspended user
    - [x] Clicking Suspend opens a `role="dialog"` with `aria-modal="true"` and `aria-label="Suspend Account?"`
    - [x] Confirming suspend calls `updateAdminUserStatus(userId, 'suspended')` — preserve existing test
    - [x] Escape key on open dialog closes it (`fireEvent.keyDown` on the panel with `{key: 'Escape'}`)
    - [x] `updateError` renders in `.hc-state-error` with `role="alert"` when mutation rejects
    - [x] Axe audit test
    - [x] Import-guard regex test (all 4 shadcn primitives)

- [x] Task 6: WCAG audit (AC: 28)
  - [x] Search input has a programmatic label (not just `aria-label`)
  - [x] Flags section heading is `<h2>` and comes after `<h1>`
  - [x] User-ID link button has `:focus-visible` ring
  - [x] Error banners have `role="alert"`; loading states have `role="status"` + `aria-label`
  - [x] Fieldset has `<legend>Account Information</legend>`
  - [x] `ConfirmDialog` provides focus trap + Escape + backdrop-close (already implemented by primitive — verify via render test)
  - [x] Axe audit passes on both pages

### Review Findings

- [x] [Review][Patch] Focus outline width on `.hc-admin-users-flag-userlink:focus-visible` was 1px, spec requires 2px — fixed [healthcabinet/frontend/src/app.css:2162]
- [x] [Review][Defer] Dialog closes on mutation failure — `finally { showConfirmDialog = false }` hides error from user; pre-existing behavior preserved per AC 1 [healthcabinet/frontend/src/routes/(admin)/admin/users/[user_id]/+page.svelte:44]
- [x] [Review][Defer] "Mark Reviewed" button has no double-click guard — pre-existing, deferred to 13-5 per epic-12 retro Action 6 [healthcabinet/frontend/src/routes/(admin)/admin/users/+page.svelte:43-52]
- [x] [Review][Defer] ConfirmDialog `previouslyFocused.focus()` on detached element — pre-existing in primitive, deferred to 13-5 per epic-12 retro [healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.svelte:119-125]

## Dev Notes

### Architecture & Patterns

- **Reskin only — preserve all behavior.** Same discipline as 13-1, 13-2, 11-1, 12-1. Scripts stay untouched except for: (a) importing `DataTable` and `Column` type in the list page, (b) importing `ConfirmDialog` in the detail page, (c) removing `role="button" tabindex="0"` from user rows (DataTable handles), (d) deleting the inline dialog markup in the detail page.
- **AdminShell already 98.css.** Both routes inherit chrome from `(admin)/+layout.svelte` → `AdminShell.svelte` (Story 9-3). Do NOT touch the layout.
- **Reuse `DataTable`** for the user list — it handles sortable columns, row-click, keyboard navigation (Enter/Space), ARIA `aria-sort`. Precedent: `/admin/documents/+page.svelte` (13-2).
- **Explicit `<table>` for flagged reports** — not `DataTable`. Two action buttons per row (Open correction / Mark Reviewed) make row-click ambiguous. Keep the explicit table and scope chrome via `.hc-admin-users-flags-table`.
- **Reuse `Badge` + `accountStatusVariant`/`accountStatusLabel`** — the helpers at `$lib/components/ui/badge/account-status.ts` already map `active` → `success`, `suspended` → `danger`. Perfect for both pages. No new badge logic.
- **Reuse `ConfirmDialog` primitive** at `$lib/components/ui/confirm-dialog/` — 12-4 extracted it, epic-12 retro Action Item 1 explicitly requires an admin flow to adopt it. This story is that flow. The primitive handles: focus trap, Escape-close, backdrop-click-close (disabled while `loading`), confirm-button disabled-while-loading, `confirmVariant` style, `canConfirm` gate, auto-focus on mount, focus restore on close.
- **`ConfirmDialog` does NOT auto-close on confirm** — the parent owns lifecycle via `bind:open`. The existing `confirmStatusChange` already sets `showConfirmDialog = false` in its `finally` block, which matches the primitive's contract exactly. No logic changes needed.
- **Reuse `.hc-badge-*` primitives** (`app.css:468-510`) — `.hc-badge-default`, `-info`, `-success`, `-warning`, `-danger`.
- **Reuse `.hc-state-*` primitives** (`app.css:511+`) — `.hc-state`, `.hc-state-empty`, `.hc-state-error`, `.hc-state-loading`, `.hc-state-title`.
- **Reuse `.hc-data-table`** chrome when inline-table is needed (flagged reports) — match the sunken border / header style by extending that class.
- **Reuse `.hc-fieldset` + `<legend>`** for the account-information metadata panel. Same pattern as 12-1 (medical profile) and 13-2 (document metadata).
- **Match the design precedent.** Compare against `ux-design-directions-v2.html` (admin pages section around L1811: "👥 Users" sidebar item) and the admin overview rendering produced in 13-1. No dedicated mockup exists for the user-list or user-detail pages — derive layout from 13-1 (overview) and 13-2 (queue/correction) conventions. Run the app in a browser after implementation and verify the chrome matches the rest of the admin console.

### Current Page Structure (What to Change)

**Users list page — current (Tailwind):**

```svelte
<main class="p-8">
  <div class="mb-6 flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-semibold">User Management</h1>
      <p class="mt-1 text-sm text-muted-foreground">View and manage user accounts</p>
    </div>
    <button onclick={handleRefresh} class="rounded-md border border-border px-4 py-2 …">Refresh</button>
  </div>
  <div class="mb-4">
    <input type="text" placeholder="Search by email or user ID…" class="w-full max-w-md rounded-md …" />
  </div>
  <div class="rounded-lg border border-border overflow-hidden">
    <table class="w-full">… inline Tailwind table with manual row-click handling …</table>
  </div>
  <div class="mt-10">
    <h2 class="mb-4 text-xl font-semibold">Flagged Value Reports</h2>
    … Tailwind flags table with two action buttons per row …
  </div>
</main>
```

**Users list page — target (98.css):**

```svelte
<main class="hc-admin-users-page">
  <header class="hc-admin-users-header">
    <div>
      <h1 class="hc-admin-users-title">User Management</h1>
      <p class="hc-admin-users-subtitle">View accounts, manage suspension, and review flagged values</p>
    </div>
    <button type="button" class="btn-standard" aria-label="Refresh user list" onclick={handleRefresh}>Refresh</button>
  </header>

  <label class="hc-admin-users-search-label">
    <span class="sr-only">Search users</span>
    <input
      type="text"
      class="hc-input hc-admin-users-search"
      placeholder="Search by email or user ID…"
      value={searchQuery}
      oninput={(e) => handleSearch(e.currentTarget.value)}
      aria-label="Search users"
    />
  </label>

  {#if usersQuery.isPending}
    <div class="hc-admin-users-skeleton" role="status" aria-label="Loading users">
      {#each Array(5) as _}<div class="hc-admin-users-skeleton-row"></div>{/each}
    </div>
  {:else if usersQuery.isError}
    <div class="hc-state hc-state-error" role="alert">
      <p class="hc-state-title">Unable to load user list.</p>
      <p>Try refreshing the page or contact support if the issue persists.</p>
      <button type="button" class="btn-standard" onclick={handleRefresh}>Try again</button>
    </div>
  {:else if usersQuery.data}
    {@const data = usersQuery.data}
    {#if data.items.length === 0}
      <div class="hc-admin-users-empty-panel">
        <div class="hc-state hc-state-empty">
          <p class="hc-state-title">{debouncedQuery ? 'No users match your search' : 'No users found'}</p>
          <p>{debouncedQuery ? 'Try a different search term.' : 'Users will appear here after registration.'}</p>
        </div>
      </div>
    {:else}
      <DataTable {columns} {rows} onRowClick={(row) => goto(`/admin/users/${row.user_id}`)}>
        {#snippet children(row, col)}
          {#if col.key === 'user_id'}
            <span>{truncateId(String(row.user_id))}</span>
          {:else if col.key === 'registration_date'}
            {formatDate(String(row.registration_date))}
          {:else if col.key === 'upload_count'}
            <span class="hc-admin-users-count-cell">{row.upload_count}</span>
          {:else if col.key === 'account_status'}
            <Badge variant={accountStatusVariant(String(row.account_status))}>
              {accountStatusLabel(String(row.account_status))}
            </Badge>
          {:else}
            {row[col.key] ?? ''}
          {/if}
        {/snippet}
      </DataTable>
      <p class="hc-admin-users-footer-count">Showing {data.items.length} user{data.items.length !== 1 ? 's' : ''}</p>
    {/if}
  {/if}

  <section class="hc-admin-users-flags-section">
    <h2 class="hc-admin-users-section-title">Flagged Value Reports</h2>
    {#if reviewError}
      <div class="hc-state hc-state-error" role="alert"><p class="hc-state-title">{reviewError}</p></div>
    {/if}
    {#if flagsQuery.isPending}
      <div class="hc-admin-users-flags-skeleton" role="status" aria-label="Loading flagged reports">…</div>
    {:else if flagsQuery.isError}
      <div class="hc-state hc-state-error" role="alert"><p class="hc-state-title">Unable to load flagged reports.</p></div>
    {:else if flagsQuery.data}
      {@const flags = flagsQuery.data}
      {#if flags.items.length === 0}
        <div class="hc-admin-users-flags-empty">
          <div class="hc-state hc-state-empty"><p>No unreviewed flagged values.</p></div>
        </div>
      {:else}
        <div class="hc-admin-users-flags-table">
          <table>
            <thead><tr>
              <th>Biomarker</th><th>Flagged Value</th><th>User ID</th><th>Document ID</th><th>Flagged At</th><th>Actions</th>
            </tr></thead>
            <tbody>
              {#each flags.items as flag (flag.health_value_id)}
                <tr>
                  <td>{flag.value_name}</td>
                  <td class="hc-admin-users-flag-value">{flag.flagged_value}</td>
                  <td>
                    <button type="button" class="hc-admin-users-flag-userlink"
                            onclick={() => goto(`/admin/users/${flag.user_id}`)}>
                      {truncateId(flag.user_id)}
                    </button>
                  </td>
                  <td>{truncateId(flag.document_id)}</td>
                  <td>{formatDate(flag.flagged_at)}</td>
                  <td>
                    <div class="hc-admin-users-flag-actions">
                      <button type="button" class="btn-standard"
                              onclick={() => goto(`/admin/documents/${flag.document_id}?health_value_id=${flag.health_value_id}`)}>
                        Open correction flow
                      </button>
                      <button type="button" class="btn-primary"
                              onclick={() => handleReviewFlag(flag.health_value_id)}>
                        Mark Reviewed
                      </button>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <p class="hc-admin-users-flags-footer-count">{flags.total} unreviewed flag{flags.total !== 1 ? 's' : ''}</p>
      {/if}
    {/if}
  </section>
</main>
```

**User detail page — target (98.css):**

```svelte
<main class="hc-admin-user-detail-page">
  <button type="button" class="btn-standard hc-admin-user-detail-back" onclick={() => goto('/admin/users')}>
    ← Back to users
  </button>

  {#if userQuery.isPending}
    <div class="hc-admin-user-detail-skeleton" role="status" aria-label="Loading user details">
      <div class="hc-admin-user-detail-skeleton-title"></div>
      <div class="hc-admin-user-detail-skeleton-panel"></div>
    </div>
  {:else if userQuery.isError}
    <div class="hc-state hc-state-error" role="alert">
      <p class="hc-state-title">Unable to load user details.</p>
      <p>The user may not exist or you may not have permission.</p>
      <button type="button" class="btn-standard" onclick={handleRefresh}>Try again</button>
    </div>
  {:else if userQuery.data}
    {@const user = userQuery.data}
    <header class="hc-admin-user-detail-header">
      <div>
        <h1 class="hc-admin-user-detail-title">{user.email}</h1>
        <p class="hc-admin-user-detail-id">{user.user_id}</p>
      </div>
      <button type="button" class="btn-standard" aria-label="Refresh user details" onclick={handleRefresh}>Refresh</button>
    </header>

    <fieldset class="hc-fieldset">
      <legend>Account Information</legend>
      <dl class="hc-admin-user-detail-meta-grid">
        <div>
          <dt class="hc-admin-user-detail-meta-label">Status</dt>
          <dd class="hc-admin-user-detail-meta-value">
            <Badge variant={accountStatusVariant(user.account_status)}>
              {accountStatusLabel(user.account_status)}
            </Badge>
          </dd>
        </div>
        <div>
          <dt class="hc-admin-user-detail-meta-label">Registered</dt>
          <dd class="hc-admin-user-detail-meta-value">{formatDate(user.registration_date)}</dd>
        </div>
        <div>
          <dt class="hc-admin-user-detail-meta-label">Last Login</dt>
          <dd class="hc-admin-user-detail-meta-value">{formatDate(user.last_login)}</dd>
        </div>
        <div>
          <dt class="hc-admin-user-detail-meta-label">Documents Uploaded</dt>
          <dd class="hc-admin-user-detail-meta-value hc-admin-user-detail-meta-value--numeric">{user.upload_count}</dd>
        </div>
      </dl>
    </fieldset>

    {#if updateError}
      <div class="hc-state hc-state-error" role="alert"><p class="hc-state-title">{updateError}</p></div>
    {/if}

    <div class="hc-admin-user-detail-actions">
      {#if user.account_status === 'active'}
        <button type="button" class="btn-destructive" onclick={() => promptStatusChange('suspended')}>
          Suspend Account
        </button>
      {:else}
        <button type="button" class="btn-primary" onclick={() => promptStatusChange('active')}>
          Reactivate Account
        </button>
      {/if}
    </div>
  {/if}
</main>

<ConfirmDialog
  bind:open={showConfirmDialog}
  title={pendingStatus === 'suspended' ? 'Suspend Account?' : 'Reactivate Account?'}
  confirmLabel={pendingStatus === 'suspended' ? 'Suspend' : 'Reactivate'}
  confirmVariant={pendingStatus === 'suspended' ? 'destructive' : 'primary'}
  loading={isUpdating}
  loadingLabel="Updating…"
  onConfirm={confirmStatusChange}
>
  {#if pendingStatus === 'suspended'}
    <p>This will immediately prevent the user from logging in or accessing the platform. Existing sessions will be terminated on their next API call.</p>
  {:else}
    <p>This will restore the user's access to the platform. They can log in normally.</p>
  {/if}
</ConfirmDialog>
```

### CSS Classes to Add (app.css)

**Users list page (`.hc-admin-users-*`):**

| Class | Purpose |
|-------|---------|
| `.hc-admin-users-page` | `max-width: 1400px; padding: 24px;` (match `.hc-admin-queue-page` from 13-2) |
| `.hc-admin-users-header` | flex row, space-between, align-items: flex-start, margin-bottom |
| `.hc-admin-users-title` | 18px bold, `color: var(--text-primary)` |
| `.hc-admin-users-subtitle` | 13px `color: var(--text-secondary)` |
| `.hc-admin-users-search-label` | `display: block; margin-bottom: 16px;` + `.sr-only` visually-hidden `<span>` child (reuse `.sr-only` or add: `position: absolute; width: 1px; …`) |
| `.hc-admin-users-search` | width override for `.hc-input` (`max-width: 28rem`) |
| `.hc-admin-users-count-cell` | `text-align: center; font-variant-numeric: tabular-nums;` |
| `.hc-admin-users-empty-panel` | centered, 48px padding inside sunken panel (match `.hc-admin-queue-empty-panel`) |
| `.hc-admin-users-skeleton` | skeleton container, grid of rows |
| `.hc-admin-users-skeleton-row` | `min-height: 40px; background: var(--surface-sunken); animation: hc-pulse 1.5s ease-in-out infinite;` + `@media (prefers-reduced-motion: reduce) { animation: none; opacity: 0.85; }` |
| `.hc-admin-users-footer-count` | small, secondary text, top margin |
| `.hc-admin-users-flags-section` | `margin-top: 40px;` — section spacing |
| `.hc-admin-users-section-title` | 16px bold, `margin-bottom: 16px;` |
| `.hc-admin-users-flags-table` | wraps `<table>`, 98.css sunken chrome (border, header bg, row separators) scoped inside |
| `.hc-admin-users-flag-value` | `color: var(--status-action); font-variant-numeric: tabular-nums;` |
| `.hc-admin-users-flag-userlink` | reset button base + `color: var(--accent); background: none; border: none; padding: 0; cursor: pointer; text-shadow: none; box-shadow: none;` + `:hover { text-decoration: underline; }` + `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }` |
| `.hc-admin-users-flag-actions` | `display: flex; gap: 8px; justify-content: flex-end;` |
| `.hc-admin-users-flags-skeleton` | 3-row skeleton, same keyframe as `.hc-admin-users-skeleton` |
| `.hc-admin-users-flags-empty` | empty-state wrapper (match `.hc-admin-users-empty-panel` scale) |
| `.hc-admin-users-flags-footer-count` | small secondary text |

**User detail page (`.hc-admin-user-detail-*`):**

| Class | Purpose |
|-------|---------|
| `.hc-admin-user-detail-page` | `max-width: 1400px; padding: 24px;` |
| `.hc-admin-user-detail-back` | `margin-bottom: 16px;` |
| `.hc-admin-user-detail-header` | flex row with title-block left, refresh right; `margin-bottom: 16px;` |
| `.hc-admin-user-detail-title` | 18px bold, `color: var(--text-primary)`, `margin: 0;` |
| `.hc-admin-user-detail-id` | monospace, 12px, `color: var(--text-secondary); margin-top: 4px;` |
| `.hc-admin-user-detail-meta-grid` | `display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px 24px;` inside fieldset |
| `.hc-admin-user-detail-meta-label` | `font-size: 12px; color: var(--text-secondary); margin: 0 0 4px;` |
| `.hc-admin-user-detail-meta-value` | `font-size: 14px; color: var(--text-primary); margin: 0;` |
| `.hc-admin-user-detail-meta-value--numeric` | `font-variant-numeric: tabular-nums;` |
| `.hc-admin-user-detail-actions` | `display: flex; gap: 8px; margin-top: 16px;` |
| `.hc-admin-user-detail-skeleton` | container |
| `.hc-admin-user-detail-skeleton-title` | `height: 28px; width: 256px; background: var(--surface-sunken); animation: hc-pulse 1.5s ease-in-out infinite;` |
| `.hc-admin-user-detail-skeleton-panel` | `height: 192px; background: var(--surface-sunken); animation: hc-pulse 1.5s ease-in-out infinite; margin-top: 16px;` |

**Reuse:** If `@keyframes hc-pulse` already exists (check `app.css:593`), reuse it instead of adding a new keyframe. Both skeletons above reference it. Add `@media (prefers-reduced-motion: reduce)` fallback for each skeleton.

### Existing CSS / Primitives to Reuse

- `.hc-badge-default`, `-info`, `-success`, `-warning`, `-danger` (via `<Badge>` component)
- `.hc-fieldset` + `legend`
- `.hc-input` — sunken text input
- `.btn-standard`, `.btn-primary`, `.btn-destructive`
- `.hc-state`, `.hc-state-empty`, `.hc-state-error`, `.hc-state-title`
- `.hc-data-table` (consumed via `DataTable` component at `$lib/components/ui/data-table/`)
- `.hc-dialog-*` (consumed via `ConfirmDialog` component at `$lib/components/ui/confirm-dialog/`)
- `@keyframes hc-pulse` (app.css:593) — reuse for skeleton animations
- `.sr-only` if defined; otherwise inline visually-hidden styles on the search-label span

### Backend API Contracts (No Changes)

```
GET  /api/v1/admin/users?q={query}
     → AdminUserListResponse { items: AdminUserListItem[], total: number }
       AdminUserListItem: { user_id, email, registration_date, upload_count, account_status }

GET  /api/v1/admin/users/{user_id}
     → AdminUserDetail { user_id, email, registration_date, last_login, upload_count, account_status }

PATCH /api/v1/admin/users/{user_id}/status
     Body: { account_status: 'active' | 'suspended' }
     → AdminUserDetail

GET  /api/v1/admin/flags
     → FlaggedReportListResponse { items: FlaggedReportItem[], total }
       FlaggedReportItem: { health_value_id, user_id, document_id, value_name, flagged_value, flagged_at }

POST /api/v1/admin/flags/{health_value_id}/review
     → FlagReviewedResponse { health_value_id, reviewed_at }
```

All types defined in `$lib/types/api.ts`. All functions in `$lib/api/admin.ts`. No backend changes.

**Privacy contract enforced server-side** (Story 5.3, repository queries): admin user endpoints never return health data, and the user list excludes admins (`role = "user"` filter in `list_admin_users`). The frontend relies on these server guarantees — do not attempt to display any additional fields.

### Previous Story Learnings (carry forward from 13-1, 13-2, 12-1, 12-4)

- Use `.hc-*` CSS classes exclusively. No Tailwind structural classes. No scoped styles. No inline styles.
- Section-based CSS prefix per page (`.hc-admin-users-*`, `.hc-admin-user-detail-*`)
- Reset 98.css button base on custom interactive elements (user-ID link button): `min-width: 0; box-shadow: none; text-shadow: none; background: none; border: none; padding: 0;`
- Use `var(--accent-text)` not hardcoded `#fff` on accent backgrounds
- Add `:focus-visible` on custom interactive elements (user-ID link)
- **Import-guard test uses regex with terminators** — `.not.toMatch(/from '\$lib\/components\/ui\/button['/]/)` (terminator `['/]`), NOT substring. Tightened in 12-5 / epic-12-retro Action 1 patch — do not regress.
- Axe audit test required on both pages (zero violations)
- Compare against `ux-design-directions-v2.html` mockup (admin section) + run the app in a browser before marking done (Epic 11 retro Action 1)
- **Baseline test count at start of this story: 547 (after 13-2)**. Maintain zero regressions. Existing 12 pre-existing failures (documents/page.test.ts, AIChatWindow.test.ts, users.test.ts) are unchanged from 13-2 — do NOT attempt to fix them in this story; they are out of scope. However, once 13-3 changes the `/admin/users` page, the existing `users.test.ts` baseline failure count may shift — verify the test file still tests what it's supposed to test (it's `$lib/api/users.test.ts`, unrelated to `/admin/users` route tests).
- **`<main>` nesting is acceptable** for parity with 13-1 and 13-2 — project-wide nested-main fix happens in 13-5 per retro deferral.
- **`ConfirmDialog` does NOT auto-close on confirm.** Parent owns `bind:open`. The existing `finally { showConfirmDialog = false }` in `confirmStatusChange` satisfies this exactly — do not add extra close logic.
- JSDOM `scrollIntoView` note (from 13-2) does not apply here — no scroll-to-highlight logic in these pages.

### Git Intelligence (recent commits informing this story)

- `b629bc2` — 13-2 queue/correction accessibility + styling refinements (immediate precedent pattern)
- `3f40d52` — 13-1 admin overview `MetricCard` + fieldset pattern
- `c761e51` — `ConfirmDialog` extracted from settings (primitive available, proven in settings page)
- `06a7da3` — input width adjustments (reminder: search input width should come from `.hc-admin-users-search` override, not inline Tailwind)

### Files to Modify

| File | Changes |
|------|---------|
| `healthcabinet/frontend/src/app.css` | Add `.hc-admin-users-*` (~20 classes + skeleton) + `.hc-admin-user-detail-*` (~12 classes + skeleton) |
| `healthcabinet/frontend/src/routes/(admin)/admin/users/+page.svelte` | Rewrite template: DataTable + inline flags table with 98.css chrome |
| `healthcabinet/frontend/src/routes/(admin)/admin/users/[user_id]/+page.svelte` | Rewrite template: fieldset + `.btn-destructive`/`.btn-primary`; replace inline modal with `<ConfirmDialog>` |
| `healthcabinet/frontend/src/routes/(admin)/admin/users/page.test.ts` | Expand to include class assertions, DataTable behavior, empty-search state, invalidation-set assertions, axe, import-guard |
| `healthcabinet/frontend/src/routes/(admin)/admin/users/[user_id]/page.test.ts` | Expand to include class assertions, ConfirmDialog behavior (role=dialog, Escape, aria-label), button-variant classes, error-banner class, axe, import-guard |

### Files NOT to Modify

- `healthcabinet/frontend/src/routes/(admin)/+layout.svelte` (AdminShell already 98.css)
- `healthcabinet/frontend/src/lib/components/AdminShell.svelte`
- `healthcabinet/frontend/src/lib/api/admin.ts` (backend contracts unchanged)
- `healthcabinet/frontend/src/lib/types/api.ts` (types unchanged)
- `healthcabinet/frontend/src/lib/components/ui/badge/*` (`Badge` + `accountStatus*` helpers already 98.css-compatible)
- `healthcabinet/frontend/src/lib/components/ui/confirm-dialog/*` (primitive unchanged)
- Any backend file (no migrations, no router changes, no service changes)

### Test Wrappers

Both `AdminUsersPageTestWrapper.svelte` and `AdminUserDetailTestWrapper.svelte` already exist (both just wrap `+page.svelte` in a `QueryClientProvider`). Reuse both as-is. No changes to wrappers.

### Project Structure Notes

- Both routes live under `(admin)/admin/users/` — SvelteKit group + nested route
- `DataTable` primitive at `lib/components/ui/data-table/` — do NOT create new table components
- `ConfirmDialog` primitive at `lib/components/ui/confirm-dialog/` — do NOT create new dialog components (epic-12 retro Action 1 explicitly requires adopting this)
- `Badge` primitive + `accountStatus*` helpers at `lib/components/ui/badge/` — already used by the current pages; keep using them

### Out-of-Scope Items (Do Not Do)

- **Do not add E2E tests.** Epic-12 retro flagged these as desirable for admin flows but they remain out of scope through Epic 13 unless explicitly scheduled in 13-5. Unit + axe only.
- **Do not fix pre-existing failures** in `documents/page.test.ts`, `AIChatWindow.test.ts`, `users.test.ts`. They were pre-existing before 13-2 and remain so; fixing them is not in 13-3 scope.
- **Do not touch the backend.** All endpoints and contracts are stable from Story 5.3.
- **Do not introduce a "delete user" action.** User deletion is a Story 6-2 (account deletion) + admin-self-deletion-policy (retro Action 5) concern, not 13-3. Suspend/reactivate is the only admin lifecycle action in scope.
- **Do not add a role filter or role column.** The backend already excludes admin accounts from the list; surfacing role in the UI would expose operational surface not specified in 5.3 ACs.
- **Do not add pagination** to either the user list or the flagged-reports list. Neither endpoint supports pagination (total is provided; no offset/limit). If list sizes grow unmanageable in production, that's a separate backend + frontend story.
- **Do not fix the nested-`<main>` issue.** It's a project-wide deferral scheduled for 13-5.
- **Do not attempt to hook up the Suspend/Reactivate mutation to `queryClient.invalidateQueries(['admin', 'users', userId])`** any differently than the current code does. The existing invalidation already covers the list-level cache — keep it as-is.

### References

- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md#fe-epic-7 — FE Epic 7 Story 3 scope: "User management and user-detail surface redesign"]
- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.3 (FR37, FR38): user management + flag response acceptance criteria]
- [Source: _bmad-output/planning-artifacts/prd.md — FR37 (admin user account management), FR38 (admin flag review)]
- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md#11-admin-dashboard — Admin shell sidebar ("Users" item) and auth-guard pattern]
- [Source: _bmad-output/implementation-artifacts/5-3-user-account-management-flag-response.md — original backend story with privacy boundary ACs and API contracts]
- [Source: _bmad-output/implementation-artifacts/13-1-admin-overview-redesign.md — admin overview pattern (MetricCard + fieldset + .hc-admin-overview-* prefix)]
- [Source: _bmad-output/implementation-artifacts/13-2-extraction-error-queue-correction-ux.md — DataTable adoption + fieldset metadata + .hc-admin-queue-* / .hc-admin-correction-* precedents]
- [Source: _bmad-output/implementation-artifacts/12-4-account-data-deletion-ux.md — inline dialog markup that was extracted into ConfirmDialog primitive]
- [Source: _bmad-output/implementation-artifacts/epic-12-retro-2026-04-15.md — Action Item 1 (ConfirmDialog admin adoption), Action Item 5 (admin self-deletion — out of scope for 13-3)]
- [Source: healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.svelte — ConfirmDialog props contract]
- [Source: healthcabinet/frontend/src/lib/components/ui/data-table/data-table.svelte — DataTable Column interface and children snippet contract]
- [Source: healthcabinet/frontend/src/lib/components/ui/badge/account-status.ts — accountStatusVariant / accountStatusLabel helpers]
- [Source: healthcabinet/frontend/src/routes/(admin)/admin/documents/+page.svelte — DataTable + children snippet pattern to mirror]
- [Source: healthcabinet/frontend/src/routes/(app)/settings/+page.svelte:659 — ConfirmDialog usage pattern to mirror]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `docker compose -f /Users/vladtara/dev/set-bmad/healthcabinet/docker-compose.yml exec frontend npm run test:unit -- 'src/routes/(admin)/admin/users/page.test.ts'` passed (`12/12`).
- `docker compose -f /Users/vladtara/dev/set-bmad/healthcabinet/docker-compose.yml exec frontend npm run test:unit -- 'src/routes/(admin)/admin/users/[user_id]/page.test.ts'` passed (`15/15`).
- `docker compose -f /Users/vladtara/dev/set-bmad/healthcabinet/docker-compose.yml exec frontend npm run check` passed with `0` errors and `1` pre-existing warning in `src/lib/components/health/AIChatWindow.svelte:179`.
- `docker compose -f /Users/vladtara/dev/set-bmad/healthcabinet/docker-compose.yml exec frontend npm run test:unit` remains red in unrelated pre-existing suites outside Story 13-3 (`documents/page.test.ts`, `AIChatWindow.test.ts`, and one additional existing failing file in the full-suite baseline).
- `docker compose -f /Users/vladtara/dev/set-bmad/healthcabinet/docker-compose.yml exec frontend npm run lint` remains repo-red due pre-existing generated `build/` formatting noise and existing Svelte parser failures outside this story's scope.

### Completion Notes List

- Reskinned `/admin/users` to shared 98.css patterns with `DataTable`, accessible search labeling, state banners, and a scoped flagged-reports table while preserving query/mutation/navigation behavior.
- Reskinned `/admin/users/[user_id]` to fieldset-based account metadata with primitive action buttons and `ConfirmDialog` replacing the inline modal implementation.
- Added `.hc-admin-users-*` and `.hc-admin-user-detail-*` CSS blocks in `app.css`, including skeletons, flag-link focus states, footer counts, and detail-page action/layout styling.
- Expanded both route test files to cover container classes, invalidation behavior, dialog semantics, accessibility checks, and import-guard enforcement.

### File List

- `healthcabinet/frontend/src/app.css`
- `healthcabinet/frontend/src/routes/(admin)/admin/users/+page.svelte`
- `healthcabinet/frontend/src/routes/(admin)/admin/users/page.test.ts`
- `healthcabinet/frontend/src/routes/(admin)/admin/users/[user_id]/+page.svelte`
- `healthcabinet/frontend/src/routes/(admin)/admin/users/[user_id]/page.test.ts`

### Change Log

- `2026-04-15`: Story implementation complete; moved to `review`.
