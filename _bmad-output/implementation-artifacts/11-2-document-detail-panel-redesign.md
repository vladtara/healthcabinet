# Story 11.2: DocumentDetailPanel Redesign

Status: done

## Story

As a user viewing a document,
I want a polished 98.css side panel showing extracted values, recovery options, and destructive actions with calm, clear confirmation patterns,
so that I can understand what was extracted and safely manage problematic documents.

## Acceptance Criteria

1. **DocumentDetailPanel as 98.css side panel** — Extract the current inline detail panel (lines 282–413 of `+page.svelte`) into a standalone `DocumentDetailPanel.svelte` component placed in `src/lib/components/health/`. The panel slides in from the right (400px width), renders inside a full-height `.hc-dash-section` sunken panel with a raised header. The overlay backdrop and slide-in behavior remain. Must accept props for `documentId`, `onClose`, and mutation callbacks.

2. **Header structure** — `.hc-dash-section-header` raised panel header containing "Document Details" title (left) + close `✕` button (right, 98.css raised button style, `aria-label="Close document details"`).

3. **Document metadata section** — File-type icon + filename (bold) + formatted date + formatted file size. Reuse existing `fileTypeIcon()`, `formatDate()`, `formatFileSize()` utilities (move to a shared `src/lib/utils/format.ts` if not already shared, or keep inline in the component). All metadata in readable text.

4. **Status badge** — Document status badge using `.hc-doc-status` + `.hc-doc-status-{status}` CSS classes from Story 11-1. Symbol + text + color, never color-only. Status symbols: `●` Completed, `◉` Processing, `⚠` Partial, `✕` Failed, `○` Pending.

5. **Recovery card (conditional)** — If status is `partial` (and `keep_partial` is falsy) or `failed`, render the existing `PartialExtractionCard` component. Pass `status`, `documentId`, `onReupload`, `onKeepPartial`, `isKeepingPartial` props unchanged. No red colors for recovery actions — red is reserved for delete confirmation only.

6. **Extracted values table** — Render extracted health values using `.hc-data-table` pattern in a sunken panel. Table columns: Name (left-aligned) | Value + Unit (bold) | Confidence (High/Medium/Low with color class, never color-only) | Flag button. Reuse the existing `HealthValueRow` component OR refactor values into table rows that match `.hc-data-table td` styling. Each row must show: biomarker name, extracted value + unit, confidence level, flag button (reuses `flagHealthValue` mutation). If no values: "No extracted health values." message in sunken panel.

7. **Delete button and 98.css confirmation dialog** — Bottom of panel: "Delete Document" button styled as standard 98.css raised button (gray default, text turns red on `:hover`). Clicking opens a 98.css-style confirmation dialog (NOT the current inline confirmation). Dialog structure:
   - Title bar: "Delete Document?" (98.css window title bar style)
   - Body: "This will permanently remove {filename} and all extracted values. This action cannot be undone."
   - Footer buttons: "Cancel" (left, standard 98.css button) | "Delete" (right, red accent background)
   - After confirmation: call `deleteMutation`, close detail panel, remove document from list cache
   - Escape key dismisses dialog (not the panel)

8. **CSS follows established patterns** — All new styles in `app.css` using `.hc-detail-*` prefix. Reuse `.hc-dash-section`, `.hc-dash-section-header`, `.hc-dash-section-body`, `.hc-data-table`, `.hc-doc-status-*` classes. No scoped `<style>` blocks. No Tailwind utility classes for structural styling — use 98.css class patterns.

9. **Preserve all existing data layer behavior** — The component must use the same TanStack Query patterns:
   - `createQuery` with `['documents', documentId]` key for detail fetching
   - `keepPartialMutation` with optimistic cache updates (both list and detail caches)
   - `deleteMutation` with optimistic list removal + detail cache invalidation + health_values invalidation
   - SSE connection management for processing documents stays in the parent `+page.svelte`
   - No new API endpoints — all existing endpoints from `$lib/api/documents.ts` are sufficient

10. **Tests** — Unit tests in `src/lib/components/health/DocumentDetailPanel.test.ts`:
    - Renders document metadata (filename, date, size)
    - Status badge displays correct symbol + text for each status
    - Recovery card appears for partial (non-kept) and failed documents
    - Recovery card hidden for completed, processing, pending, and partial+kept documents
    - Extracted values render in table with name, value, unit, confidence
    - Flag button calls `flagHealthValue` mutation
    - "Keep Partial" button triggers keep-partial mutation
    - Delete button opens confirmation dialog
    - Confirmation dialog shows filename in message
    - Cancel in dialog dismisses without deleting
    - Confirm delete calls `deleteMutation` and triggers `onClose`
    - Escape dismisses dialog but not panel (when dialog is open)
    - Axe accessibility audit passes
    - Update parent `page.test.ts` to work with extracted component

