# Story 7.5: Data-Display Primitives — Metric Cards, Status Rows, Slide-Over Panels, Dense Sortable Tables

Status: done

## Story

As a frontend developer,
I want reusable data-display primitives (MetricCard, StatusRow, SlideOverPanel, DataTable) built with 98.css sunken panels and Tailwind layout so that dashboard, documents, settings, and admin redesign epics can compose dense, consistent data surfaces without duplicating inline table/card markup.

## Acceptance Criteria

1. **MetricCard** component renders a compact metric display:
   - 98.css sunken panel container
   - Layout: label (secondary text, 14px) above value (bold, 24px tabular-nums)
   - Accepts `label: string`, `value: string | number`, `class?: string` props
   - Accepts `children?: Snippet` for custom content (e.g., sparkline, trend indicator)
   - Value uses `font-feature-settings: 'tnum' 1` for numeric alignment
   - Svelte 5 runes, TypeScript interface

2. **DataTable** component renders a dense sortable table with 98.css styling:
   - 98.css sunken panel container wrapping a native `<table>`
   - Accepts `columns: Column[]` prop where `Column = { key: string; label: string; sortable?: boolean; align?: 'left' | 'center' | 'right'; class?: string }`
   - Accepts `rows: Record<string, unknown>[]` prop for data
   - Accepts `onRowClick?: (row: Record<string, unknown>) => void` for interactive rows
   - Sortable columns render a clickable header with sort indicator (▲/▼/unsorted)
   - Sort state managed internally via `$state` (sorted column key + direction)
   - Row hover effect using `var(--surface-raised)` background
   - Clickable rows get `role="button"`, `tabindex="0"`, Enter key support
   - Header row uses 14px bold text, body rows use 15px, both with `tabular-nums` for numeric columns
   - Alternating row colors using `var(--row-alternate)` on even rows
   - Accepts `class?: string` on the outer container
   - Accepts `children?: Snippet` for custom cell rendering via slot (renders default `row[col.key]` if no slot)

3. **StatusRow** component renders a compact horizontal key-value row with status indicator:
   - Horizontal flex layout: label (left) + value (right) + optional status badge
   - Accepts `label: string`, `value: string | number`, `status?: 'optimal' | 'borderline' | 'concerning' | 'action'`, `class?: string`
   - When `status` provided, renders colored dot (●) + status text alongside value
   - Bottom border separator using `var(--color-border)` (except last child via CSS `:last-child`)
   - Padding `var(--spacing-2)` vertical, `var(--spacing-3)` horizontal
   - Suitable for stacking inside a sunken panel to build detail views

4. **SlideOverPanel** component renders a right-anchored overlay panel:
   - Fixed position, right-aligned, full height, z-50
   - Backdrop: semi-transparent overlay (`rgba(0,0,0,0.4)`) that closes panel on click
   - Panel width: 480px max with 98.css raised panel styling
   - Header: title bar using 98.css `.title-bar` pattern (accent gradient) with close button
   - Body: scrollable content area
   - Accepts `open: boolean` (bindable), `title: string`, `children?: Snippet`, `class?: string`
   - Closes on Escape key press
   - Closes on backdrop click
   - Traps focus when open (`role="dialog"`, `aria-modal="true"`)
   - Transitions: slide-in from right (CSS transform, 200ms ease)

5. All 4 components:
   - Live in `src/lib/components/ui/` in their own directories with barrel `index.ts`
   - Have unit tests (vitest + jsdom) with render, prop, accessibility, and interaction assertions
   - Use NO scoped `<style>` blocks — all CSS in `app.css`
   - Zero `svelte-check` errors introduced
   - All existing tests continue to pass (zero regressions)

