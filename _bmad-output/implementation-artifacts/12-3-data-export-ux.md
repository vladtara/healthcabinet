# Story 12.3: Data Export UX

Status: done

## Story

As a registered user viewing my settings page,
I want the data export section to clearly explain what will be exported, show explicit progress status during generation, and provide trustworthy success/failure messaging,
so that exercising my GDPR Article 20 data portability right feels transparent and product-grade.

## Acceptance Criteria

1. **Redesign Data & Privacy fieldset into dedicated Export section** -- Rename the "Data & Privacy" fieldset legend to "Data Export" (privacy text moves here, consent history is already separate). The section communicates what the export includes before the user clicks.

2. **Export contents summary** -- Display a brief, scannable list of what the export ZIP contains: "Your export includes: uploaded documents, extracted health values, AI interpretations, admin corrections, consent history, and account summary." Use `.hc-export-contents` class. This sets delivery expectations before the user initiates.

3. **Export file format note** -- Below the contents summary: "Delivered as a ZIP file with CSV data files and original documents. Both machine-readable and human-readable." Use `.hc-export-format-note` (13px, `var(--text-secondary)`).

4. **Export button with status states** -- "Download My Data" button (`.btn-standard`). Four visual states:
   - **Idle**: "Download My Data" -- clickable
   - **Generating**: "Generating export..." -- disabled, shows processing indication
   - **Success**: Button reverts to idle. Success banner appears above button: `.hc-state .hc-state-success` with "Export downloaded successfully" and `role="status"`. Auto-hides after 3s.
   - **Error**: Button reverts to idle. Error banner appears: `.hc-state .hc-state-error` with specific error message and `role="alert"`. Persists until next action.

5. **Export timing expectation** -- Below the button, add helper text: "Export generation may take a few moments depending on your data volume." Use `.hc-export-timing-note` (13px, `var(--text-disabled)`).

6. **CSS follows established patterns** -- All new styles in `app.css` using `.hc-export-*` prefix. Reuse existing design tokens and `.hc-state-*` classes. No Tailwind. No inline styles. No scoped styles.

7. **Tests** -- Frontend: test export section renders with contents summary, format note, timing note; test button states (idle, generating, success, error); test success auto-hides after 3s; test error persists; axe accessibility audit passes.

8. **WCAG compliance** -- Fieldset has descriptive legend. Success/error banners have correct ARIA roles. Button has accessible disabled state. Axe audit passes.

## Tasks / Subtasks

- [x] Task 1: Add `.hc-export-*` CSS classes to `app.css` (AC: 6)
  - [x] `.hc-export-contents` -- contents summary list styling
  - [x] `.hc-export-format-note` -- format description (13px, secondary text)
  - [x] `.hc-export-timing-note` -- timing helper text (13px, disabled text)

- [x] Task 2: Redesign Data & Privacy fieldset in `+page.svelte` (AC: 1, 2, 3, 4, 5)
  - [x] Rename fieldset legend from "Data & Privacy" to "Data Export"
  - [x] Add export contents summary with `.hc-export-contents`
  - [x] Add format note with `.hc-export-format-note`
  - [x] Restructure success/error banners to use existing `.hc-state-*` pattern (already done from 12-1)
  - [x] Add timing note below button with `.hc-export-timing-note`
  - [x] Preserve all existing export handler logic unchanged

- [x] Task 3: Update tests (AC: 7)
  - [x] Test export fieldset has legend "Data Export"
  - [x] Test contents summary text renders
  - [x] Test format note renders
  - [x] Test timing note renders
  - [x] Test button idle state text and class (existing tests)
  - [x] Test generating state (existing tests)
  - [x] Test success banner appears and has role="status" (existing tests)
  - [x] Test error banner appears and has role="alert" (existing tests)
  - [x] Axe accessibility audit passes

- [x] Task 4: WCAG audit (AC: 8)
  - [x] Fieldset has `<legend>Data Export</legend>`
  - [x] Success banner has `role="status"`
  - [x] Error banner has `role="alert"`
  - [x] Button disabled state is accessible
  - [x] Axe audit passes

## Dev Notes

### Architecture & Patterns

- **Frontend-only story**: No backend changes. The export endpoint (`POST /api/v1/users/me/export`) and frontend `exportMyData()` function are already fully implemented and working.
- **Reskin and enhance**: The current Data & Privacy fieldset already has a working export button with success/error handling. This story enhances the UX with better information architecture -- not behavior changes.
- **Preserve existing export handler**: The `handleExport()` function, `exportMyData()` API call, `getExportErrorMessage()` helper, and all state variables (`exportLoading`, `exportSuccess`, `exportError`) are correct. Do NOT modify the `<script>` logic.

### Current Export Section (What to Enhance)