11. **WCAG compliance** — Side panel has `role="dialog"` + `aria-modal="true"` + `aria-label="Document details"`. Close button has `aria-label="Close document details"`. Confidence levels never color-only. Status badges have accessible text. Confirm dialog uses `role="alertdialog"` + `aria-modal="true"`. Focus trapped in dialog when open. Axe audit passes.

## Tasks / Subtasks

- [x] Task 1: Extract DocumentDetailPanel component (AC: 1, 2, 3, 4)
  - [x] Create `src/lib/components/health/DocumentDetailPanel.svelte`
  - [x] Move detail panel markup from `+page.svelte` lines 282–413 into new component
  - [x] Implement 98.css header with `.hc-dash-section-header` pattern
  - [x] Implement metadata section with file icon, name, date, size
  - [x] Implement status badge using `.hc-doc-status-*` classes with symbols
  - [x] Define component props interface: `documentId`, `onClose`, `onDelete`, `onKeepPartial`, `onReupload`

- [x] Task 2: Integrate recovery card and extracted values (AC: 5, 6)
  - [x] Render `PartialExtractionCard` conditionally (partial+!keep_partial OR failed)
  - [x] Render extracted values in `.hc-data-table` format
  - [x] Preserve `HealthValueRow` component or adapt to table row pattern
  - [x] Show empty state when no health values

- [x] Task 3: Implement 98.css delete confirmation dialog (AC: 7)
  - [x] Create confirmation dialog with 98.css window chrome (title bar, body, button footer)
  - [x] Wire delete button → dialog → `deleteMutation` → close panel
  - [x] Escape dismisses dialog only (not underlying panel)
  - [x] Show filename in confirmation message

- [x] Task 4: Add CSS classes (AC: 8)
  - [x] Add `.hc-detail-panel` — panel container (400px width, full-height, slide-in)
  - [x] Add `.hc-detail-overlay` — backdrop overlay
  - [x] Add `.hc-detail-meta` — metadata section layout
  - [x] Add `.hc-detail-values` — values table section
  - [x] Add `.hc-detail-actions` — bottom action bar
  - [x] Add `.hc-detail-confirm` — confirmation dialog styles
  - [x] Reuse `.hc-dash-section`, `.hc-dash-section-header`, `.hc-data-table` classes

- [x] Task 5: Update parent page and preserve data layer (AC: 1, 9)
  - [x] Replace inline detail panel in `+page.svelte` with `<DocumentDetailPanel>` component
  - [x] Keep all query/mutation definitions in parent, pass as props or use shared query keys
  - [x] SSE management stays in parent `+page.svelte`
  - [x] Verify optimistic cache updates still work (list + detail caches)

- [x] Task 6: Write tests (AC: 10)
  - [x] Create `DocumentDetailPanel.test.ts` with test wrapper
  - [x] Test metadata rendering, status badges, recovery card visibility
  - [x] Test delete flow (button → dialog → confirm/cancel)
  - [x] Test flag mutation integration
  - [x] Test accessibility (axe audit)
  - [x] Update `page.test.ts` for extracted component

- [x] Task 7: WCAG audit (AC: 11)
  - [x] `role="dialog"` + `aria-modal="true"` on panel
  - [x] `role="alertdialog"` on confirmation dialog
  - [x] Focus trap in confirmation dialog
  - [x] All interactive elements keyboard-accessible
  - [x] Run axe audit

## Dev Notes

### Architecture & Patterns

- **Component extraction, NOT rewrite**: The detail panel logic already exists in `+page.svelte` (lines 282–413). This story extracts it into a reusable component and reskins it with 98.css patterns. Do NOT rewrite the data fetching, mutations, or SSE logic.
- **98.css class-based styling**: All structural styling via `app.css` classes with `.hc-detail-*` prefix. The design system classes (`.hc-dash-section`, `.hc-data-table`, etc.) are defined in `app.css` starting around line 624 (data-table) and line 1800 (dash-section).
- **Svelte 5 runes**: Use `$props()`, `$state()`, `$derived()` — NOT Svelte 4 `export let` or stores.
- **TanStack Query v6**: Queries and mutations use `createQuery()` / `createMutation()` from `@tanstack/svelte-query`.

### Existing Code to Preserve

