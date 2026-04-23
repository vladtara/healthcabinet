---
title: 'Extract inline confirmation dialog into reusable ConfirmDialog component'
type: 'refactor'
created: '2026-04-15'
status: 'done'
baseline_commit: '06a7da35fc0591675135837b88f949b0f940681e'
context:
  - _bmad-output/implementation-artifacts/epic-12-retro-2026-04-15.md
  - healthcabinet/frontend/src/lib/components/ui/slide-over/slide-over.svelte
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story 12-4's account-deletion dialog is inline in `settings/+page.svelte` (~80 lines of markup + dialog state). Epic 13 needs admin confirmations (ban user, bulk corrections) — without extraction, those will copy-paste diverge from the tested 12-4 contract.

**Approach:** Extract the dialog shell (backdrop, raised panel, title bar, body slot, footer buttons, focus trap, Escape, programmatic focus) into `lib/components/ui/confirm-dialog/` following the `slide-over` pattern. Keep all product-specific state (email input, type-to-confirm gate, deletion handler) in the settings page, passed into the dialog as body children + `canConfirm` prop. Zero behavior change — 6 existing dialog tests on `settings/page.test.ts` must pass unchanged.

## Boundaries & Constraints

**Always:**
- Preserve the exact dialog contract: `role="dialog"`, `aria-modal="true"`, `aria-label`, `tabindex="-1"`, focus trap with Tab cycling (forward + shift-Tab), Escape close, backdrop click close, programmatic focus via `requestAnimationFrame` on open
- Reuse existing `.hc-delete-*` CSS classes OR rename to `.hc-dialog-*` — caller's choice, but must be tokenized (no scoped styles, no Tailwind)
- Restore previously-focused element on close (slide-over pattern — 12-4 didn't have this, but the pattern is better)
- `open` must be `$bindable()` so parent owns the state
- Zero regressions across 520 frontend tests; 6 dialog tests in `settings/page.test.ts` pass without edits

**Ask First:**
- Renaming CSS class prefix from `.hc-delete-*` to `.hc-dialog-*` (cross-cuts multiple stories' CSS) — DEFAULT: rename to `.hc-dialog-*` since the class is no longer delete-specific
- Whether to add focus restoration on close (slide-over has it, 12-4 didn't) — DEFAULT: add it, it's a 5-line a11y improvement

**Never:**
- Do NOT change the account-deletion behavior (handler logic, auth flow, redirect, error shape)
- Do NOT add new UX: no animations beyond 12-4's current state, no custom close icons, no toast on close
- Do NOT touch `consent_logs` migration, backend endpoint, or any other Epic 12 stories' work
- Do NOT build for hypothetical future admin flows beyond the stated props — `confirmVariant`, `canConfirm`, `loading` cover the known cases

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|----------------------------|----------------|
| Open dialog | `open = true` | Dialog renders with `role="dialog"`, focus moves to panel via `requestAnimationFrame`; previously-focused element saved | N/A |
| Escape key | dialog open, focus inside | `open = false`, previously-focused element restored | N/A |
| Backdrop click | dialog open | `open = false` | N/A |
| Tab cycling | dialog open, focus on last focusable | Focus wraps to first focusable | N/A |
| Shift+Tab on first | dialog open, focus on first focusable | Focus wraps to last focusable | N/A |
| Confirm disabled | `canConfirm = false` | Confirm button is `disabled`; click does nothing | N/A |
| Loading state | `loading = true` | Both buttons disabled; confirm shows `loadingLabel` text | N/A |
| Close while loading | `loading = true`, user presses Escape / backdrop | Dialog stays open (matches 12-4 behavior — `closeDeleteDialog` gated on `!deleteLoading`) | N/A |

</frozen-after-approval>

## Code Map

- `healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.svelte` -- NEW: component shell with props, focus trap, backdrop, title bar, body slot, footer buttons
- `healthcabinet/frontend/src/lib/components/ui/confirm-dialog/index.ts` -- NEW: `export { default as ConfirmDialog }`
- `healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.test.ts` -- NEW: unit tests for the component in isolation (open/close, focus trap, Escape, backdrop, canConfirm gate, loading state, ARIA contract)
- `healthcabinet/frontend/src/app.css` -- Rename `.hc-delete-*` dialog classes to `.hc-dialog-*` (backdrop, dialog, title, body, actions). Keep `.hc-delete-section-warning` and `.hc-delete-email-label` since they're page-side, not dialog-side
- `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` -- Replace inline dialog markup (lines 670-750) with `<ConfirmDialog>`; keep confirmEmail/emailMatches/deleteLoading/deleteError state; drop the inline focus-trap + dialogEl binding
- `healthcabinet/frontend/src/routes/(app)/settings/page.test.ts` -- No edits expected; tests query by `[role="dialog"]` which survives extraction

## Tasks & Acceptance

**Execution:**
- [x] `healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.svelte` -- create component mirroring slide-over's focus-trap + restore pattern, with props: `open` (bindable), `title`, `confirmLabel`, `confirmVariant` ('destructive' | 'primary' | 'standard'), `cancelLabel` (default 'Cancel'), `canConfirm` (default `true`), `loading` (default `false`), `loadingLabel` (default 'Working...'), `onConfirm` (required), `children` (body snippet) -- rationale: contract is explicit, reusable for admin flows
- [x] `healthcabinet/frontend/src/lib/components/ui/confirm-dialog/index.ts` -- re-export component -- rationale: match ui/ folder convention
- [x] `healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.test.ts` -- 8 component-level tests covering I/O matrix scenarios -- rationale: isolated tests don't need the full settings-page mock harness
- [x] `healthcabinet/frontend/src/app.css` -- rename `.hc-delete-dialog-backdrop/dialog/title/body/actions` → `.hc-dialog-backdrop/panel/title/body/actions` -- rationale: class name was a 12-4-era mistake; fix now before admin flows reuse it
- [x] `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` -- replace `{#if deleteDialogOpen}...{/if}` block (lines 670-750) with `<ConfirmDialog bind:open={deleteDialogOpen} title="Account Deletion" confirmLabel="Delete My Account" confirmVariant="destructive" loadingLabel="Deleting..." canConfirm={emailMatches} loading={deleteLoading} onConfirm={handleDeleteAccount}>...body children...</ConfirmDialog>`; remove `deleteDialogEl`, the inline focus-trap, the `requestAnimationFrame` block from `openDeleteDialog` -- rationale: 80 lines of dialog chrome collapse to ~20 lines of props + body content

**Acceptance Criteria:**
- Given the settings page renders, when the user clicks "Delete My Account", then a dialog with `role="dialog"`, `aria-modal="true"`, `aria-label="Account deletion confirmation"` opens and receives focus
- Given the dialog is open, when the user presses Escape, then the dialog closes and focus returns to the "Delete My Account" button
- Given the dialog is open and `loading = true`, when the user presses Escape, then the dialog stays open
- Given the dialog is open, when the user presses Tab on the last focusable element, then focus wraps to the first focusable element
- Given the dialog is open and email does not match, then the confirm button has `disabled` attribute; when the email matches, then it becomes enabled
- Given the existing 6 dialog tests in `settings/page.test.ts`, when run after refactor, then all pass without test file edits

## Design Notes

The dialog is pure chrome. All product-specific content (warning paragraph with `id="delete-warning"`, error banner, email input with `aria-describedby`) stays in the parent as body children — the dialog doesn't know or care what's inside. This mirrors the slide-over pattern and keeps 12-4's ARIA relationships intact.

The `confirmVariant` prop maps to CSS class: `destructive` → `.btn-destructive`, `primary` → `.btn-primary`, `standard` → `.btn-standard`. No inline styles, no custom variants.

One focus-trap behavior upgrade: restore focus to the element that opened the dialog on close (slide-over's `previouslyFocused` pattern). 12-4 doesn't do this — after Cancel, focus falls back to `<body>`. The new component does it by default. This is a quiet a11y win; tests don't care (they don't assert focus restoration), so it's safe.

## Verification

**Commands (run inside Docker Compose per CLAUDE.md):**
- `docker compose exec frontend npm run test:unit` -- expected: 520+ tests pass, 0 failures, 0 regressions (new ConfirmDialog unit tests add ~8)
- `docker compose exec frontend npm run check` -- expected: 0 type errors
- `docker compose exec frontend npm run lint` -- expected: 0 lint errors

**Manual checks:**
- Settings page loads, Delete dialog opens/closes/Cancel/type-to-confirm behavior identical to before refactor
- Dialog visual: same raised panel, same title bar color, same backdrop opacity

## Suggested Review Order

**Component design**

- Props interface — JSDoc documents each prop's contract, including the caller-owns-lifecycle rule on `onConfirm`
  [`confirm-dialog.svelte:6`](../../healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.svelte#L6)

- Focus trap + Escape handling — Tab wraps via modular arithmetic; Escape gated on `loading`
  [`confirm-dialog.svelte:70`](../../healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.svelte#L70)

- Open/close lifecycle — captures previously-focused element on open, restores on close via `$effect`
  [`confirm-dialog.svelte:108`](../../healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.svelte#L108)

- Markup: backdrop with `stopPropagation` on panel keeps inner clicks from closing
  [`confirm-dialog.svelte:132`](../../healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.svelte#L132)

- Module entry point
  [`index.ts:1`](../../healthcabinet/frontend/src/lib/components/ui/confirm-dialog/index.ts#L1)

**Settings page integration**

- Import + usage — ~80 lines of inline chrome collapsed to ~35 lines of props + body children
  [`+page.svelte:659`](../../healthcabinet/frontend/src/routes/(app)/settings/+page.svelte#L659)

- Import statement (the one edge that required adjusting the import-guard test)
  [`+page.svelte:14`](../../healthcabinet/frontend/src/routes/(app)/settings/+page.svelte#L14)

**CSS chrome generalization**

- Class rename `.hc-delete-dialog-*` → `.hc-dialog-*` with updated header comment
  [`app.css:3975`](../../healthcabinet/frontend/src/app.css#L3975)

**Tests**

- Unit tests for the component in isolation (18 tests covering I/O matrix)
  [`confirm-dialog.test.ts:1`](../../healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.test.ts#L1)

- Narrowed import-guard test — regex now requires path terminator (`/` or `'`) to prevent `button-group` false positives
  [`page.test.ts:218`](../../healthcabinet/frontend/src/routes/(app)/settings/page.test.ts#L218)