```svelte
<!-- CURRENT: Minimal GDPR text + button -->
<fieldset class="hc-fieldset">
  <legend>Data & Privacy</legend>
  <p class="hc-profile-gdpr-text">Under GDPR Article 20, you have the right to...</p>
  {#if exportSuccess}...success banner...{/if}
  {#if exportError}...error banner...{/if}
  <div class="hc-profile-export-row">
    <button class="btn-standard" ...>Download My Data</button>
  </div>
</fieldset>
```

```svelte
<!-- TARGET: Informative export section -->
<fieldset class="hc-fieldset">
  <legend>Data Export</legend>
  <p class="hc-profile-gdpr-text">Under GDPR Article 20, you have the right to...</p>
  <div class="hc-export-contents">
    <p>Your export includes: uploaded documents, extracted health values, AI interpretations,
       admin corrections, consent history, and account summary.</p>
  </div>
  <p class="hc-export-format-note">Delivered as a ZIP file with CSV data files and original
     documents. Both machine-readable and human-readable.</p>
  {#if exportSuccess}...success banner...{/if}
  {#if exportError}...error banner...{/if}
  <div class="hc-profile-export-row">
    <button class="btn-standard" ...>Download My Data</button>
  </div>
  <p class="hc-export-timing-note">Export generation may take a few moments depending on
     your data volume.</p>
</fieldset>
```

### CSS Classes to Add (app.css)

| Class | Purpose |
|-------|---------|
| `.hc-export-contents` | `font-size: 14px; color: var(--text-primary); line-height: 1.5; margin-bottom: 8px;` |
| `.hc-export-format-note` | `font-size: 13px; color: var(--text-secondary); line-height: 1.4; margin-bottom: 12px;` |
| `.hc-export-timing-note` | `font-size: 13px; color: var(--text-disabled); margin-top: 8px;` |

### Existing CSS Classes to Reuse

- `.hc-fieldset` + `legend` -- 98.css fieldset
- `.hc-profile-gdpr-text` -- GDPR description text (already styled)
- `.hc-profile-export-row` -- export button container (already styled)
- `.btn-standard` -- default 98.css gray button
- `.hc-state`, `.hc-state-success`, `.hc-state-error` -- feedback banners

### Backend API Contract (No Changes)

```
POST /api/v1/users/me/export
Authorization: Bearer <access_token>
Response: StreamingResponse (application/zip)
Filename: healthcabinet-export-{YYYY-MM-DD}.zip
```

ZIP contents: documents/, health_values.csv, ai_interpretations.csv, admin_corrections.csv, consent_log.csv, summary.txt

### Previous Story Learnings (Stories 12-1, 12-2)

- Use `.hc-*` CSS classes exclusively, no Tailwind, no inline styles
- Section-based CSS prefix naming (`.hc-export-*` for this story)
- Reuse design tokens: `--text-primary`, `--text-secondary`, `--text-disabled`
- Success/error banners use `.hc-state .hc-state-success`/`.hc-state-error` with `role="status"`/`role="alert"`
- Axe audit test required
- 508 frontend tests currently pass -- maintain zero regressions

### Files to Modify

| File | Changes |
|------|---------|
| `healthcabinet/frontend/src/app.css` | Add `.hc-export-*` classes (~3 new classes) |
| `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` | Enhance Data & Privacy fieldset (rename legend, add content summary/notes) |
| `healthcabinet/frontend/src/routes/(app)/settings/page.test.ts` | Add export section content tests |

### Project Structure Notes

- No backend changes -- export service and endpoint are fully implemented
- No new components -- enhance existing fieldset on settings page
- Minimal CSS additions -- 3 new classes only

### References

- [Source: _bmad-output/planning-artifacts/epics.md -- Story 6.1 Full Data Export acceptance criteria]
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md -- FE Epic 6 Story 3: data export UX]
- [Source: _bmad-output/planning-artifacts/prd.md -- FR5, FR32 export requirements]
- [Source: _bmad-output/implementation-artifacts/12-2-consent-history-timeline.md -- CSS patterns, learnings]
- [Source: healthcabinet/backend/app/users/export_service.py -- ZIP contents reference]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Renamed "Data & Privacy" fieldset to "Data Export"
- Added export contents summary listing all ZIP contents (documents, health values, AI interpretations, admin corrections, consent history, account summary)
- Added format note explaining ZIP delivery with CSV data files
- Added timing expectation note below export button
- 3 new `.hc-export-*` CSS classes in app.css
- All existing export behavior preserved unchanged (handleExport, exportMyData, error handling)
- 3 new tests for contents summary, format note, timing note
- Updated legend assertion from "Data & Privacy" to "Data Export"
- 511/511 tests pass, 0 regressions, 0 type errors

### Change Log

- 2026-04-05: Story implementation complete -- Data Export UX enhancement

### File List

- `healthcabinet/frontend/src/app.css` (modified -- added .hc-export-* CSS classes)
- `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` (modified -- enhanced Data Export fieldset)
- `healthcabinet/frontend/src/routes/(app)/settings/page.test.ts` (modified -- added 3 export content tests, updated legend assertion)
