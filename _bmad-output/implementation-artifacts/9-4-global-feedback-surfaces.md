# Story 9.4: Global Feedback Surfaces

Status: done

## Story

As an authenticated user,
I want route-level toasts, banners, and inline feedback regions using 98.css patterns,
so that I receive clear, non-blocking feedback about actions and system state throughout the application.

## Acceptance Criteria

1. **Toast notification system** — A global toast store (`feedback.svelte.ts`) manages toast state using Svelte 5 runes. Supports `success`, `error`, and `warning` variants. Toasts auto-dismiss after 3 seconds. Each toast has a unique ID for removal.

2. **Toast component** — A `Toast.svelte` component renders individual toasts with 98.css styling: sunken panel border, left color accent (green/red/yellow matching status colors), icon, message text, optional dismiss button. Uses `role="status"` for success/warning, `role="alert"` for errors.

3. **Toast container in AppShell** — A `ToastContainer.svelte` renders active toasts from the store. Positioned as a fixed overlay in the bottom-right corner above the status bar. Toasts stack vertically with newest on top. Both AppShell and AdminShell include the container.

4. **Banner component** — A `FeedbackBanner.svelte` renders persistent page-level messages using 98.css panel patterns. Variants: `info`, `success`, `error`, `warning`. Includes optional dismiss button. Uses `role="alert"` for errors, `role="status"` for others. Rendered inline within page content (not global overlay).

5. **Toast helper functions** — The feedback store exports convenience functions: `showSuccess(message)`, `showError(message)`, `showWarning(message)`, `dismissToast(id)`, `clearAll()`. Functions are importable from `$lib/stores/feedback.svelte`.

6. **CSS follows established patterns** — All feedback styles in `app.css` using `.hc-toast-*` and `.hc-banner-*` naming conventions. Uses existing CSS custom properties for status colors (`--color-status-optimal`, `--color-status-action`, `--color-status-borderline`). 98.css sunken border pattern for toast panels.

7. **Tests** — Unit tests for: feedback store (add/remove/auto-dismiss), Toast component rendering per variant, ToastContainer rendering multiple toasts, FeedbackBanner rendering per variant, accessibility (axe audit on all variants).

## Tasks / Subtasks

