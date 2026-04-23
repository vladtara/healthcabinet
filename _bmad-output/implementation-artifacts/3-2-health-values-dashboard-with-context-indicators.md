# Story 3.2: Health Values Dashboard with Context Indicators

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a registered user,
I want to view my extracted health values with clear contextual status indicators,
so that I can understand whether each value is normal, borderline, or concerning without needing medical training.

## Acceptance Criteria

1. **Given** a user has at least one successfully processed document **When** they visit the dashboard **Then** all extracted health values are displayed as value cards **And** each card shows: biomarker name, value with unit, and a `HealthValueBadge` with one of four states: `Optimal` / `Borderline` / `Concerning` / `Action needed`

2. **Given** a `HealthValueBadge` is rendered **Then** it always shows both a color and a text label — color is never the sole indicator **And** the color contrast ratio meets WCAG 2.1 AA minimum of 4.5:1

3. **Given** a value card is rendered **Then** a plain-language note is shown alongside the status badge explaining what the value means in context (no orphaned numbers)

4. **Given** reference ranges are demographic-adjusted **When** a user's age and sex are available from their profile **Then** the reference range used for status determination matches their demographic group

5. **Given** one or more values have `confidence < 0.7` **When** the dashboard renders **Then** a `ConfidenceWarning` indicator is shown on those value cards

6. **Given** a user navigates the dashboard with keyboard **Then** all value cards are reachable via Tab and focusable with visible focus indicators

7. **Given** the dashboard renders after authentication **When** the page loads **Then** content appears within 2 seconds **And** skeleton loaders are shown for each value card during the fetch

## Tasks / Subtasks

