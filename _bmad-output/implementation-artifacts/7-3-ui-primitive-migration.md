# Story 7.3: UI Primitive Migration — Badge, Select, Radio, Fieldset

Status: done

## Story

As a frontend developer,
I want a complete set of 98.css UI primitive components (Badge, Select, Radio/RadioGroup, Fieldset) so that every page-level redesign epic can compose from a shared, tested component library instead of using inline ad-hoc styling.

## Acceptance Criteria

1. **Badge** component renders a compact status label with variant-driven styling:
   - Variants: `default` (gray), `info` (accent blue), `success` (optimal green), `warning` (borderline gold), `danger` (action red)
   - Always renders text content — never color-only
   - Uses 98.css beveled chrome (raised box-shadow) at small scale
   - Accepts `class` prop for external Tailwind overrides
   - Svelte 5 runes, TypeScript interface

2. **Select** component wraps native `<select>` with 98.css sunken styling:
   - Matches `.hc-input` visual treatment (sunken box-shadow, white background)
   - Supports `disabled` state with `.5` opacity and `not-allowed` cursor
   - Bindable `value` prop
   - Passes through standard `HTMLSelectAttributes`
   - Accepts `class` prop

3. **Radio** component wraps native `<input type="radio">` with 98.css styling:
   - Custom appearance matching 98.css checkbox pattern (pixel-art dot for checked state)
   - Visible focus ring (dotted outline)
   - Disabled state support
   - Passes through `HTMLInputAttributes`

4. **RadioGroup** component provides labeled grouping:
   - Renders `<fieldset>` + `<legend>` using 98.css fieldset chrome
   - Accepts `legend` string prop and `children` snippet
   - Horizontal or vertical layout via `direction` prop (`'horizontal' | 'vertical'`, default `'vertical'`)
   - Accepts `class` prop

5. **Fieldset** component renders a 98.css-styled `<fieldset>`:
   - Native 98.css fieldset appearance (beveled border + legend)
   - Accepts `legend` string prop and `children` snippet
   - Disabled state propagates to all child form elements
   - Accepts `class` prop

6. All 5 new components:
   - Follow barrel export pattern (`index.ts`) consistent with existing `$lib/components/ui/*`
   - Have unit tests (vitest + jsdom) with at least render, variant/prop, and accessibility assertions
   - Use NO scoped `<style>` blocks — all custom CSS in `app.css` (vitest jsdom limitation from Story 7-1)
   - Zero `svelte-check` errors introduced
   - All existing tests continue to pass (zero regressions)

7. Admin pages' inline `statusBadge()` helper functions (`admin/users/+page.svelte`, `admin/users/[user_id]/+page.svelte`) are refactored to use the new `Badge` component

## Tasks / Subtasks

