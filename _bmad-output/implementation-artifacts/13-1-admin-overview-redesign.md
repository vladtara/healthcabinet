# Story 13.1: Admin Overview Redesign

Status: done

## Story

As a platform admin viewing the overview page at `/admin`,
I want the page restyled with 98.css stat cards and decision surfaces matching the rest of the app,
so that the admin surface feels like an operations console rather than a leftover utility scaffold.

## Acceptance Criteria

1. **Replace all Tailwind structural classes with `.hc-admin-overview-*` CSS classes** -- Remove every Tailwind utility class from `(admin)/admin/+page.svelte`. Replace with `.hc-admin-overview-*` classes defined in `app.css`. No scoped `<style>` blocks. No inline Tailwind colors, spacing, or layout classes. Same discipline as Stories 12-1 and 11-1.

2. **Use `MetricCard` primitive for stat cards** -- Replace the 5 inline `<div class="rounded-lg border...">` stat blocks with 5 `<MetricCard>` instances from `$lib/components/ui/metric-card`. The primitive already renders `.hc-metric-card`, `.hc-metric-label`, `.hc-metric-value` — no duplication needed.

3. **Page layout** -- Page container uses `.hc-admin-overview-page` class: max-width around 1100px (or full-width with right padding), internal padding 24px. Page header uses `.hc-admin-overview-header` with title "Platform Metrics" (left) and refresh button (right). Stat cards use `.hc-admin-overview-stats` grid: 5 cards, responsive column layout, 12px gap.

4. **Refresh button** -- "Refresh" button uses `.btn-standard` (default 98.css gray). Accessible label preserved. Click still invalidates the `['admin', 'metrics']` query.

5. **Replace navigation cards with `.hc-fieldset` decision panels** -- The two current `<button>` cards (User Management, Extraction Error Queue) become `<fieldset class="hc-fieldset">` panels with:
   - `<legend>` for the section name
   - `.hc-admin-overview-section-desc` paragraph describing what the admin can do there
   - `.btn-standard` action button inside `.hc-admin-overview-section-action` row
   - Preserve the `goto('/admin/users')` / `goto('/admin/documents')` navigation behavior
   - No `<svg>` chevron icons — replace with a right-aligned button labeled "Open →" (or similar) for 98.css consistency

6. **Loading state** -- Skeleton grid stays semantically correct with `role="status"` and `aria-label="Loading metrics"`, but uses `.hc-admin-overview-skeleton` + `.hc-admin-overview-skeleton-card` classes in place of Tailwind `animate-pulse` + `bg-muted`. Animation via CSS keyframes on the new class (keep visual intent, drop Tailwind primitive).

7. **Error state** -- "Unable to load platform metrics" error uses `.hc-state .hc-state-error` design-system banner with `role="alert"`. "Try again" button uses `.btn-standard`. No inline Tailwind destructive colors.

8. **Rate formatting preserved** -- `formatRate()` helper, the `N/A` fallback, and the `metrics.*` property access remain unchanged. Zero behavior change in the `<script>` block except removing any imports not used after the rewrite.

9. **CSS follows established patterns** -- All new styles in `app.css` using `.hc-admin-overview-*` prefix. Reuse design tokens (`--text-primary`, `--text-secondary`, `--surface-sunken`, `--border-sunken-outer`, `--accent`). No duplication of existing `.hc-fieldset`, `.hc-metric-*`, `.hc-state-*`, `.btn-*` styles.

10. **Tests** -- Update `(admin)/admin/page.test.ts`:
    - Page container has `.hc-admin-overview-page` class
    - 5 `.hc-metric-card` elements render after metrics load
    - Each card shows the correct label and value (total_signups, total_uploads, upload_success_rate formatted, documents_error_or_partial, ai_interpretation_completion_rate formatted)
    - Refresh button has `.btn-standard` class and invalidates the query on click
    - User Management fieldset has `<legend>User Management</legend>` and an action button that calls `goto('/admin/users')`
    - Extraction Error Queue fieldset has `<legend>Extraction Error Queue</legend>` and an action button that calls `goto('/admin/documents')`
    - Loading skeleton uses `.hc-admin-overview-skeleton`
    - Error state uses `.hc-state-error` with `role="alert"`
    - Axe accessibility audit passes with zero violations
    - Verify no `$lib/components/ui/button|input|label|textarea` imports remain (regex-terminator pattern from 12-1/12-5 update)

