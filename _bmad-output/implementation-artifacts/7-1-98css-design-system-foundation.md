# Story 7.1: 98.css Design System Foundation

Status: done

## Story

As a **visitor, registered user, or admin**,
I want the HealthCabinet interface to use a consistent Windows 98 clinical workstation aesthetic with 98.css chrome and DM Sans typography,
so that every screen feels like a trustworthy, professional medical-grade tool from the first interaction.

## Acceptance Criteria

1. **Given** the frontend dependencies are updated
   **When** `package.json` is inspected
   **Then** `98.css` is installed, `bits-ui` is removed, and no shadcn-svelte references remain in any config file

2. **Given** the global stylesheet is loaded
   **When** any page renders
   **Then** DM Sans (400, 700 weights) is loaded from Google Fonts CDN with tabular figures enabled
   **And** 98.css provides base UI chrome for all native form elements

3. **Given** the Tailwind CSS v4 theme is configured
   **When** `app.css` is inspected
   **Then** it defines CSS custom properties for the complete Arctic Blue palette, health status colors, accent colors, and the 2px-based spacing scale per UX spec v2

4. **Given** the 5 existing UI primitive components (Button, Input, Label, Checkbox, Textarea) have been migrated
   **When** they render on any route (auth, app, admin)
   **Then** they use 98.css native styling (raised buttons, sunken inputs, proper fieldset/legend patterns)
   **And** the Button component supports 5 tiers: Primary (accent blue), Standard (default 98.css), Destructive (red on hover), Toolbar (compact), Tab (accent bottom border)
   **And** no bits-ui imports remain in any component file

5. **Given** existing routes (login, register, onboarding, dashboard, documents, settings, admin) render
   **When** each page loads
   **Then** no route regresses to unstyled or broken state
   **And** form validation, submission, navigation, and auth behavior remain unchanged

6. **Given** the design tokens are applied
   **When** viewed at 1024px+ desktop width
   **Then** text contrast meets WCAG 2.1 AA (4.5:1 minimum)
   **And** focus states are visible on all interactive elements (98.css dotted outline)

## Tasks / Subtasks

