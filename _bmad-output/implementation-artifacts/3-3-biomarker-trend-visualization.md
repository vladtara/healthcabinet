# Story 3.3: Biomarker Trend Visualization

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a registered user with 2 or more uploads,
I want to see trend lines per biomarker across time,
so that I can understand whether my health values are improving, worsening, or stable.

## Acceptance Criteria

1. **Given** a user has 2 or more processed documents with overlapping biomarkers
   **When** they view a biomarker trend
   **Then** a `BiomarkerTrendChart` is displayed showing the value over time with data points for each upload date
   **And** a reference band showing the optimal range is overlaid on the chart
   **And** hovering over (or focusing on) a data point shows a tooltip with the exact value, unit, and upload date

2. **Given** a user has only one processed document
   **When** they view the trend section for a biomarker
   **Then** the chart renders in a disabled state with an "Upload another document to unlock trends" overlay
   **And** the disabled state does not show broken or empty axes

3. **Given** a `BiomarkerTrendChart` is rendered
   **Then** it is wrapped in a `<figure>` element with a `<figcaption>` describing the biomarker and date range
   **And** an accessible data table alternative is available for screen reader users (same data in tabular format)

4. **Given** a new document is successfully processed
   **When** the `document.completed` SSE event is received (in the documents page)
   **Then** the TanStack Query cache keys `['health_values']` and `['timeline']` are invalidated
   **And** trend charts update automatically without a page reload

5. **Given** a user views the dashboard on mobile (< 768px)
   **Then** inline sparklines are hidden and only the full chart view is shown to preserve readability

## Tasks / Subtasks

