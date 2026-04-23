# Story 11.4: Processing Pipeline 98.css Progress Bar

Status: done

## Story

As a user uploading a health document,
I want to see a 98.css-styled processing pipeline with named stages and a classic progress bar,
so that I can track extraction progress with the same retro-clinical aesthetic as the rest of the application.

## Acceptance Criteria

1. **98.css stage indicators** — Replace the current Tailwind-based stage rendering in `ProcessingPipeline.svelte` with `.hc-pipeline-*` CSS classes in `app.css`. Stage symbols per UX spec: `✅` done, `⏳` active (pulsing), `○` pending, `✕` error. Active stage gets bold text + accent color + warm background tint. Completed stages get muted text. Pending stages are gray/disabled. Error stage gets red text.

2. **98.css progress bar** — Add a native 98.css `<progress>` element below the stage list. The progress bar reflects processing completion: 0% at idle, 25% per completed stage (Upload=25%, Read=50%, Extract=75%, Generate=100%). Uses the `<progress>` HTML element which 98.css styles automatically with the classic Windows 98 raised/sunken bar appearance.

3. **Stage list in sunken panel** — Wrap the stage `<ol>` in a sunken panel (`.hc-dash-section` border pattern). The overall component container uses `.hc-pipeline-container` class with appropriate padding.

4. **Replace all Tailwind structural classes** — Remove `flex`, `gap-*`, `p-*`, `text-*`, `w-*`, `h-*`, `items-center`, etc. from the component template. All structural styling via `.hc-pipeline-*` CSS classes in `app.css`. Inline color classes (like `text-[#2E8B57]`) replaced with CSS custom property references.

5. **Preserve all SSE behavior** — The `$effect` block, `EventSource` lifecycle, `updateStage()`, `resetPipeline()`, stage tracking, error resilience (3-error threshold), and callback interface (`onComplete`, `onFailed`) must remain identical. Zero changes to the `<script>` logic except removing unused imports if any.

6. **CSS follows established patterns** — All new styles in `app.css` using `.hc-pipeline-*` prefix. Reuse `.hc-dash-section` sunken panel border pattern. No scoped `<style>` blocks. No Tailwind utility classes in the component template.

7. **Tests** — Update `ProcessingPipeline.test.ts` selectors for new markup structure. Preserve all 12 existing test cases. Add tests for:
   - Progress bar renders with correct `value`/`max` attributes
   - Progress bar updates as stages progress
   - Stage symbols match spec (✅, ⏳, ○, ✕)
   - Axe accessibility audit still passes

8. **WCAG compliance** — Container keeps `role="status"`. `aria-live="polite"` region preserved. Progress bar has `aria-valuenow`, `aria-valuemin`, `aria-valuemax` (native `<progress>` provides these). Stage status conveyed via accessible text, not just symbols.

## Tasks / Subtasks

- [x] Task 1: Replace Tailwind markup with CSS classes (AC: 1, 3, 4)
  - [x] Replace container with `.hc-pipeline-container` (sunken panel)
  - [x] Replace `<ol>` with `.hc-pipeline-stages`
  - [x] Replace stage `<li>` with `.hc-pipeline-stage` + `.hc-pipeline-stage-{status}`
  - [x] Replace symbol container with `.hc-pipeline-symbol`
  - [x] Replace label with `.hc-pipeline-label`
  - [x] Updated symbols: `✓` → `✅`, spinner → `⏳`, `·` → `○`, `!` → `✕`

- [x] Task 2: Add 98.css progress bar (AC: 2)
  - [x] Added `<progress>` element after stage list
  - [x] `progressValue` derived from `stages.filter(done).length * 25`
  - [x] `.hc-pipeline-progress` CSS class for full-width layout
  - [x] 98.css styles `<progress>` automatically

- [x] Task 3: Wrap in sunken panel (AC: 3)
  - [x] `.hc-pipeline-container` has sunken panel border pattern

- [x] Task 4: Add CSS classes (AC: 6)
  - [x] All 10 `.hc-pipeline-*` classes added to `app.css`

- [x] Task 5: Update tests (AC: 7)
  - [x] Selectors updated (`.stage-done` → `.hc-pipeline-stage-done`, etc.)
  - [x] Progress bar tests: value/max, stage progression, clamping
  - [x] Symbol tests: ✅/⏳/○/✕ verified per state
  - [x] Sunken panel container class verified
  - [x] Axe audit passes
  - [x] All 12 existing tests preserved + 4 new = 16 total

- [x] Task 6: WCAG audit (AC: 8)
  - [x] `role="status"` preserved
  - [x] `aria-live="polite"` preserved
  - [x] `<progress>` provides native ARIA
  - [x] Axe audit passes

## Dev Notes

### Architecture & Patterns