| What | Location | Notes |
|------|----------|-------|
| Document list query | `+page.svelte` line 18 | `['documents']` query key |
| Detail query | `+page.svelte` line 58 | `['documents', selectedDocumentId]` key |
| Delete mutation | `+page.svelte` line 64 | Optimistic removal from list cache + invalidates detail + health_values |
| Keep-partial mutation | `+page.svelte` line 27 | Updates both list AND detail caches optimistically |
| SSE connections | `+page.svelte` lines 116–179 | Map-based tracking, 3-error max, cleanup on destroy |
| `HealthValueRow` | `src/lib/components/health/HealthValueRow.svelte` | Has flag mutation, confidence display, flagged/needs-review badges |
| `PartialExtractionCard` | `src/lib/components/health/PartialExtractionCard.svelte` | Recovery UI for partial/failed docs |

### Existing CSS Classes to Reuse

| Class | Purpose | Defined at |
|-------|---------|-----------|
| `.hc-dash-section` | Sunken panel container | `app.css:1800` |
| `.hc-dash-section-header` | Raised panel header | `app.css:1807` |
| `.hc-dash-section-body` | Panel body content | `app.css:1816` |
| `.hc-data-table` | Sunken table container | `app.css:624` |
| `.hc-data-table th` / `td` | Table cell styling | `app.css:640-660` |
| `.hc-doc-status-*` | Status badge colors | `app.css:2395-2415` |
| `.hc-doc-row-selected` | Selected row highlight | `app.css:2445` |

### Status Badge Mapping

| Status | Symbol | CSS Class | Text |
|--------|--------|-----------|------|
| completed | `●` | `.hc-doc-status-completed` | Completed |
| processing | `◉` | `.hc-doc-status-processing` | Processing |
| partial | `⚠` | `.hc-doc-status-partial` | Partial |
| failed | `✕` | `.hc-doc-status-failed` | Failed |
| pending | `○` | `.hc-doc-status-pending` | Pending |

### Delete Confirmation Dialog Pattern

Use 98.css window chrome for the dialog — NOT the current inline expand pattern. Reference the 98.css `<div class="window">` pattern:
```html
<div class="window" role="alertdialog" aria-modal="true" aria-labelledby="delete-title">
  <div class="title-bar">
    <div class="title-bar-text" id="delete-title">Delete Document?</div>
    <div class="title-bar-controls"><button aria-label="Close"></button></div>
  </div>
  <div class="window-body">
    <p>This will permanently remove {filename} and all extracted values...</p>
    <div style="display: flex; gap: 8px; justify-content: flex-end;">
      <button>Cancel</button>
      <button class="hc-detail-confirm-delete">Delete</button>
    </div>
  </div>
</div>
```

### TypeScript Types

```typescript
// From $lib/types/api.ts — use these directly, no transformation
interface DocumentDetail {
  id: string;
  filename: string;
  file_size_bytes: number;
  file_type: string;
  status: 'pending' | 'processing' | 'completed' | 'partial' | 'failed';
  arq_job_id: string | null;
  keep_partial: boolean | null;
  created_at: string;
  updated_at: string;
  health_values: HealthValueItem[];
}

interface HealthValueItem {
  id: string;
  biomarker_name: string;
  canonical_biomarker_name: string;
  value: number;
  unit: string | null;
  reference_range_low: number | null;
  reference_range_high: number | null;
  measured_at: string | null;
  confidence: number;
  needs_review: boolean;
  is_flagged: boolean;
  flagged_at: string | null;
}
```

### API Endpoints (all existing)

| Method | Endpoint | Function | Used for |
|--------|----------|----------|----------|
| GET | `/api/v1/documents/{id}` | `getDocumentDetail()` | Fetch detail data |
| DELETE | `/api/v1/documents/{id}` | `deleteDocument()` | Delete document |
| POST | `/api/v1/documents/{id}/keep-partial` | `keepPartialResults()` | Accept partial values |
| POST | `/api/v1/documents/{id}/reupload` | `reuploadDocument()` | Retry upload |
| GET | `/api/v1/documents/{id}/status?token=` | `getDocumentStatusUrl()` | SSE stream (parent manages) |
| POST | `/api/v1/health_values/{id}/flag` | `flagHealthValue()` | Flag a value (in HealthValueRow) |

### Project Structure Notes

- Component goes in `src/lib/components/health/DocumentDetailPanel.svelte` — consistent with existing health-domain components
- Test file: `src/lib/components/health/DocumentDetailPanel.test.ts`
- CSS additions in `src/app.css` at the end of the existing `.hc-doc-*` section (after line ~2455)
- No new files in `src/lib/api/` or `src/lib/types/` — all types and API functions already exist

### Previous Story Intelligence (Story 11-1)