- [x] Task 1: Create feedback store (AC: #1, #5)
  - [x] 1.1 Create `src/lib/stores/feedback.svelte.ts` with Svelte 5 runes (`$state`)
  - [x] 1.2 Implement toast state as reactive array of `{ id, type, message }` objects with timer Map
  - [x] 1.3 Implement `showSuccess(message)`, `showError(message)`, `showWarning(message)` — success/warning auto-dismiss 3s, errors persist until manually dismissed
  - [x] 1.4 Implement `dismissToast(id)` and `clearAll()`
  - [x] 1.5 Write 7 tests for store: add each type, dismiss, clearAll, auto-dismiss, error persistence

- [x] Task 2: Create Toast component (AC: #2)
  - [x] 2.1 Create `src/lib/components/ui/toast/Toast.svelte` with props: `type`, `message`, `onDismiss`
  - [x] 2.2 Render 98.css sunken panel with left color accent per type
  - [x] 2.3 Add icon (✓/✕/⚠), message text, optional dismiss "×" button
  - [x] 2.4 Set `role="alert"` for error, `role="status"` for success/warning
  - [x] 2.5 Write 8 tests: each variant, dismiss behavior, accessibility (axe)

- [x] Task 3: Create ToastContainer component (AC: #3)
  - [x] 3.1 Create `src/lib/components/ui/toast/ToastContainer.svelte` reading from feedbackStore
  - [x] 3.2 Fixed overlay: bottom-right, z-index 100, bottom 32px, right 12px
  - [x] 3.3 Stack vertically with column-reverse + 8px gap (newest on top)
  - [x] 3.4 Container only renders when toasts exist, with `aria-live="polite"`

- [x] Task 4: Create FeedbackBanner component (AC: #4)
  - [x] 4.1 Create `src/lib/components/ui/banner/FeedbackBanner.svelte` with 4 variants
  - [x] 4.2 Render 98.css panel with left accent + icon per type
  - [x] 4.3 Optional dismiss button with internal dismissed state + onDismiss callback
  - [x] 4.4 Write 10 tests: each variant, dismiss behavior, callbacks, accessibility (axe)

- [x] Task 5: Integrate ToastContainer into shells (AC: #3)
  - [x] 5.1 Added ToastContainer to AppShell.svelte (after StatusBar, before closing div)
  - [x] 5.2 Added ToastContainer to AdminShell.svelte (same position)

- [x] Task 6: Add CSS classes to app.css (AC: #6)
  - [x] 6.1 Added `.hc-toast-container` fixed positioning (bottom-right, z-100, pointer-events: none)
  - [x] 6.2 Added `.hc-toast` base styles: sunken border, shadow, 280-420px width
  - [x] 6.3 Added `.hc-toast-success`, `.hc-toast-error`, `.hc-toast-warning` left-border variants
  - [x] 6.4 Added `.hc-toast-icon`, `.hc-toast-message`, `.hc-toast-dismiss` element styles
  - [x] 6.5 Added `.hc-banner` + 4 variants (info/success/error/warning) with same accent pattern
  - [x] 6.6 Added `@keyframes hc-toast-slide-in` + `prefers-reduced-motion` respect

- [x] Task 7: Run full test suite and verify (AC: #7)
  - [x] 7.1 Run `npm run test:unit` — 372 pass, 1 pre-existing failure (users.test.ts)
  - [x] 7.2 Run `npm run check` — 0 errors, 2 pre-existing warnings

### Review Findings

- [x] [Review][Patch] Fixed `aria-live="polite"` on always-rendered container with `role="region"` for screen reader compatibility [ToastContainer.svelte]
- [x] [Review][Patch] Fixed typo `autoDissmissMs` → `autoDismissMs` in feedback store [feedback.svelte.ts]
- [x] [Review][Patch] Added dedicated ToastContainer test file with 5 tests including axe audit [toast-container.test.ts]

## Dev Notes

### Architecture Decisions

- **Svelte 5 runes store** — Use `$state` for reactive toast array. No Svelte 4 writable stores. Pattern matches `auth.svelte.ts`.
- **Fixed overlay positioning** — Toasts render as fixed-position overlay in bottom-right corner rather than inline in the layout. This avoids modifying the flex layout of AppShell/AdminShell body area. `z-index: 100` to sit above all content.
- **Separate Toast vs Banner** — Toasts are transient (auto-dismiss, overlay). Banners are persistent (inline, page-level). Different components for different purposes.
- **No toast limit** — Keep it simple. If multiple toasts stack, they stack. Future enhancement could limit visible count.

### Design Patterns (from UX spec)

- **"Recognition over alarm"** — Toasts are informative, not panic-inducing. Use factual messages, no apologetic copy.
- **"Straightforward errors"** — Classic Windows dialog pattern: icon + specific message. No "Oops!" or "We're sorry!"
- **Success toast** — Green left accent, 3s auto-hide (UX page spec line 773, 783)
- **Error alert** — Red left accent, `role="alert"`, stays until dismissed (UX page spec line 784)
- **Non-blocking** — Architecture requires UI stays responsive during background processing.

### Color Tokens

Use existing CSS custom properties:
- Success: `var(--color-status-optimal)` (#2E8B57 green)
- Error: `var(--color-status-action)` (#CC3333 red)
- Warning: `var(--color-status-borderline)` (#DAA520 yellow)
- Info: `var(--accent)` (#3366FF blue)

### 98.css Panel Styling

Toasts use sunken panel border pattern (same as `.hc-app-content`):
```css
border: 2px solid;
border-color: #A0B0C0 #D0D8E4 #D0D8E4 #A0B0C0;
```
Plus a 3px left border in the variant color for emphasis.

### Component Structure

```
src/lib/
├── stores/
│   └── feedback.svelte.ts          # Toast state + helper functions
├── components/ui/
│   ├── toast/
│   │   ├── index.ts                # Re-exports
│   │   ├── Toast.svelte            # Individual toast
│   │   └── ToastContainer.svelte   # Renders all active toasts
│   └── banner/
│       ├── index.ts                # Re-exports
│       └── FeedbackBanner.svelte   # Inline page-level banner
```

### Existing Components to Reuse

- `StatusBar`, `StatusBarField` — already in AppShell/AdminShell
- State components (`ErrorState`, `SuccessState`, `WarningState`) — similar patterns, but those are full-page states. Toasts/banners are smaller, transient.
- `Panel` — could wrap banner content, but likely simpler to style directly.

### Previous Story Intelligence (9-1, 9-2, 9-3)

- **CSS pattern:** All styles in `app.css` with `.hc-[section]-[element]` naming. No scoped styles.
- **Testing:** vitest + jsdom + @testing-library/svelte + axe-core. Baseline: 347 tests.
- **Pre-existing failure:** 1 test in `users.test.ts` (backend, unrelated).
- **Desktop-only:** No responsive prefixes (story 9-2).
- **Svelte 5 runes:** `$state`, `$derived`, `$effect` patterns used throughout.

### What NOT to Touch

- Existing state components (ErrorState, SuccessState, etc.) — they serve a different purpose (full-section states)
- Page-level inline error patterns (they work fine for form validation)
- Status bar content (already handled by AppShell/AdminShell)
- Any backend code

### References

- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md, lines 773, 783-784] — Toast specs: success green 3s, error red alert, save feedback
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md, line 157] — "Recognition over alarm" design principle
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md, lines 224-228] — Status bar, error dialog, tooltip feedback patterns
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md, line 149] — Story candidate: "Global feedback surfaces: route-level toasts, banners, and inline status regions"
- [Source: _bmad-output/planning-artifacts/architecture.md, line 57] — Real-time status feedback, non-blocking UI requirement

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

No issues encountered.

### Completion Notes List

- Created feedback store with Svelte 5 runes: FeedbackStore class with $state reactive toasts array
- Error toasts persist (autoDissmissMs=0), success/warning auto-dismiss at 3s
- Toast component: 3 variants with type-specific icons (✓/✕/⚠), accessible roles, optional dismiss
- ToastContainer: fixed overlay bottom-right, column-reverse stacking, pointer-events passthrough on container
- FeedbackBanner: 4 variants (info/success/error/warning), internal dismiss state, inline page-level use
- Both AppShell and AdminShell now include ToastContainer
- CSS: 20+ new classes (.hc-toast-*, .hc-banner-*), slide-in animation, prefers-reduced-motion respected
- 25 new tests across 3 test files, all passing with axe accessibility audits
- 372/373 total tests pass

### File List

- healthcabinet/frontend/src/lib/stores/feedback.svelte.ts (new)
- healthcabinet/frontend/src/lib/stores/feedback.test.ts (new)
- healthcabinet/frontend/src/lib/components/ui/toast/Toast.svelte (new)
- healthcabinet/frontend/src/lib/components/ui/toast/ToastContainer.svelte (new)
- healthcabinet/frontend/src/lib/components/ui/toast/index.ts (new)
- healthcabinet/frontend/src/lib/components/ui/toast/toast.test.ts (new)
- healthcabinet/frontend/src/lib/components/ui/banner/FeedbackBanner.svelte (new)
- healthcabinet/frontend/src/lib/components/ui/banner/index.ts (new)
- healthcabinet/frontend/src/lib/components/ui/banner/banner.test.ts (new)
- healthcabinet/frontend/src/lib/components/AppShell.svelte (modified)
- healthcabinet/frontend/src/lib/components/AdminShell.svelte (modified)
- healthcabinet/frontend/src/app.css (modified)

### Change Log

- Implemented global feedback surfaces: toast store, Toast/ToastContainer/FeedbackBanner components (Date: 2026-04-04)