- **Reskin only — zero script changes**: The `<script>` block has working SSE logic, state machine, error resilience, and callbacks. Only the template markup and CSS classes change. Do NOT modify the script.
- **98.css `<progress>` element**: 98.css automatically styles `<progress>` elements with the classic Windows 98 progress bar appearance. Just use `<progress value={n} max="100"></progress>` — no custom CSS needed for the bar itself.
- **Symbol changes**: Current symbols (`✓`, spinner div, `·`, `!`) change to UX spec symbols (`✅`, `⏳`, `○`, `✕`). The spinner `<span>` with Tailwind `animate-spin` is replaced by the `⏳` emoji.

### Existing Code to Preserve (Script Block)

| What | Lines | Notes |
|------|-------|-------|
| STAGE_ORDER | 27-33 | 5 stages with id + label |
| TERMINAL_EVENTS | 35 | completed, failed, partial |
| createInitialStages() | 37-39 | Factory for stage array |
| State variables | 41-56 | currentStage, stages, statusAnnouncement, consecutiveErrors, lastProgressedIdx |
| updateStage() | 58-85 | SSE event → stage state update |
| $effect SSE block | 87-135 | EventSource lifecycle, error handling, callbacks |

### Current Markup → New Markup

| Current (Tailwind) | New (CSS classes) |
|--------------------|-------------------|
| `class="flex flex-col gap-4 p-6"` | `class="hc-pipeline-container"` |
| `class="flex flex-col gap-3 list-none m-0 p-0"` | `class="hc-pipeline-stages"` |
| `class="stage-item stage-{status} flex items-center gap-3 text-sm"` | `class="hc-pipeline-stage hc-pipeline-stage-{stage.status}"` |
| `class="w-6 h-6 flex items-center justify-center font-semibold"` | `class="hc-pipeline-symbol"` |
| Inline color classes on label | `class="hc-pipeline-label"` |
| Spinner `<span>` with `animate-spin` | `⏳` emoji |
| `✓` text | `✅` emoji |
| `·` text | `○` text |
| `!` text | `✕` text |

### Progress Value Calculation

```typescript
// Derived from stages state
const progressValue = $derived(
  stages.filter(s => s.status === 'done').length * 25
);
// Or: map stage index to percentage
// Upload done = 25, Read done = 50, Extract done = 75, Generate done = 100
```

### CSS Classes to Add

| Class | CSS |
|-------|-----|
| `.hc-pipeline-container` | Sunken panel border, padding: 16px |
| `.hc-pipeline-stages` | `list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px;` |
| `.hc-pipeline-stage` | `display: flex; align-items: center; gap: 10px; font-size: 14px;` |
| `.hc-pipeline-stage-done .hc-pipeline-label` | `color: var(--color-status-optimal);` |
| `.hc-pipeline-stage-active` | `font-weight: 700; color: var(--accent); background: rgba(51, 102, 255, 0.05); padding: 4px 8px; border-radius: 0;` |
| `.hc-pipeline-stage-pending .hc-pipeline-label` | `color: var(--text-disabled);` |
| `.hc-pipeline-stage-error .hc-pipeline-label` | `color: var(--color-status-action);` |
| `.hc-pipeline-symbol` | `width: 24px; text-align: center; font-size: 16px; flex-shrink: 0;` |
| `.hc-pipeline-progress` | `width: 100%; margin-top: 12px;` |

### Previous Story Learnings

From stories 11-2 and 11-3:
- Use `.hc-*` CSS classes exclusively — no Tailwind structural classes
- Add `default` case to any switch statements
- Axe audit test required: `const results = await axe.run(container); expect(results.violations).toHaveLength(0);`
- `role="region"` for non-modal containers (not `role="dialog"`)
- Update test selectors as needed but preserve existing test coverage

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Section 8: ImportDialog pipeline states]
- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md — Processing state wireframe]
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md — Epic 11 Story 4]
- [Source: _bmad-output/planning-artifacts/prd.md — FR23]
- [Source: _bmad-output/implementation-artifacts/11-3-import-dialog-98css-window-chrome.md — Previous story]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Replaced all Tailwind structural classes with `.hc-pipeline-*` CSS classes
- Stage symbols updated to UX spec: ✅ done, ⏳ active, ○ pending, ✕ error
- Added native `<progress>` element — 98.css provides classic Windows 98 progress bar styling
- Progress value derived: `stages.filter(done).length * 25` (clamped by `<progress max="100">`)
- Container uses sunken panel border pattern (`.hc-pipeline-container`)
- Active stage gets bold text + accent color + warm background tint
- Zero script changes — all SSE logic, state machine, callbacks preserved
- 16 tests (12 preserved + 4 new), 468 total suite, 0 failures
- `svelte-check` 0 errors

### Change Log

- 2026-04-05: Story implementation complete — 98.css reskin, progress bar, CSS classes

### File List

- `healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.svelte` (modified)
- `healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.test.ts` (modified)
- `healthcabinet/frontend/src/app.css` (modified)
