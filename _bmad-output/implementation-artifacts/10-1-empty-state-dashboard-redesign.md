# Story 10.1: Empty-State Dashboard Redesign

Status: done

## Story

As a new user with no uploaded documents,
I want the dashboard to show personalized baseline recommendations in a 98.css clinical layout with a clear upload CTA,
so that I see a professional, populated interface from my first visit and know exactly what to do next.

## Acceptance Criteria

1. **Page header** — Dashboard title "Your Health Dashboard" with subtitle "Welcome, {name}." in a 98.css raised panel header strip. Upload button ("Upload Document") in top-right of header, linking to `/documents/upload`.

2. **AI Baseline section** — When no uploads exist (`has_uploads === false`), render the existing baseline recommendations inside a 98.css sunken panel with header "Recommended Tests". Each recommendation shows test name, rationale, frequency, and category badge. Disclaimer text: "Based on your profile. Not a medical diagnosis." visible below recommendations.

3. **Empty-state upload CTA** — Below baseline section, a 98.css sunken panel with centered content: document icon, "Upload your first lab result" heading, "Your trends and insights will appear here." subtext, and a prominent Upload button. Optional: blurred chart preview behind CTA (CSS `filter: blur(6px)` on a decorative background).

4. **Loading state** — Skeleton loaders in 98.css sunken panels with `aria-live` status announcements. Matches existing skeleton pattern.

5. **Error state** — Error message in 98.css panel with retry button. Preserves existing error handling pattern.

6. **CSS follows established patterns** — All new styles in `app.css` using `.hc-dash-*` naming convention. 98.css sunken/raised border patterns. No scoped styles.

7. **Tests** — Update existing dashboard tests for new layout structure. Axe accessibility audit passes on empty state. Test: header renders with upload button, baseline section renders recommendations, empty CTA renders, loading skeleton renders.

8. **WCAG Considerations** — Upload CTA has clear focus state. Disclaimer has appropriate contrast. All interactive elements keyboard-accessible. Status announcements for loading/error states preserved.

## Tasks / Subtasks

