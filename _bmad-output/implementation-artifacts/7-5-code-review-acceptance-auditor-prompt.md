You are the Acceptance Auditor reviewer.

Review this implementation diff against the story and context below.

Diff file:

- `/Users/vladtara/dev/set-bmad/_bmad-output/implementation-artifacts/7-5-code-review.diff`

Story:

- `Story 7.5: Data-Display Primitives — Metric Cards, Status Rows, Slide-Over Panels, Dense Sortable Tables`

Acceptance criteria to audit:

1. `MetricCard` renders a compact metric display with sunken panel styling, accepts `label`, `value`, optional `class`, optional `children`, and uses tabular numbers for value display.
2. `DataTable` renders a dense sortable table with:
   - sunken panel wrapper around native `<table>`
   - `columns` and `rows` props
   - optional `onRowClick`
   - clickable sortable headers with visible sort indicator
   - internal sort state via runes
   - hover state for interactive rows
   - clickable rows with `role="button"`, `tabindex="0"`, and Enter key support
   - header/body typography requirements
   - alternating row colors
   - optional outer `class`
   - custom cell rendering via `children?: Snippet`, with default fallback to `row[col.key]`
3. `StatusRow` renders a compact label/value row with optional colored dot plus status text.
4. `SlideOverPanel` renders a right-anchored dialog with:
   - backdrop click to close
   - Escape key close
   - `role="dialog"` and `aria-modal="true"`
   - focus trap when open
   - title-bar header with close button
   - scrollable body
   - transition / reduced motion handling
5. All four components:
   - live under `src/lib/components/ui/`
   - have unit tests with render, prop, accessibility, and interaction assertions
   - use no scoped `<style>` blocks
   - introduce zero `svelte-check` errors
6. CSS classes in `app.css` must cover the specified component primitives and states.

Relevant project/context constraints:

- Frontend uses Svelte 5 runes, not Svelte 4 patterns.
- Desktop-only MVP is acceptable.
- Accessibility behavior matters for interactive rows and dialogs.
- Unit tests are expected for props, interactions, and accessibility assertions.
- Story explicitly says DataTable should support `children?: Snippet` for custom cell rendering.

Task:

Review the diff against the acceptance criteria and constraints. Report only concrete mismatches, omissions, or contradictions.

Output requirements:

- Return findings as a Markdown list.
- Each finding must include:
  - a one-line title
  - which acceptance criterion or constraint is violated
  - evidence from the implementation
  - why it matters

If you find no issues, say `No findings.`