11. **WCAG compliance** -- Fieldsets have descriptive legends. Error messages use `role="alert"`. Loading state uses `role="status"`. Refresh button retains `aria-label="Refresh metrics"`. Axe audit passes.

## Tasks / Subtasks

- [x] Task 1: Add `.hc-admin-overview-*` CSS classes to `app.css` (AC: 3, 5, 6, 9)
  - [x] `.hc-admin-overview-page` — container layout (max-width, padding, centering)
  - [x] `.hc-admin-overview-header` — flex row with title (left) and refresh button (right)
  - [x] `.hc-admin-overview-title` — page heading
  - [x] `.hc-admin-overview-stats` — 5-card responsive grid
  - [x] `.hc-admin-overview-sections` — flex column, 16px gap for fieldset panels
  - [x] `.hc-admin-overview-section-desc` — description paragraph inside fieldset
  - [x] `.hc-admin-overview-section-action` — right-aligned action button row
  - [x] `.hc-admin-overview-skeleton` + `.hc-admin-overview-skeleton-card` — loading placeholder with CSS keyframe animation

- [x] Task 2: Rewrite `+page.svelte` template (AC: 1, 2, 4, 5, 6, 7, 8)
  - [x] Import `MetricCard` from `$lib/components/ui/metric-card`
  - [x] Replace `<main class="p-8">` with `<main class="hc-admin-overview-page">`
  - [x] Replace header `<div class="mb-6 flex items-center justify-between">` with `<header class="hc-admin-overview-header">`
  - [x] Swap refresh button Tailwind classes for `.btn-standard`
  - [x] Replace 5 inline stat `<div>` blocks with 5 `<MetricCard label={...} value={...} />`
  - [x] Rewrite pending/error states using `.hc-state`/`.hc-state-error` and skeleton classes
  - [x] Replace navigation `<button>` cards with `<fieldset class="hc-fieldset"><legend>...</legend>...</fieldset>`
  - [x] Verify no `<svg>` icons remain in the 2 navigation panels
  - [x] Preserve `handleRefresh` and `formatRate` exactly

- [x] Task 3: Preserve behavior (AC: 8)
  - [x] `createQuery` config unchanged (no refetchOnWindowFocus, no refetchOnReconnect)
  - [x] `queryClient.invalidateQueries({ queryKey: ['admin', 'metrics'] })` unchanged
  - [x] `goto` navigation targets unchanged (`/admin/users`, `/admin/documents`)

- [x] Task 4: Update tests (AC: 10)
  - [x] Add CSS class assertions for 5 metric cards, fieldsets, error state
  - [x] Add test: refresh button click calls queryClient.invalidateQueries
  - [x] Add test: User Management action button calls goto('/admin/users')
  - [x] Add test: Extraction Error Queue action button calls goto('/admin/documents')
  - [x] Add loading-state and error-state class tests
  - [x] Add axe audit test
  - [x] Add import-guard regex test (block shadcn-svelte primitives, mirror settings/page.test.ts pattern)

- [x] Task 5: WCAG audit (AC: 11)
  - [x] All fieldsets have `<legend>`
  - [x] Error has `role="alert"`
  - [x] Loading has `role="status"` + `aria-label`
  - [x] Refresh button has `aria-label="Refresh metrics"`
  - [x] Axe audit passes

### Review Findings

- [x] [Review][Defer] Nested `<main>` element — AdminShell provides outer `<main>`; inner `<main class="hc-admin-overview-page">` creates invalid HTML landmark. Same bug exists project-wide in `settings/+page.svelte:349` and likely other routes. Deferred to Story 13-5 a11y audit (pattern-wide fix). [+page.svelte:27]
- [x] [Review][Defer] Refresh button has no disabled-during-fetch state — parity with pre-13-1 Tailwind; no correctness bug (TanStack dedupes), UX polish. Deferred to Story 13-5 or separate polish pass. [+page.svelte:30-37]
- [x] [Review][Defer] `role="alert"` banner wraps action button — project-wide `.hc-state-*` pattern. Screen readers may announce button label with alert. Would need sweep of all error banners. Deferred to Story 13-5 a11y audit. [+page.svelte:50-54]
- [x] [Review][Defer] Empty success-state fallback — theoretical given TypeScript + apiFetch contracts; page renders empty if `query.isSuccess && !query.data`. Not a regression. Deferred. [+page.svelte:58]