- [x] Task 1: Add dashboard CSS classes to app.css (AC: #6)
  - [x] 1.1 Add `.hc-dash-header` raised panel strip with title + right-aligned button
  - [x] 1.2 Add `.hc-dash-section` sunken panel for content sections (baseline, CTA)
  - [x] 1.3 Add `.hc-dash-section-header` for section titles inside panels (accent color, raised bg)
  - [x] 1.4 Add `.hc-dash-empty-cta` centered CTA block styles
  - [x] 1.5 Add `.hc-dash-disclaimer` muted text with top border separator
  - [x] 1.6 Add `.hc-dash-rec-*` classes for recommendation items, badges, rationale, frequency

- [x] Task 2: Restructure dashboard page layout (AC: #1, #2, #3)
  - [x] 2.1 Replace `<main>` wrapper and header with `.hc-dash-header` raised panel
  - [x] 2.2 Add "Upload Document" button in header top-right (link to `/documents/upload`)
  - [x] 2.3 Wrap baseline recommendations in `.hc-dash-section` sunken panel with "Recommended Tests" header
  - [x] 2.4 Add disclaimer text: "Based on your profile. Not a medical diagnosis."
  - [x] 2.5 Create empty-state CTA panel with icon, heading, subtext, upload button
  - [x] 2.6 Preserved existing recommendation rendering logic

- [x] Task 3: Update loading and error states (AC: #4, #5)
  - [x] 3.1 Updated skeleton loaders to use `.hc-dash-section` sunken panel
  - [x] 3.2 Updated error state to use `.hc-dash-section` panel with retry
  - [x] 3.3 Preserved `aria-live`, `role="status"`, and `role="alert"` announcements

- [x] Task 4: Update tests (AC: #7, #8)
  - [x] 4.1 Updated upload CTA test for new text ("Upload your first lab result")
  - [x] 4.2 Added test: dashboard header renders with Upload Document button
  - [x] 4.3 Added test: baseline recommendations render inside sunken panel with "Recommended Tests" header
  - [x] 4.4 Added test: empty state shows disclaimer text
  - [x] 4.5 Existing axe accessibility audit passes on empty state

- [x] Task 5: Run full test suite (AC: #7)
  - [x] 5.1 Run `npm run test:unit` — 380 pass, 1 pre-existing failure (users.test.ts)
  - [x] 5.2 Run `npm run check` — 0 errors, 2 pre-existing warnings

### Review Findings

- [x] [Review][Patch] Changed `<main>` to `<div>` — nested `<main>` inside AppShell's `<main>` was invalid HTML [+page.svelte]
- [x] [Review][Patch] Changed `<div class="hc-dash-header-title">` to `<h1>` — restored heading semantics (WCAG 1.3.1) [+page.svelte]
- [x] [Review][Patch] Restored `<article>` and `<h2>` on recommendation items — restores navigable semantic structure [+page.svelte]
- [x] [Review][Defer] No empty-recommendations fallback message — pre-existing gap
- [x] [Review][Defer] Active state still uses Tailwind (redesign in story 10-3)
- [x] [Review][Defer] Loading skeleton mixes class systems — cosmetic

## Dev Notes

### Architecture Decisions

- **Restructure, don't rewrite** — The current dashboard has working data fetching, error handling, and test coverage. The redesign adds 98.css panels around existing content, not a ground-up rewrite.
- **Active state untouched** — This story ONLY modifies the empty state and page header. The active state (health values, stat cards, trends) will be redesigned in stories 10-2 through 10-4. Preserve all active-state code as-is.
- **CSS classes scoped to dashboard** — Use `.hc-dash-*` prefix to avoid conflicts with `.hc-app-*` (shell) and `.hc-toast-*` (feedback) namespaces.

### Parallel Development Note

This story can be developed **in parallel with story 10-2** (PatientSummaryBar + stat cards). They don't share components:
- 10-1 modifies the empty-state branch of the dashboard page
- 10-2 creates new standalone components (PatientSummaryBar, StatCardGrid) that will be integrated into the active-state branch in story 10-3

### Current Dashboard Structure (to preserve)

The current `+page.svelte` has this branching:
```
{#if loading} → skeleton
{:else if error} → error + retry
{:else if values.length > 0} → ACTIVE STATE (don't touch)
{:else} → EMPTY STATE (redesign this)
```

### 98.css Panel Pattern

Sunken panel (for content sections):
```css
background: var(--surface-sunken);
border: 2px solid;
border-color: #A0B0C0 #D0D8E4 #D0D8E4 #A0B0C0;
```

Raised panel (for header strip):
```css
background: var(--surface-raised);
border-bottom: 2px solid #A0B0C0;
box-shadow: inset 0 1px 0 #fff;
```

### Existing Components to Reuse

- `Button` from `$lib/components/ui/button` — for Upload CTA
- Existing `getDashboardBaseline()` query and recommendation rendering
- Existing skeleton and error patterns

### Previous Story Intelligence

- **From Epic 9:** CSS in `app.css` only, `.hc-[section]-[element]` naming, no scoped styles
- **Testing baseline:** 377 tests, vitest + jsdom + @testing-library/svelte + axe-core
- **Desktop-only:** No responsive prefixes (story 9-2)

### What NOT to Touch

- Active state rendering (values.length > 0 branch)
- Trend section and BiomarkerTrendSection/BiomarkerTrendChart usage
- Data fetching queries (valuesQuery, baselineQuery)
- Any health components (HealthValueBadge, etc.)

### References

- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md, lines 458-490] — Empty state wireframe
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md, line 157] — "Meaning before raw data" principle
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md, lines 173] — Story candidate: "Empty-state dashboard redesign"
- [Source: _bmad-output/planning-artifacts/prd.md, FR16-FR17] — Baseline recommendations and health view requirements

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

No issues encountered.

### Completion Notes List

- Restructured dashboard page with 98.css panels: raised header strip + sunken content sections
- Added "Upload Document" button in header top-right (always visible in all states)
- Wrapped baseline recommendations in sunken panel with "Recommended Tests" section header (accent color)
- Added recommendation item CSS: name, badge (condition-specific/general), rationale, frequency
- Added disclaimer: "Based on your profile. Not a medical diagnosis." with separator border
- Created empty-state CTA panel with document icon, heading, subtext, upload button
- Updated loading skeleton to render inside sunken panel
- Updated error state to render inside sunken panel with role="alert"
- Preserved all active-state code untouched (values.length > 0 branch)
- Added 15+ `.hc-dash-*` CSS classes following established naming convention
- 3 new tests + updated 1 existing test; 380/381 total pass

### File List

- healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte (modified)
- healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts (modified)
- healthcabinet/frontend/src/app.css (modified)

### Change Log

- Redesigned dashboard empty state with 98.css panel layout (Date: 2026-04-04)
