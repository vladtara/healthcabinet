# Story 12.1: Medical Profile Page Redesign

Status: done

## Story

As a registered user viewing my medical profile at `/settings`,
I want the page restyled with 98.css fieldsets, sunken panels, and design system tokens matching the rest of the app,
so that settings feels like an integrated part of the clinical workstation rather than a leftover utility form.

## Acceptance Criteria

1. **Replace all Tailwind structural classes with `.hc-profile-*` CSS classes** -- Remove every Tailwind utility class from `+page.svelte`. Replace with `.hc-profile-*` prefixed classes defined in `app.css`. No scoped `<style>` blocks. No inline Tailwind colors, spacing, or layout classes.

2. **Replace shadcn-svelte component imports with native HTML + 98.css classes** -- Remove imports of `Button`, `Input`, `Label`, `Textarea` from `$lib/components/ui/*`. Use native `<input>`, `<label>`, `<textarea>`, `<button>` elements styled with existing `.hc-input`, `.hc-label`, `.hc-textarea`, `.hc-button`, `.btn-primary`, `.btn-standard` classes. The page must not import any `$lib/components/ui/` modules.

3. **98.css fieldset grouping** -- Wrap each section (Basic Info, Health Conditions, Family History, Data & Privacy) in a `<fieldset class="hc-fieldset">` with `<legend>` in accent color and bold text. Legends: "Basic Information", "Health Conditions", "Family History", "Data & Privacy". Use existing `.hc-fieldset` class from `app.css`.

4. **Page layout** -- Page container uses `.hc-profile-page` class: `max-width: 640px`, centered, padding 24px. Page heading "Medical Profile" uses `.hc-profile-title` (18px, bold, `var(--text-primary)`, margin-bottom 16px). Sections have 16px gap between fieldsets.

5. **Basic Information section** -- Age and Sex fields on one conceptual level. Height and Weight fields below. All `<input type="number">` use `.hc-input` class. Labels use `.hc-label` class. Sex radio group uses `.hc-radio-group .hc-radio-group-horizontal` existing classes with standard `<input type="radio">` elements. Field errors render as `<p class="hc-profile-field-error" role="alert">` below the field with `font-size: 13px; color: var(--color-status-action)`.

6. **Health Conditions section** -- Condition toggle buttons use `.hc-profile-condition-chip` class: rectangular (no rounded corners), border `1px solid var(--border-sunken-outer)`, padding `4px 10px`, font-size 14px. Selected state: `.hc-profile-condition-chip-active` with `background: var(--accent); color: #fff; border-color: var(--accent)`. "Other condition" input uses `.hc-input` + `.hc-button .btn-standard` Add button. Custom condition removal chips show `condition + " x"` with `.hc-profile-condition-chip-active`. Medications input: `<input class="hc-input">` with `.hc-label`.

7. **Family History section** -- `<textarea class="hc-textarea">` with `.hc-label`. Character counter: `.hc-profile-char-count` (font-size 13px, `var(--text-secondary)`, text-align right).

8. **Save Profile button** -- `.btn-primary` (accent blue bg, white text, outset border). Full-width or right-aligned below all fieldsets. Disabled + "Saving..." text when mutation pending. Sits between the Family History fieldset and the Data & Privacy fieldset.

9. **Data & Privacy section** -- GDPR description text in `var(--text-secondary)`, font-size 14px. "Download My Data" button uses `.btn-standard`. Export loading state: "Generating export..." + disabled.

10. **Success and error feedback** -- Profile save success: `.hc-state .hc-state-success` banner above form, role="status", auto-hides 3s. Profile save error: `.hc-state .hc-state-error` banner above form, role="alert", persists. Export success/error: same pattern inside Data & Privacy fieldset. No inline Tailwind colors for feedback -- use design system state classes exclusively.

11. **CSS follows established patterns** -- All new styles in `app.css` using `.hc-profile-*` prefix. Reuse existing design tokens (`--text-primary`, `--text-secondary`, `--accent`, `--surface-sunken`, `--border-sunken-outer`, etc.). No duplication of existing `.hc-input`, `.hc-label`, `.hc-fieldset`, `.hc-button` styles.

12. **Tests** -- Update `settings/page.test.ts`:
    - All form fields render with correct CSS classes (`.hc-input`, `.hc-label`, `.hc-fieldset`)
    - Condition chips toggle correctly with active class
    - Save button has `.btn-primary` class
    - Export button has `.btn-standard` class
    - Success/error banners use `.hc-state-success`/`.hc-state-error`
    - Character counter renders for family history
    - Axe accessibility audit passes
    - Verify no `$lib/components/ui/` imports remain in page