## Dev Notes

### Architecture & Patterns

- **Reskin only — preserve all behavior**: The page's `createQuery`, `handleRefresh`, `formatRate` functions, navigation handlers, and all state transitions are correct. Only replace the template markup and CSS classes. Same discipline as Stories 11-1, 12-1, 12-3.
- **Admin shell is already 98.css**: `AdminShell.svelte` (from Story 9-3) wraps this route via `(admin)/+layout.svelte` and provides the title-bar, left nav, and status bar. This story only touches the inner page content. Do NOT modify AdminShell or the layout.
- **Reuse `MetricCard` primitive**: `$lib/components/ui/metric-card/metric-card.svelte` already renders the sunken-panel stat card with `.hc-metric-card`, `.hc-metric-label`, `.hc-metric-value`. No new stat-card markup or CSS needed.
- **Match the design mockup**: Compare against `ux-design-directions-v2.html` and `ux-page-mockups.html#11` in planning-artifacts before marking done. The overview should look like a Windows 98 properties dialog, not a rounded Tailwind card grid. (This is Epic 11 retro Action 1 applied — mockup comparison is mandatory before "done".)

### Current Page Structure (What to Change)

```svelte
<!-- CURRENT: Tailwind + inline stat cards + rounded navigation buttons -->
<main class="p-8">
  <div class="mb-6 flex items-center justify-between">
    <h1 class="text-2xl font-semibold">Platform Metrics</h1>
    <button class="rounded-md border border-border px-4 py-2 ...">Refresh</button>
  </div>
  <div class="grid grid-cols-3 gap-4">
    <div class="rounded-lg border border-border bg-card p-6">
      <p class="text-sm text-muted-foreground">Total Signups</p>
      <p class="mt-2 text-3xl font-bold tabular-nums">{metrics.total_signups}</p>
    </div>
    <!-- 4 more similar blocks -->
  </div>
  <button class="flex w-full items-center justify-between rounded-lg ...">
    <!-- User Management navigation card -->
  </button>
</main>
```

```svelte
<!-- TARGET: 98.css MetricCard + fieldset decision panels -->
<main class="hc-admin-overview-page">
  <header class="hc-admin-overview-header">
    <h1 class="hc-admin-overview-title">Platform Metrics</h1>
    <button class="btn-standard" aria-label="Refresh metrics" onclick={handleRefresh}>
      Refresh
    </button>
  </header>

  {#if metricsQuery.isPending}
    <div role="status" aria-label="Loading metrics" class="hc-admin-overview-skeleton">
      {#each Array(5) as _}
        <div class="hc-admin-overview-skeleton-card"></div>
      {/each}
    </div>
  {:else if metricsQuery.isError}
    <div class="hc-state hc-state-error" role="alert">
      <p class="hc-state-title">Unable to load platform metrics.</p>
      <p>Try refreshing the page or contact support if the issue persists.</p>
      <button class="btn-standard" onclick={handleRefresh}>Try again</button>
    </div>
  {:else if metricsQuery.data}
    {@const metrics = metricsQuery.data}
    <div class="hc-admin-overview-stats">
      <MetricCard label="Total Signups" value={metrics.total_signups} />
      <MetricCard label="Total Uploads" value={metrics.total_uploads} />
      <MetricCard label="Upload Success Rate" value={formatRate(metrics.upload_success_rate)} />
      <MetricCard label="Error / Partial Documents" value={metrics.documents_error_or_partial} />
      <MetricCard label="AI Interpretation Rate" value={formatRate(metrics.ai_interpretation_completion_rate)} />
    </div>

    <div class="hc-admin-overview-sections">
      <fieldset class="hc-fieldset">
        <legend>User Management</legend>
        <p class="hc-admin-overview-section-desc">
          View accounts, manage suspension, and review flagged values.
        </p>
        <div class="hc-admin-overview-section-action">
          <button class="btn-standard" onclick={() => goto('/admin/users')}>Open →</button>
        </div>
      </fieldset>

      <fieldset class="hc-fieldset">
        <legend>Extraction Error Queue</legend>
        <p class="hc-admin-overview-section-desc">
          Review and correct documents with extraction problems.
        </p>
        <div class="hc-admin-overview-section-action">
          <button class="btn-standard" onclick={() => goto('/admin/documents')}>Open →</button>
        </div>
      </fieldset>
    </div>
  {/if}
</main>
```

