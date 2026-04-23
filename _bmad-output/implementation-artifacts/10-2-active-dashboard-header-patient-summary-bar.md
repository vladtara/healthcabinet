# Story 10.2: Active Dashboard Header & PatientSummaryBar

Status: done

## Story

As a user with uploaded health documents,
I want a PatientSummaryBar showing my key metadata and a stat card grid showing biomarker status counts,
so that I get an instant overview of my health status before diving into detailed results.

## Acceptance Criteria

1. **PatientSummaryBar component** — A new `PatientSummaryBar.svelte` in `src/lib/components/health/` renders a compact header bar with: user display name or email, document count, last upload date (formatted), and "Upload Document" button (right-aligned, links to `/documents/upload`). Uses 98.css raised panel styling.

2. **StatCardGrid component** — A new `StatCardGrid.svelte` in `src/lib/components/health/` renders 4 stat cards in a grid: Optimal (green), Borderline (yellow), Concerning (orange), Action Needed (red). Each card shows count + label. Uses 98.css raised panel with health status color accent. Grid is always 4 columns (desktop-only).

3. **Component isolation** — Both components are standalone with their own props interface. They do NOT import from or modify `+page.svelte`. They receive data via props, not by reading stores or queries directly. This enables parallel development and later integration.

4. **PatientSummaryBar props** — `email: string`, `documentCount: number`, `lastUploadDate: string | null`. Displays "No uploads yet" when `lastUploadDate` is null. Date formatted as relative ("Mar 15" or "2 days ago").

5. **StatCardGrid props** — `counts: { optimal: number, borderline: number, concerning: number, action_needed: number }`. Each card uses the health status color system (`--color-status-optimal`, `--color-status-action`, etc.).

6. **CSS follows established patterns** — All styles in `app.css` using `.hc-summary-*` and `.hc-stat-*` naming. 98.css raised panel borders. No scoped styles.

7. **Tests** — Unit tests for PatientSummaryBar: renders email, document count, last upload date, "No uploads yet" state, upload button link, axe audit. Unit tests for StatCardGrid: renders all 4 cards with correct counts, correct status colors, zero-count display, axe audit.

8. **WCAG Considerations** — Stat cards have accessible text (not color-only). PatientSummaryBar upload button has clear focus state. Both components pass axe audits.

## Tasks / Subtasks

