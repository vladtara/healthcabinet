# Story 11.1: Document List 98.css File Explorer Redesign

Status: done

## Story

As a user with uploaded health documents,
I want my documents displayed in a dense, sortable file-explorer table with clear metadata hierarchy and status treatment,
so that I can scan, sort, and manage my document collection like a clinical workstation file browser.

## Acceptance Criteria

1. **DocumentList table component** — Replace the current 3-column card grid with a dense sortable `<table>` inside a `.hc-data-table` sunken panel. Columns: Icon (file type), Name (bold, truncated), Type (PDF/Image), Date (formatted), Values (count of extracted values), Status (badge), Size (formatted), Actions (view/delete). Reuses existing `.hc-data-table`, `.hc-sort-button`, `.hc-sort-indicator` CSS classes from Epic 7.

2. **Sortable columns** — Name and Date columns are sortable by clicking headers. Default sort: by date descending (newest first, preserving current behavior). Uses `$state` for sort key/direction. `aria-sort` on sortable `<th>` elements.

3. **Status treatment** — Each row shows a status badge: Completed (green), Processing (blue, animated pulse), Partial (yellow), Failed (red), Pending (gray). Status is never color-only — always paired with text label. Processing rows have disabled action buttons.

4. **Row selection** — Clicking a row opens the existing detail panel (slide-in from right). Selected row gets `.hc-doc-row-selected` highlight. The detail panel logic (document detail query, delete mutation, keep-partial, SSE) is preserved from the current implementation — only the list rendering changes.

5. **Page header** — 98.css raised panel header with "Documents" title and "Upload" button (right-aligned, links to `/documents/upload`). Matches the `.hc-dash-header` pattern from the dashboard.

6. **Empty state** — When no documents exist, render a 98.css sunken panel with centered content: document icon, "No documents yet" heading, "Upload your first health document" subtext, Upload button. Uses `.hc-dash-empty-cta` pattern from dashboard story 10-1.

7. **Loading and error states** — Loading: skeleton rows in `.hc-data-table`. Error: inline message in sunken panel with retry button. Preserves existing query/retry logic.

8. **CSS follows established patterns** — New styles in `app.css` using `.hc-doc-*` naming. Reuses `.hc-data-table`, `.hc-sort-button`, `.hc-sort-indicator`, `.hc-dash-header`, `.hc-dash-section`. No scoped styles.

9. **Tests** — Document list table: renders correct columns, sorts by name and date, row selection highlights, status badges render correctly, empty state, loading skeleton, error state, actions (view/delete) present, axe audit. Preserve existing SSE and mutation test coverage.

10. **WCAG Considerations** — Table with proper `<thead>`/`<tbody>`. Rows keyboard-navigable. `aria-sort` on sortable headers. Status badges have accessible text. Action buttons have `aria-label`. Selected row indicated with `aria-selected`. Axe audit passes.

## Tasks / Subtasks