- [x] Task 1: Migrate dashboard data fetching to TanStack Query (prerequisite for reactive SSE updates) (AC: #4)
  - [x] Import `createQuery` and `useQueryClient` from `@tanstack/svelte-query` in `+page.svelte`
  - [x] Replace the `$state`/`$effect`/`Promise.allSettled` fetch pattern with two `createQuery` calls:
    - `createQuery({ queryKey: ['health_values'], queryFn: getHealthValues })`
    - `createQuery({ queryKey: ['baseline'], queryFn: getDashboardBaseline })`
  - [x] Derive `values`, `recommendations`, `hasUploads`, `loading`, `error` from query results using `$derived`
  - [x] Remove the `retry()` function; replace the "Try again" button with `queryClient.invalidateQueries({ queryKey: ['health_values'] })` + `queryClient.invalidateQueries({ queryKey: ['baseline'] })`
  - [x] Verify all existing tests still pass — the rendered HTML must stay identical to 3.2's implementation

- [x] Task 2: Add timeline invalidation to documents SSE handler (AC: #4)
  - [x] In `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte`, find the SSE `onmessage` handler (line ~160)
  - [x] After the existing `queryClient.invalidateQueries({ queryKey: ['health_values'] })` call (line 163), add:
    ```ts
    queryClient.invalidateQueries({ queryKey: ['timeline'] });
    ```
  - [x] This covers all per-biomarker `['timeline', name]` keys because TanStack Query matches on prefix

- [x] Task 3: Add `getHealthValueTimeline()` API helper and TypeScript types (AC: #1, #2, #3)
  - [x] Add to `healthcabinet/frontend/src/lib/api/health-values.ts`:
    ```typescript
    export interface HealthValueTimelineResponse {
      biomarker_name: string;
      canonical_biomarker_name: string;
      skipped_corrupt_records: number;
      values: HealthValue[]; // HealthValue already defined in same file; sorted oldest→newest
    }

    /**
     * Fetch all historical values for a single biomarker for the authenticated user.
     * Values are ordered oldest-first by measured_at.
     */
    export async function getHealthValueTimeline(
      canonicalBiomarkerName: string
    ): Promise<HealthValueTimelineResponse> {
      return apiFetch<HealthValueTimelineResponse>(
        `/api/v1/health-values/timeline/${encodeURIComponent(canonicalBiomarkerName)}`
      );
    }
    ```

- [x] Task 4: Build `BiomarkerTrendChart.svelte` component (AC: #1, #2, #3, #5)
  - [x] Install charting library: used raw SVG fallback (zero-dependency) — layerchart skipped per Dev Notes fallback; raw SVG is fully acceptable
  - [x] Create `healthcabinet/frontend/src/lib/components/health/BiomarkerTrendChart.svelte`
  - [x] Props interface:
    ```typescript
    interface Props {
      points: Array<{ date: string; value: number; unit: string | null }>;
      referenceRangeLow?: number | null;
      referenceRangeHigh?: number | null;
      unit?: string | null;
      biomarkerName: string;
    }
    ```
  - [x] Derive `hasEnoughData = points.length >= 2` — controls active vs disabled state
  - [x] **Active state (≥ 2 points):** render line chart with:
    - X-axis: date labels (format: `MMM 'YY`)
    - Y-axis: numeric value + unit
    - Reference range band between `referenceRangeLow` and `referenceRangeHigh` (skip band if both null)
    - Data points as dots, colored by the status of the latest point
    - Tooltip on hover/focus: value, unit, date (SVG `<title>` elements)
  - [x] **Disabled state (< 2 points):** render a placeholder container (same height as active chart), dim SVG background axes (decorative), centered overlay text: `"Upload another document to unlock trends"`; no broken or empty axes — uses static decorative placeholder lines
  - [x] **Accessibility wrapper:** `<figure>` with `<figcaption class="sr-only">`, `<details>` data table
  - [x] Mobile: sparkline `mini` variant hidden at < 768px (`hidden sm:block`) — full chart always shown on mobile

- [x] Task 5: Add sparklines to value cards + trend section to dashboard (AC: #1, #2, #5)
  - [x] **Sparklines in value cards** (inline, computed from existing `values` array — no extra API calls):
    - Derive `timelineByBiomarker` from the existing `values` query result:
      ```typescript
      const timelineByBiomarker = $derived(
        Object.fromEntries(
          [...new Set(values.map(v => v.canonical_biomarker_name))].map(name => [
            name,
            values
              .filter(v => v.canonical_biomarker_name === name)
              .sort((a, b) => new Date(a.measured_at ?? 0).getTime() - new Date(b.measured_at ?? 0).getTime())
          ])
        )
      );
      ```
    - In each value card `<article>`, add after the value+unit row:
      ```svelte
      {#if (timelineByBiomarker[value.canonical_biomarker_name]?.length ?? 0) >= 2}
        <div class="hidden sm:block mt-2 h-6 w-16">
          <BiomarkerTrendChart
            points={...}
            biomarkerName={value.biomarker_name}
            referenceRangeLow={value.reference_range_low}
            referenceRangeHigh={value.reference_range_high}
            unit={value.unit}
          />
        </div>
      {/if}
      ```
    - Sparkline variant: pass a `variant="sparkline"` prop to use 60×20px inline SVG, no axes, no tooltip, no reference band
  - [x] **Trend section below value cards:**
    - Add `<section aria-label="Biomarker trends">` below the value cards section
    - For each unique `canonical_biomarker_name` in `values`, render one full `BiomarkerTrendChart` per card via `BiomarkerTrendSection.svelte` (child component encapsulating per-biomarker createQuery)
    - Loading skeleton: `animate-pulse rounded-lg border border-border bg-card` placeholder (same pattern as existing)
    - Section heading: "Trends" (use `text-sm font-semibold text-muted-foreground mb-3`)
  - [x] Only render trend section when `values.length > 0` (same gate as active state)

- [x] Task 6: Add and update tests (AC: #1, #2, #3)
  - [x] Backend: add 1–2 tests in `tests/health_data/test_router.py` under a `# Story 3.3` section:
    - `test_get_health_value_timeline_returns_ordered_values` — 24 backend tests pass ✓
    - `test_get_health_value_timeline_empty_returns_empty_list` — passes ✓
  - [x] Frontend: add `BiomarkerTrendChart.test.ts` in `src/lib/components/health/`: 13/13 pass ✓
    - Renders disabled state with `points.length < 2`; overlay text present; no broken axes (no `NaN` in SVG)
    - Renders active state with `points.length >= 2`; `<figure>` and `<figcaption>` present
    - Accessible data table exists in `<details>` element
    - axe-core audit passes on both states
  - [x] Frontend: update `page.test.ts` to include `getHealthValueTimeline: vi.fn()` in the `$lib/api/health-values` mock
  - [x] Frontend: add dashboard test asserting sparklines hidden on narrow viewport and trend section present in active state; 14/14 pass ✓

## Dev Notes

### Current State — What Exists After Story 3.2

- Dashboard `+page.svelte` uses plain `$state`/`$effect`/`Promise.allSettled` (NO TanStack Query yet)
- Documents `+page.svelte` already uses TanStack Query — `queryClient.invalidateQueries({ queryKey: ['health_values'] })` fires on `document.completed` SSE (line 163 of documents page)
- `health-values.ts` exports: `HealthValue`, `getHealthValues()`, `flagHealthValue()`, `RecommendationItem`, `BaselineSummaryResponse`, `getDashboardBaseline()`
- `src/lib/components/health/` has: `HealthValueBadge.svelte`, `HealthValueRow.svelte`, `DocumentUploadZone.svelte`, `ProcessingPipeline.svelte`, `PartialExtractionCard.svelte`
- `HealthValueBadge` uses `role="img"` with `aria-label="{config.label} status"` (NOT `role="status"` — this was corrected in code review)
- 168 backend tests, 109 frontend tests all passing

### ⚠️ CRITICAL: Charting Library — Do NOT Use Recharts

The architecture document mentions "Recharts (Tailwind-native)" — **this is wrong**. Recharts is a React-only library and cannot run in Svelte 5.

**Use `layerchart`** — a Svelte-native charting library built on d3:
```bash
# Run inside the Docker container, not locally
docker compose exec frontend npm install layerchart
```

If `layerchart` is not suitable (API breaking changes), fallback option is raw SVG with computed coordinates — see Dev Notes below for the SVG approach.

### Backend Timeline Endpoint — Already Implemented (No Changes Needed)

```
GET /api/v1/health-values/timeline/{canonical_biomarker_name}
Authorization: Bearer <token>

Response: HealthValueTimelineResponse {
  biomarker_name: str
  canonical_biomarker_name: str
  skipped_corrupt_records: int   # corrupted/non-decryptable records skipped
  values: list[HealthValueResponse]  # same shape as GET /health-values items; ordered oldest→newest
}
```

`HealthValueResponse` fields useful for trend: `value` (float), `unit` (str|null), `measured_at` (datetime|null), `reference_range_low` (float|null), `reference_range_high` (float|null), `status` (Literal).

### Sparkline Optimization — Derive from Existing Data (No Extra API Calls)

The inline sparklines in value cards should be computed from the existing `values` array already fetched by TanStack Query — **do not call `getHealthValueTimeline()` per biomarker for sparklines**. That would be an N+1 API call per page load.

Group existing values by `canonical_biomarker_name`, sort by `measured_at`. Use this for sparklines. Reserve `getHealthValueTimeline()` for the full trend chart section only.

### TanStack Query Migration for Dashboard

`@tanstack/svelte-query` is already installed (v6.1.0). The `QueryClientProvider` must already be set up at a layout level (used by documents page) — verify in `src/routes/(app)/+layout.svelte`.

Migration pattern:
```typescript
import { createQuery, useQueryClient } from '@tanstack/svelte-query';
import { getHealthValues, getDashboardBaseline, getHealthValueTimeline } from '$lib/api/health-values';

const queryClient = useQueryClient();

const valuesQuery = createQuery({
  queryKey: ['health_values'],
  queryFn: getHealthValues
});

const baselineQuery = createQuery({
  queryKey: ['baseline'],
  queryFn: getDashboardBaseline
});

// Derived state from queries
const values = $derived(valuesQuery.data ?? []);
const recommendations = $derived(baselineQuery.data?.recommendations ?? []);
const hasUploads = $derived(baselineQuery.data?.has_uploads ?? false);
const loading = $derived(valuesQuery.isPending || baselineQuery.isPending);
const error = $derived(
  valuesQuery.isError && baselineQuery.isError
    ? 'Unable to load your health data. Please try again.'
    : null
);
```

Replace retry function:
```typescript
function retry() {
  queryClient.invalidateQueries({ queryKey: ['health_values'] });
  queryClient.invalidateQueries({ queryKey: ['baseline'] });
}
```

### Per-Biomarker Timeline Query (in trend section)

```typescript
// One createQuery per unique canonical_biomarker_name
const timelineQuery = createQuery({
  queryKey: ['timeline', canonicalBiomarkerName],
  queryFn: () => getHealthValueTimeline(canonicalBiomarkerName),
  enabled: values.length > 0  // don't fetch until we have values
});
```

TanStack Query matches `['timeline']` prefix when invalidating, so `queryClient.invalidateQueries({ queryKey: ['timeline'] })` refreshes all per-biomarker timelines.

### Fallback: Raw SVG Sparkline (if layerchart causes issues)

For sparklines especially, a simple hand-rolled SVG requires no library:
```svelte
<svg width="60" height="20" aria-hidden="true" focusable="false">
  {#if points.length >= 2}
    {@const minV = Math.min(...points.map(p => p.value))}
    {@const maxV = Math.max(...points.map(p => p.value))}
    {@const range = maxV - minV || 1}
    {@const coords = points.map((p, i) => {
      const x = (i / (points.length - 1)) * 58 + 1;
      const y = 19 - ((p.value - minV) / range) * 18;
      return `${x},${y}`;
    }).join(' ')}
    <polyline points={coords} fill="none" stroke="#4F6EF7" stroke-width="1.5" />
  {/if}
</svg>
```
This zero-dependency approach is acceptable for the `mini` sparkline variant.

### Health Status Color Tokens (from Story 3.2 — reuse exactly)

| Status | Text color | Background |
|---|---|---|
| optimal | `text-[#2DD4A0]` | `bg-[#2DD4A0]/15` |
| borderline | `text-[#F5C842]` | `bg-[#F5C842]/15` |
| concerning | `text-[#F08430]` | `bg-[#F08430]/15` |
| action_needed | `text-[#E05252]` | `bg-[#E05252]/15` |

Use the latest status in `timeline.values` to color the sparkline polyline and trend chart data points.

### Architecture Compliance

- `user_id` from `Depends(get_current_user)` only (backend enforced; no changes to backend auth)
- Encryption/decryption in `repository.py` only; `service.py` works with decrypted floats
- New Svelte components go in `src/lib/components/health/`
- No new backend endpoints — `GET /health-values/timeline/{name}` already exists in `router.py`
- Story 3.2's empty state (baseline recs + upload CTA) must remain byte-for-byte unchanged

### File Structure Requirements

Backend (no changes expected beyond tests):
- `healthcabinet/backend/tests/health_data/test_router.py` — add Story 3.3 section

Frontend files to change:
- `healthcabinet/frontend/src/lib/api/health-values.ts` — add `HealthValueTimelineResponse` + `getHealthValueTimeline()`
- `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte` — migrate to TanStack Query, add sparklines + trend section
- `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts` — extend mock + add new tests
- `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` — add `['timeline']` invalidation (1-line change)

New frontend files to create:
- `healthcabinet/frontend/src/lib/components/health/BiomarkerTrendChart.svelte`
- `healthcabinet/frontend/src/lib/components/health/BiomarkerTrendChart.test.ts`

### Testing Requirements

**Run inside Docker Compose only — never locally:**
```bash
docker compose exec backend uv run pytest tests/health_data/test_router.py
docker compose exec frontend npm run test:unit
```

**Backend tests** (under `# Story 3.3` in `test_router.py`):
```python
# Use existing fixture pattern from Story 3.2:
# make_user(), make_document(), replace_document_health_values() (or equivalent)
#
# test 1: two values for same canonical_biomarker_name
#   - Insert measured_at=T1 (older) and measured_at=T2 (newer)
#   - GET /health-values/timeline/glucose
#   - Assert len(values) == 2
#   - Assert values[0].measured_at < values[1].measured_at  (oldest-first ordering)
#
# test 2: empty timeline for unknown biomarker
#   - GET /health-values/timeline/nonexistent_biomarker
#   - Assert values == [] and skipped_corrupt_records == 0
```

**Frontend test mock extension** (critical — will break tests if missing):
```typescript
vi.mock('$lib/api/health-values', () => ({
  getHealthValues: vi.fn(),
  getDashboardBaseline: vi.fn(),
  getHealthValueTimeline: vi.fn(),  // ← ADD THIS
  flagHealthValue: vi.fn(),
}));
```

**axe-core audit** must pass on `BiomarkerTrendChart` in both disabled and active states.

### Previous Story Learnings (from 3.2)

- `Promise.allSettled` is the pattern for parallel fetches — but now we're migrating to TanStack Query; do not mix both patterns in the same component
- `role="img"` with `aria-label` on status indicators (corrected from `role="status"` in code review)
- Skeleton pattern: `animate-pulse rounded-lg border border-border bg-card p-5` with inner `h-4 w-2/5 rounded bg-muted` divs — reuse exactly
- `renderComponent` test utility at `$lib/test-utils/render`
- Dark neutral theme: `bg-card`, `border-border`, `text-muted-foreground` for structural elements; hardcoded hex only for health status/accent colors
- `$lib/components/ui/button` for Button component
- Code review patched `retry()` closure — the new TanStack Query `retry` (via `queryClient.invalidateQueries`) avoids that class of bug entirely

### Antipatterns to Prevent

- **Do NOT install Recharts** — it is React-only; use `layerchart` or raw SVG
- **Do NOT create a new backend timeline endpoint** — `GET /health-values/timeline/{name}` already exists in `router.py`
- **Do NOT break the existing value cards, stat cards, or empty state** from Story 3.2
- **Do NOT show broken axes or `NaN` SVG coordinates** in the disabled state — use a static decorative placeholder
- **Do NOT fetch `getHealthValueTimeline()` per biomarker for inline sparklines** — that's an N+1 call; derive from existing `values` array
- **Do NOT mix TanStack Query and the old `$state`/`$effect`/`Promise.allSettled` pattern** in the same component after migration
- **Do NOT forget the accessible `<details>` data table** inside `BiomarkerTrendChart` (AC #3)
- **Do NOT skip updating the `$lib/api/health-values` mock** in `page.test.ts` — omitting `getHealthValueTimeline: vi.fn()` will cause all existing tests to fail

### References

- Epic source: `_bmad-output/planning-artifacts/epics.md` (Story 3.3 section)
- Architecture: `_bmad-output/planning-artifacts/architecture.md`
- UX design spec: `_bmad-output/planning-artifacts/ux-design-specification.md` (TrendChart anatomy, sparkline spec, status colors)
- UX page spec: `_bmad-output/planning-artifacts/ux-page-specifications.md` (dashboard trend section layout)
- Previous story: `_bmad-output/implementation-artifacts/3-2-health-values-dashboard-with-context-indicators.md`
- Backend router: `healthcabinet/backend/app/health_data/router.py`
- Backend schemas: `healthcabinet/backend/app/health_data/schemas.py`
- Backend service: `healthcabinet/backend/app/health_data/service.py`
- Backend tests: `healthcabinet/backend/tests/health_data/test_router.py`
- Frontend dashboard: `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte`
- Frontend documents: `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` (SSE pattern to reuse)
- Frontend API: `healthcabinet/frontend/src/lib/api/health-values.ts`
- Frontend tests: `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts`
- Frontend package: `healthcabinet/frontend/package.json` (no charting library yet)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Auto-discovered story: `3-3-biomarker-trend-visualization` from sprint-status.yaml (first backlog story)
- Read `schemas.py`: `HealthValueTimelineResponse` contains `{ biomarker_name, canonical_biomarker_name, skipped_corrupt_records, values: list[HealthValueResponse] }`
- Read `router.py`: confirmed `GET /health-values/timeline/{canonical_biomarker_name}` exists with `get_current_user` dependency
- Read `health-values.ts`: confirmed current exports; `getHealthValueTimeline` not yet added
- Read `+page.svelte` (dashboard): uses `$state`/`$effect`/`Promise.allSettled` — NO TanStack Query yet
- Read `+page.svelte` (documents): TanStack Query `queryClient.invalidateQueries(['health_values'])` already fires on SSE completion (line 163); `['timeline']` invalidation not yet added
- Architecture doc says "Recharts (Tailwind-native)" — this is incorrect for Svelte 5; flagged as architecture doc discrepancy
- Optimization identified: sparklines can be derived from existing `values` array (N+1 prevention)
- Confirmed `@tanstack/svelte-query` v6.1.0 already in package.json (no new install needed for query library itself)

### Completion Notes List

- Task 1: Migrated dashboard `+page.svelte` from `$state`/`$effect`/`Promise.allSettled` to TanStack Query (`createQuery`). All 11 original tests preserved; added `DashboardPageTestWrapper.svelte` for `QueryClientProvider` wrapping in tests (same pattern as documents page).
- Task 2: Added `queryClient.invalidateQueries({ queryKey: ['timeline'] })` to documents SSE handler after health_values invalidation — covers all per-biomarker `['timeline', name]` cache keys via prefix matching.
- Task 3: Added `HealthValueTimelineResponse` interface and `getHealthValueTimeline()` function to `health-values.ts`.
- Task 4: Built `BiomarkerTrendChart.svelte` using raw SVG (zero-dependency fallback per Dev Notes). Full chart: polyline + circles + reference band + axes + `<title>` tooltips. Disabled state: decorative placeholder lines + centered overlay. Sparkline variant: 60×20px `<polyline>`, `aria-hidden`. Accessibility: `<figure>`, `<figcaption class="sr-only">`, `<details>` data table.
- Task 5: Added sparklines in value cards (derived from existing `values` array — no N+1 calls). Added `BiomarkerTrendSection.svelte` child component encapsulating per-biomarker `createQuery` calls. Added "Trends" section using these child components.
- Task 6: Backend 24/24 pass. Frontend: BiomarkerTrendChart 13/13, dashboard 14/14. Pre-existing failures (9) in documents/upload tests are unrelated to this story.

### File List

healthcabinet/frontend/src/lib/api/health-values.ts
healthcabinet/frontend/src/lib/components/health/BiomarkerTrendChart.svelte
healthcabinet/frontend/src/lib/components/health/BiomarkerTrendChart.test.ts
healthcabinet/frontend/src/lib/components/health/BiomarkerTrendSection.svelte
healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte
healthcabinet/frontend/src/routes/(app)/dashboard/DashboardPageTestWrapper.svelte
healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts
healthcabinet/frontend/src/routes/(app)/documents/+page.svelte
healthcabinet/backend/tests/health_data/test_router.py

### Review Findings

- [x] [Review][Patch] Reference range band uses `values[0]` (oldest) — use `values[values.length - 1]` (most recent) for the reference band since it reflects current clinical context [`BiomarkerTrendSection.svelte:33-34`]

- [x] [Review][Patch] `$derived(() => ...)` should be `$derived.by(() => ...)` for `sparklineCoords`, `yRange`, `yTicks` — current form makes the derived hold a function object; reactivity to `points` changes is not tracked by Svelte [`BiomarkerTrendChart.svelte:40,68,104`]
- [x] [Review][Patch] Data points and sparkline polyline use hardcoded `#4F6EF7` — spec requires coloring by the latest point's status (optimal/borderline/concerning/action_needed color tokens) [`BiomarkerTrendChart.svelte:131,204,208`]
- [x] [Review][Patch] `<figure aria-label>` and inner `<svg aria-label>` both have `aria-label` — screen readers double-announce; remove `aria-label` from `<figure>` and let `<figcaption class="sr-only">` carry the description [`BiomarkerTrendChart.svelte:136,142`]
- [x] [Review][Patch] `sm:block` breakpoint (640px) should be `md:block` (768px) to match AC5 "< 768px" requirement [`+page.svelte:159`]
- [x] [Review][Patch] `BiomarkerTrendSection` has no error state — a network failure on the timeline query silently hides the section with no message or retry affordance [`BiomarkerTrendSection.svelte:20-37`]
- [x] [Review][Patch] `error` derived uses `&&` (both queries must fail) — a single-query failure (e.g. only `valuesQuery` errors) is silently swallowed; change to `||` or add per-query error display [`+page.svelte:34-38`]
- [x] [Review][Patch] Sparkline sort uses `measured_at ?? 0` (epoch 1970 for null) — should use `measured_at ?? created_at` to match the date field mapping used in the chart [`+page.svelte:56`]
- [x] [Review][Patch] `PLOT_W` and `PLOT_H` are `$derived` from pure constants — should be `const` to avoid unnecessary reactive nodes and avoid misleading maintainers [`BiomarkerTrendChart.svelte:61-62`]
- [x] [Review][Patch] `retry()` doesn't invalidate `['timeline']` queries — after a combined error the trend section stays stale when the user retries [`+page.svelte:65-68`]

- [x] [Review][Defer] Date timezone ambiguity — `new Date("2026-01-01")` parsed as UTC midnight then displayed in local time; users west of UTC may see the previous calendar day [`BiomarkerTrendChart.svelte:29-37`] — deferred, pre-existing/systemic
- [x] [Review][Defer] X-axis label overlap for 6–9 data points — modulo condition renders adjacent labels at indices N-2 and N-1 which can overlap at shorter date strings [`BiomarkerTrendChart.svelte:179`] — deferred, pre-existing
- [x] [Review][Defer] Backend test ISO string comparison is lexicographic — works correctly for UTC zero-padded timestamps but fragile if serializer emits non-UTC offsets [`test_router.py:804`] — deferred, low risk for current UTC fixture data
- [x] [Review][Defer] `hasValues` prop always `true` inside `uniqueBiomarkers` loop — redundant guard (loop only executes when values exist); no functional impact [`+page.svelte:184`] — deferred, code smell only
- [x] [Review][Defer] `make_document(status="completed")` fixture contract not visible in diff — test passes in practice; confirm fixture sets `status` correctly if adding similar tests [`test_router.py`] — deferred, low risk

### Change Log

- 2026-03-25: Story 3.3 created — biomarker trend visualization; migrates dashboard to TanStack Query; introduces `BiomarkerTrendChart` component with layerchart (not Recharts); sparklines derived from existing values array; full trend section per-biomarker; SSE invalidation of `['timeline']` key added to documents page handler
- 2026-03-26: Story 3.3 implemented — dashboard migrated to TanStack Query; `BiomarkerTrendChart` built with raw SVG (fallback per Dev Notes); `BiomarkerTrendSection` child component for per-biomarker queries; sparklines in value cards; trend section; 2 new backend tests; 13 new frontend component tests + 3 new dashboard tests; all passing