- [x] **Task 1: Install 98.css, remove bits-ui** (AC: #1)
  - [x] Run `npm install 98.css` in `healthcabinet/frontend/`
  - [x] Remove `bits-ui` from package.json: `npm uninstall bits-ui`
  - [x] Import 98.css globally in `app.css` or `app.html`: `@import '98.css/dist/98.css';`
  - [x] Search codebase for any `bits-ui` imports and remove them
  - [x] Verify `npm run build` succeeds with no missing module errors

- [x] **Task 2: Set up DM Sans font** (AC: #2)
  - [x] Add Google Fonts link to `healthcabinet/frontend/src/app.html` `<head>`:
    ```html
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;700&display=swap" rel="stylesheet">
    ```
  - [x] Set font-family globally in `app.css`: `body { font-family: "DM Sans", sans-serif; }`
  - [x] Enable tabular figures for tables: `font-feature-settings: 'tnum' 1;` on table elements
  - [x] Verify DM Sans renders on all routes (check DevTools computed styles)

- [x] **Task 3: Replace Tailwind theme tokens in app.css** (AC: #3)
  - [x] Replace the entire `@theme inline` block with new Arctic Blue palette tokens (see Dev Notes for complete values)
  - [x] Define CSS custom properties for all color tokens
  - [x] Replace spacing scale to use 2px base unit
  - [x] Remove `--radius` tokens (98.css uses square corners, no border-radius)
  - [x] Remove dark theme HSL color definitions
  - [x] Add type scale tokens matching UX spec (13px–18px range)

- [x] **Task 4: Migrate Button component** (AC: #4)
  - [x] Rewrite `$lib/components/ui/button/button.svelte` to use 98.css native `<button>` styling
  - [x] Implement 5 button tiers via a `variant` prop: `primary`, `standard`, `destructive`, `toolbar`, `tab`
  - [x] Primary: `background: var(--accent); color: #fff; border: 2px outset var(--accent-light);`
  - [x] Standard: default 98.css raised button (no custom styling needed)
  - [x] Destructive: gray default, red text + red background on hover
  - [x] Toolbar: smaller padding (`4px 10px`), icon + text
  - [x] Tab: standard button with accent bottom border when active
  - [x] Keep TypeScript props interface and Svelte 5 runes pattern
  - [x] Remove `bits-ui` button primitive import if present
  - [x] Remove `index.ts` barrel re-export if it imports from bits-ui

- [x] **Task 5: Migrate Input component** (AC: #4)
  - [x] Rewrite `$lib/components/ui/input/input.svelte` to use 98.css native `<input>` styling
  - [x] 98.css automatically styles `<input>` elements with sunken border
  - [x] Keep `bind:value`, `type`, `placeholder`, `disabled` props
  - [x] Remove all Tailwind border/rounded/focus-ring classes (98.css handles these)
  - [x] Preserve `class` prop passthrough for layout overrides (width, margin)

- [x] **Task 6: Migrate Label, Checkbox, Textarea** (AC: #4)
  - [x] Label: simplify to semantic `<label>` with DM Sans styling (98.css handles base)
  - [x] Checkbox: use native `<input type="checkbox">` — 98.css provides classic checkbox styling
  - [x] Textarea: use native `<textarea>` — 98.css provides sunken border treatment
  - [x] Remove any bits-ui imports from all three components
  - [x] Keep Svelte 5 runes props pattern (`$props()`, `$bindable()`)

- [x] **Task 7: Regression testing across all routes** (AC: #5)
  - [x] Visually verify each route renders without broken layout:
    - `/login`, `/register`, `/onboarding`
    - `/dashboard`, `/documents`, `/documents/upload`
    - `/settings`
    - `/admin`, `/admin/documents`, `/admin/users`
  - [x] Verify form submissions still work (login, register, profile edit)
  - [x] Verify auth flow (login → redirect → dashboard)
  - [x] Run `npm run check` (svelte-check) — aim for no new errors
  - [x] Run `npm run test:unit` via Docker Compose for existing frontend tests

- [x] **Task 8: Accessibility verification** (AC: #6)
  - [x] Check color contrast ratios with new Arctic Blue palette (text-primary #1A2030 on surface-sunken #FFFFFF = ~15:1)
  - [x] Verify focus states are visible on buttons, inputs, checkboxes, textareas
  - [x] Verify keyboard navigation (Tab, Enter, Escape) still works on forms
  - [x] Verify skip-to-content link still functions

## Dev Notes

### CRITICAL: Color Scheme is Changing from Dark to Light

The ENTIRE color scheme is being replaced. This is not just a component swap:
- **OLD (dark):** Background `#0F1117`, text `#F0F2F8`, accent `#4F6EF7`
- **NEW (Arctic Blue/light):** Background `#E4EAF0`, text `#1A2030`, accent `#3366FF`

Every page will look dramatically different. This is intentional — the Windows 98 aesthetic uses a light gray palette.

### Health Status Colors Also Changed

| Status | Old | New |
|--------|-----|-----|
| Optimal | `#2DD4A0` | `#2E8B57` |
| Borderline | `#F5C842` | `#DAA520` |
| Concerning | `#F08430` | `#E07020` |
| Action | `#E05252` | `#CC3333` |

### Complete Arctic Blue Token Definitions (for app.css)

Replace the entire `@theme inline` block with:

```css
@import '98.css';
@import 'tailwindcss';

@theme inline {
  /* Arctic Blue Base Palette */
  --color-surface-base: #E4EAF0;
  --color-surface-raised: #EEF2F8;
  --color-surface-sunken: #FFFFFF;
  --color-surface-window: #FFFFFF;

  /* Border System */
  --color-border-raised-outer: #FFFFFF;
  --color-border-raised-inner: #D0D8E4;
  --color-border-sunken-outer: #A0B0C0;
  --color-border-sunken-inner: #D0D8E4;

  /* Text */
  --color-text-primary: #1A2030;
  --color-text-secondary: #5A6A80;
  --color-text-disabled: #8898A8;

  /* Accent (Electric Blue) */
  --color-accent: #3366FF;
  --color-accent-light: #6690FF;
  --color-accent-text: #FFFFFF;

  /* Health Status */
  --color-status-optimal: #2E8B57;
  --color-status-borderline: #DAA520;
  --color-status-concerning: #E07020;
  --color-status-action: #CC3333;

  /* Table */
  --color-row-alternate: #EEF2F8;

  /* Spacing (2px base unit) */
  --spacing-0_5: 2px;
  --spacing-1: 4px;
  --spacing-1_5: 6px;
  --spacing-2: 8px;
  --spacing-3: 12px;
  --spacing-4: 16px;
  --spacing-5: 20px;
  --spacing-6: 24px;
}
```

Also add CSS custom properties for non-Tailwind consumers:

```css
:root {
  --surface-base: #E4EAF0;
  --surface-raised: #EEF2F8;
  --surface-sunken: #FFFFFF;
  --surface-window: #FFFFFF;
  --text-primary: #1A2030;
  --text-secondary: #5A6A80;
  --text-disabled: #8898A8;
  --accent: #3366FF;
  --accent-light: #6690FF;
  --accent-text: #FFFFFF;
  --status-optimal: #2E8B57;
  --status-borderline: #DAA520;
  --status-concerning: #E07020;
  --status-action: #CC3333;
  --row-alternate: #EEF2F8;
}

body {
  font-family: "DM Sans", sans-serif;
  background: var(--surface-base);
  color: var(--text-primary);
}
```

### Type Scale (for reference — implement as Tailwind utilities or CSS classes)

| Level | Size | Weight | Usage |
|---|---|---|---|
| window-title | 16px | 700 | Window title bars |
| menu | 15px | 400 | Menu bar items |
| heading | 18px | 700 | Section headers |
| body | 15px | 400 | Default text, table cells |
| table-header | 14px | 700 | Column headers |
| status-bar | 14px | 400 | Status bar text |
| micro | 13px | 400 | Reference ranges, tooltips |

### Button Tier CSS Reference

```css
/* Primary */
.btn-primary {
  background: var(--accent);
  color: var(--accent-text);
  border: 2px outset var(--accent-light);
  font-weight: 700;
}

/* Destructive (hover only) */
.btn-destructive:hover {
  background: var(--status-action);
  color: white;
}

/* Toolbar */
.btn-toolbar {
  min-width: 0;
  padding: 4px 10px;
  font-size: 15px;
}

/* Tab (active) */
.btn-tab[aria-selected="true"] {
  border-bottom: 3px solid var(--accent);
}
```

### What NOT to Do in This Story

- **Do NOT rewrite AppShell** — that's Epic 9 (Story 9-1). Leave the sidebar/nav structure as-is. It will look different with new tokens but the layout change comes later.
- **Do NOT remove responsive CSS** from AppShell — that cleanup is also Epic 9.
- **Do NOT create new components** (BiomarkerTable, ImportDialog, etc.) — those come in Epics 10–11.
- **Do NOT change any backend code** — this is frontend-only.
- **Do NOT modify page layouts or content structure** — only the design token layer and UI primitives change.

### Existing Files to Modify

| File | Action |
|------|--------|
| `healthcabinet/frontend/package.json` | Add 98.css, remove bits-ui |
| `healthcabinet/frontend/src/app.css` | Replace entire theme block with Arctic Blue tokens + 98.css import |
| `healthcabinet/frontend/src/app.html` | Add DM Sans Google Fonts link |
| `healthcabinet/frontend/src/lib/components/ui/button/button.svelte` | Rewrite for 98.css + 5 button tiers |
| `healthcabinet/frontend/src/lib/components/ui/input/input.svelte` | Simplify to native 98.css input |
| `healthcabinet/frontend/src/lib/components/ui/label/label.svelte` | Simplify to native label |
| `healthcabinet/frontend/src/lib/components/ui/checkbox/checkbox.svelte` | Simplify to native 98.css checkbox |
| `healthcabinet/frontend/src/lib/components/ui/textarea/textarea.svelte` | Simplify to native 98.css textarea |

### Barrel Export Pattern to Preserve

Each component directory has an `index.ts` that re-exports. Keep this pattern:
```typescript
export { default as Button } from './button.svelte';
```

If the old `index.ts` imported from bits-ui, replace with the local svelte file import.

### Testing Strategy

- `npm run check` (svelte-check) should pass with no NEW errors
- `npm run test:unit` via `docker compose exec frontend npm run test:unit` for existing tests
- Visual regression: manually check each route at 1024px+ width
- Auth flow: login → dashboard redirect must still work

### Previous Story Learnings (from Story 3-0)

- Base UI components were initially bare wrappers with zero styles — Story 3-0 added shadcn-svelte defaults. Now we're replacing those defaults with 98.css native styling.
- When modifying base components, regression test ALL routes that use them (login, register, settings, admin).
- Route tests are colocated as `page.test.ts` (not `+page.test.ts`).
- Use Svelte 5 runes patterns already established: `$props()`, `$bindable()`, `$derived()`.

### Project Structure Notes

- Tailwind CSS v4 uses CSS-first configuration via `@theme inline` in `app.css` — there is NO `tailwind.config.js` file
- Vite plugin for Tailwind: `@tailwindcss/vite` registered in `vite.config.ts`
- Components follow barrel export pattern: `ui/button/button.svelte` + `ui/button/index.ts`
- Global styles in `src/app.css`, HTML shell in `src/app.html`

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Sections: Design System, Color Palette, Typography, Spacing, Components]
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md — FE Epic 1 scope and exit criteria]
- [Source: _bmad-output/planning-artifacts/architecture.md — Frontend Architecture section]
- [Source: _bmad-output/project-context.md — Frontend tech stack and styling rules]
- [Source: _bmad-output/implementation-artifacts/3-0-registration-onboarding-ui-refinement.md — UI component patterns and lessons]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Vite CSS preprocessor fails with `<style>` blocks in Svelte components during vitest (jsdom) — "Cannot create proxy with a non-object as target or handler". Resolved by moving component styles to global `app.css` instead of using scoped `<style>` blocks.
- `@import '98.css'` not resolved by Tailwind/Vite build — needed explicit path `@import '98.css/dist/98.css'`.
- Docker container has separate `node_modules` volume; `npm install 98.css` needed inside container separately from host.

### Completion Notes List

- Installed 98.css, removed bits-ui dependency
- Replaced entire dark-neutral HSL color system with Arctic Blue light palette
- Added legacy Tailwind class compatibility aliases (bg-background, text-foreground, etc.) mapped to new Arctic Blue values so 28 existing route files continue working without modification
- Migrated 5 UI primitives (Button, Input, Label, Checkbox, Textarea) from Tailwind utility classes to 98.css native styling
- Button now supports 5 tiers: primary, standard, destructive, toolbar, tab (was: default, destructive, outline, secondary, ghost, link)
- Updated all route files using old Button variant/size props to new system
- Added `variant="primary"` to login, register, and onboarding submit buttons
- DM Sans font loaded via Google Fonts CDN with tabular figures for tables
- Removed `class="dark"` from `<html>` tag
- Updated 2 existing tests that checked for old Tailwind CSS classes on components
- Pre-existing test failure in `users.test.ts` (object.stream) confirmed unrelated to this story
- svelte-check: 0 errors, 2 pre-existing warnings
- Build: successful

### File List

**Modified:**
- healthcabinet/frontend/package.json
- healthcabinet/frontend/package-lock.json
- healthcabinet/frontend/src/app.css
- healthcabinet/frontend/src/app.html
- healthcabinet/frontend/src/lib/components/ui/button/button.svelte
- healthcabinet/frontend/src/lib/components/ui/input/input.svelte
- healthcabinet/frontend/src/lib/components/ui/label/label.svelte
- healthcabinet/frontend/src/lib/components/ui/checkbox/checkbox.svelte
- healthcabinet/frontend/src/lib/components/ui/textarea/textarea.svelte
- healthcabinet/frontend/src/routes/+page.svelte
- healthcabinet/frontend/src/routes/(auth)/login/+page.svelte
- healthcabinet/frontend/src/routes/(auth)/login/page.test.ts
- healthcabinet/frontend/src/routes/(auth)/register/+page.svelte
- healthcabinet/frontend/src/routes/(app)/onboarding/+page.svelte
- healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte
- healthcabinet/frontend/src/routes/(app)/settings/+page.svelte
- healthcabinet/frontend/src/routes/(app)/settings/page.test.ts

### Change Log

- 2026-04-02: Story 7-1 implemented — 98.css design system foundation with Arctic Blue palette, DM Sans font, 5 button tiers, and migrated UI primitives
