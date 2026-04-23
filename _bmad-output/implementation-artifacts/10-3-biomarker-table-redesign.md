# Story 10.3: BiomarkerTable Redesign

Status: done

## Story

As a user with uploaded health documents,
I want my biomarker results displayed in a dense, sortable table with inline status indicators, reference ranges, and sparklines,
so that I can scan my complete health picture at a glance like a clinical workstation instead of scrolling through cards.

## Acceptance Criteria

1. **BiomarkerTable component** — A new `BiomarkerTable.svelte` in `src/lib/components/health/` renders a dense sortable `<table>` inside a 98.css sunken data region (`.hc-data-table`). Columns: Biomarker (name), Value (large + colored by status), Status (badge), Reference (range text), Trend (sparkline SVG). The table replaces the current card-based active state in `+page.svelte`.

2. **Sortable columns** — Biomarker name and Value columns are sortable by clicking column headers. Uses existing `.hc-sort-button` and `.hc-sort-indicator` CSS classes. Default sort: by biomarker name ascending. Sort state is local component state (`$state`). Status column is NOT sortable (the UX spec doesn't call for it).

3. **Inline sparklines** — Each row shows a 60x20px sparkline (using existing `BiomarkerTrendChart` with `variant="sparkline"`) when 2+ data points exist for that biomarker. When <2 points, the cell shows "—". Sparkline data comes from the `timelineByBiomarker` derived value already computed in `+page.svelte` — passed as a prop, no new API calls.

4. **Expandable detail rows** — Clicking a table row expands an inline detail section below it showing: plain-language status note, full reference range with unit, confidence level (High/Medium/Low with color), and a flag button (reuse flagging logic from `HealthValueRow.svelte`). Only one row expanded at a time. Expanded row has a subtle highlight. Use `aria-expanded` on the row and `aria-controls` pointing to the detail panel.

5. **Dashboard page integration** — The active state branch of `+page.svelte` is restructured to use:
   - `PatientSummaryBar` (from story 10-2) at top
   - `StatCardGrid` (from story 10-2) below summary bar
   - `BiomarkerTable` (this story) as the main content area inside a `.hc-dash-section` sunken panel with "Biomarker Results" section header
   - Existing trend section (`BiomarkerTrendSection`) preserved below the table
   
   The old card-based value display (`<article>` cards with inline sparklines) is fully removed.

6. **CSS follows established patterns** — New styles in `app.css` using `.hc-bio-*` naming for BiomarkerTable-specific styles. Reuses `.hc-data-table`, `.hc-sort-button`, `.hc-sort-indicator` (already exist from story 7-5). No scoped styles.

7. **Tests** — Unit tests for BiomarkerTable: renders all rows with correct column data, sortable by name (asc/desc), sortable by value, row click expands detail section, expanded detail shows status note and reference range, sparkline renders when 2+ points exist, "—" when <2 points, low confidence warning in detail, flag button in detail row, axe accessibility audit. Dashboard page tests updated for new table-based layout.

8. **WCAG Considerations** — Table has proper `<thead>`/`<tbody>` structure. Rows are keyboard-navigable (`tabindex="0"` on `<tr>` elements). Expandable rows use `aria-expanded` and `aria-controls`. Sort buttons have `aria-sort` attribute. Status is never color-only (badge text + color). Axe audit passes.

## Tasks / Subtasks

- [x] Task 1: Add BiomarkerTable CSS to app.css (AC: #6)
  - [x] 1.1 Add `.hc-bio-value` for large value text (18px bold, colored by status)
  - [x] 1.2 Add `.hc-bio-unit` for unit text (12px, secondary color)
  - [x] 1.3 Add `.hc-bio-ref` for reference range text (11px, muted)
  - [x] 1.4 Add `.hc-bio-detail` for expanded detail row panel (indented, sunken background)
  - [x] 1.5 Add `.hc-bio-detail-note` for status note text
  - [x] 1.6 Add `.hc-bio-detail-confidence` for confidence label
  - [x] 1.7 Add `.hc-bio-sparkline-cell` for sparkline cell alignment (60px width)
  - [x] 1.8 Add `.hc-bio-row-expanded` highlight style for currently-expanded row

- [x] Task 2: Create BiomarkerTable component (AC: #1, #2, #3, #4)
  - [x] 2.1 Create `src/lib/components/health/BiomarkerTable.svelte` with typed props interface
  - [x] 2.2 Props: `values: HealthValue[]`, `timelineByBiomarker: Record<string, HealthValue[]>`, `statusNotes: Record<string, string>`
  - [x] 2.3 Implement sortable column headers using `$state` for `sortKey` ('name' | 'value') and `sortDir` ('asc' | 'desc')
  - [x] 2.4 Derive sorted values using `$derived` — sort by `biomarker_name` or `value` based on state
  - [x] 2.5 Render `<table>` inside `.hc-data-table` wrapper with proper `<thead>` and `<tbody>`
  - [x] 2.6 Each row: biomarker name (13px medium), value + unit (18px bold, status-colored), HealthValueBadge, reference range text, sparkline SVG or "—"
  - [x] 2.7 Row click handler: toggle `expandedId` state. Use `aria-expanded` and `aria-controls` on button in name cell
  - [x] 2.8 Expanded detail row: status note, full reference range, confidence (High/Medium/Low colored), flag button
  - [x] 2.9 Flag button logic: reuse `flagHealthValue` mutation pattern from `HealthValueRow.svelte`
  - [x] 2.10 Sort button `aria-sort` attributes: "ascending", "descending", or "none"

- [x] Task 3: Integrate into dashboard page (AC: #5)
  - [x] 3.1 Import `PatientSummaryBar`, `StatCardGrid`, `BiomarkerTable` in `+page.svelte`
  - [x] 3.2 Replace stat card grid (Tailwind `grid-cols-4` divs) with `<StatCardGrid>` component
  - [x] 3.3 Add `<PatientSummaryBar>` above stat cards — pass `email` from auth store, `documentCount` and `lastUploadDate` from values data
  - [x] 3.4 Replace card-based value display section with `<BiomarkerTable>` inside `.hc-dash-section` sunken panel
  - [x] 3.5 Add `.hc-dash-section-header` with "Biomarker Results" title above table
  - [x] 3.6 Remove old `<article>` card markup and inline sparkline rendering
  - [x] 3.7 Preserve existing trend section (`BiomarkerTrendSection`) below table — wrapped in `.hc-dash-section`
  - [x] 3.8 Pass `timelineByBiomarker` and `STATUS_NOTES` to BiomarkerTable as props

- [x] Task 4: Write BiomarkerTable tests (AC: #7, #8)
  - [x] 4.1 Test: renders table with correct number of rows
  - [x] 4.2 Test: displays biomarker name, value, unit in each row
  - [x] 4.3 Test: clicking "Biomarker" header sorts alphabetically (asc then desc)
  - [x] 4.4 Test: clicking "Value" header sorts numerically
  - [x] 4.5 Test: clicking row expands detail section with status note
  - [x] 4.6 Test: expanded detail shows reference range and confidence
  - [x] 4.7 Test: only one row expanded at a time (clicking another collapses first)
  - [x] 4.8 Test: sparkline renders when timelineByBiomarker has 2+ entries
  - [x] 4.9 Test: "—" displayed when fewer than 2 timeline entries
  - [x] 4.10 Test: flag button appears in expanded detail
  - [x] 4.11 Test: axe accessibility audit passes

- [x] Task 5: Update dashboard page tests (AC: #7)
  - [x] 5.1 Update active state tests to assert table-based layout instead of card-based
  - [x] 5.2 Update stat card tests to use StatCardGrid component assertions
  - [x] 5.3 Verify trend section still renders below table
  - [x] 5.4 Verify PatientSummaryBar renders in active state
  - [x] 5.5 Axe accessibility audit passes on updated active state

- [x] Task 6: Run full test suite (AC: #7)
  - [x] 6.1 Run `docker compose exec frontend npm run test:unit` — 404/405 pass (1 pre-existing failure in users.test.ts)
  - [x] 6.2 Run `docker compose exec frontend npm run check` — 0 errors, 2 pre-existing warnings

### Review Findings

- [x] [Review][Patch] Removed inner `<button>` from name cell — was independently focusable with no onclick, keyboard Tab dead-end. Now plain `<td>` text, `<tr>` handles all interaction [BiomarkerTable.svelte]
- [x] [Review][Patch] Sort indicator returns empty string for inactive columns instead of misleading `▲` [BiomarkerTable.svelte:60-63]
- [x] [Review][Patch] Row striping uses class-based `.hc-bio-row-even` via index instead of `nth-child(even)` which broke with detail rows. Detail row gets `.hc-bio-detail-row` with transparent background [app.css + BiomarkerTable.svelte]
- [x] [Review][Defer] `.hc-sort-button` class reused for name cell expand button — hover underline suggests link action, cosmetic
- [x] [Review][Defer] `lastUploadDate` uses string comparison instead of Date — works for ISO 8601 (current API format), pre-existing pattern
- [x] [Review][Defer] `.hc-sort-button` semantic reuse — expand button has sort-button class, semantically misleading but functionally harmless

## Dev Notes

### Architecture Decisions

- **BiomarkerTable is a standalone component** — receives data via props, does not fetch data itself. The dashboard page owns data fetching (TanStack Query) and passes results down.
- **Reuse existing CSS primitives** — `.hc-data-table`, `.hc-sort-button`, `.hc-sort-indicator` already exist from story 7-5. Only add `.hc-bio-*` classes for BiomarkerTable-specific styling (value colors, detail panel, sparkline cell).
- **Reuse existing components** — `HealthValueBadge` for status column, `BiomarkerTrendChart` (sparkline variant) for trend column. Do NOT create new badge or sparkline components.
- **Integration story** — This story both creates BiomarkerTable AND integrates the 10-2 components (PatientSummaryBar, StatCardGrid) into `+page.svelte`. The old Tailwind card-based active state is fully replaced.

### Component Specifications

**BiomarkerTable layout (inside .hc-data-table sunken region):**
```
┌──────────────────────────────────────────────────────────┐
│ Biomarker ▼  │ Value ▼     │ Status    │ Reference │Trend│
│──────────────┼─────────────┼───────────┼───────────┼─────│
│ TSH          │ 5.8 mIU/L   │ Concerning│ 0.4–4.0   │ ╱╲╱│
│ ┌─ expanded detail ─────────────────────────────────────┐│
│ │ Outside reference range — consider discussing with    ││
│ │ your doctor. Ref: 0.4–4.0 mIU/L · High confidence    ││
│ │                                            [🚩 Flag]  ││
│ └───────────────────────────────────────────────────────┘│
│ Free T4      │ 0.8 ng/dL   │ Borderline│ 0.8–1.8   │ ╲╲╲│
│ Hemoglobin   │ 13.2 g/dL   │ Optimal   │ 12–16     │ ───│
│ Ferritin     │ 18 ng/mL    │ Borderline│ 20–200    │ ╲╲╲│
│ Vit B12      │ 485 pg/mL   │ Optimal   │ 200–900   │ ───│
└──────────────────────────────────────────────────────────┘
```

**Full active state layout after integration:**
```
┌─ .hc-dash-header ───────────────────────────── [Upload] ─┐
│ Your Health Dashboard                                     │
│ Your extracted health values with context indicators      │
└──────────────────────────────────────────────────────────┘
┌─ PatientSummaryBar (.hc-summary-bar) ────────────────────┐
│ user@email.com · 3 documents · Last: Mar 15   [Upload]   │
└──────────────────────────────────────────────────────────┘
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│    18    │ │     3    │ │     1    │ │     0    │
│ Optimal  │ │Borderline│ │Concerning│ │  Action  │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
┌─ .hc-dash-section ───────────────────────────────────────┐
│ ┌─ .hc-dash-section-header ─────────────────────────────┐│
│ │ 📊 Biomarker Results                                  ││
│ └───────────────────────────────────────────────────────┘│
│ ┌─ .hc-data-table (BiomarkerTable) ────────────────────┐│
│ │ [dense sortable table as above]                       ││
│ └───────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────┘
┌─ Trends section (existing BiomarkerTrendSection) ────────┐
│ ...                                                       │
└──────────────────────────────────────────────────────────┘
```

### Props Interface

```typescript
interface BiomarkerTableProps {
  values: HealthValue[];
  timelineByBiomarker: Record<string, HealthValue[]>;
  statusNotes: Record<HealthValue['status'], string>;
}
```

### Sort Implementation

```typescript
let sortKey = $state<'name' | 'value'>('name');
let sortDir = $state<'asc' | 'desc'>('asc');

const sorted = $derived(
  [...values].sort((a, b) => {
    const mul = sortDir === 'asc' ? 1 : -1;
    if (sortKey === 'name') return mul * a.biomarker_name.localeCompare(b.biomarker_name);
    return mul * (a.value - b.value);
  })
);
```

### Expandable Row Pattern

```typescript
let expandedId = $state<string | null>(null);

function toggleRow(id: string) {
  expandedId = expandedId === id ? null : id;
}
```

Each `<tr>` gets `tabindex="0"`, `role="row"`, `aria-expanded={expandedId === value.id}`, and `onclick/onkeydown` handlers. The detail panel is a full-width `<tr>` with `<td colspan="5">` immediately after the data row.

### Value Color Mapping

Use inline `style` attribute to color the value text by status:
```typescript
const STATUS_COLORS: Record<string, string> = {
  optimal: '#2E8B57',
  borderline: '#DAA520',
  concerning: '#E07020',
  action_needed: '#CC3333',
  unknown: '#3366FF'
};
```
This matches `BiomarkerTrendChart.svelte` line 28-34 and `HealthValueBadge.svelte`.

### Confidence Label Pattern

Reuse from `HealthValueRow.svelte` line 34-38:
```typescript
function confidenceLabel(confidence: number): { text: string; classes: string } {
  if (confidence >= 0.9) return { text: 'High', classes: 'text-[#2E8B57]' };
  if (confidence >= 0.7) return { text: 'Medium', classes: 'text-[#DAA520]' };
  return { text: 'Low', classes: 'text-[#CC3333]' };
}
```

### PatientSummaryBar Data

The dashboard page needs to derive PatientSummaryBar props from existing queries:
- `email`: from auth store (`authStore` in `$lib/stores/auth.svelte.ts`) or user profile
- `documentCount`: derive from `values` by counting unique `document_id` values
- `lastUploadDate`: derive from `values` by finding the most recent `created_at`

Check existing auth store for email access pattern. If email is not readily available from auth store, use a placeholder approach matching how the header subtitle currently works — the PatientSummaryBar can accept email as optional and fall back to a generic label.

### Existing CSS Classes to Reuse (DO NOT recreate)

| Class | Source | Purpose |
|-------|--------|---------|
| `.hc-data-table` | app.css:624 | Sunken table container with 98.css box-shadow |
| `.hc-data-table table/th/td` | app.css:635-658 | Table styling, font sizes, padding |
| `.hc-data-table tbody tr:nth-child(even)` | app.css:660 | Alternating row colors |
| `.hc-data-table tbody tr.hc-row-interactive` | app.css:664 | Cursor pointer + hover/focus styles |
| `.hc-sort-button` | app.css:689 | Unstyled button for sort headers |
| `.hc-sort-indicator` | app.css:677 | Sort arrow indicator (▲/▼) |
| `.hc-sort-indicator.hc-sort-active` | app.css:685 | Active sort column indicator |
| `.hc-dash-section` | app.css | Sunken panel container |
| `.hc-dash-section-header` | app.css | Section header bar |

### Color Tokens (from app.css @theme)

```css
--color-status-optimal: #2E8B57;
--color-status-borderline: #DAA520;
--color-status-concerning: #E07020;
--color-status-action: #CC3333;
```

### Existing Components to Reuse

| Component | Import Path | Usage |
|-----------|-------------|-------|
| `HealthValueBadge` | `$lib/components/health/HealthValueBadge.svelte` | Status column badge |
| `BiomarkerTrendChart` | `$lib/components/health/BiomarkerTrendChart.svelte` | Sparkline (`variant="sparkline"`) in trend column |
| `PatientSummaryBar` | `$lib/components/health/PatientSummaryBar.svelte` | Active state header bar |
| `StatCardGrid` | `$lib/components/health/StatCardGrid.svelte` | 4-card status summary |
| `BiomarkerTrendSection` | `$lib/components/health/BiomarkerTrendSection.svelte` | Full trend charts below table |
| `Button` | `$lib/components/ui/button` | Flag button in detail row |

### What to Remove from +page.svelte

- The entire `<section aria-label="Health value summary">` with Tailwind `grid-cols-4` stat cards (lines 111-130) — replaced by `<StatCardGrid>`
- The entire `<section aria-label="Health values">` with `<article>` cards (lines 132-183) — replaced by `<BiomarkerTable>`
- The `BiomarkerTrendChart` import is no longer needed directly in +page.svelte (BiomarkerTable handles sparklines internally)

### What NOT to Touch

- Empty state rendering (the `{:else}` branch with recommendations + CTA)
- Loading and error states
- Data fetching queries (`valuesQuery`, `baselineQuery`)
- `BiomarkerTrendSection` and its full chart rendering
- AppShell / AdminShell
- Any backend code

### Previous Story Intelligence

**From story 10-1:**
- Changed `<main>` to `<div>` — dashboard is nested inside AppShell's `<main>`, so avoid nested landmarks
- Used `<h1>` for dashboard title, `<h2>` for section items — maintain heading hierarchy
- Review deferred: "Active state still uses Tailwind (redesign in story 10-3)" — THIS is the story that addresses that

**From story 10-2:**
- PatientSummaryBar and StatCardGrid are standalone, props-driven components
- CSS in app.css: `.hc-summary-*` and `.hc-stat-*` namespaces
- Components do NOT import or modify `+page.svelte` — integration happens in this story
- Test baseline: 390/391 passed (one pre-existing failure in `users.test.ts`)

**From story 9-4 (Global feedback surfaces):**
- Toast and feedback banner components added
- CSS naming: `.hc-toast-*`, `.hc-feedback-*`

**Git intelligence (recent commits):**
- `a3630d8` feat(ui): add toast and feedback banner components
- `02f3756` feat(ui): implement AdminShell component
- Pattern: `feat(ui):` prefix for UI component commits
- All new components have unit tests + axe audits

### Testing Patterns

- **Framework:** Vitest + jsdom + @testing-library/svelte + axe-core
- **Mock pattern:** `vi.mock('$lib/api/health-values', ...)` — already set up in `page.test.ts`
- **BiomarkerTable standalone tests:** Render component directly with props (no query client needed since it doesn't fetch data)
- **Dashboard integration tests:** Use existing `DashboardPageTestWrapper.svelte` with QueryClient
- **Axe audit:** `const results = await axe.run(container); expect(results.violations).toHaveLength(0);`
- **BiomarkerTrendChart mock:** In BiomarkerTable tests, mock or render the sparkline. Since it's SVG-based, it renders in jsdom. No special mocking needed.

### Project Structure Notes

- All new component files go in `src/lib/components/health/`
- Test files go alongside components: `BiomarkerTable.test.ts`
- CSS goes in `src/app.css` — append new `.hc-bio-*` classes near the existing `.hc-data-table` section
- No new directories or module structure changes needed

### References

- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md, lines 510-549] — Biomarker table wireframe, row spec, column definitions
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md, lines 113-116] — "Density over whitespace", "Tables over cards"
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md, lines 211-216] — Sortable column list view pattern, alternating row colors, inline status indicators
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md, line 175] — Story candidate: "BiomarkerTable redesign (flagship component)"
- [Source: _bmad-output/planning-artifacts/prd.md, FR14] — Health values with context indicators
- [Source: _bmad-output/planning-artifacts/prd.md, FR15] — Trend lines per biomarker
- [Source: healthcabinet/frontend/src/app.css, lines 623-706] — Existing .hc-data-table and .hc-sort-* CSS classes
- [Source: healthcabinet/frontend/src/lib/api/health-values.ts] — HealthValue interface and API functions
- [Source: healthcabinet/frontend/src/lib/components/health/BiomarkerTrendChart.svelte] — Sparkline variant (variant="sparkline", 60x20px)
- [Source: healthcabinet/frontend/src/lib/components/health/HealthValueRow.svelte, lines 34-38] — Confidence label pattern to reuse

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- `docker compose exec frontend npm run test:unit` (full suite): 404/405 passed; one pre-existing failure in `src/lib/api/users.test.ts` (`object.stream is not a function`)
- `docker compose exec frontend npm run check`: 0 errors, 2 pre-existing warnings in admin user page
- Fixed Svelte 5 `{@const}` placement error — must be direct child of `{#if}`, not inside `<div>`
- Fixed ARIA `aria-expanded` on `<tr role="row">` — moved to `<button>` in name cell per ARIA spec (aria-conditional-attr rule)
- Fixed TypeScript implicit `any` on event handler parameter

### Completion Notes List

- Created `BiomarkerTable.svelte` — dense sortable table with 5 columns (Biomarker, Value, Status, Reference, Trend) inside `.hc-data-table` sunken region
- Sortable by biomarker name (default) and value via `.hc-sort-button` column headers with `aria-sort` attributes
- Expandable detail rows: click any row to see status note, reference range, confidence level (High/Medium/Low colored), and flag button
- Inline sparklines via `BiomarkerTrendChart` (sparkline variant) when 2+ data points exist; "—" otherwise
- Flag mutation reuses `flagHealthValue` API with `aria-live` announcement pattern from `HealthValueRow.svelte`
- Integrated `PatientSummaryBar` and `StatCardGrid` (story 10-2) into dashboard active state
- Derived `email`, `documentCount`, `lastUploadDate` from auth store and health values data
- Replaced old Tailwind card-based active state with 98.css table-based layout
- Wrapped trend section in `.hc-dash-section` sunken panel for visual consistency
- Added 11 BiomarkerTable unit tests + axe audit via `BiomarkerTableTestWrapper.svelte`
- Updated 7 dashboard page tests for table-based layout assertions
- Total new tests: 18 (11 BiomarkerTable + 7 dashboard updates)

### File List

- `healthcabinet/frontend/src/app.css` (modified — added `.hc-bio-*` CSS classes for BiomarkerTable)
- `healthcabinet/frontend/src/lib/components/health/BiomarkerTable.svelte` (new)
- `healthcabinet/frontend/src/lib/components/health/BiomarkerTable.test.ts` (new)
- `healthcabinet/frontend/src/lib/components/health/BiomarkerTableTestWrapper.svelte` (new — test helper)
- `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte` (modified — integrated PatientSummaryBar, StatCardGrid, BiomarkerTable; removed card layout)
- `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts` (modified — updated active state tests for table layout)
- `_bmad-output/implementation-artifacts/10-3-biomarker-table-redesign.md` (modified — tasks, status, dev record)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified — story status)

### Change Log

- 2026-04-04: Implemented story 10-3 BiomarkerTable redesign — dense sortable table, expandable detail rows, dashboard integration with PatientSummaryBar + StatCardGrid