- [x] **Task 1: Badge component** (AC: #1, #6)
  - [x] Create `src/lib/components/ui/badge/badge.svelte` with variant prop
  - [x] Add `.hc-badge` and `.badge-{variant}` CSS rules to `app.css`
  - [x] Create `badge/index.ts` barrel export
  - [x] Write unit tests: renders, variant classes, custom class prop, snapshot per variant
  - [x] Verify accessible contrast for all variant color + text combinations

- [x] **Task 2: Select component** (AC: #2, #6)
  - [x] Create `src/lib/components/ui/select/select.svelte` wrapping native `<select>`
  - [x] Add `.hc-select` CSS rules to `app.css` (sunken box-shadow matching `.hc-input`)
  - [x] Create `select/index.ts` barrel export
  - [x] Write unit tests: renders, disabled state, value binding, class prop

- [x] **Task 3: Radio + RadioGroup components** (AC: #3, #4, #6)
  - [x] Create `src/lib/components/ui/radio/radio.svelte`
  - [x] Create `src/lib/components/ui/radio/radio-group.svelte`
  - [x] Add `.hc-radio` CSS rules to `app.css` (pixel-art dot for checked, matching checkbox pattern)
  - [x] Create `radio/index.ts` barrel export (exports both Radio and RadioGroup)
  - [x] Write unit tests: renders, checked/unchecked, group direction, legend rendering

- [x] **Task 4: Fieldset component** (AC: #5, #6)
  - [x] Create `src/lib/components/ui/fieldset/fieldset.svelte`
  - [x] Add `.hc-fieldset` CSS rules to `app.css` if 98.css native fieldset needs augmentation
  - [x] Create `fieldset/index.ts` barrel export
  - [x] Write unit tests: renders, legend text, disabled propagation, class prop

- [x] **Task 5: Refactor admin badge usage** (AC: #7)
  - [x] Replace `statusBadge()` in `(admin)/admin/users/+page.svelte` with `<Badge>` component
  - [x] Replace `statusBadge()` in `(admin)/admin/users/[user_id]/+page.svelte` with `<Badge>` component
  - [x] Verify admin pages render correctly after refactoring

- [x] **Task 6: Validation** (AC: #6)
  - [x] Run full test suite in Docker: `docker compose exec frontend npm run test:unit`
  - [x] Run `svelte-check`: zero new errors
  - [x] Run build: `docker compose exec frontend npm run build` — success

### Review Findings

- [x] [Review][Decision] RadioGroup `border:none` removed — restored 98.css fieldset chrome per AC 4
- [x] [Review][Decision] Exhaustive `account_status` mapping added via shared `accountStatusVariant`/`accountStatusLabel` util
- [x] [Review][Patch] Select sunken box-shadow + white background added to `.hc-select` [app.css]
- [x] [Review][Patch] Select focus override added — neutralizes 98.css navy background [app.css]
- [x] [Review][Patch] Badge variant classes namespaced to `.hc-badge-{variant}` [app.css, badge.svelte, badge.test.ts]
- [x] [Review][Patch] Shared `accountStatusVariant`/`accountStatusLabel` extracted to `badge/account-status.ts`, both admin pages updated
- [x] [Review][Patch] Radio label adjacency neutralized — `.hc-radio + label::before { content: none }` [app.css]
- [x] [Review][Defer] Checkbox label adjacency conflict — pre-existing, same pattern as radio issue
- [x] [Review][Defer] WindowFrame close/minimize/maximize buttons non-functional — pre-existing
- [x] [Review][Defer] Admin `formatDate` in list page missing null guard — pre-existing

## Dev Notes

### Critical Patterns from Stories 7-1 and 7-2

**NO scoped `<style>` blocks.** Vite CSS preprocessor fails in vitest with jsdom. All custom CSS lives in `app.css`. This was a hard-won lesson from Story 7-1 — do NOT attempt scoped styles.

**98.css import path:** `@import '98.css/dist/98.css'` (already in `app.css` line 1).

**Docker-only testing.** Never run tests locally. Always: `docker compose exec frontend npm run test:unit`.

**Docker node_modules.** The container has a separate `node_modules` volume. If you add dependencies, run `docker compose exec frontend npm install` inside the container.

**Svelte 5 component pattern (follow exactly):**
```svelte
<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';

  interface Props extends HTMLButtonAttributes {
    children?: Snippet;
    variant?: 'default' | 'primary';
  }

  let { children, class: className, variant = 'default', ...rest }: Props = $props();
  let classes = $derived(`hc-component variant-${variant} ${className ?? ''}`.trim());
</script>

<element class={classes} {...rest}>
  {@render children?.()}
</element>
```

**Barrel export pattern:**
```ts
export { default as ComponentName } from './component-name.svelte';
```

### CSS Architecture

All `.hc-*` CSS classes follow the same box-shadow pattern established in Story 7-1:

- **Raised** (buttons, badges, toolbar): `inset -1px -1px #0a0a0a, inset 1px 1px #fff, inset -2px -2px grey, inset 2px 2px #dfdfdf`
- **Sunken** (inputs, select, textarea, panels): `inset -1px -1px #fff, inset 1px 1px #0a0a0a, inset -2px -2px #dfdfdf, inset 2px 2px grey`

Badge should use raised at reduced scale. Select should use sunken matching `.hc-input`.

### Design Token Reference

Colors from `app.css` `:root` and `@theme inline`:

| Token | Hex | Badge Variant |
|-------|-----|---------------|
| `--text-primary` | `#1A2030` | default text |
| `--accent` | `#3366FF` | `info` |
| `--status-optimal` | `#2E8B57` | `success` |
| `--status-borderline` | `#DAA520` | `warning` |
| `--status-action` | `#CC3333` | `danger` |
| `silver` | `silver` | `default` background |

### Existing Components to Reference

| Component | Path | Pattern to Follow |
|-----------|------|-------------------|
| Button | `src/lib/components/ui/button/button.svelte` | Variant system, class merging, TypeScript Props |
| Checkbox | `src/lib/components/ui/checkbox/checkbox.svelte` | Custom appearance CSS, pixel-art checked state |
| Input | `src/lib/components/ui/input/input.svelte` | Sunken styling, bindable value |
| Panel | `src/lib/components/ui/panel/panel.svelte` | Variant-driven class, test patterns |
| WindowFrame | `src/lib/components/ui/window-frame/window-frame.svelte` | Children snippet, optional props |

### Admin Badge Refactoring Target

Two files contain inline `statusBadge()` functions that build CSS classes manually:

1. `src/routes/(admin)/admin/users/+page.svelte:70` — `statusBadge()` returns `{ classes, label }`, used with `<span>` at line 179
2. `src/routes/(admin)/admin/users/[user_id]/+page.svelte:57` — same pattern, used at line 118

Replace these with:
```svelte
import { Badge } from '$lib/components/ui/badge';
<Badge variant={mapStatusToVariant(user.account_status)}>
  {statusLabel}
</Badge>
```

Create a small mapping function (or inline) rather than the verbose `statusBadge()` helper.

### 98.css Native Elements

98.css already styles these semantic HTML elements natively:
- `<fieldset>` — beveled border with legend
- `<select>` — basic dropdown styling
- `<input type="radio">` — basic radio appearance

The components should leverage these native styles and only add `.hc-*` overrides where the native 98.css styling is insufficient (e.g., custom appearance for radio dot, DM Sans font override, focus ring consistency).

### What NOT to Do

- Do NOT create a Dialog component — that is a later story
- Do NOT create Card, Tabs, or Skeleton components — those belong to stories 7-4/7-5
- Do NOT refactor any page besides the admin badge usage — page redesigns are Epics 8-13
- Do NOT remove legacy Tailwind compatibility aliases from `app.css` — other pages still depend on them
- Do NOT add scoped `<style>` blocks — they break vitest
- Do NOT use `bits-ui` or `shadcn-svelte` — they are removed and must stay removed

### Project Structure Notes

New files to create:
```
src/lib/components/ui/
├── badge/
│   ├── badge.svelte
│   ├── badge.test.ts
│   └── index.ts
├── select/
│   ├── select.svelte
│   ├── select.test.ts
│   └── index.ts
├── radio/
│   ├── radio.svelte
│   ├── radio-group.svelte
│   ├── radio.test.ts
│   └── index.ts
└── fieldset/
    ├── fieldset.svelte
    ├── fieldset.test.ts
    └── index.ts
```

Files to modify:
- `src/app.css` — add `.hc-badge`, `.hc-select`, `.hc-radio`, `.hc-fieldset` CSS
- `src/routes/(admin)/admin/users/+page.svelte` — replace statusBadge with Badge component
- `src/routes/(admin)/admin/users/[user_id]/+page.svelte` — replace statusBadge with Badge component

### References

- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md#FE Epic 1 Story 3]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Arctic Blue palette, typography scale, health status colors]
- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md — Badge/status usage across admin pages]
- [Source: _bmad-output/implementation-artifacts/7-1-98css-design-system-foundation.md — CSS architecture, vitest limitations, Svelte 5 patterns]
- [Source: _bmad-output/implementation-artifacts/7-2-base-layout-components.md — Component patterns, test patterns, barrel exports]
- [Source: healthcabinet/frontend/src/app.css — Design tokens, CSS box-shadow patterns]

## Change Log

- 2026-04-03: Implemented all 5 UI primitive components (Badge, Select, Radio, RadioGroup, Fieldset) with 98.css styling, 29 unit tests, and refactored admin pages to use Badge component.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Radio component: Svelte 5 does not allow `bind:checked` on `<input type="radio">` — removed binding, passes props through instead. Consumers use `bind:group` at usage site.
- Pre-existing test failure in `src/lib/api/users.test.ts` (Blob.stream mock issue) — not introduced by this story.
- Pre-existing svelte-check warnings (2) on admin user detail dialog a11y — not introduced by this story.

### Completion Notes List

- Badge: 5 variants (default/info/success/warning/danger) with raised 98.css chrome, 7 tests
- Select: Native `<select>` wrapper with sunken styling matching `.hc-input`, bindable value, 5 tests
- Radio: Custom appearance with pixel-art dot for checked state, circular 98.css box-shadow, 4 tests
- RadioGroup: Fieldset-based grouping with legend, horizontal/vertical layout, 7 tests
- Fieldset: Native 98.css fieldset with legend and disabled propagation, 6 tests
- Admin refactor: Replaced inline `statusBadge()` helpers in 2 admin pages with `<Badge>` component
- All CSS in `app.css` (no scoped styles) — consistent with Stories 7-1/7-2
- svelte-check: 0 errors, 2 pre-existing warnings
- Build: success
- Tests: 246 passed, 1 pre-existing failure (unrelated)

### File List

New files:
- healthcabinet/frontend/src/lib/components/ui/badge/badge.svelte
- healthcabinet/frontend/src/lib/components/ui/badge/badge.test.ts
- healthcabinet/frontend/src/lib/components/ui/badge/index.ts
- healthcabinet/frontend/src/lib/components/ui/select/select.svelte
- healthcabinet/frontend/src/lib/components/ui/select/select.test.ts
- healthcabinet/frontend/src/lib/components/ui/select/index.ts
- healthcabinet/frontend/src/lib/components/ui/radio/radio.svelte
- healthcabinet/frontend/src/lib/components/ui/radio/radio-group.svelte
- healthcabinet/frontend/src/lib/components/ui/radio/radio.test.ts
- healthcabinet/frontend/src/lib/components/ui/radio/index.ts
- healthcabinet/frontend/src/lib/components/ui/fieldset/fieldset.svelte
- healthcabinet/frontend/src/lib/components/ui/fieldset/fieldset.test.ts
- healthcabinet/frontend/src/lib/components/ui/fieldset/index.ts

Modified files:
- healthcabinet/frontend/src/app.css
- healthcabinet/frontend/src/routes/(admin)/admin/users/+page.svelte
- healthcabinet/frontend/src/routes/(admin)/admin/users/[user_id]/+page.svelte
