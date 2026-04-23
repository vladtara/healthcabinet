# Story 9.2: Remove Mobile/Tablet Responsive Code

Status: done

## Story

As a developer maintaining the HealthCabinet frontend,
I want all mobile and tablet responsive code removed from the codebase,
so that the desktop-only MVP (1024px+) has a clean, simplified codebase without dead responsive paths that conflict with the 98.css clinical workstation aesthetic.

## Acceptance Criteria

1. **No Tailwind responsive prefixes** — Zero instances of `sm:`, `md:`, `lg:`, `xl:`, `2xl:`, `max-sm:`, `max-md:`, `max-lg:` in any `.svelte` file. Each responsive class is replaced with its desktop-equivalent value (e.g., `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` becomes `grid-cols-3`).

2. **No mobile detection logic** — The `isMobile` state, `matchMedia('(pointer: coarse)')` listener, and camera-input conditional in `DocumentUploadZone.svelte` are fully removed. Only the desktop file-picker path remains.

3. **No layout-constraining max-width on overlays** — The `.hc-slide-over` `max-width: 480px`, `.hc-auth-login` `max-width: 420px`, and `.hc-auth-register` `max-width: 460px` constraints in `app.css` are removed or replaced with desktop-appropriate values.

4. **Accessibility media queries preserved** — `@media (prefers-reduced-motion: reduce)` rules in `app.css` are NOT removed (they are accessibility features, not responsive layout).

5. **No visual regressions on desktop** — All existing pages render identically at 1024px, 1280px, and 1536px viewports. Grid layouts display at their maximum column count. No elements are hidden that should be visible.

6. **All existing tests pass** — Zero test regressions. Update any tests that reference removed responsive classes or mobile logic.

7. **Camera input element removed** — The hidden `<input type="file" capture="environment">` element in `DocumentUploadZone.svelte` is removed along with its `cameraInput` state variable.

## Tasks / Subtasks