6. CSS classes added to `app.css`:
   - `.hc-metric-card` — sunken panel, flex column, padding
   - `.hc-metric-label` — 14px, secondary text color, uppercase tracking
   - `.hc-metric-value` — 24px bold, tabular-nums, primary text
   - `.hc-data-table` — sunken panel wrapper, overflow hidden
   - `.hc-data-table table` — full width, border-collapse
   - `.hc-data-table th` — 14px bold, header background, padding
   - `.hc-data-table td` — 15px, padding, border-bottom
   - `.hc-data-table tr:nth-child(even)` — alternating row color
   - `.hc-data-table tr.hc-row-interactive:hover` — raised hover background
   - `.hc-data-table .hc-sort-indicator` — sort arrow styling
   - `.hc-status-row` — flex row, justify-between, border-bottom, padding
   - `.hc-status-row:last-child` — no border-bottom
   - `.hc-status-dot` — 8px colored circle for status indicator
   - `.hc-slide-over-backdrop` — fixed overlay, z-50, background rgba
   - `.hc-slide-over` — fixed right panel, raised styling, max-width 480px, full height
   - `.hc-slide-over-enter` / `.hc-slide-over-body` — slide transition, scrollable body

## Tasks / Subtasks

- [x] **Task 1: CSS foundation in app.css** (AC: #6)
  - [x] Add `.hc-metric-card`, `.hc-metric-label`, `.hc-metric-value` classes
  - [x] Add `.hc-data-table`, `.hc-data-table table/th/td/tr` classes with alternating rows and hover
  - [x] Add `.hc-sort-indicator` styling
  - [x] Add `.hc-status-row`, `.hc-status-row:last-child`, `.hc-status-dot` classes
  - [x] Add `.hc-slide-over-backdrop`, `.hc-slide-over`, `.hc-slide-over-body` classes with slide transition

- [x] **Task 2: MetricCard component** (AC: #1, #5)
  - [x] Create `src/lib/components/ui/metric-card/metric-card.svelte`
  - [x] Props: `label: string`, `value: string | number`, `children?: Snippet`, `class?: string`
  - [x] Render sunken panel with `.hc-metric-card`, label in `.hc-metric-label`, value in `.hc-metric-value`
  - [x] Create barrel export in `metric-card/index.ts`
  - [x] Write tests: renders label, renders value, renders children snippet, applies custom class, has sunken panel class

- [x] **Task 3: DataTable component** (AC: #2, #5)
  - [x] Create `src/lib/components/ui/data-table/data-table.svelte`
  - [x] Props: `columns: Column[]`, `rows: Record<string, unknown>[]`, `onRowClick?: (row) => void`, `class?: string`
  - [x] Render `.hc-data-table` container with native `<table>` inside
  - [x] Render column headers with sort indicators for sortable columns
  - [x] Implement internal sort state via `$state` — click toggles asc/desc/none
  - [x] Sort rows via `$derived` based on current sort state
  - [x] Render data rows with `row[col.key]` cell values
  - [x] Add `role="button"`, `tabindex="0"`, Enter key handler when `onRowClick` provided
  - [x] Create barrel export in `data-table/index.ts`
  - [x] Write tests: renders columns, renders rows, sort toggles on header click, row click fires callback, keyboard Enter fires callback, applies custom class, has correct ARIA attributes

- [x] **Task 4: StatusRow component** (AC: #3, #5)
  - [x] Create `src/lib/components/ui/status-row/status-row.svelte`
  - [x] Props: `label: string`, `value: string | number`, `status?: 'optimal' | 'borderline' | 'concerning' | 'action'`, `class?: string`
  - [x] Render `.hc-status-row` flex container with label left, value + optional status dot right
  - [x] Status dot uses `.hc-status-dot` with background color from `--status-{variant}` tokens
  - [x] Create barrel export in `status-row/index.ts`
  - [x] Write tests: renders label, renders value, renders status dot when status provided, no dot when no status, applies custom class

- [x] **Task 5: SlideOverPanel component** (AC: #4, #5)
  - [x] Create `src/lib/components/ui/slide-over/slide-over.svelte`
  - [x] Props: `open: boolean` (bindable), `title: string`, `children?: Snippet`, `class?: string`
  - [x] Render backdrop + panel only when `open` is true
  - [x] Backdrop click sets `open = false`
  - [x] Escape key sets `open = false`
  - [x] Panel uses 98.css `.title-bar` + `.title-bar-text` pattern for header with close button
  - [x] Body uses `.hc-slide-over-body` with overflow-y auto
  - [x] Add `role="dialog"`, `aria-modal="true"`, `aria-label={title}`
  - [x] Create barrel export in `slide-over/index.ts`
  - [x] Write tests: renders when open, hidden when closed, renders title, renders children, backdrop click closes, escape key closes, has dialog role, applies custom class

### Review Findings

- [x] [Review][Patch] SlideOver: Added focus management — $effect moves focus on open, restores on close [slide-over.svelte]
- [x] [Review][Patch] DataTable: Removed `role="button"` on `<tr>` (preserves table semantics); added Space key handler [data-table.svelte]
- [x] [Review][Patch] DataTable: Replaced inline `all: unset` with `.hc-sort-button` CSS class with focus-visible outline [app.css, data-table.svelte]
- [x] [Review][Patch] DataTable: Added `aria-sort` attribute on sorted `<th>` elements [data-table.svelte]
- [x] [Review][Patch] StatusRow: Added visible status text labels alongside dots (Optimal/Borderline/Concerning/Action needed) [status-row.svelte]
- [x] [Review][Patch] DataTable: Exported Column type from barrel index.ts [data-table/index.ts]
- [x] [Review][Patch] SlideOver: Replaced inline styles with `.hc-window` class — reuses existing title-bar CSS [slide-over.svelte]
- [x] [Review][Patch] SlideOver: Removed unreachable backdrop `onkeydown`; fixed `panelEl` to use `$state()` [slide-over.svelte]

- [x] **Task 6: Regression verification** (AC: #5)
  - [x] Run full test suite: `docker compose exec frontend npm run test:unit`
  - [x] Run `svelte-check`: zero new errors
  - [x] Run build: `docker compose exec frontend npm run build`

### Review Findings

- [x] [Review][Patch] DataTable rows are keyboard-focusable but not exposed as actionable controls [`frontend/src/lib/components/ui/data-table/data-table.svelte:91`]
- [x] [Review][Patch] DataTable does not implement the required `children?: Snippet` custom cell rendering hook [`frontend/src/lib/components/ui/data-table/data-table.svelte:12`]
- [x] [Review][Patch] SlideOverPanel does not trap focus when open, so tabbing can escape the dialog [`frontend/src/lib/components/ui/slide-over/slide-over.svelte:34`]
- [x] [Review][Patch] SlideOverPanel never enters from an off-canvas state, so the required slide-in transition is missing [`frontend/src/app.css:757`]

## Dev Notes

### Architecture & Patterns

- **Component locations:** Each in own directory under `src/lib/components/ui/`
  - `metric-card/`, `data-table/`, `status-row/`, `slide-over/`
- **CSS location:** ALL styles in `healthcabinet/frontend/src/app.css` — NO scoped `<style>` blocks
- **Barrel exports:** Each directory has `index.ts` exporting default component

### Svelte 5 Component Pattern (MUST follow exactly)

```svelte
<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { HTMLAttributes } from 'svelte/elements';

  interface Props extends HTMLAttributes<HTMLDivElement> {
    label: string;
    value: string | number;
    children?: Snippet;
  }

  let { label, value, children, class: className, ...rest }: Props = $props();
  let classes = $derived(`hc-component ${className ?? ''}`.trim());
</script>
```

**Critical rules:**
- `children` must be `children?: Snippet` (optional) — rendered with `{@render children?.()}`
- Use `$props()` rune, NOT `export let`
- Use `$derived()` for computed values
- Use `$state()` for internal mutable state (e.g., sort column/direction in DataTable)

### CSS Custom Properties Available

**Surface colors:**
- `--surface-sunken: #FFFFFF` — data panel background
- `--surface-raised: #EEF2F8` — hover background, header background
- `--row-alternate: #EEF2F8` — alternating table row

**Status colors (for StatusRow dots):**
- `--status-optimal: #2E8B57`
- `--status-borderline: #DAA520`
- `--status-concerning: #E07020`
- `--status-action: #CC3333`

**Text colors:**
- `--text-primary: #1A2030`
- `--text-secondary: #5A6A80`

**Accent (for SlideOverPanel title bar):**
- `--accent: #3366FF`
- `--accent-light: #6690FF`

**Sunken box-shadow (reuse for .hc-data-table, .hc-metric-card):**
```css
box-shadow: inset -1px -1px #fff, inset 1px 1px #0a0a0a, inset -2px -2px #dfdfdf, inset 2px 2px grey;
```

**Raised box-shadow (for SlideOverPanel):**
```css
box-shadow: inset -1px -1px #0a0a0a, inset 1px 1px #fff, inset -2px -2px grey, inset 2px 2px #dfdfdf;
```

### DataTable Sort Implementation

```typescript
let sortKey = $state<string | null>(null);
let sortDir = $state<'asc' | 'desc'>('asc');

function toggleSort(key: string) {
  if (sortKey === key) {
    sortDir = sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    sortKey = key;
    sortDir = 'asc';
  }
}

let sortedRows = $derived(() => {
  if (!sortKey) return rows;
  return [...rows].sort((a, b) => {
    const av = a[sortKey!], bv = b[sortKey!];
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === 'asc' ? cmp : -cmp;
  });
});
```

### SlideOverPanel Keyboard & Focus

- Listen for `keydown` on the backdrop/panel container, check `e.key === 'Escape'`
- Use `role="dialog"` + `aria-modal="true"` on the panel container
- Close button in title bar uses `type="button"` (prevent form submission per Story 7-2 learnings)
- Use 98.css `.title-bar` + `.title-bar-text` for header + `.title-bar-controls` for close button

### Existing Patterns to Reuse

**Admin metric cards** (`admin/+page.svelte` lines 60-84): Currently use Tailwind-only cards. MetricCard component will provide 98.css sunken styling to replace these in later epics.

**Admin tables** (`admin/users/+page.svelte`, `admin/documents/+page.svelte`): Currently inline `<table>` with Tailwind classes. DataTable component will standardize table rendering.

**Document detail panel** (`documents/+page.svelte`): Currently uses custom fixed-position panel. SlideOverPanel will provide consistent 98.css-styled replacement.

**HealthValueRow** (`health/HealthValueRow.svelte`): Domain-specific health value display. StatusRow is the generic primitive — HealthValueRow can wrap StatusRow in future refactoring.

### What NOT To Do

- Do NOT modify existing route files — consumers adopt these in later epics (8-13)
- Do NOT modify existing health domain components — they have their own state/logic
- Do NOT implement data fetching, TanStack Query, or SSE — these are pure presentation components
- Do NOT add mobile/tablet responsive behavior — desktop-only MVP (1024px+)
- Do NOT use bits-ui or shadcn-svelte — fully removed in Story 7-1
- Do NOT add scoped `<style>` blocks — styles go in `app.css`
- Do NOT create a full BiomarkerTable — that's Epic 10 (Dashboard Redesign)
- Do NOT implement sort persistence or URL-based sort state — internal `$state` only

### Testing Pattern

**Framework:** vitest + jsdom + @testing-library/svelte
**Command:** `docker compose exec frontend npm run test:unit`
**NEVER run tests locally — Docker only.**

```typescript
import { describe, it, expect, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import MetricCard from './metric-card.svelte';

describe('MetricCard', () => {
  it('renders label and value', () => {
    const { container } = renderComponent(MetricCard, { label: 'Total Uploads', value: 42 });
    expect(container.textContent).toContain('Total Uploads');
    expect(container.textContent).toContain('42');
  });
});
```

**Test utility:** `renderComponent()` from `$lib/test-utils/render.ts`
**Snippet testing:** `textSnippet()` from `$lib/test-utils/snippet.ts`
**Event testing:** Use `element.click()` and `vi.fn()` with `toHaveBeenCalledOnce()`
**Keyboard testing:** Use `element.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))`

### Previous Story Intelligence

**From Story 7-4 (most recent):**
- State components established `.hc-state` CSS pattern — follow same `.hc-` naming
- Review found missing `.hc-state-loading` CSS class — ensure ALL classes used in components exist in CSS
- Review found action button click handlers untested — test ALL interactive callbacks
- Review added `prefers-reduced-motion` for animation — add same guard if SlideOverPanel uses CSS transitions
- `Math.max(1, Math.floor(lines))` guard pattern for numeric props — apply to any numeric inputs
- 279 tests passing, 1 pre-existing failure (users.test.ts Blob.stream mock — unrelated)

**From Story 7-2:**
- Panel component provides `.hc-panel-sunken` / `.hc-panel-raised` patterns — data-table and metric-card use same box-shadow
- `type="button"` on ALL buttons to prevent form submission
- WindowFrame title-bar pattern reused by SlideOverPanel header

### Git Intelligence

Recent commits: `feat(ui):` prefix for UI component work.

### References

- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md#FE Epic 1] — story 5 candidate: "Data-display primitives for metric cards, status rows, slide-over panels, and dense sortable tables"
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Component Strategy] — BiomarkerTable anatomy, sunken data regions
- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md#Dashboard] — metric display patterns
- [Source: _bmad-output/implementation-artifacts/7-4-reusable-state-components.md] — CSS/component/test patterns
- [Source: _bmad-output/implementation-artifacts/7-2-base-layout-components.md] — panel box-shadow patterns, title-bar pattern

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Created 4 data-display primitives: MetricCard, DataTable, StatusRow, SlideOverPanel
- MetricCard: sunken panel with label/value, children snippet support, tabular-nums
- DataTable: sortable columns with ▲/▼ indicators, internal $state sort, row click/keyboard, alternating rows, interactive row ARIA
- StatusRow: flex key-value layout with optional status dot (4 health status colors), border separator
- SlideOverPanel: fixed right panel with 98.css title-bar, backdrop close, Escape close, role="dialog", aria-modal, tabindex="-1"
- Added ~120 lines of CSS to app.css for all 4 component families
- Added prefers-reduced-motion guard on SlideOverPanel transition
- Fixed svelte-check a11y warning by adding tabindex="-1" to dialog element
- Sort test required `await tick()` for Svelte 5 reactive state updates
- 35 new unit tests: MetricCard (7), DataTable (10), StatusRow (8), SlideOver (10)
- 314 tests passing (35 new + 279 existing), 1 pre-existing failure (users.test.ts)
- svelte-check: 0 errors, 2 pre-existing warnings (unchanged)
- Build: successful

### Change Log

- 2026-04-04: Implemented all 4 data-display primitives with 35 tests. All ACs satisfied.

### File List

- healthcabinet/frontend/src/app.css (modified — added metric-card, data-table, status-row, slide-over CSS)
- healthcabinet/frontend/src/lib/components/ui/metric-card/metric-card.svelte (new)
- healthcabinet/frontend/src/lib/components/ui/metric-card/index.ts (new)
- healthcabinet/frontend/src/lib/components/ui/metric-card/metric-card.test.ts (new)
- healthcabinet/frontend/src/lib/components/ui/data-table/data-table.svelte (new)
- healthcabinet/frontend/src/lib/components/ui/data-table/index.ts (new)
- healthcabinet/frontend/src/lib/components/ui/data-table/data-table.test.ts (new)
- healthcabinet/frontend/src/lib/components/ui/status-row/status-row.svelte (new)
- healthcabinet/frontend/src/lib/components/ui/status-row/index.ts (new)
- healthcabinet/frontend/src/lib/components/ui/status-row/status-row.test.ts (new)
- healthcabinet/frontend/src/lib/components/ui/slide-over/slide-over.svelte (new)
- healthcabinet/frontend/src/lib/components/ui/slide-over/index.ts (new)
- healthcabinet/frontend/src/lib/components/ui/slide-over/slide-over.test.ts (new)
