# Story 7.4: Reusable State Components — Empty, Loading, Error, Success, Warning

Status: done

## Story

As a frontend developer,
I want a set of reusable state components (empty, loading, error, success, warning) built with 98.css panels so that every page and domain component can render consistent, accessible, well-styled state feedback without duplicating ad-hoc inline patterns.

## Acceptance Criteria

1. **EmptyState** component renders a centered message with optional icon and CTA:
   - Sunken 98.css panel container
   - Centered layout: icon/emoji slot (optional) + title (bold) + description (secondary text) + optional action button
   - Accepts `title`, `description`, `icon`, `action` (label + callback) props
   - Accepts `children` snippet for custom content override
   - Accepts `class` prop for external overrides
   - Svelte 5 runes, TypeScript interface

2. **LoadingState** component renders skeleton placeholder content:
   - Sunken 98.css panel container with `aria-busy="true"`
   - Renders 3 animated skeleton lines of varying widths (60%, 80%, 45%) using pulse animation
   - Accepts `lines` prop (number, default 3) to control skeleton line count
   - Accepts optional `message` prop (e.g., "Loading biomarkers...") rendered as `sr-only` text + visible subtle label
   - `aria-live="polite"` region for screen reader announcements
   - Never renders a bare spinner — always contextual skeleton or labeled indicator
   - Accepts `class` prop

3. **ErrorState** component renders a recoverable error message:
   - Sunken 98.css panel with 3px left border in `--status-action` red
   - Layout: icon (default "!") + title (bold, action-red text) + description + optional retry button
   - Accepts `title`, `description`, `action` (label + callback) props
   - Uses `role="alert"` for immediate screen reader announcement
   - Never shows vague copy — title must be specific (e.g., "Failed to load documents", not "Oops!")
   - Accepts `class` prop

4. **SuccessState** component renders a transient or persistent success message:
   - Sunken 98.css panel with 3px left border in `--status-optimal` green
   - Layout: icon (default "✓") + title (bold, optimal-green text) + optional description
   - Accepts `title`, `description` props
   - Uses `role="status"` for polite screen reader announcement
   - Accepts `class` prop

5. **WarningState** component renders an actionable warning:
   - Sunken 98.css panel with 3px left border in `--status-borderline` gold
   - Layout: icon (default "⚠") + title (bold, borderline-gold text) + description + optional action button
   - Accepts `title`, `description`, `action` (label + callback) props
   - Uses `role="status"` for polite announcement
   - Accepts `class` prop

6. All 5 components:
   - Live in `src/lib/components/ui/state/` with barrel `index.ts`
   - Have unit tests (vitest + jsdom) with render, prop, accessibility, and variant assertions
   - Use NO scoped `<style>` blocks — all CSS in `app.css` (vitest jsdom limitation from Story 7-1)
   - Zero `svelte-check` errors introduced
   - All existing tests continue to pass (zero regressions)

7. CSS classes added to `app.css`:
   - `.hc-state` — base state panel styling (sunken panel, padding, flex column layout)
   - `.hc-state-empty` — centered content alignment
   - `.hc-state-loading` — skeleton animation styles
   - `.hc-state-error` — 3px left border `var(--color-status-action)`
   - `.hc-state-success` — 3px left border `var(--color-status-optimal)`
   - `.hc-state-warning` — 3px left border `var(--color-status-borderline)`
   - `.hc-skeleton-line` — animated pulse placeholder (gray → lighter gray, 1.5s ease-in-out infinite)

## Tasks / Subtasks