- [x] Task 1: Add CSS classes to app.css (AC: #6)
  - [x] 1.1 Add `.hc-summary-bar` raised panel strip (same pattern as `.hc-app-header`)
  - [x] 1.2 Add `.hc-summary-bar-info` for left-side metadata (email, counts, date)
  - [x] 1.3 Add `.hc-summary-bar-actions` for right-side button area
  - [x] 1.4 Add `.hc-stat-grid` 4-column grid container
  - [x] 1.5 Add `.hc-stat-card` raised panel with accent top border
  - [x] 1.6 Add `.hc-stat-card-optimal`, `.hc-stat-card-borderline`, `.hc-stat-card-concerning`, `.hc-stat-card-action` accent color variants
  - [x] 1.7 Add `.hc-stat-card-count` and `.hc-stat-card-label` typography styles

- [x] Task 2: Create PatientSummaryBar component (AC: #1, #3, #4)
  - [x] 2.1 Create `src/lib/components/health/PatientSummaryBar.svelte` with typed props interface
  - [x] 2.2 Render raised panel with email, document count badge, last upload date
  - [x] 2.3 Handle null `lastUploadDate` with "No uploads yet" text
  - [x] 2.4 Add "Upload Document" button right-aligned, linking to `/documents/upload`
  - [x] 2.5 Format date display (short month + day, e.g., "Mar 15")

- [x] Task 3: Create StatCardGrid component (AC: #2, #3, #5)
  - [x] 3.1 Create `src/lib/components/health/StatCardGrid.svelte` with typed `counts` prop
  - [x] 3.2 Render 4-column grid of 98.css raised cards
  - [x] 3.3 Each card: large count number (colored by status) + label text below
  - [x] 3.4 Use CSS custom properties for status colors
  - [x] 3.5 Display "0" gracefully for zero counts (not hidden)

- [x] Task 4: Write PatientSummaryBar tests (AC: #7, #8)
  - [x] 4.1 Test: renders user email
  - [x] 4.2 Test: renders document count
  - [x] 4.3 Test: renders formatted last upload date
  - [x] 4.4 Test: renders "No uploads yet" when lastUploadDate is null
  - [x] 4.5 Test: upload button links to /documents/upload
  - [x] 4.6 Test: axe accessibility audit passes

- [x] Task 5: Write StatCardGrid tests (AC: #7, #8)
  - [x] 5.1 Test: renders all 4 stat cards with labels
  - [x] 5.2 Test: displays correct counts
  - [x] 5.3 Test: handles zero counts gracefully
  - [x] 5.4 Test: axe accessibility audit passes

- [x] Task 6: Run full test suite (AC: #7)
  - [x] 6.1 Run `npm run test:unit` — all tests pass
  - [x] 6.2 Run `npm run check` — zero svelte-check errors

### Review Findings

- [x] [Review][Patch] `formatLastUploadDate` has no "today" handler — `diffDays === 0` falls through to absolute date format ("Apr 4") instead of "Today" [PatientSummaryBar.svelte:28]
- [x] [Review][Patch] `.hc-summary-bar-actions .hc-button` min-height 24px may clip button text with 2px border + 4px padding at 13px font — increase to 28px [app.css:~1630]
- [x] [Review][Defer] Email text has no overflow/truncation — long emails could push Upload button off-screen. Pre-existing pattern, no other component truncates email
- [x] [Review][Defer] `HealthValue.status` includes `unknown` but neither dashboard counts nor StatCardGrid account for it — pre-existing gap from story 3.2

## Dev Notes

### Architecture Decisions

- **Standalone components, not page modifications** — This story creates PatientSummaryBar and StatCardGrid as isolated, reusable components. They are NOT integrated into `+page.svelte` yet. Integration into the active dashboard state happens in story 10-3 (BiomarkerTable redesign) which brings all pieces together.
- **Props-driven, not store-dependent** — Components receive data via props. The dashboard page will later pass query results as props. This keeps components testable and reusable (admin dashboard could use StatCardGrid too).
- **CSS namespacing** — `.hc-summary-*` for PatientSummaryBar, `.hc-stat-*` for StatCardGrid. Separate from `.hc-dash-*` (story 10-1's page layout classes).

### Parallel Development Note

This story can be developed **in parallel with story 10-1** (empty-state dashboard). They are fully independent:
- 10-1 modifies `+page.svelte` (empty state layout, page header, CSS)
- 10-2 creates new files only (PatientSummaryBar.svelte, StatCardGrid.svelte, tests, CSS classes)
- No file conflicts possible

### Component Specifications

**PatientSummaryBar layout:**
```
┌──────────────────────────────────────────────────────┐
│ user@email.com  ·  3 documents  ·  Last: Mar 15    [Upload Document] │
└──────────────────────────────────────────────────────┘
```
Height: ~36px, raised background, 13-14px text, secondary color for metadata.

**StatCardGrid layout:**
```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│    18    │ │     3    │ │     1    │ │     0    │
│ Optimal  │ │Borderline│ │Concerning│ │  Action  │
│  (green) │ │ (yellow) │ │ (orange) │ │  (red)   │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```
4-column grid, `grid-cols-4 gap-3`. Each card: 98.css raised panel, 3px top border in status color, centered count (24px bold) + label (12px muted).

### Color Tokens

- Optimal: `var(--color-status-optimal)` (#2E8B57)
- Borderline: `var(--color-status-borderline)` (#DAA520)
- Concerning: `var(--color-status-concerning)` (#E07020)
- Action: `var(--color-status-action)` (#CC3333)

### 98.css Raised Panel Pattern

```css
background: var(--surface-raised);
border: 2px solid;
border-color: #D0D8E4 #A0B0C0 #A0B0C0 #D0D8E4;
box-shadow: inset 0 1px 0 #fff;
```

### Existing Components to Reference

- `HealthValueBadge.svelte` — status color mapping pattern
- `.hc-app-header` in app.css — raised panel header pattern to follow for PatientSummaryBar
- `Button` from `$lib/components/ui/button` — for Upload button

### Previous Story Intelligence

- **From Epic 9:** CSS in `app.css` only, `.hc-[section]-[element]` naming, no scoped styles
- **Testing baseline:** 377 tests, vitest + jsdom + @testing-library/svelte + axe-core
- **Desktop-only:** No responsive prefixes, always `grid-cols-4` (story 9-2)
- **Svelte 5 runes:** `$state`, `$derived`, `$props` patterns

### What NOT to Touch

- `+page.svelte` dashboard page (integration happens in story 10-3)
- Existing health components (HealthValueBadge, BiomarkerTrendChart, etc.)
- AppShell/AdminShell
- Any data fetching or API code

### References

- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md, lines 495-520] — Active state wireframe with summary bar and stat cards
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] — "Density over whitespace", health status color system
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md, line 174] — Story candidate: "Active dashboard header and PatientSummaryBar"
- [Source: _bmad-output/planning-artifacts/prd.md, FR14] — Health values with context indicators

## Dev Agent Record

### Agent Model Used

- GPT-5.3-Codex (model ID: gpt-5.3-codex)

### Debug Log References

- `docker compose exec frontend npm run test:unit` (full suite): 390/391 passed; one pre-existing failure in `src/lib/api/users.test.ts` (`object.stream is not a function`)
- `docker compose exec frontend npm run check`: 0 errors, 2 pre-existing warnings in admin user page
- `docker compose exec frontend npm run lint`: pre-existing/prettier environment errors unrelated to this story

### Completion Notes List

- Added `.hc-summary-*` and `.hc-stat-*` CSS blocks in `app.css` for the active dashboard summary bar and 4-column stat grid.
- Implemented `PatientSummaryBar.svelte` as a standalone prop-driven component (`email`, `documentCount`, `lastUploadDate`) with:
  - raised 98.css header strip styling,
  - null-state handling (`No uploads yet`),
  - date display formatting (`2 days ago` for recent dates, month/day fallback),
  - right-aligned `Upload Document` button linking to `/documents/upload`.
- Implemented `StatCardGrid.svelte` as a standalone prop-driven component (`counts`) with four fixed cards:
  - Optimal, Borderline, Concerning, Action Needed,
  - status-accented top border and count color using health status tokens.
- Added unit and accessibility test coverage:
  - `PatientSummaryBar.test.ts` (6 tests),
  - `StatCardGrid.test.ts` (4 tests),
  - total new tests: 10/10 passing.

### File List

- `healthcabinet/frontend/src/app.css` (modified — added `.hc-summary-*` and `.hc-stat-*` dashboard classes)
- `healthcabinet/frontend/src/lib/components/health/PatientSummaryBar.svelte` (new)
- `healthcabinet/frontend/src/lib/components/health/StatCardGrid.svelte` (new)
- `healthcabinet/frontend/src/lib/components/health/PatientSummaryBar.test.ts` (new)
- `healthcabinet/frontend/src/lib/components/health/StatCardGrid.test.ts` (new)
- `_bmad-output/implementation-artifacts/10-2-active-dashboard-header-patient-summary-bar.md` (modified — tasks, status, dev record, file list, change log)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified — story status updated to in-progress, then review, then done)
- `_bmad-output/implementation-artifacts/deferred-work.md` (modified — code review defer entry for out-of-scope dashboard edge case)

### Change Log

- 2026-04-04: Implemented story 10-2 active dashboard summary components (PatientSummaryBar + StatCardGrid), CSS, and unit/axe coverage.
- 2026-04-04: Addressed code review findings — scope split for app.css and defensive input handling in summary/stat components.

### Review Findings

- [x] [Review][Decision] Scope ambiguity: `app.css` diff includes out-of-scope `.hc-dash-*` additions — resolved by user choice: treat as required fix (split/remove `.hc-dash-*` from this story scope).
- [x] [Review][Patch] Split/remove out-of-scope `.hc-dash-*` additions from story 10-2 diff [healthcabinet/frontend/src/app.css]
- [x] [Review][Patch] Avoid contradictory fallback when `lastUploadDate` is invalid (do not render `Last: No uploads yet`) [healthcabinet/frontend/src/lib/components/health/PatientSummaryBar.svelte:43-55]
- [x] [Review][Patch] Sanitize invalid `documentCount` values (negative/non-integer) before rendering [healthcabinet/frontend/src/lib/components/health/PatientSummaryBar.svelte:40-42]
- [x] [Review][Patch] Make `StatCardGrid` resilient to missing/partial `counts` values [healthcabinet/frontend/src/lib/components/health/StatCardGrid.svelte:13-38]
- [x] [Review][Defer] Empty recommendations branch can render blank dashboard guidance state [healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte:204-217] — deferred, pre-existing