### CSS Classes to Add (app.css)

| Class | Purpose |
|-------|---------|
| `.hc-admin-overview-page` | `max-width: 1100px; margin: 0; padding: 24px;` |
| `.hc-admin-overview-header` | `display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;` |
| `.hc-admin-overview-title` | `font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0;` |
| `.hc-admin-overview-stats` | `display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 16px;` |
| `.hc-admin-overview-sections` | `display: flex; flex-direction: column; gap: 16px;` |
| `.hc-admin-overview-section-desc` | `font-size: 14px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 12px;` |
| `.hc-admin-overview-section-action` | `display: flex; justify-content: flex-end;` |
| `.hc-admin-overview-skeleton` | `display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px;` |
| `.hc-admin-overview-skeleton-card` | `background: var(--surface-sunken); height: 84px; box-shadow: inset ...` (mirror `.hc-metric-card` chrome) + `@keyframes` pulse animation |

### Existing CSS Classes to Reuse (already in `app.css`)

- `.hc-fieldset` + `legend` — 98.css fieldset with accent bold legend
- `.hc-metric-card`, `.hc-metric-label`, `.hc-metric-value` — stat card primitives (via `MetricCard` component)
- `.btn-standard` — default 98.css gray button
- `.hc-state`, `.hc-state-error` — feedback banners
- `.hc-state-title` — banner heading

### Backend API Contract (No Changes)

```
GET /api/v1/admin/metrics
Authorization: Bearer <access_token> (admin role required)
Response 200:
{
  "total_signups": int,
  "total_uploads": int,
  "upload_success_rate": float | null,
  "documents_error_or_partial": int,
  "ai_interpretation_completion_rate": float | null
}
```

Type `AdminMetrics` already defined in `$lib/types/api.ts`. API function `getAdminMetrics()` already implemented in `$lib/api/admin.ts`. No changes to either.

### Previous Story Learnings (carry forward)

From Stories 12-1 through 12-5 (latest delivered) and 11-1 through 11-5:

- Use `.hc-*` CSS classes exclusively. No Tailwind structural classes. No scoped styles. No inline styles.
- Section-based CSS prefix naming (`.hc-admin-overview-*` here)
- Reset 98.css button base on custom interactive elements if needed (`min-width: 0; box-shadow: none; text-shadow: none;`)
- Use `var(--accent-text)` not hardcoded `#fff` on accent backgrounds
- Add `:focus-visible` on any custom interactive elements
- **Import-guard test**: use regex `not.toMatch(/from '\$lib\/components\/ui\/button['/]/)` with terminators (not substring). This was tightened in Story 12-5 / epic-12-retro Action 1 patch — do not regress to substring matching.
- Axe audit test required; Axe must pass zero violations
- Compare against `ux-design-directions-v2.html` mockup before marking done (Epic 11 retro Action 1)
- Baseline test count at start of this story: 528 (Epic 12 close + confirm-dialog extraction). Maintain zero regressions.
- Story 12-4 introduced the `ConfirmDialog` primitive. If admin actions in future stories (13-2/13-3) need confirmations, use `$lib/components/ui/confirm-dialog` — do NOT copy inline dialog markup from 12-4.

### Files to Modify

| File | Changes |
|------|---------|
| `healthcabinet/frontend/src/app.css` | Add `.hc-admin-overview-*` classes (~9 new classes + 1 keyframe) |
| `healthcabinet/frontend/src/routes/(admin)/admin/+page.svelte` | Replace template markup (MetricCard, fieldsets, state classes) |
| `healthcabinet/frontend/src/routes/(admin)/admin/page.test.ts` | Expand test coverage (CSS classes, state feedback, axe audit, import-guard regex) |

### Project Structure Notes

- `MetricCard` primitive lives at `lib/components/ui/metric-card/` — reuse it, do NOT create a new stat-card component
- AdminShell provides the surrounding chrome — do NOT touch `(admin)/+layout.svelte` or `AdminShell.svelte`
- The admin route lives under `routes/(admin)/admin/` due to SvelteKit's group + nested-route convention
- Test wrapper `AdminMetricsPageTestWrapper.svelte` exists — update it only if the page's props/dependencies change (they won't)

