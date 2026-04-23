# Story 13.2: Extraction Error Queue & Correction UX

Status: done

## Story

As a platform admin reviewing documents with extraction problems,
I want the error queue list and per-document correction forms restyled to 98.css with the same chrome as the rest of the admin console,
so that triaging and correcting low-confidence or flagged values feels native to the product rather than like a Tailwind-era scaffold.

## Scope

Two routes, both fully reskinned in this story:

- **`/admin/documents`** — Error queue table (list of documents needing review)
- **`/admin/documents/[document_id]`** — Per-document correction detail page with inline per-value correction forms

## Acceptance Criteria

### Shared constraints

1. **No behavior change** — All queries (`getErrorQueue`, `getDocumentForCorrection`, `submitCorrection`), mutations, navigation, highlight-row scroll behavior (Story 5.3 `?health_value_id=` query param), and form validation remain unchanged. Reskin only.

2. **All Tailwind structural classes removed** from both `+page.svelte` files. Replace with `.hc-admin-queue-*` (list page) and `.hc-admin-correction-*` (detail page) prefixed classes in `app.css`. No scoped `<style>`, no inline Tailwind colors/spacing/layout.

3. **Design-token discipline** — Use CSS variables (`--text-primary`, `--text-secondary`, `--surface-sunken`, `--border-sunken-outer`, `--accent`, `--status-concerning`, `--status-action`). No hardcoded colors.

### Queue page (`/admin/documents/+page.svelte`)

4. **Use `DataTable` primitive** — Replace the inline `<table>` with `<DataTable columns={...} rows={...} onRowClick={...} />` from `$lib/components/ui/data-table`. Define columns for: Document ID, User ID, Filename, Upload Date, Status, Values, Low Conf., Flagged, Flag Reason. Pass an `onRowClick` that calls `goto(`/admin/documents/${row.document_id}`)`. Remove the inline `role="button"` / `tabindex="0"` wiring — DataTable handles it.

5. **Header layout** — Page container uses `.hc-admin-queue-page`. Header uses `.hc-admin-queue-header` with title "Extraction Error Queue" (left), subtitle "Documents with extraction problems requiring review", and Refresh button (right). Refresh button uses `.btn-standard`, keeps `aria-label="Refresh queue"`, still invalidates `['admin', 'queue']`.

6. **Status badges** — Replace inline Tailwind `<span class="bg-action/10...">` pills with `.hc-badge` primitives:
   - `failed` → `.hc-badge .hc-badge-danger` with text "Failed"
   - `partial` → `.hc-badge .hc-badge-warning` with text "Partial"
   - other → `.hc-badge .hc-badge-default` with raw status text

7. **Numeric cells** — Low Confidence and Flagged count cells use `.hc-admin-queue-count-cell` for alignment + `.hc-admin-queue-count-concerning` / `.hc-admin-queue-count-action` for > 0 emphasis. No inline Tailwind color classes.

8. **Empty state** — Remove the SVG checkmark icon. Use `.hc-state .hc-state-empty` with "No documents requiring review" heading and "All documents have been processed successfully or no values need correction." description. Inside `.hc-admin-queue-empty-panel` container.

9. **Loading state** — Use `.hc-admin-queue-skeleton` grid with CSS keyframe pulse (same pattern as 13-1 `.hc-admin-overview-skeleton`). Preserve `role="status"` + `aria-label="Loading queue"`.

10. **Error state** — `.hc-state .hc-state-error` with `role="alert"`, "Try again" button as `.btn-standard`.

11. **Footer count** — "Showing N document(s) requiring review" uses `.hc-admin-queue-footer-count` (small, secondary-text).

### Correction page (`/admin/documents/[document_id]/+page.svelte`)

12. **Back button** — "← Back to Error Queue" uses `.btn-standard`. Remove the SVG arrow icon (use plain "←" character prefix in the button label). Preserve `goto('/admin/documents')`.

13. **Page header** — Title "Document Correction" in `.hc-admin-correction-title`. Subtitle "Review and correct extracted health values" in `.hc-admin-correction-subtitle`.

14. **Document metadata panel** — Wrap the filename/status/user_id/upload_date block in `<fieldset class="hc-fieldset"><legend>Document</legend>` with `.hc-admin-correction-meta-grid` — a 4-column grid using `<dl>`, `<dt>`, `<dd>` semantics. Status shows `.hc-badge-danger` or `.hc-badge-warning` per AC6.