- [x] **Task 1: CSS foundation in app.css** (AC: #7)
  - [x] Add `.hc-state` base class: sunken box-shadow, white background, `padding: var(--spacing-4)`, flex column, `gap: var(--spacing-2)`
  - [x] Add `.hc-state-empty`: `text-align: center`, `align-items: center`, `justify-content: center`, `min-height: 120px`
  - [x] Add `.hc-state-loading`: `aria-busy` styles
  - [x] Add `.hc-state-error`: `border-left: 3px solid var(--color-status-action)`
  - [x] Add `.hc-state-success`: `border-left: 3px solid var(--color-status-optimal)`
  - [x] Add `.hc-state-warning`: `border-left: 3px solid var(--color-status-borderline)`
  - [x] Add `.hc-skeleton-line`: `height: 14px`, `border-radius: 2px`, `background: var(--color-surface-raised)`, `animation: hc-pulse 1.5s ease-in-out infinite`
  - [x] Add `@keyframes hc-pulse` — opacity 0.6 → 1.0 → 0.6

- [x] **Task 2: EmptyState component** (AC: #1, #6)
  - [x] Create `src/lib/components/ui/state/empty-state.svelte`
  - [x] Props: `title?: string`, `description?: string`, `icon?: string`, `action?: { label: string; onclick: () => void }`, `children?: Snippet`, `class?: string`
  - [x] Render sunken panel with `.hc-state .hc-state-empty` classes
  - [x] Create barrel export in `state/index.ts`
  - [x] Write tests: renders title, renders description, renders action button, renders icon, renders children snippet, applies custom class

- [x] **Task 3: LoadingState component** (AC: #2, #6)
  - [x] Create `src/lib/components/ui/state/loading-state.svelte`
  - [x] Props: `lines?: number` (default 3), `message?: string`, `class?: string`
  - [x] Render sunken panel with `.hc-state .hc-state-loading`, `aria-busy="true"`
  - [x] Render `{lines}` skeleton divs with `.hc-skeleton-line` and varying widths
  - [x] If `message` provided: render as visible label + `aria-live="polite"` region
  - [x] Write tests: renders skeleton lines, respects lines prop, renders message, has aria-busy, applies custom class

- [x] **Task 4: ErrorState component** (AC: #3, #6)
  - [x] Create `src/lib/components/ui/state/error-state.svelte`
  - [x] Props: `title: string`, `description?: string`, `action?: { label: string; onclick: () => void }`, `icon?: string` (default "!"), `class?: string`
  - [x] Render sunken panel with `.hc-state .hc-state-error`, `role="alert"`
  - [x] Title in bold with action-red color, icon prefix
  - [x] Optional retry/action button using standard 98.css `<button>`
  - [x] Write tests: renders title, renders description, renders action button, has role="alert", title is red, applies custom class

- [x] **Task 5: SuccessState component** (AC: #4, #6)
  - [x] Create `src/lib/components/ui/state/success-state.svelte`
  - [x] Props: `title: string`, `description?: string`, `icon?: string` (default "✓"), `class?: string`
  - [x] Render sunken panel with `.hc-state .hc-state-success`, `role="status"`
  - [x] Title in bold with optimal-green color, icon prefix
  - [x] Write tests: renders title, renders description, has role="status", title is green, applies custom class

- [x] **Task 6: WarningState component** (AC: #5, #6)
  - [x] Create `src/lib/components/ui/state/warning-state.svelte`
  - [x] Props: `title: string`, `description?: string`, `action?: { label: string; onclick: () => void }`, `icon?: string` (default "⚠"), `class?: string`
  - [x] Render sunken panel with `.hc-state .hc-state-warning`, `role="status"`
  - [x] Title in bold with borderline-gold color, icon prefix
  - [x] Optional action button using standard 98.css `<button>`
  - [x] Write tests: renders title, renders description, renders action button, has role="status", title is gold, applies custom class

- [x] **Task 7: Regression verification** (AC: #6)
  - [x] Run full test suite: `docker compose exec frontend npm run test:unit`
  - [x] Run `svelte-check`: zero new errors
  - [x] Run build: `docker compose exec frontend npm run build`

### Review Findings

- [x] [Review][Patch] Missing CSS `.hc-state-loading` rule — added gap rule for loading variant [app.css]
- [x] [Review][Patch] No `prefers-reduced-motion` guard on `.hc-skeleton-line` animation — added media query [app.css]
- [x] [Review][Patch] Action button click handlers never tested for invocation — added click + assertion to all 3 action tests [state.test.ts]
- [x] [Review][Patch] Duplicate `sr-only` text in LoadingState — removed redundant sr-only span [loading-state.svelte]
- [x] [Review][Patch] LoadingState: negative/invalid `lines` prop causes RangeError — added `Math.max(1, Math.floor(lines))` guard [loading-state.svelte]
- [x] [Review][Patch] Missing test assertion for `aria-live="polite"` attribute — added aria-live assertion [state.test.ts]

## Dev Notes

### Architecture & Patterns

- **Component location:** `src/lib/components/ui/state/` — follows established `ui/*` convention
- **CSS location:** ALL styles in `healthcabinet/frontend/src/app.css` — NO scoped `<style>` blocks (vitest jsdom breaks with Vite CSS preprocessor; established in Story 7-1)
- **Import path:** `@import '98.css/dist/98.css'` (explicit path, not bare `'98.css'`)
- **Barrel exports:** Each component directory has `index.ts` exporting default component

### Svelte 5 Component Pattern (MUST follow exactly)

```svelte
<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    title?: string;
    description?: string;
    children?: Snippet;
    class?: string;
  }

  let { title, description, children, class: className, ...rest }: Props = $props();
  let classes = $derived(`hc-state hc-state-variant ${className ?? ''}`.trim());
</script>

<div class={classes} {...rest}>
  {#if children}
    {@render children()}
  {:else}
    <!-- default content -->
  {/if}
</div>
```

**Critical Svelte 5 rules:**
- `children` must be `children?: Snippet` (optional) and rendered with `{@render children?.()}` for test compatibility with `renderComponent()`
- Use `$props()` rune, NOT Svelte 4 `export let`
- Use `$derived()` for computed values, NOT `$:` reactive statements

### CSS Custom Properties Available (from app.css)

**Status colors (use these — do NOT hardcode hex):**
- `--color-status-optimal: #2E8B57` — success/green
- `--color-status-borderline: #DAA520` — warning/gold
- `--color-status-action: #CC3333` — error/red

**Surface colors:**
- `--color-surface-sunken: #FFFFFF` — sunken panel background (white)
- `--color-surface-raised: #EEF2F8` — raised surface / skeleton line color
- `--color-surface-base: #E4EAF0` — page background

**Text colors:**
- `--color-text-primary: #1A2030` — main text
- `--color-text-secondary: #5A6A80` — descriptions
- `--color-text-disabled: #8898A8` — disabled/placeholder

**Sunken box-shadow pattern (match existing `.hc-panel-sunken`):**
```css
box-shadow: inset -1px -1px #fff, inset 1px 1px #0a0a0a, inset -2px -2px #dfdfdf, inset 2px 2px grey;
```

### Spacing

Use `var(--spacing-*)` tokens (2px base unit):
- `--spacing-2`: 8px (component internal padding)
- `--spacing-3`: 12px (gap between elements)
- `--spacing-4`: 16px (panel padding)

### Typography

- Title text: `font-weight: 700`, `font-size: 15px` (body size, bold)
- Description text: `color: var(--color-text-secondary)`, `font-size: 15px`
- Icon: inline before title text, same line

### Testing Pattern

**Framework:** vitest + jsdom + @testing-library/svelte
**Command:** `docker compose exec frontend npm run test:unit`
**NEVER run tests locally — Docker only.**

```typescript
import { describe, it, expect } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { EmptyState } from '$lib/components/ui/state';

describe('EmptyState', () => {
  it('renders with title', () => {
    const { container } = renderComponent(EmptyState, { title: 'No documents yet' });
    expect(container.textContent).toContain('No documents yet');
  });

  it('applies custom class', () => {
    const { container } = renderComponent(EmptyState, { title: 'Test', class: 'my-class' });
    const el = container.firstElementChild;
    expect(el?.classList.contains('my-class')).toBe(true);
  });
});
```

**Test utility:** Use `renderComponent()` from `$lib/test-utils/render.ts` (NOT raw `render()`)
**Snippet testing:** Use `textSnippet()` from `$lib/test-utils/snippet.ts` for children props

### UX Design Rules

- **Never a bare spinner** — always skeleton content or labeled indicator [Source: ux-design-specification.md#Loading States]
- **Never vague error copy** — no "Oops!", no "We're sorry!" — be specific [Source: prd.md#Journey 3]
- **Color is never the only signal** — always pair with icon + text label [Source: ux-design-specification.md#Accessibility]
- **Health status colors only for clinical data** — use status-optimal/borderline/action for state feedback borders, NOT as decorative backgrounds
- **Accessibility:** `aria-live="polite"` for loading/status, `role="alert"` for errors, `aria-busy="true"` for loading containers

### What NOT To Do

- Do NOT modify any existing components — this story creates new components only
- Do NOT modify any route files — consumers will adopt these components in later epics
- Do NOT create a toast/notification system — that's Epic 9 (global feedback surfaces)
- Do NOT create processing pipeline or progress bar components — those already exist in `health/ProcessingPipeline.svelte`
- Do NOT use bits-ui or shadcn-svelte — fully removed in Story 7-1
- Do NOT add scoped `<style>` blocks — styles go in `app.css`
- Do NOT add mobile/tablet responsive behavior — desktop-only MVP (1024px+)
- Do NOT modify AppShell — AppShell redesign is Epic 9

### Existing Patterns to Be Aware Of (Do NOT Duplicate)

These components already handle their own state internally — story 7-4 components are for reuse in NEW page-level redesigns, not for retrofitting into these:

- `health/DocumentUploadZone.svelte` — has its own upload state machine (idle/dragging/uploading/success/error)
- `health/ProcessingPipeline.svelte` — has its own multi-stage pipeline with SSE
- `health/AiInterpretationCard.svelte` — has its own TanStack Query loading/error
- `health/PartialExtractionCard.svelte` — has its own partial/failed recovery UI
- Routes like `dashboard/+page.svelte` and `documents/+page.svelte` have inline state handling

The new state components will be used by future epic redesigns (Epics 8-13) to replace ad-hoc patterns with consistent shared primitives.

### Project Structure Notes

- New directory: `healthcabinet/frontend/src/lib/components/ui/state/`
- Files to create:
  - `empty-state.svelte`
  - `loading-state.svelte`
  - `error-state.svelte`
  - `success-state.svelte`
  - `warning-state.svelte`
  - `index.ts` (barrel export for all 5)
  - `state.test.ts` (all tests in one file, following badge.test.ts pattern)
- Files to modify:
  - `healthcabinet/frontend/src/app.css` (add `.hc-state*` and `.hc-skeleton-line` classes + keyframes)

### Previous Story Intelligence

**From Story 7-3 (most recent):**
- Badge component established the variant-driven pattern with `.hc-badge-{variant}` — follow same naming: `.hc-state-{variant}`
- Account status utility extracted to shared file — consider if any shared type/utility needed
- Radio label adjacency conflict required `content: none` override — watch for similar CSS conflicts
- 246 tests passing, 1 pre-existing failure in `users.test.ts` (Blob.stream mock) — unrelated, ignore

**From Story 7-2:**
- Panel component provides `.hc-panel-sunken` — state components should use the same sunken box-shadow pattern directly (don't wrap Panel component, apply CSS directly for simplicity)
- `type="button"` on any `<button>` inside forms to prevent unintended submission

**From Story 7-1:**
- Docker node_modules isolation — if adding deps, run `npm install` inside container
- No new dependencies needed for this story

### Git Intelligence

Recent commits follow `feat(ui):` prefix for UI component work. Last 3 Epic 7 commits:
- `6df1ad7` feat(ui): add new UI components including Badge, Fieldset, Radio, and Select with corresponding tests
- `ca758bb` feat: implement UI components for panels, status bars, toolbars, and window frames with corresponding tests
- `8f93a91` refactor: update color scheme for health indicators and UI components

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Loading States] — skeleton patterns, never bare spinners
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Feedback Patterns] — dialogs, alerts, inline notifications
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Accessibility] — triple redundancy (symbol + color + text)
- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md#Dashboard] — empty/loading/error state examples
- [Source: _bmad-output/planning-artifacts/prd.md#Journey 3] — error handling philosophy, no vague copy
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md#FE Epic 1] — story 4 candidate description
- [Source: _bmad-output/implementation-artifacts/7-3-ui-primitive-migration.md] — previous story patterns and learnings
- [Source: _bmad-output/implementation-artifacts/7-2-base-layout-components.md] — panel/window-frame patterns
- [Source: _bmad-output/implementation-artifacts/7-1-98css-design-system-foundation.md] — CSS-in-app.css rule, Docker testing

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Created 5 reusable state components (EmptyState, LoadingState, ErrorState, SuccessState, WarningState) in `src/lib/components/ui/state/`
- Added 14 CSS rules to `app.css`: `.hc-state` base, 5 variant classes, `.hc-skeleton-line`, `@keyframes hc-pulse`, plus `.hc-state-title`, `.hc-state-description`, `.hc-state-icon`, and 3 variant-specific title color overrides
- All components follow established Svelte 5 runes pattern with `$props()` and `$derived()`
- No scoped `<style>` blocks — all CSS in `app.css` per Story 7-1 convention
- Barrel exports in `state/index.ts`
- 33 new unit tests: EmptyState (7), LoadingState (6), ErrorState (7), SuccessState (6), WarningState (7)
- Accessibility: `role="alert"` on ErrorState, `role="status"` on Success/Warning, `aria-busy="true"` on Loading, `aria-live="polite"` for loading messages
- All buttons use `type="button"` per Story 7-2 learnings
- 279 tests passing (33 new + 246 existing), 1 pre-existing failure (users.test.ts Blob.stream mock — unrelated)
- svelte-check: 0 errors, 2 pre-existing warnings (unchanged)
- Build: successful

### Change Log

- 2026-04-04: Implemented all 5 state components with 33 tests. All ACs satisfied.

### File List

- healthcabinet/frontend/src/app.css (modified — added state component CSS)
- healthcabinet/frontend/src/lib/components/ui/state/empty-state.svelte (new)
- healthcabinet/frontend/src/lib/components/ui/state/loading-state.svelte (new)
- healthcabinet/frontend/src/lib/components/ui/state/error-state.svelte (new)
- healthcabinet/frontend/src/lib/components/ui/state/success-state.svelte (new)
- healthcabinet/frontend/src/lib/components/ui/state/warning-state.svelte (new)
- healthcabinet/frontend/src/lib/components/ui/state/index.ts (new)
- healthcabinet/frontend/src/lib/components/ui/state/state.test.ts (new)