### References

- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md#11-admin-dashboard — Admin Overview wireframe, stat cards, decision surfaces]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Form patterns, typography, color tokens]
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md#fe-epic-7 — FE Epic 7 Story 1 scope]
- [Source: _bmad-output/planning-artifacts/epics.md — Epic 13 summary, FR34-FR38]
- [Source: _bmad-output/planning-artifacts/prd.md — FR34 (admin platform metrics)]
- [Source: _bmad-output/implementation-artifacts/5-1-admin-platform-metrics-dashboard.md — original admin metrics story with backend contract]
- [Source: _bmad-output/implementation-artifacts/12-1-medical-profile-page-redesign.md — reskin pattern reference]
- [Source: _bmad-output/implementation-artifacts/epic-12-retro-2026-04-15.md — Action 1 context (ConfirmDialog for future admin confirmations)]
- [Source: _bmad-output/implementation-artifacts/spec-confirm-dialog-extraction.md — ConfirmDialog API if confirmations are needed]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add the `.hc-admin-overview-*` layout, section, and skeleton classes to `healthcabinet/frontend/src/app.css`, reusing existing `hc-fieldset`, `hc-state-*`, `hc-metric-*`, and `btn-standard` primitives.
- Rewrite `healthcabinet/frontend/src/routes/(admin)/admin/+page.svelte` as a behavior-preserving reskin: keep `createQuery`, `formatRate()`, refresh invalidation, and `goto()` targets unchanged while switching the markup to `MetricCard`, fieldsets, and shared state surfaces.
- Expand `healthcabinet/frontend/src/routes/(admin)/admin/page.test.ts` to cover the new classes, fieldset/navigation semantics, loading and error states, refresh invalidation, axe, and the import-guard regex.
- Run focused frontend validation first, then broader checks if needed before marking the story ready for review.

### Debug Log References

- 2026-04-15: `docker compose -f /Users/vladtara/dev/set-bmad/healthcabinet/docker-compose.yml exec frontend npm run test:unit -- src/routes/'(admin)'/admin/page.test.ts` — passed (10/10)
- 2026-04-15: `docker compose -f /Users/vladtara/dev/set-bmad/healthcabinet/docker-compose.yml exec frontend npm run check` — passed with 0 errors and 1 existing unrelated warning in `src/lib/components/health/AIChatWindow.svelte:179`
- 2026-04-15: `docker compose -f /Users/vladtara/dev/set-bmad/healthcabinet/docker-compose.yml exec frontend npm run test:unit` — failed outside story scope in existing tests:
  - `src/routes/(app)/documents/page.test.ts`
  - `src/lib/api/users.test.ts`
  - `src/lib/components/health/AIChatWindow.test.ts`

### Completion Notes List

- Replaced the admin overview Tailwind layout with `.hc-admin-overview-*` classes in `app.css`, including a dedicated skeleton grid and reduced-motion-safe pulse animation.
- Rebuilt the `/admin` route markup around `MetricCard`, shared `hc-state` banners, and `hc-fieldset` decision panels while preserving `createQuery`, `formatRate()`, refresh invalidation, and both `goto()` targets.
- Removed the inline stat-card markup and the navigation chevron SVGs; the decision surfaces now use right-aligned `btn-standard` actions with contextual accessible labels.
- Expanded `page.test.ts` to cover the new layout classes, skeleton/error states, refresh invalidation, both admin navigation actions, axe, and the shadcn import guard.
- Story-specific validation is green. The broader frontend suite is currently red due unrelated existing failures listed above.

### Change Log

- 2026-04-15: Story implementation complete — Admin overview reskinned to shared 98.css primitives and route tests expanded.

### File List

- `healthcabinet/frontend/src/app.css` (modified — added `.hc-admin-overview-*` page, section, and skeleton styles)
- `healthcabinet/frontend/src/routes/(admin)/admin/+page.svelte` (modified — switched to `MetricCard`, fieldsets, shared state banners, and button primitives)
- `healthcabinet/frontend/src/routes/(admin)/admin/page.test.ts` (modified — added class, behavior, accessibility, and import-guard coverage)