13. **WCAG compliance** -- Fieldsets have descriptive legends (announced by screen readers). Error messages use `role="alert"` + `aria-describedby` linking. Radio group uses native `<fieldset>` + `<legend>` for sex selection. Condition chips use `aria-pressed` attribute. Axe audit passes with zero violations.

## Tasks / Subtasks

- [x] Task 1: Add `.hc-profile-*` CSS classes to `app.css` (AC: 4, 5, 6, 7, 11)
  - [x] `.hc-profile-page` -- container layout (max-width, padding, centering)
  - [x] `.hc-profile-title` -- page heading
  - [x] `.hc-profile-sections` -- flex column with 16px gap between fieldsets
  - [x] `.hc-profile-field-group` -- vertical field layout (label + input + error)
  - [x] `.hc-profile-field-row` -- horizontal field layout for inline fields
  - [x] `.hc-profile-field-error` -- validation error text
  - [x] `.hc-profile-condition-chip` + `.hc-profile-condition-chip-active` -- toggle buttons
  - [x] `.hc-profile-condition-grid` -- chip container layout
  - [x] `.hc-profile-add-condition` -- "Other condition" input + button row
  - [x] `.hc-profile-custom-conditions` -- custom condition chips container
  - [x] `.hc-profile-char-count` -- character counter
  - [x] `.hc-profile-save-row` -- save button container
  - [x] `.hc-profile-gdpr-text` -- GDPR description text
  - [x] `.hc-profile-export-row` -- export button container