- [x] Task 1: Remove mobile detection logic from DocumentUploadZone.svelte (AC: #2, #7)
  - [x] 1.1 Remove `isMobile` state variable, `cameraInput` state variable, and the `$effect` with `matchMedia` listener
  - [x] 1.2 Simplify `handleUploadClick()` to always use `fileInput?.click()` (remove camera conditional)
  - [x] 1.3 Remove conditional class logic using `isMobile` ternary (line ~127), keep desktop class `min-h-[200px]`
  - [x] 1.4 Remove the hidden camera `<input type="file" capture="environment">` element from template
  - [x] 1.5 Update or add tests to verify upload zone renders without mobile logic

- [x] Task 2: Remove Tailwind responsive prefixes from (app) route pages (AC: #1, #5)
  - [x] 2.1 `dashboard/+page.svelte`: Replace `grid-cols-2 sm:grid-cols-4` → `grid-cols-4`; replace `hidden md:block` → remove `hidden` class (element always visible)
  - [x] 2.2 `documents/+page.svelte`: Replace `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` → `grid-cols-3`; replace `sm:rounded-l-xl` → `rounded-l-xl`
  - [x] 2.3 `documents/upload/+page.svelte`: Remove `max-md:max-w-none max-md:p-0`; remove `max-md:hidden` (element always visible)
  - [x] 2.4 `onboarding/+page.svelte`: Replace `sm:px-6 sm:py-12` → `px-6 py-12`; replace `sm:px-8 sm:py-8` → `px-8 py-8`; replace `grid-cols-1 sm:grid-cols-2` → `grid-cols-2` (two instances)

- [x] Task 3: Remove Tailwind responsive prefixes from (admin) route pages (AC: #1, #5)
  - [x] 3.1 `admin/+page.svelte`: Replace `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` → `grid-cols-3` (two instances)
  - [x] 3.2 `admin/users/[user_id]/+page.svelte`: Replace `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` → `grid-cols-3`
  - [x] 3.3 `admin/documents/[document_id]/+page.svelte`: Replace `grid-cols-2 sm:grid-cols-4` → `grid-cols-4`

- [x] Task 4: Remove responsive prefixes from health components (AC: #1, #5)
  - [x] 4.1 `AiFollowUpChat.svelte`: Replace `w-full sm:w-auto` → `w-auto`
  - [x] 4.2 `PartialExtractionCard.svelte`: Replace `flex-col sm:flex-row sm:items-center` → `flex-row items-center`

- [x] Task 5: Clean up CSS constraints in app.css (AC: #3, #4)
  - [x] 5.1 Remove `max-width: 480px` from `.hc-slide-over`
  - [x] 5.2 Remove `max-width: 420px` from `.hc-auth-login`
  - [x] 5.3 Remove `max-width: 460px` from `.hc-auth-register`
  - [x] 5.4 Verify `@media (prefers-reduced-motion: reduce)` rules are untouched

- [x] Task 6: Run full test suite and verify no regressions (AC: #5, #6)
  - [x] 6.1 Run `npm run test:unit` — 341 pass, 1 pre-existing failure (users.test.ts)
  - [x] 6.2 Run `npm run check` — 0 errors, 2 pre-existing warnings
  - [x] 6.3 Verify no remaining responsive prefixes — grep confirms zero matches across all .svelte files

### Review Findings

- [x] [Review][Decision] Auth forms/slide-over lost max-width — Resolved: keep removed per spec AC#3. Parent containers already constrain width via Epic 8 redesign.
- [x] [Review][Patch] Empty `.hc-auth-login` and `.hc-auth-register` CSS rulesets removed [app.css]
- [x] [Review][Patch] Stale "responsive" comment updated in documents grid [documents/+page.svelte:252]

## Dev Notes

### Architecture & Design Decisions

- **Desktop-only MVP (1024px+):** The UX spec explicitly states "No `@media` queries for MVP." The 98.css aesthetic is inherently desktop-native. Mobile/tablet support is deferred to post-MVP with a completely different paradigm (bottom toolbar, stacked layout, no 3D bevels).
- **Responsive prefixes are dead code:** Since desktop is the only target, `sm:` and `md:` prefixes activate at breakpoints below the 1024px minimum. They are unreachable code. `lg:` prefixes (1024px+) should be promoted to base classes.
- **Max-width constraints:** The auth dialog max-widths (420px, 460px) were from the pre-98.css era. The redesigned login/register pages (Epic 8) already use `.hc-auth-*` CSS classes without these constraints. The slide-over 480px max-width may also be unnecessary.

### Replacement Strategy

For each responsive class pattern, apply this rule:
- `sm:X` or `md:X` → promote `X` to base class (it's the desktop value)
- `lg:X` → promote `X` to base class (1024px IS the base)
- `max-md:X` → remove entirely (mobile-only override)
- `hidden md:block` → remove `hidden` (always visible on desktop)
- `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` → `grid-cols-3` (use widest layout)

### Files Affected (from codebase audit)

**Components:**
- `src/lib/components/health/DocumentUploadZone.svelte` — mobile detection logic + camera input
- `src/lib/components/health/AiFollowUpChat.svelte` — 1 responsive class
- `src/lib/components/health/PartialExtractionCard.svelte` — 1 responsive class

**Route pages:**
- `src/routes/(app)/dashboard/+page.svelte` — 2 responsive classes
- `src/routes/(app)/documents/+page.svelte` — 2 responsive classes
- `src/routes/(app)/documents/upload/+page.svelte` — 2 responsive classes
- `src/routes/(app)/onboarding/+page.svelte` — 4 responsive classes
- `src/routes/(admin)/admin/+page.svelte` — 2 responsive classes
- `src/routes/(admin)/admin/users/[user_id]/+page.svelte` — 1 responsive class
- `src/routes/(admin)/admin/documents/[document_id]/+page.svelte` — 1 responsive class

**CSS:**
- `src/app.css` — 3 max-width constraints to remove

### What NOT to Touch

- `@media (prefers-reduced-motion: reduce)` in app.css — accessibility, not responsive
- Any `min-width` or `max-width` that's a layout constraint for desktop panels (e.g., sidebar 200px)
- The AppShell component (already desktop-only from story 9-1)
- Landing page, login page, register page (already clean from Epic 8 redesign)

### Previous Story Intelligence (9-1)

- **CSS pattern:** All styles in `app.css` with `.hc-[section]-[element]` naming — no scoped `<style>` blocks
- **Testing:** vitest + jsdom + @testing-library/svelte + axe-core; baseline is ~342 tests
- **Build verification:** Always run `npm run check` after changes
- **Known pre-existing:** 1 failing test in `users.test.ts` (backend, unrelated)

### Project Structure Notes

- All frontend source: `healthcabinet/frontend/src/`
- Route groups: `(app)/` (authenticated), `(auth)/` (public), `(admin)/` (admin role guard)
- Components: `lib/components/ui/` (98.css primitives), `lib/components/health/` (domain)
- Tests run in Docker: `docker compose exec frontend npm run test:unit`

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Responsive-Strategy] — "No @media queries for MVP"
- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md#Desktop-Only-MVP] — "Desktop-only MVP (1024px+)"
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md#FE-Epic-3] — Story candidate: "Remove existing mobile bottom tab bar and tablet icon-rail responsive code"
- [Source: _bmad-output/implementation-artifacts/9-1-appshell-98css-window-chrome.md] — Previous story patterns and learnings

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Dashboard test `sparklines are hidden on narrow viewport` failed after removing `hidden md:block` — updated test to verify sparklines are always visible (desktop-only MVP)
- Upload zone test `mobile camera input has capture attribute` updated to verify camera input no longer exists

### Completion Notes List

- Removed all mobile detection logic from DocumentUploadZone.svelte: `isMobile` state, `matchMedia` listener, camera input conditional, camera `<input>` element
- Replaced 13+ Tailwind responsive prefixes (`sm:`, `md:`, `lg:`, `max-md:`) across 10 .svelte files with desktop-equivalent base classes
- Removed 3 max-width constraints from app.css (`.hc-slide-over`, `.hc-auth-login`, `.hc-auth-register`)
- Preserved both `@media (prefers-reduced-motion: reduce)` accessibility rules
- Updated 2 test files to reflect removal of responsive/mobile code
- Final grep confirms zero responsive prefixes remain in any .svelte file
- 341/342 tests pass (1 pre-existing failure in users.test.ts, unrelated)
- svelte-check: 0 errors, 2 pre-existing warnings

### File List

- healthcabinet/frontend/src/lib/components/health/DocumentUploadZone.svelte (modified)
- healthcabinet/frontend/src/lib/components/health/AiFollowUpChat.svelte (modified)
- healthcabinet/frontend/src/lib/components/health/PartialExtractionCard.svelte (modified)
- healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte (modified)
- healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts (modified)
- healthcabinet/frontend/src/routes/(app)/documents/+page.svelte (modified)
- healthcabinet/frontend/src/routes/(app)/documents/upload/+page.svelte (modified)
- healthcabinet/frontend/src/routes/(app)/documents/upload/page.test.ts (modified)
- healthcabinet/frontend/src/routes/(app)/onboarding/+page.svelte (modified)
- healthcabinet/frontend/src/routes/(admin)/admin/+page.svelte (modified)
- healthcabinet/frontend/src/routes/(admin)/admin/users/[user_id]/+page.svelte (modified)
- healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte (modified)
- healthcabinet/frontend/src/app.css (modified)

### Change Log

- Removed all mobile/tablet responsive code for desktop-only MVP (Date: 2026-04-04)