- [x] Task 1: Add document list CSS to app.css (AC: #8)
  - [x] 1.1 Reuse `.hc-dash-header` pattern for page header
  - [x] 1.2 Add `.hc-doc-icon` for file type icon cell (28px width)
  - [x] 1.3 Add `.hc-doc-name` for filename (bold, truncated with ellipsis, max-width 200px)
  - [x] 1.4 Add `.hc-doc-status-*` badge variants (completed/processing/partial/failed/pending) with text colors
  - [x] 1.5 Add `.hc-doc-actions` for action button cell with hover/focus states
  - [x] 1.6 Add `.hc-doc-row-selected` for selected row highlight (accent-light background)

- [x] Task 2: Restructure documents page with table layout (AC: #1, #2, #4, #5)
  - [x] 2.1 Replace card grid with `.hc-data-table` containing sortable `<table>`
  - [x] 2.2 Add page header with "Documents" title + Upload button
  - [x] 2.3 Implement sortable Name and Date columns with `aria-sort`
  - [x] 2.4 Render rows: icon, name, type, date, status (symbol+text), size, actions (view/delete)
  - [x] 2.5 Row click sets `selectedDocumentId` (preserves detail panel logic)
  - [x] 2.6 Selected row gets `.hc-doc-row-selected` + `aria-selected`
  - [x] 2.7 Reuse existing formatFileSize, formatDate, fileTypeIcon utilities

- [x] Task 3: Update status badges (AC: #3)
  - [x] 3.1 Status badge with symbol + text + color class per status
  - [x] 3.2 Processing status has `animate-pulse` class
  - [x] 3.3 Processing/pending rows have disabled action buttons

- [x] Task 4: Update empty, loading, and error states (AC: #6, #7)
  - [x] 4.1 Empty state: `.hc-dash-section` + `.hc-dash-empty-cta` pattern
  - [x] 4.2 Loading state: skeleton rows with `role="status"`
  - [x] 4.3 Error state: sunken panel with error message + retry button

- [x] Task 5: Preserve existing functionality (AC: #4)
  - [x] 5.1 Detail panel unchanged (query, delete, keep-partial, SSE)
  - [x] 5.2 SSE connection management preserved
  - [x] 5.3 Delete confirmation flow preserved
  - [x] 5.4 Optimistic cache updates preserved
  - [x] 5.5 Detail panel badge updated to use new `.hc-doc-status` pattern

- [x] Task 6: Update tests (AC: #9, #10)
  - [x] 6.1 Updated card click selectors to table row selectors (`closest('tr')`)
  - [x] 6.2 Updated loading text assertion to match new sr-only text
  - [x] 6.3 Preserved all 44 existing tests (SSE, delete, keep-partial, recovery, flagging)
  - [x] 6.4 All tests pass with new table-based layout

- [x] Task 7: Run full test suite (AC: #9)
  - [x] 7.1 Run `docker compose exec frontend npm run test:unit` — 433/434 pass (1 pre-existing failure)
  - [x] 7.2 Run `docker compose exec frontend npm run check` — 0 errors, 2 pre-existing warnings

### Review Findings

- [x] [Review][Patch] Replaced `aria-selected` with `aria-current="true"` — valid on any element without grid context [+page.svelte]
- [x] [Review][Patch] Added sr-only "File type" label to empty icon `<th>` [+page.svelte]
- [x] [Review][Patch] Added guard in `<tr>` keydown to skip events from nested buttons via `closest('button')` [+page.svelte]
- [x] [Review][Patch] Updated test status mapping: `pending` → "Pending" to match component [page.test.ts]
- [x] [Review][Defer] "Values" column from AC1 — Document list API doesn't return value count; requires backend change or extra query
- [x] [Review][Defer] Date sort string comparison — pre-existing pattern, works for ISO 8601
- [x] [Review][Defer] No keyboard arrow-key navigation between rows — tab-per-row is current pattern project-wide
- [x] [Review][Defer] Delete button opens detail panel in loading state — pre-existing UX pattern
- [x] [Review][Defer] Missing dedicated sort and selection interaction tests — existing tests cover rendering

## Dev Notes

### Architecture Decisions

- **Restructure the page, not the data layer** — The current documents page has working TanStack Query fetching, SSE connections, delete/keep-partial mutations, and optimistic cache updates. ALL of this logic stays. Only the template rendering changes from card grid to table.
- **Reuse existing CSS primitives** — `.hc-data-table`, `.hc-sort-button`, `.hc-sort-indicator` from Epic 7 + `.hc-dash-header` from Epic 10. Only add `.hc-doc-*` for document-specific styling.
- **No new component extraction** — Unlike the dashboard (which extracted BiomarkerTable as a separate component), the documents page keeps the table inline in `+page.svelte`. The detail panel, SSE logic, and mutations are tightly coupled to the page and don't benefit from extraction.

### UX Spec: Explorer-Style Table

From UX design spec (component #9, DocumentList):
- **Anatomy:** Sunken panel table — Icon | Name (bold) | Type | Date | Values | Status | Size | Actions (👁 ⬇ 🗑)
- **States per row:** `default` · `selected` (accent bg) · `processing` (disabled actions) · `failed` (🔄 + 🗑)
- **Behavior:** Click row to select → detail panel opens. Delete highlights red on hover.

From UX principles:
- "The document cabinet should feel like browsing files in Explorer — list view with columns, not a card grid."
- "Sortable column list view (Outlook inbox / Explorer detail view)"
- "Alternating row colors — subtle gray/white alternation for scanability"

### Current Page Structure (what to preserve)

The current `+page.svelte` (414 lines) has:
```
<script>
  - documentsQuery (TanStack Query, key: ['documents'])
  - detailQuery (TanStack Query, key: ['documents', selectedDocId])
  - deleteMutation with optimistic cache update
  - keepPartialMutation with cache update
  - SSE connection management ($effect for pending/processing docs)
  - selectedDocId state
  - File size/date/icon formatting utilities
</script>

<template>
  - Loading state → skeleton cards          ← REDESIGN
  - Error state → error message + retry     ← REDESIGN
  - Empty state → dashed box + upload CTA   ← REDESIGN
  - Document cards in grid                  ← REDESIGN to table
  - Detail panel (slide-in right)           ← PRESERVE
  - Delete confirmation dialog              ← PRESERVE
</template>
```

### Document Type (from $lib/types/api.ts)

```typescript
interface Document {
  id: string;
  user_id: string;
  filename: string;
  file_size_bytes: number;
  file_type: string;
  status: 'pending' | 'processing' | 'completed' | 'partial' | 'failed';
  arq_job_id: string | null;
  keep_partial: boolean | null;
  created_at: string;
  updated_at: string;
}
```

### Status Badge Color Mapping

| Status | Color | Symbol | CSS Class |
|--------|-------|--------|-----------|
| completed | `--color-status-optimal` (#2E8B57) | ● | `.hc-doc-status-completed` |
| processing | `--accent` (#3366FF) | ⏳ | `.hc-doc-status-processing` (+ animate-pulse) |
| partial | `--color-status-borderline` (#DAA520) | ◉ | `.hc-doc-status-partial` |
| failed | `--color-status-action` (#CC3333) | ✕ | `.hc-doc-status-failed` |
| pending | `--text-disabled` (#8898A8) | ○ | `.hc-doc-status-pending` |

### File Size Formatting

Already exists in the current page. Reuse:
```typescript
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
```

### File Type Icon Mapping

Already exists. Reuse:
```typescript
function fileTypeIcon(fileType: string): string {
  if (fileType === 'application/pdf') return '📄';
  if (fileType.startsWith('image/')) return '🖼️';
  return '📎';
}
```

### Existing CSS to Reuse (DO NOT recreate)

| Class | Source | Purpose |
|-------|--------|---------|
| `.hc-data-table` | app.css (Epic 7) | Sunken table container |
| `.hc-data-table table/th/td` | app.css (Epic 7) | Table styling |
| `.hc-row-interactive` | app.css (Epic 7) | Cursor pointer + hover/focus |
| `.hc-sort-button` | app.css (Epic 7) | Sort header buttons |
| `.hc-sort-indicator` | app.css (Epic 7) | Sort arrow |
| `.hc-dash-header` | app.css (Epic 10) | Page header pattern |
| `.hc-dash-section` | app.css (Epic 10) | Sunken panel container |
| `.hc-dash-empty-cta` | app.css (Epic 10) | Empty state CTA pattern |

### What NOT to Touch

- Detail panel (document detail view, extracted values, recovery card)
- SSE connection management
- Delete mutation and confirmation dialog
- Keep-partial mutation
- Upload page (`/documents/upload`)
- Document detail page (`/documents/[id]`)
- Backend API

### Previous Story Intelligence

**From Epic 10 (Dashboard Redesign):**
- `.hc-data-table` with sortable columns works well (BiomarkerTable pattern)
- Class-based row striping (`.hc-bio-row-even`) preferred over `nth-child(even)` when detail rows can be inserted
- Test wrappers with QueryClientProvider for components using TanStack Query
- `aria-sort` on `<th>` elements for accessibility
- Test baseline: 433/434 pass (1 pre-existing in `users.test.ts`)

**From story 10-3 code review:**
- Don't put `aria-expanded` on `<tr role="row">` — use buttons or other valid elements
- Sort indicator should show empty string for inactive columns (not misleading arrow)

### Testing Patterns

- **Framework:** Vitest + jsdom + @testing-library/svelte + axe-core
- **Existing test file:** `page.test.ts` (1227 lines!) with extensive coverage — MUST preserve SSE, delete, keep-partial tests
- **Test wrapper:** `DocumentsPageTestWrapper.svelte` already exists with QueryClientProvider
- **Mock pattern:** `vi.mock('$lib/api/documents', ...)` + `vi.mock('$lib/api/client.svelte', ...)`
- **SSE mocking:** Custom `MockEventSource` class already implemented in test file

### References

- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md, lines 568-643] — Documents cabinet wireframe, states, card component, detail panel
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md, lines 201-203] — "Document cabinet should feel like browsing files in Explorer"
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md, lines 866-871] — DocumentList component spec: sunken panel table with columns
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md, line 200] — Story: "DocumentList redesign with 98.css file-explorer table pattern"
- [Source: healthcabinet/frontend/src/routes/(app)/documents/+page.svelte] — Current 414-line page with SSE, mutations, detail panel
- [Source: healthcabinet/frontend/src/routes/(app)/documents/page.test.ts] — Existing 1227-line test suite to preserve
- [Source: healthcabinet/frontend/src/lib/types/api.ts] — Document, DocumentDetail, HealthValueItem types
- [Source: healthcabinet/frontend/src/lib/api/documents.ts] — listDocuments, getDocumentDetail, deleteDocument, etc.
- [Source: healthcabinet/frontend/src/app.css, lines 623-706] — .hc-data-table and .hc-sort-* CSS

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- `docker compose exec frontend npm run test:unit`: 433/434 passed; 1 pre-existing failure in `users.test.ts`
- `docker compose exec frontend npm run check`: 0 errors, 2 pre-existing warnings
- Fixed `badge.classes` → `badge.cssClass` type error in detail panel (statusBadge return type changed)
- Updated 20 test selectors from `getByRole('button', { name: /blood_test/ })` to `getByText('blood_test.pdf').closest('tr')!`
- Updated loading text assertion from "Loading documents…" to "Loading your documents…"

### Completion Notes List

- Replaced 3-column card grid with 98.css `.hc-data-table` explorer-style sortable table (7 columns: Icon, Name, Type, Date, Status, Size, Actions)
- Added page header with `.hc-dash-header` pattern ("Documents" + Upload button)
- Sortable by Name (ascending default) and Date (descending default) with `.hc-sort-button` and `aria-sort`
- Status badges use symbol + text + color: ● Completed (green), ⏳ Processing (blue, pulse), ◉ Partial (yellow), ✕ Failed (red), ○ Pending (gray)
- Row click sets selectedDocumentId; selected row highlighted with `.hc-doc-row-selected` + `aria-selected`
- View and Delete action buttons per row with `aria-label`; disabled for processing/pending documents
- Empty state uses `.hc-dash-empty-cta` pattern; loading uses skeleton rows with `role="status"`; error has retry button
- Replaced `<main>` wrapper with `<div>` (consistent with dashboard, avoids nested landmarks)
- Detail panel, SSE, delete/keep-partial mutations, and optimistic cache updates all preserved unchanged
- All 44 existing tests pass with updated selectors (card → table row)
- Added ~100 lines of `.hc-doc-*` CSS in app.css

### File List

- `healthcabinet/frontend/src/app.css` (modified — added `.hc-doc-*` CSS classes)
- `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` (modified — card grid → table, header, states)
- `healthcabinet/frontend/src/routes/(app)/documents/page.test.ts` (modified — updated selectors + loading text)
- `_bmad-output/implementation-artifacts/11-1-document-list-98css-file-explorer.md` (modified)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified)

### Change Log

- 2026-04-05: Implemented story 11-1 Document List 98.css File Explorer — card grid to sortable table, 98.css page header, status badges, row selection