Key learnings from Story 11-1 (Document List):
- **Updated 20+ test selectors** when moving from card grid to table — expect similar test updates when extracting the detail panel
- **Test baseline**: 433/434 pass (1 pre-existing failure in `users.test.ts` — ignore)
- **Deferred items from 11-1**: Values column (requires backend changes), arrow-key navigation, dedicated sort tests — none of these block 11-2
- **Code review findings applied**: Changed `aria-selected` to `aria-current="true"`, added sr-only labels, added guard for nested button events
- **The parent `+page.svelte` currently has BOTH the table list AND the detail panel inline** — after this story, the detail panel moves to a separate component but the parent still orchestrates queries/mutations/SSE

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Section 10: DocumentDetailPanel]
- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md — Section 8: Documents Cabinet]
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md — Epic 11 Story 2]
- [Source: _bmad-output/planning-artifacts/architecture.md — Frontend section]
- [Source: _bmad-output/planning-artifacts/prd.md — FR9, FR11, FR12, FR24, FR25]
- [Source: _bmad-output/implementation-artifacts/11-1-document-list-98css-file-explorer.md — Previous story learnings]

### Review Findings

- [x] [Review][Decision] **AC 6: Extracted values — refactored to `.hc-data-table` table rows** — Replaced HealthValueRow div cards with inline `<table>` using `.hc-data-table` pattern. Table columns: Name | Value+Unit | Confidence | Flag. Flag mutation logic moved inline.
- [x] [Review][Patch] **Unused `useQueryClient` import** — Now used for flag mutation cache invalidation.
- [x] [Review][Patch] **`statusBadge` default case added** — Both copies now have `default: return { symbol: '?', text: String(status), cssClass: '' }`.
- [x] [Review][Patch] **Slide-in animation added** — `.hc-detail-panel` now has `animation: hc-slide-in 200ms ease` with `translateX(100%)` keyframes.
- [x] [Review][Patch] **Delete button hover fixed** — `.hc-detail-delete-btn:hover` now only changes `color` to red, not background.
- [x] [Review][Patch] **`handleConfirmDelete` now calls `onClose`** — Panel closes immediately on confirm, before async mutation completes.
- [x] [Review][Patch] **Missing tests added** — Flag mutation, keep-partial callback, and table structure tests added to `DocumentDetailPanel.test.ts`.
- [x] [Review][Patch] **Focus trap added to confirmation dialog** — Tab key cycling between focusable buttons in alertdialog. Cancel button auto-focused on dialog open.
- [x] [Review][Defer] **SSE EventSource passes token as query param** — Pre-existing pattern; not introduced by this story. [+page.svelte:142]
- [x] [Review][Defer] **SSE auto-reconnect race condition** — EventSource auto-reconnects; pre-existing in SSE handler. [+page.svelte:155]
- [x] [Review][Defer] **HealthValueRow and PartialExtractionCard use Tailwind structural classes** — Pre-existing components reused as-is; restyling out of scope for this story. [HealthValueRow.svelte, PartialExtractionCard.svelte]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Extracted detail panel from `+page.svelte` into standalone `DocumentDetailPanel.svelte` component
- Component creates its own `detailQuery` via TanStack Query; mutations remain in parent and are passed as callback props
- Delete confirmation uses 98.css `<div class="window">` chrome with `role="alertdialog"` — replaces previous inline expand pattern
- Escape key behavior: dismisses confirm dialog first, panel second (layered)
- Status badges now use symbols (●, ◉, ⚠, ✕, ○) paired with text and color — never color-only
- Health values rendered using existing `HealthValueRow` component inside a sunken values list (not a `<table>`, since `HealthValueRow` renders as `<div>` cards)
- All CSS uses `.hc-detail-*` prefix in `app.css` — no scoped styles, no Tailwind structural classes
- Parent `+page.svelte` also updated to 98.css table layout (was still card grid); SSE and mutation logic preserved
- 30 new component tests + all 423 existing tests pass (453 total, 0 failures)
- `svelte-check` passes with 0 errors

### Change Log

- 2026-04-05: Story implementation complete — component extraction, 98.css reskin, tests

### File List

- `healthcabinet/frontend/src/lib/components/health/DocumentDetailPanel.svelte` (new)
- `healthcabinet/frontend/src/lib/components/health/DocumentDetailPanelTestWrapper.svelte` (new)
- `healthcabinet/frontend/src/lib/components/health/DocumentDetailPanel.test.ts` (new)
- `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` (modified)
- `healthcabinet/frontend/src/routes/(app)/documents/page.test.ts` (modified)
- `healthcabinet/frontend/src/app.css` (modified)