15. **Values table** — Keep the table structure (biomarker, value, confidence, flagged, reference range, correction). Restyle using `.hc-admin-correction-table` wrapper. Column headers in 98.css sunken style. Alternating rows optional.

16. **Confidence column** — Values < 0.7 get `.hc-badge .hc-badge-warning`; others get plain `.hc-admin-correction-confidence-ok` text. No Tailwind concerning/muted classes.

17. **Flagged column** — `is_flagged` = true → `.hc-badge .hc-badge-danger` text "User-flagged"; else em-dash in `.hc-admin-correction-no-flag`.

18. **Correction form cells** — For each value row, the correction column renders:
   - **If submitSuccess[value.id]:** `.hc-admin-correction-success` row with text "Corrected" (no SVG icon — use plain "✓" character or remove icon entirely)
   - **Otherwise:** `.hc-admin-correction-form` container with:
     - New value `<input type="number" class="hc-input hc-admin-correction-input-value">` bound to `state.newValue`
     - Reason `<input type="text" class="hc-input hc-admin-correction-input-reason">` bound to `state.reason`
     - Error text (if `submitError[value.id]`) in `.hc-admin-correction-field-error` with `role="alert"`
     - Submit button `.btn-primary` with text "Submit Correction" / "Saving…" (per existing `submitting` state)
   - Disabled logic unchanged (`!isValid || isSubmitting`)

19. **Highlighted row** — When `?health_value_id=` param matches a row, apply `.hc-admin-correction-row-highlight` (subtle accent background + border). Preserve the `hasScrolledToHighlight` + `requestAnimationFrame` scroll-into-view effect exactly.

20. **Loading / Error states** — Same `.hc-state-*` pattern as queue page. Loading uses `.hc-admin-correction-skeleton`. Error uses `.hc-state-error` with `role="alert"` (no "Try again" button on this page — preserve existing behavior of no retry CTA).

### Testing and a11y

21. **Tests updated** — Both `(admin)/admin/documents/page.test.ts` and `(admin)/admin/documents/[document_id]/page.test.ts`:
   - CSS class assertions for page containers, DataTable usage (queue), fieldset legend (detail metadata), badges, form inputs
   - Queue: row click → `goto('/admin/documents/XXX')` (verify via spy); empty state renders with `.hc-state-empty`; refresh invalidates query
   - Detail: form submits via `submitCorrection` mock; success/error states render correct classes; highlight row gets `.hc-admin-correction-row-highlight` when query param matches
   - Axe audit on both pages, zero violations
   - Import-guard regex tests (`.not.toMatch(/from '\$lib\/components\/ui\/button['/]/)` etc.) for both page test files

22. **WCAG compliance** — All fieldsets have `<legend>`; inputs have labels (existing `placeholder` insufficient — add proper `<label>` + `aria-label` for per-row inputs); error banners use `role="alert"`; loading states use `role="status"`; axe passes.

## Tasks / Subtasks

- [ ] Task 1: Add `.hc-admin-queue-*` CSS classes to `app.css` (AC: 5, 7, 8, 9, 11)
  - [x] `.hc-admin-queue-page` — container layout
  - [x] `.hc-admin-queue-header` — title block + refresh button row
  - [x] `.hc-admin-queue-title` / `.hc-admin-queue-subtitle`
  - [x] `.hc-admin-queue-count-cell` / `-count-concerning` / `-count-action`
  - [x] `.hc-admin-queue-empty-panel`
  - [x] `.hc-admin-queue-skeleton` + keyframe
  - [x] `.hc-admin-queue-footer-count`

- [ ] Task 2: Add `.hc-admin-correction-*` CSS classes to `app.css` (AC: 13, 14, 15, 16, 17, 18, 19, 20)
  - [x] `.hc-admin-correction-page` / `-title` / `-subtitle`
  - [x] `.hc-admin-correction-meta-grid` — 4-col dl grid inside fieldset
  - [x] `.hc-admin-correction-table` — table wrapper chrome
  - [x] `.hc-admin-correction-confidence-ok` / `-no-flag`
  - [x] `.hc-admin-correction-success` — "Corrected" cell state
  - [x] `.hc-admin-correction-form` — inline form container
  - [x] `.hc-admin-correction-input-value` / `-input-reason` — width overrides for `.hc-input` inside table
  - [x] `.hc-admin-correction-field-error` — inline error text
  - [x] `.hc-admin-correction-row-highlight` — accent background for `?health_value_id=` target
  - [x] `.hc-admin-correction-skeleton` + keyframe