- [x] Task 2: Rewrite `+page.svelte` template (AC: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
  - [x] Remove all `$lib/components/ui/*` imports (Button, Input, Label, Textarea)
  - [x] Replace `<main class="mx-auto max-w-xl p-8">` with `<main class="hc-profile-page">`
  - [x] Wrap Basic Info in `<fieldset class="hc-fieldset"><legend>Basic Information</legend>`
  - [x] Replace `<Input>` components with `<input class="hc-input">`
  - [x] Replace `<Label>` components with `<label class="hc-label">`
  - [x] Replace `<Textarea>` with `<textarea class="hc-textarea">`
  - [x] Replace `<Button>` components with `<button class="btn-primary">` / `<button class="btn-standard">`
  - [x] Wrap Health Conditions in `<fieldset class="hc-fieldset">`
  - [x] Wrap Family History in `<fieldset class="hc-fieldset">`
  - [x] Wrap Data & Privacy in `<fieldset class="hc-fieldset">`
  - [x] Replace condition pills (`rounded-full`) with rectangular `.hc-profile-condition-chip`
  - [x] Replace success/error inline Tailwind with `.hc-state-success`/`.hc-state-error`
  - [x] Ensure all `aria-*` attributes preserved and fieldset/legend semantics added

- [x] Task 3: Preserve all behavior (AC: 1, 2)
  - [x] Verify `$effect` profile loading still works
  - [x] Verify `createMutation` save flow unchanged
  - [x] Verify all validation handlers unchanged (handleAgeBlur, handleHeightBlur, handleWeightBlur)
  - [x] Verify condition toggle, add-other, remove-custom all work
  - [x] Verify export flow unchanged
  - [x] Verify success/error auto-hide timing unchanged (3s)

- [x] Task 4: Update tests (AC: 12)
  - [x] Update selectors for new markup structure
  - [x] Add CSS class assertions (`.hc-input`, `.hc-fieldset`, `.btn-primary`, etc.)
  - [x] Add condition chip toggle class test
  - [x] Add success/error state class test
  - [x] Add character counter test
  - [x] Add Axe accessibility audit
  - [x] Verify no UI component imports test

- [x] Task 5: WCAG audit (AC: 13)
  - [x] All fieldsets have `<legend>`
  - [x] Error `<p>` elements have `role="alert"` and are linked via `aria-describedby`
  - [x] Sex radio group in native `<fieldset>` + `<legend>`
  - [x] Condition chips have `aria-pressed`
  - [x] Axe audit passes

### Review Findings

- [x] [Review][Patch] 98.css button base leaks into condition chips — added min-width:0, box-shadow:none, text-shadow:none reset
- [x] [Review][Patch] 3 inline style attributes violate AC1 — extracted to .hc-profile-field-row > .hc-profile-field-group and .hc-profile-medications CSS classes
- [x] [Review][Patch] No :focus-visible on condition chips — added .hc-profile-condition-chip:focus-visible rule
- [x] [Review][Patch] Hardcoded #fff in .hc-profile-condition-chip-active — changed to var(--accent-text)
- [x] [Review][Patch] Custom condition chips missing aria-pressed (AC13) — added aria-pressed="true"
- [x] [Review][Patch] No test for export flow — added 2 tests for export success and error banners
- [x] [Review][Defer] mockIsPending closure capture in test mock — pre-existing test infra, works correctly now
- [x] [Review][Defer] ?raw import test may break on bundler changes — theoretical fragility, works now
- [x] [Review][Defer] No disabled state styling on condition chips when fieldset disabled — not currently used

## Dev Notes

### Architecture & Patterns

- **Reskin only -- preserve all behavior**: The page's `$state` variables, `$effect` for loading, `createMutation` for saving, validation handlers, condition toggle logic, and export flow are all correct. Only replace the template markup and CSS classes. Do NOT modify any `<script>` logic except removing UI component imports.
- **No shadcn-svelte components**: This is a core Epic 12 migration goal. The page currently imports `Button`, `Input`, `Label`, `Textarea` from `$lib/components/ui/`. Replace all with native HTML elements + `.hc-*` / `.btn-*` classes. This matches the pattern established in Epics 10-11.
- **Match the design mockup**: Compare against `ux-design-directions-v2.html` and `ux-page-mockups.html` in planning-artifacts. The page should look like a Windows 98 properties dialog -- clean fieldsets with beveled borders, not rounded Tailwind cards.

### Current Page Structure (What to Change)

```svelte
<!-- CURRENT: Tailwind + shadcn components -->
<main class="mx-auto max-w-xl p-8">
  <h1 class="mb-6 text-2xl font-semibold">Medical Profile</h1>
  <div class="space-y-6">
    <section><h2 class="mb-4 text-lg font-medium">Basic Information</h2>...</section>
    <section><h2 class="mb-4 text-lg font-medium">Health Conditions</h2>...</section>
    <section><h2 class="mb-4 text-lg font-medium">Family History</h2>...</section>
    <Button onclick={handleSave}>Save Profile</Button>
    <section><h2 class="mb-4 text-lg font-medium">Data & Privacy</h2>...</section>
  </div>
</main>
```

```svelte
<!-- TARGET: 98.css fieldsets + design tokens -->
<main class="hc-profile-page">
  <h1 class="hc-profile-title">Medical Profile</h1>
  {#if successMessage}...hc-state hc-state-success...{/if}
  {#if errorMessage}...hc-state hc-state-error...{/if}
  <div class="hc-profile-sections">
    <fieldset class="hc-fieldset"><legend>Basic Information</legend>...</fieldset>
    <fieldset class="hc-fieldset"><legend>Health Conditions</legend>...</fieldset>
    <fieldset class="hc-fieldset"><legend>Family History</legend>...</fieldset>
    <div class="hc-profile-save-row">
      <button class="btn-primary" onclick={handleSave}>Save Profile</button>
    </div>
    <fieldset class="hc-fieldset"><legend>Data & Privacy</legend>...</fieldset>
  </div>
</main>
```

### Condition Chips (Current vs Target)

```svelte
<!-- CURRENT: rounded pill buttons with Tailwind -->
<button class="rounded-full border px-3 py-1 text-sm transition-colors
  {selected ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background hover:bg-accent'}">

<!-- TARGET: rectangular 98.css chips -->
<button class="hc-profile-condition-chip {selected ? 'hc-profile-condition-chip-active' : ''}">
```

### CSS Classes to Add (app.css)

| Class | Purpose |
|-------|---------|
| `.hc-profile-page` | `max-width: 640px; margin: 0 auto; padding: 24px;` |
| `.hc-profile-title` | `font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 16px;` |
| `.hc-profile-sections` | `display: flex; flex-direction: column; gap: 16px;` |
| `.hc-profile-field-group` | `display: flex; flex-direction: column; gap: 2px; margin-bottom: 8px;` |
| `.hc-profile-field-row` | `display: flex; gap: 16px; align-items: flex-start;` |
| `.hc-profile-field-error` | `font-size: 13px; color: var(--color-status-action); margin-top: 2px;` |
| `.hc-profile-condition-grid` | `display: flex; flex-wrap: wrap; gap: 6px;` |
| `.hc-profile-condition-chip` | `border: 1px solid var(--border-sunken-outer); padding: 4px 10px; font-size: 14px; background: var(--surface-raised); cursor: pointer;` |
| `.hc-profile-condition-chip-active` | `background: var(--accent); color: #fff; border-color: var(--accent);` |
| `.hc-profile-add-condition` | `display: flex; gap: 8px; margin-top: 8px;` |
| `.hc-profile-custom-conditions` | `display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px;` |
| `.hc-profile-char-count` | `font-size: 13px; color: var(--text-secondary); text-align: right; margin-top: 2px;` |
| `.hc-profile-save-row` | `display: flex; justify-content: flex-end;` |
| `.hc-profile-gdpr-text` | `font-size: 14px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 12px;` |
| `.hc-profile-export-row` | `display: flex; gap: 8px;` |

### Existing CSS Classes to Reuse (already in app.css)

- `.hc-fieldset` + `legend` -- 98.css fieldset with accent bold legend
- `.hc-input` -- sunken panel text input
- `.hc-label` -- form label styling
- `.hc-textarea` -- sunken panel textarea
- `.hc-radio-group`, `.hc-radio-group-horizontal` -- radio button layout
- `.btn-primary` -- accent blue button
- `.btn-standard` -- default 98.css gray button
- `.hc-state`, `.hc-state-success`, `.hc-state-error` -- feedback banners

### Backend API Contracts (No Changes Needed)

```
GET  /api/v1/users/me/profile → ProfileResponse
PUT  /api/v1/users/me/profile → ProfileResponse (body: ProfileUpdateRequest)
POST /api/v1/users/me/export  → StreamingResponse (ZIP)
```

`ProfileUpdateRequest` fields: `age` (1-120), `sex` (male/female/other/prefer_not_to_say), `height_cm` (50-300), `weight_kg` (10-500), `known_conditions` (list, max 50), `medications` (list, max 50), `family_history` (str, max 2000).

### Existing Test Structure

Current `settings/page.test.ts` already expects `.hc-input` and `.btn-standard` classes (tests were written ahead of migration). The test mocks `getProfile` and `createMutation`. Expand tests to cover all new CSS class assertions, state feedback, and Axe audit.

### Previous Story Learnings (Epic 11)

- Use `.hc-*` CSS classes exclusively, no Tailwind structural classes
- Section header pattern (not WindowFrame) for content containers
- Right-align action buttons where appropriate
- Axe audit test required
- Match the design mockup visually after changes
- Pattern reuse from earlier stories accelerates velocity
- 98.css form primitives (`.hc-fieldset`, `.hc-radio-group`, `.hc-checkbox`) already exist -- no new pattern spike needed

### Files to Modify

| File | Changes |
|------|---------|
| `healthcabinet/frontend/src/app.css` | Add `.hc-profile-*` classes (~14 new classes) |
| `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` | Replace template markup (remove UI imports, add fieldsets, swap classes) |
| `healthcabinet/frontend/src/routes/(app)/settings/page.test.ts` | Expand test coverage (CSS classes, state feedback, Axe audit) |

### Project Structure Notes

- Alignment with established Epic 10-11 CSS architecture (section-prefixed classes in `app.css`)
- No new components created -- this is a reskin of existing page
- No backend changes required

### References

- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md#Section-10 -- Settings page wireframe and states]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md -- Form patterns, typography, color tokens]
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md -- FE Epic 6 Story 1 scope]
- [Source: _bmad-output/planning-artifacts/epics.md -- Epic 12 summary, FR3/FR4/FR5/FR6]
- [Source: _bmad-output/planning-artifacts/prd.md -- FR3, FR32, FR33 requirements]
- [Source: _bmad-output/implementation-artifacts/11-5-re-upload-partial-extraction-flow-polish.md -- CSS pattern learnings]
- [Source: _bmad-output/implementation-artifacts/epic-11-retro-2026-04-05.md -- Epic 11 retrospective]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Removed all 4 shadcn-svelte component imports (Button, Input, Label, Textarea) from settings page
- Replaced all Tailwind structural classes with `.hc-profile-*` prefixed CSS classes
- Added 15 new `.hc-profile-*` CSS classes to app.css following section-based naming convention
- Wrapped 4 sections in `<fieldset class="hc-fieldset">` with descriptive `<legend>` elements
- Sex radio group uses native `<fieldset class="hc-radio-group">` with `.hc-radio` inputs
- Condition chips: rectangular `.hc-profile-condition-chip` (no rounded corners), with `.hc-profile-condition-chip-active` toggle
- Height and Weight fields placed side-by-side using `.hc-profile-field-row`
- Success/error feedback uses `.hc-state .hc-state-success`/`.hc-state-error` design system banners
- Save button: `.btn-primary`, Export/Add buttons: `.btn-standard`
- Zero behavior changes -- all script logic preserved exactly (validation, mutation, export, conditions)
- 18 tests written covering CSS classes, field rendering, condition toggle, character counter, validation errors, profile loading, WCAG, Axe audit
- 500/500 tests pass, 0 regressions, 0 type errors

### Change Log

- 2026-04-05: Story implementation complete -- Medical Profile page 98.css reskin
- 2026-04-05: Code review patches applied -- 6 fixes (98.css reset, inline styles, focus-visible, token, aria-pressed, export tests)

### File List

- `healthcabinet/frontend/src/app.css` (modified -- added `.hc-profile-*` CSS classes)
- `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` (modified -- replaced template markup)
- `healthcabinet/frontend/src/routes/(app)/settings/page.test.ts` (modified -- expanded to 18 tests)