- [x] Task 1: Add `status` field to backend `HealthValueResponse` schema (AC: #1, #2, #4)
  - [x] Add `status: Literal["optimal", "borderline", "concerning", "action_needed", "unknown"]` to `HealthValueResponse` in `schemas.py`
  - [x] Implement `_compute_status(value, ref_low, ref_high)` pure function in `service.py` using the algorithm in Dev Notes
  - [x] Update `_to_response()` in `service.py` to call `_compute_status()` and set the field
  - [x] Verify existing `test_get_health_values_returns_user_rows` still passes (field addition is additive/non-breaking)

- [x] Task 2: Add `getHealthValues()` API helper to frontend (AC: #1, #7)
  - [x] Add `getHealthValues()` function and `HealthValue` TypeScript type to `healthcabinet/frontend/src/lib/api/health-values.ts`
  - [x] `HealthValue` must mirror `HealthValueResponse` including the new `status` field with the same four-value literal union

- [x] Task 3: Build `HealthValueBadge` Svelte component (AC: #1, #2)
  - [x] Create `healthcabinet/frontend/src/lib/components/health/HealthValueBadge.svelte`
  - [x] Props: `status: 'optimal' | 'borderline' | 'concerning' | 'action_needed' | 'unknown'`
  - [x] Always renders color + text label (never color alone) — see color tokens in Dev Notes
  - [x] Text labels: "Optimal" / "Borderline" / "Concerning" / "Action needed" / "Unknown"
  - [x] Include `role="status"` or use semantic markup; ensure 4.5:1 contrast on `surface-card` background

- [x] Task 4: Implement active state in dashboard page (AC: #1, #2, #3, #5, #6, #7)
  - [x] Refactor `+page.svelte` to fetch both `getDashboardBaseline()` and `getHealthValues()` in parallel (see Dev Notes for pattern)
  - [x] When `values.length > 0` (active state): render stat cards row + value cards grid — do NOT render baseline recommendation cards
  - [x] When `values.length === 0` (empty state): render existing baseline rec cards + upload CTA (existing behavior from 3.1 — preserve exactly)
  - [x] Each value card: biomarker name, value (bold), unit, `HealthValueBadge`, plain-language note (template string from Dev Notes), reference range display, `ConfidenceWarning` when `confidence < 0.7`
  - [x] Stat cards at top of active state: count of Optimal / Borderline / Concerning / Action needed values
  - [x] Skeleton loaders during fetch (same pattern as existing: 3 animated placeholder divs in `role="status"` region)
  - [x] All value cards keyboard-reachable via `Tab`; add `tabindex="0"` to non-interactive card wrappers if needed; visible focus ring via Tailwind `focus-visible:ring-2`

- [x] Task 5: Add and update tests (AC: #1, #2, #3, #5, #7)
  - [x] Backend: add 2–3 tests in `test_router.py` under a `Story 3.2` section — verify `status` field is present on `GET /health-values`, verify `optimal` for in-range value, verify `action_needed` for significantly out-of-range value
  - [x] Frontend: update `vi.mock('$lib/api/health-values', ...)` in `page.test.ts` to include `getHealthValues: vi.fn()` (existing mock must be extended — failure to do this causes the import to fail)
  - [x] Frontend: add tests for active state: value cards render, `HealthValueBadge` shows correct label, `ConfidenceWarning` appears for low-confidence values, stat cards show correct counts, accessibility audit passes on active state

## Dev Notes

### Current State — What Exists

Story 3.1 implemented and shipped:
- `GET /api/v1/health-values/baseline` → `BaselineSummaryResponse` (`recommendations`, `has_uploads`)
- `GET /api/v1/health-values` → `list[HealthValueResponse]` (id, user_id, document_id, biomarker_name, canonical_biomarker_name, value, unit, reference_range_low, reference_range_high, measured_at, confidence, needs_review, is_flagged, flagged_at, created_at) — **no `status` field yet**
- Dashboard `+page.svelte` fetches baseline only, shows empty-state recommendations + upload CTA
- `health-values.ts` exports `flagHealthValue()`, `getDashboardBaseline()`, `RecommendationItem`, `BaselineSummaryResponse`
- `page.test.ts` mocks `getDashboardBaseline` and `flagHealthValue` — **must update mock when adding `getHealthValues`**

### Status Computation Algorithm (backend, add to `service.py`)

```python
def _compute_status(
    value: float,
    ref_low: float | None,
    ref_high: float | None,
) -> str:
    """Derive Optimal/Borderline/Concerning/Action needed from reference range."""
    if ref_low is None and ref_high is None:
        return "unknown"
    in_low = ref_low is None or value >= ref_low
    in_high = ref_high is None or value <= ref_high
    if in_low and in_high:
        return "optimal"
    # Two-bound case: percentage deviation from range
    if ref_low is not None and ref_high is not None:
        span = ref_high - ref_low
        if span > 0:
            pct = (ref_low - value) / span if value < ref_low else (value - ref_high) / span
            if pct <= 0.20:
                return "borderline"
            if pct <= 0.50:
                return "concerning"
            return "action_needed"
    # Single-bound case: value is outside the one provided bound
    return "borderline"
```

Update `_to_response()`:
```python
def _to_response(record: repository.HealthValueRecord) -> HealthValueResponse:
    return HealthValueResponse(
        ...  # existing fields unchanged
        status=_compute_status(record.value, record.reference_range_low, record.reference_range_high),
    )
```

**Demographic adjustment note:** Story 2.3's LangGraph extraction pipeline captures reference ranges directly from lab documents, which labs typically print as demographic-specific values. No separate adjustment table is required for MVP — the stored `reference_range_low`/`high` already reflects the lab's demographic context. True cross-lab normalization with a demographic reference database is a future enhancement.

### Frontend Data Fetching Pattern (parallel, matches existing Svelte 5 runes style)

```typescript
// In +page.svelte <script>
import { getDashboardBaseline, getHealthValues } from '$lib/api/health-values';

let loading = $state(true);
let values = $state<HealthValue[]>([]);
let recommendations = $state<RecommendationItem[]>([]);
let hasUploads = $state(false);
let error = $state<string | null>(null);

$effect(() => {
    let cancelled = false;
    Promise.all([getDashboardBaseline(), getHealthValues()])
        .then(([baseline, vals]) => {
            if (cancelled) return;
            recommendations = baseline.recommendations;
            hasUploads = baseline.has_uploads;
            values = vals;
            loading = false;
        })
        .catch(() => {
            if (cancelled) return;
            error = 'Unable to load your health data. Please try again.';
            loading = false;
        });
    return () => { cancelled = true; };
});
```

Use `values.length > 0` (not `hasUploads`) to decide which state to render. This handles edge cases where `has_uploads` is true but no values are returned.

### Health Status Color Tokens (apply as inline styles or custom Tailwind classes)

| Status | Color | Hex | Background (15% opacity) |
|---|---|---|---|
| Optimal | `#2DD4A0` | green | `bg-[#2DD4A0]/15 text-[#2DD4A0]` |
| Borderline | `#F5C842` | yellow | `bg-[#F5C842]/15 text-[#F5C842]` |
| Concerning | `#F08430` | orange | `bg-[#F08430]/15 text-[#F08430]` |
| Action needed | `#E05252` | red | `bg-[#E05252]/15 text-[#E05252]` |
| Unknown | muted | — | `bg-muted text-muted-foreground` |

These use the project's established inline Tailwind color pattern (same as category badges in Story 3.1 using `bg-[#4F6EF7]/15 text-[#4F6EF7]`).

### Plain-Language Note Templates (compute on frontend, not backend)

```typescript
const STATUS_NOTES: Record<string, string> = {
    optimal: 'Within healthy reference range.',
    borderline: 'Slightly outside reference range — worth monitoring.',
    concerning: 'Outside reference range — consider discussing with your doctor.',
    action_needed: 'Significantly outside reference range — please consult your doctor.',
    unknown: 'No reference range available for this value.',
};
```

### ConfidenceWarning Pattern

Inline indicator for values where `confidence < 0.7`:
```svelte
{#if value.confidence < 0.7}
    <span class="text-xs text-[#F5C842]" title="Low extraction confidence — value may be inaccurate">
        ⚠ Low confidence
    </span>
{/if}
```

This is presentational only — no backend changes needed.

### Stat Cards (active state, top of dashboard)

Four cards showing counts by status. Compute from `values` array:
```typescript
const counts = $derived({
    optimal: values.filter(v => v.status === 'optimal').length,
    borderline: values.filter(v => v.status === 'borderline').length,
    concerning: values.filter(v => v.status === 'concerning').length,
    action_needed: values.filter(v => v.status === 'action_needed').length,
});
```

Cards layout: `grid grid-cols-2 gap-3 sm:grid-cols-4 mb-6`

### Architecture Compliance

- `status` field added to `HealthValueResponse` schema is additive — all existing tests remain valid
- `_compute_status()` is a pure function in `service.py` — no DB call, no side effects
- `user_id` still comes from `Depends(get_current_user)` only — do not accept it from request body/query
- Encryption/decryption lives in `repository.py` only — `service.py` never touches encrypted bytes
- New Svelte component under `src/lib/components/health/` — matches the established health-domain component directory
- No new backend endpoints needed — `GET /health-values` already exists; only schema and service logic change

### File Structure Requirements

Backend files to change:
- `healthcabinet/backend/app/health_data/schemas.py` — add `status` field to `HealthValueResponse`
- `healthcabinet/backend/app/health_data/service.py` — add `_compute_status()`, update `_to_response()`
- `healthcabinet/backend/tests/health_data/test_router.py` — add Story 3.2 test section

Frontend files to change:
- `healthcabinet/frontend/src/lib/api/health-values.ts` — add `HealthValue` type + `getHealthValues()`
- `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte` — parallel fetch + active/empty state branching
- `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts` — extend mock + add active state tests

New frontend files to create:
- `healthcabinet/frontend/src/lib/components/health/HealthValueBadge.svelte` — new component

Optional (only if it reduces duplication in `+page.svelte`):
- `healthcabinet/frontend/src/lib/components/health/ConfidenceWarning.svelte` — extract if used in multiple places

### Testing Requirements

Run all tests inside Docker Compose — never locally:
- Backend: `docker compose exec backend uv run pytest tests/health_data/test_router.py`
- Frontend: `docker compose exec frontend npm run test:unit`

**Backend tests to add** (under `# Story 3.2` section in `test_router.py`):
```python
# Use existing replace_document_health_values + make_user + make_document fixture pattern
# Test 1: GET /health-values returns status field
#   - Insert value with ref_low=70, ref_high=99, value=91 → status=="optimal"
# Test 2: Optimal classification
#   - ref_low=70, ref_high=99, value=91 → "optimal"
# Test 3: Borderline classification
#   - ref_low=70, ref_high=99, value=65 → "borderline" (pct = (70-65)/29 ≈ 0.17 ≤ 0.20)
# Test 4: Action needed classification
#   - ref_low=70, ref_high=99, value=30 → "action_needed" (pct = (70-30)/29 ≈ 1.38 > 0.50)
# Test 5: Unknown when no reference range
#   - ref_low=None, ref_high=None → "unknown"
```

**Frontend test updates** (in `page.test.ts`):
- Update `vi.mock('$lib/api/health-values', ...)` to include `getHealthValues: vi.fn()` — **CRITICAL: existing tests will fail if this is missing when `getHealthValues` is imported**
- Add `mockGetHealthValues = vi.mocked(getHealthValues)` alongside existing `mockGetDashboardBaseline`
- In `beforeEach`, set a default for both mocks (e.g., `mockGetHealthValues.mockResolvedValue([])` for empty state tests)

### Previous Story Learnings (from 3.1)

- The `$effect` cancellation guard pattern (`let cancelled = false; return () => { cancelled = true; }`) is established — extend it to the parallel fetch
- shadcn-svelte `Button` component is available from `$lib/components/ui/button`
- Skeleton pattern: `animate-pulse rounded-lg border border-border bg-card p-5` with inner `h-4 w-2/5 rounded bg-muted` divs — reuse exactly
- `axe-core` accessibility audit is part of the test suite — run on active state too
- Dark neutral theme is live: use `bg-card`, `border-border`, `text-muted-foreground` Tailwind tokens (not hardcoded colors) for structural elements; use hardcoded hex only for health status colors per design system
- `renderComponent` utility is at `$lib/test-utils/render` — no changes needed

### Antipatterns to Prevent

- **Do NOT** refactor the empty state (baseline recs + upload CTA) — it is tested and working; only add the active state branch
- **Do NOT** add sparklines or trend charts — that is Story 3.3
- **Do NOT** add AI interpretation cards — that is Story 4.1
- **Do NOT** fetch user profile in the backend `list_health_values` service function — status is computed from the already-stored reference ranges without a profile lookup
- **Do NOT** create a new backend endpoint — `GET /health-values` already exists; only extend the schema
- **Do NOT** use `has_uploads` from baseline to gate the health values fetch — always fetch both in parallel and use `values.length > 0` to decide the render branch
- **Do NOT** break the existing `page.test.ts` mock — the mock for `$lib/api/health-values` must include ALL exported functions that the component imports, including `getHealthValues`

### Project Structure Notes

- Health-domain component directory `src/lib/components/health/` does not yet exist in the repo — create it when creating `HealthValueBadge.svelte`
- The backend `health_data` module boundary owns FR14-FR17; all changes stay within `app/health_data/`
- `HealthValueResponse` schema change is backward-compatible (additive field); no migration needed
- The `GET /health-values` endpoint is already registered in `router.py` with `APIRouter(prefix="/health-values")`

### References

- Epic source: `_bmad-output/planning-artifacts/epics.md#story-32-health-values-dashboard-with-context-indicators`
- Architecture source: `_bmad-output/planning-artifacts/architecture.md`
- UX design spec: `_bmad-output/planning-artifacts/ux-design-specification.md` (health status colors, design tokens, "Informed Calm" philosophy)
- UX page spec: `_bmad-output/planning-artifacts/ux-page-specifications.md` (Dashboard active state layout: stat cards + biomarker table)
- Previous story: `_bmad-output/implementation-artifacts/3-1-profile-based-baseline-test-recommendations.md`
- Backend schemas: `healthcabinet/backend/app/health_data/schemas.py`
- Backend service: `healthcabinet/backend/app/health_data/service.py`
- Backend router: `healthcabinet/backend/app/health_data/router.py`
- Backend tests: `healthcabinet/backend/tests/health_data/test_router.py`
- Frontend dashboard: `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte`
- Frontend tests: `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts`
- Frontend API client: `healthcabinet/frontend/src/lib/api/health-values.ts`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Auto-discovered first backlog story from sprint-status.yaml: `3-2-health-values-dashboard-with-context-indicators`
- Analyzed Epic 3 in epics.md for complete AC and cross-story context
- Read current implementation: router.py, service.py, schemas.py, +page.svelte, health-values.ts
- Read previous story 3.1 for learnings, patterns, and component conventions
- Read test files (test_router.py, page.test.ts) for exact testing patterns
- Determined status computation algorithm based on reference range deviation percentages
- Confirmed HealthValueResponse schema extension is additive and backward-compatible
- Confirmed existing mock in page.test.ts must be updated when getHealthValues() is added

### Completion Notes List

- Story created for Epic 3 health values active dashboard state
- Scope excludes sparklines/trend charts (Story 3.3) and AI interpretation (Story 4.1)
- Status computation is pure backend logic on stored reference ranges — no demographic adjustment DB needed for MVP
- Dashboard page refactored to parallel-fetch baseline + values; render branch determined by values.length
- Existing empty state (3.1 implementation) preserved exactly — only adds active state branch
- ✅ Task 1: Added `status` field to `HealthValueResponse` schema; implemented `_compute_status()` pure function in `service.py`; all 21 backend tests pass (including 5 new Story 3.2 tests)
- ✅ Task 2: Added `HealthValue` TypeScript interface and `getHealthValues()` function to `health-values.ts`
- ✅ Task 3: Created `HealthValueBadge.svelte` component with `role="status"`, color+text always rendered together, all 5 status variants
- ✅ Task 4: Refactored dashboard `+page.svelte` to parallel-fetch; active state with stat cards + value cards grid; empty state preserved exactly from 3.1; `tabindex="0"` + `focus-visible:ring-2` on value cards; skeleton loaders; `ConfidenceWarning` inline
- ✅ Task 5: 5 backend tests added (status field present, optimal, borderline, action_needed, unknown); frontend mock extended with `getHealthValues`; 7 new frontend tests added (value cards, badge labels, confidence warning, stat cards, accessibility audit); all 109 frontend tests pass
- Full regression suite: 168 backend tests pass, 109 frontend tests pass

### File List

- `_bmad-output/implementation-artifacts/3-2-health-values-dashboard-with-context-indicators.md`
- `healthcabinet/backend/app/health_data/schemas.py`
- `healthcabinet/backend/app/health_data/service.py`
- `healthcabinet/backend/tests/health_data/test_router.py`
- `healthcabinet/frontend/src/lib/api/health-values.ts`
- `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte`
- `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts`
- `healthcabinet/frontend/src/lib/components/health/HealthValueBadge.svelte` (new)

### Review Findings

- [x] [Review][Decision] Promise.all vs Promise.allSettled — resolved: switched to `Promise.allSettled`; partial rendering on single-call failure; error banner only when both fail. [`+page.svelte`]
- [x] [Review][Patch] Zero-span reference range falls through silently — added explicit `return "borderline"` with degenerate-range comment inside the `if span > 0` block. [`service.py` `_compute_status`]
- [x] [Review][Patch] `_compute_status` return type should be `Literal[...]` not `str` — updated to `-> Literal["optimal", "borderline", "concerning", "action_needed", "unknown"]`; added `from typing import Literal`. [`service.py`]
- [x] [Review][Patch] NaN/Inf value produces incorrect `action_needed` — added `if not math.isfinite(value): return "unknown"` guard; added `import math`. [`service.py` `_compute_status`]
- [x] [Review][Patch] Missing backend test for `concerning` status range — added `test_get_health_values_status_concerning_for_moderately_out_of_range` (value=58, pct≈0.41). [`test_router.py`]
- [x] [Review][Patch] `retry()` cancellation closure is discarded — rewrote `retry` to use `Promise.allSettled`, removed return, added `if (loading) return` guard to prevent concurrent invocations. [`+page.svelte` `retry`]
- [x] [Review][Patch] `role="status"` on HealthValueBadge misuses ARIA live region — changed to `role="img"` with `aria-label="{config.label} status"`. [`HealthValueBadge.svelte`]
- [x] [Review][Patch] `STATUS_NOTES` typed as `Record<string, string>` — changed to `Record<HealthValue['status'], string>` for compile-time exhaustiveness. [`+page.svelte`]
- [x] [Review][Patch] Stat cards test only checks section exists, not count values — added `within(summarySection)` assertions for count values (2×`'1'`, 2×`'0'`); imported `within`. [`page.test.ts`]
- [x] [Review][Defer] Single-bound case always returns `"borderline"` regardless of deviation magnitude [`service.py`] — deferred, spec-defined behavior ("Single-bound case: value is outside the one provided bound" → borderline); severity scaling for one-sided ranges is future enhancement
- [x] [Review][Defer] `counts` omits `unknown` status — summary tiles won't sum to `values.length` when unknowns exist [`+page.svelte`] — deferred, design decision per spec; no "unknown" stat card in spec layout
- [x] [Review][Defer] Duplicate fetch logic in `$effect` and `retry` [`+page.svelte`] — deferred, pre-existing style pattern, not a regression
- [x] [Review][Defer] Exact boundary values (`value == ref_low`, `value == ref_high`) untested [`test_router.py`] — deferred, behavior correct by inspection (`>=`/`<=`), low risk
- [x] [Review][Defer] WCAG 4.5:1 contrast ratio not statically verifiable [`HealthValueBadge.svelte`] — deferred, color tokens match design system spec; requires visual/browser audit

### Change Log

- 2026-03-25: Story 3.2 implemented — added `status` field to backend `HealthValueResponse` with `_compute_status()` pure function; added `HealthValue` TypeScript type and `getHealthValues()` frontend API helper; created `HealthValueBadge.svelte` component; refactored dashboard to parallel-fetch and render active state (stat cards + value cards with badges, notes, confidence warnings) while preserving empty state from 3.1; added 5 backend and 7 frontend tests; full regression suite passes (168 backend, 109 frontend)