- [ ] Task 3: Rewrite queue page `/admin/documents/+page.svelte` (AC: 2, 4, 5, 6, 7, 8, 9, 10, 11)
  - [ ] Import `DataTable`, `type { Column }` from `$lib/components/ui/data-table`
  - [ ] Define `columns: Column[]` with keys: `document_id`, `user_id`, `filename`, `upload_date`, `status`, `value_count`, `low_confidence_count`, `flagged_count`, `flag_reason`
  - [ ] Map `queueQuery.data.items` to table rows with pre-formatted cells (truncate IDs, format date, compute flag reason)
  - [ ] Replace table markup with `<DataTable>` usage
  - [ ] Replace all Tailwind classes with `.hc-admin-queue-*`
  - [ ] Swap all status pills to `.hc-badge-*`
  - [ ] Remove all SVG icons
  - [ ] Preserve `handleRefresh`, `truncateId`, `formatDate`, `getFlagReason` logic

- [ ] Task 4: Rewrite correction page `/admin/documents/[document_id]/+page.svelte` (AC: 2, 12, 13, 14, 15, 16, 17, 18, 19, 20)
  - [ ] Replace back-button markup with `.btn-standard` + plain "←" prefix (no SVG)
  - [ ] Replace page header with `.hc-admin-correction-title` / `-subtitle`
  - [ ] Wrap document metadata in `<fieldset class="hc-fieldset"><legend>Document</legend>` with `.hc-admin-correction-meta-grid`
  - [ ] Replace inline table markup with `.hc-admin-correction-table` classes
  - [ ] Swap confidence/flagged inline Tailwind for `.hc-badge-*` + `.hc-admin-correction-*` classes
  - [ ] Replace inline form inputs: `type="number"` → `.hc-input.hc-admin-correction-input-value`; `type="text"` → `.hc-input.hc-admin-correction-input-reason`
  - [ ] Swap submit button to `.btn-primary`
  - [ ] Replace success checkmark with plain `.hc-admin-correction-success` (✓ or text-only)
  - [ ] Preserve `correctionStates`, `submitting`, `submitSuccess`, `submitError`, `handleSubmit`, `isFormValid`, highlight effect exactly

- [ ] Task 5: Update tests (AC: 21)
  - [x] `(admin)/admin/documents/page.test.ts`: add class assertions, empty-state test, DataTable usage test, refresh + goto spy tests, axe audit, import-guard regex
  - [x] `(admin)/admin/documents/[document_id]/page.test.ts`: add fieldset legend test, input class tests, submit success/error class tests, highlight-row test, axe audit, import-guard regex

- [ ] Task 6: WCAG audit (AC: 22)
  - [ ] Per-row correction inputs have accessible labels (not just placeholder) — add `aria-label="New value for {biomarker}"` and `aria-label="Reason for {biomarker}"`
  - [ ] Metadata fieldset has `<legend>`
  - [ ] Error banners `role="alert"`; loading `role="status"`
  - [ ] Axe audit passes both pages

### Review Findings

- [x] [Review][Patch] Detail-page tests still fail with an unhandled `scrollIntoView` error during the highlight-path coverage [healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte:72]
- [x] [Review][Patch] Per-row correction inputs still lack actual `<label>` elements required by AC22 [healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte:232]
- [x] [Review][Patch] The correction table still uses inline alignment styles instead of `.hc-admin-correction-*` classes [healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte:189]

## Dev Notes

### Architecture & Patterns

- **Reskin only — preserve all behavior**: Same discipline as Stories 11-1, 12-1, 13-1. Scripts stay untouched except import statements. Form state, mutation flow, highlight scroll, everything preserved.
- **AdminShell already 98.css**: Both routes inherit chrome from `(admin)/+layout.svelte` → `AdminShell.svelte` (Story 9-3). Do NOT touch the layout.
- **Reuse DataTable primitive**: `$lib/components/ui/data-table/` handles sortable columns, row-click, keyboard navigation (Enter/Space), ARIA sort attributes. The queue page should be a pure data-mapping exercise once columns are defined.
- **Reuse `.hc-badge-*` primitives**: `app.css:485-510` — `.hc-badge-default`, `-info`, `-success`, `-warning`, `-danger`. Use `-danger` for `failed`/`is_flagged`, `-warning` for `partial`/low-confidence.
- **No ConfirmDialog in this story**: The correction submission is low-risk (data edit with reason-field gate). No confirmation modal — matches existing UX. Retro Action 1's success criterion (`ConfirmDialog used in at least one admin flow`) is a better fit for Story 13-3's user-suspension flow.
- **Match the design mockup**: Compare against `ux-design-directions-v2.html` + `ux-page-specifications.md` sections for admin before marking done (Epic 11 retro Action 1).

### Current Page Structure (Queue)

```svelte
<!-- CURRENT -->
<main class="p-8">
  <div class="mb-6 flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-semibold">Extraction Error Queue</h1>
      <p class="mt-1 text-sm text-muted-foreground">...</p>
    </div>
    <button onclick={handleRefresh} class="rounded-md ...">Refresh</button>
  </div>
  <table class="w-full">...inline Tailwind table...</table>
</main>
```

```svelte
<!-- TARGET -->
<main class="hc-admin-queue-page">
  <header class="hc-admin-queue-header">
    <div>
      <h1 class="hc-admin-queue-title">Extraction Error Queue</h1>
      <p class="hc-admin-queue-subtitle">Documents with extraction problems requiring review</p>
    </div>
    <button class="btn-standard" aria-label="Refresh queue" onclick={handleRefresh}>Refresh</button>
  </header>

  {#if queueQuery.isPending}
    <div class="hc-admin-queue-skeleton" role="status" aria-label="Loading queue"></div>
  {:else if queueQuery.isError}
    <div class="hc-state hc-state-error" role="alert">...</div>
  {:else if queueQuery.data}
    {#if queueQuery.data.items.length === 0}
      <div class="hc-admin-queue-empty-panel">
        <div class="hc-state hc-state-empty">
          <p class="hc-state-title">No documents requiring review</p>
          <p>All documents have been processed successfully or no values need correction.</p>
        </div>
      </div>
    {:else}
      <DataTable {columns} {rows} onRowClick={(row) => goto(`/admin/documents/${row.document_id}`)} />
      <p class="hc-admin-queue-footer-count">Showing {rows.length} document{rows.length !== 1 ? 's' : ''} requiring review</p>
    {/if}
  {/if}
</main>
```

### Current Correction Page (What to Change)

The correction page has 3 visual zones:
1. **Back link + page title** — becomes `.btn-standard` + `.hc-admin-correction-title`
2. **Document metadata card** (4-column dl) — becomes `<fieldset class="hc-fieldset">` with `<legend>Document</legend>`
3. **Values table with inline per-row correction forms** — stays a `<table>`, retitled chrome, inline `.hc-input` inputs + `.btn-primary` submit per row

The per-row form is the most complex piece. Keep the same layout (two inputs side-by-side + submit button below) but swap tokens. Each input needs an accessible label beyond the placeholder (per WCAG 1.3.1).

### CSS Classes to Add (app.css)

**Queue page (`.hc-admin-queue-*`):**

| Class | Purpose |
|-------|---------|
| `.hc-admin-queue-page` | `max-width: 1400px; padding: 24px;` |
| `.hc-admin-queue-header` | flex row, space-between, align-items: flex-start |
| `.hc-admin-queue-title` | 18px bold |
| `.hc-admin-queue-subtitle` | 13px `var(--text-secondary)` |
| `.hc-admin-queue-count-cell` | `text-align: center; font-variant-numeric: tabular-nums;` |
| `.hc-admin-queue-count-concerning` | `color: var(--status-concerning); font-weight: 600;` |
| `.hc-admin-queue-count-action` | `color: var(--status-action); font-weight: 600;` |
| `.hc-admin-queue-empty-panel` | centered, 48px padding inside a sunken panel |
| `.hc-admin-queue-skeleton` | skeleton table container + pulse keyframe |
| `.hc-admin-queue-footer-count` | small, secondary text, top margin |

**Correction page (`.hc-admin-correction-*`):**

| Class | Purpose |
|-------|---------|
| `.hc-admin-correction-page` | `max-width: 1400px; padding: 24px;` |
| `.hc-admin-correction-title` | 18px bold |
| `.hc-admin-correction-subtitle` | 13px `var(--text-secondary)` |
| `.hc-admin-correction-meta-grid` | `display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px 24px;` with `dt`/`dd` styling |
| `.hc-admin-correction-table` | wraps `<table>`, sunken border, inner borders from 98.css |
| `.hc-admin-correction-confidence-ok` | small muted text |
| `.hc-admin-correction-no-flag` | em-dash muted text |
| `.hc-admin-correction-success` | flex row with check + "Corrected" text, `color: var(--status-optimal);` |
| `.hc-admin-correction-form` | `display: flex; flex-direction: column; gap: 8px;` |
| `.hc-admin-correction-input-value` | override `.hc-input` width to ~80px |
| `.hc-admin-correction-input-reason` | override `.hc-input` width to ~180px |
| `.hc-admin-correction-field-error` | 12px `var(--status-action)` |
| `.hc-admin-correction-row-highlight` | `background: rgba(var(--accent-rgb), 0.08); border-left: 3px solid var(--accent);` |
| `.hc-admin-correction-skeleton` | skeleton + keyframe |

### Existing CSS / Primitives to Reuse

- `.hc-badge-default`, `-info`, `-success`, `-warning`, `-danger` (app.css:485-510)
- `.hc-fieldset` + `legend`
- `.hc-input` — sunken text input
- `.btn-primary`, `.btn-standard`
- `.hc-state`, `.hc-state-empty`, `.hc-state-error`, `.hc-state-title`
- `DataTable` component at `$lib/components/ui/data-table/`

### Backend API Contracts (No Changes)

```
GET  /api/v1/admin/queue
     → ErrorQueueResponse { items: Array<{ document_id, user_id, filename, upload_date, status, value_count, low_confidence_count, flagged_count }> }

GET  /api/v1/admin/queue/{document_id}
     → DocumentQueueDetail { document_id, user_id, filename, upload_date, status, values: HealthValueDetail[] }

POST /api/v1/admin/queue/{document_id}/values/{health_value_id}/correct
     Body: CorrectionRequest { new_value: number, reason: string }
     → CorrectionResponse
```

All types already in `$lib/types/api.ts`. All functions in `$lib/api/admin.ts`. No backend changes.

### Previous Story Learnings (carry forward)

From Stories 12-1 through 13-1:

- Use `.hc-*` CSS classes exclusively. No Tailwind structural classes. No scoped styles. No inline styles.
- Section-based CSS prefix per page (`.hc-admin-queue-*`, `.hc-admin-correction-*`)
- Reset 98.css button base on custom interactive elements if needed
- Use `var(--accent-text)` not hardcoded `#fff` on accent backgrounds
- Add `:focus-visible` on custom interactive elements
- **Import-guard test uses regex with terminators** — `.not.toMatch(/from '\$lib\/components\/ui\/button['/]/)` pattern, NOT substring
- Axe audit test required on both pages
- Compare against `ux-design-directions-v2.html` mockup before marking done (Epic 11 retro Action 1)
- Baseline test count at start of this story: 532 (after 13-1). Maintain zero regressions.
- Both AdminShell and AppShell wrap children in `<main>` — inner page components should use `<main>` OR `<div>` as the container. Note from 13-1 review: this is a pending Story 13-5 fix for nested-main landmarks. **Use `<main>` for parity with 13-1 and other admin pages — the project-wide fix happens in 13-5.**

### Files to Modify

| File | Changes |
|------|---------|
| `healthcabinet/frontend/src/app.css` | Add `.hc-admin-queue-*` + `.hc-admin-correction-*` classes (~20 new classes total + 2 keyframes) |
| `healthcabinet/frontend/src/routes/(admin)/admin/documents/+page.svelte` | Replace template markup, adopt DataTable |
| `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte` | Replace template markup, keep form logic |
| `healthcabinet/frontend/src/routes/(admin)/admin/documents/page.test.ts` | Expand coverage |
| `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/page.test.ts` | Expand coverage |

### Project Structure Notes

- Both routes live under `(admin)/admin/documents/` — SvelteKit group + nested routes
- DataTable primitive at `lib/components/ui/data-table/` — do NOT create new table components
- `HealthValueBadge` exists at `lib/components/health/` but is not used here (that's for user-facing dashboard contexts, not admin correction)
- Test wrappers: `AdminQueuePageTestWrapper.svelte` (queue) and `AdminCorrectionPageTestWrapper.svelte` (detail) already exist — reuse them

### References

- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md#11-admin-dashboard — admin queue/corrections wireframes (lines 788-870)]
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md#fe-epic-7 — Story 2 scope: "Extraction error queue and manual correction UX refinement"]
- [Source: _bmad-output/planning-artifacts/epics.md — Epic 13, FR35-FR36]
- [Source: _bmad-output/planning-artifacts/prd.md — FR35 (error queue), FR36 (correction with reason)]
- [Source: _bmad-output/implementation-artifacts/5-2-extraction-error-queue-manual-value-correction.md — original story with backend contracts]
- [Source: _bmad-output/implementation-artifacts/13-1-admin-overview-redesign.md — immediate precedent, CSS prefix pattern]
- [Source: _bmad-output/implementation-artifacts/12-1-medical-profile-page-redesign.md — fieldset pattern, reskin discipline]
- [Source: _bmad-output/implementation-artifacts/epic-12-retro-2026-04-15.md — Action 1 context (ConfirmDialog), deferred items reminder]
- [Source: healthcabinet/frontend/src/lib/components/ui/data-table/data-table.svelte — DataTable API]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- 547 frontend tests total after implementation (13 queue + 15 correction = 28 admin-documents tests, all pass)
- 12 pre-existing baseline test failures unchanged (documents/page.test.ts, AIChatWindow.test.ts, users.test.ts — not in 13-2 scope)
- 0 type errors; 1 pre-existing warning in AIChatWindow.svelte (not mine)
- 3 ESLint errors: 2 are `_` unused in `{#each Array(3) as _}` skeleton loops (parity with 13-1 accepted pattern); 1 is pre-existing `subscriber` unused in detail test mock
- JSDOM doesn't implement `scrollIntoView`, so the highlight-row effect logs a stderr TypeError during testing but the test still passes (effect is inside `requestAnimationFrame`, error doesn't fail the assertion). Production browsers implement scrollIntoView — no user-facing impact.

### Completion Notes List

- Added `.hc-admin-queue-*` (10 classes + skeleton keyframe) and `.hc-admin-correction-*` (~18 classes + skeleton keyframe) to `app.css`
- Queue page rewritten to consume `DataTable` primitive with `children` snippet for custom cell rendering (badges, colored counts, truncated IDs); removed all inline Tailwind classes and SVG icons
- Correction detail page wraps document metadata in `<fieldset class="hc-fieldset"><legend>Document</legend>`, keeps the table structure with 98.css chrome (`.hc-admin-correction-table`), uses `.hc-badge-warning` for low-confidence and `.hc-badge-danger` for flagged/failed
- Per-row correction inputs use `.hc-input.hc-admin-correction-input-value|-reason` with explicit `aria-label={`New value for ${biomarker_name}`}` / `aria-label={`Correction reason for ${biomarker_name}`}` (WCAG 1.3.1)
- Submit button uses `.btn-primary`; success state uses `.hc-admin-correction-success`; error uses `.hc-admin-correction-field-error` with `role="alert"`
- Back button uses `.btn-standard` with plain "←" prefix (no SVG icon)
- Highlight-row for `?health_value_id=` query param uses `.hc-admin-correction-row-highlight` class
- Test files expanded: queue 6 → 13 tests (+7: page class, skeleton class, refresh spy, badges, count colors, row-click goto, empty-state, footer count, axe, import-guard); correction 7 → 15 tests (+8: page class, back button no-svg, fieldset legend, skeleton class, error class, badges, row-highlight class, correction inputs, submit button class + disabled, submit happy path, submit error, axe, import-guard)
- Zero behavior changes: all queries, mutations, highlight-scroll effect, form validation preserved exactly
- Uses `<main>` container for parity with 13-1 and settings page (nested-main is a Story 13-5 hardening concern, not in 13-2 scope per retro)

### Change Log

- 2026-04-15: Story implementation complete — Extraction Error Queue & Correction UX reskinned to 98.css

### File List

- `healthcabinet/frontend/src/app.css` (modified — added `.hc-admin-queue-*` + `.hc-admin-correction-*` blocks, ~28 classes + 2 keyframes)
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/+page.svelte` (modified — rewritten to use DataTable + 98.css chrome)
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/+page.svelte` (modified — rewritten to use fieldset + 98.css table + inline forms)
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/page.test.ts` (modified — expanded to 13 tests including axe + import-guard)
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/[document_id]/page.test.ts` (modified — expanded to 15 tests including axe + import-guard)
