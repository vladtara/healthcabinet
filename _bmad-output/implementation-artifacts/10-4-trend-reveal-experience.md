# Story 10.4: Trend Reveal Experience

Status: review

## Story

As a user with 2+ uploaded health documents,
I want cross-upload trend patterns surfaced prominently with stronger visual hierarchy,
so that I can immediately see which biomarkers are changing over time and understand what those changes mean.

## Acceptance Criteria

1. **Pattern alert panel** — When the user has 2+ uploads AND the AI patterns API returns patterns, render a "Pattern Alerts" section between the StatCardGrid and BiomarkerTable. Each pattern shows: description text, document dates referenced, and recommendation. Uses a 98.css sunken panel with an orange/warning left-border accent for concerning patterns. If no patterns are returned, the section is not rendered (no empty state needed).

2. **Pattern alert data fetching** — Fetch patterns via `getAiPatterns()` from `$lib/api/ai.ts` using TanStack Query with key `['ai_patterns']`. Only enable the query when `values.length > 0` (user has uploads). Handle loading (skeleton), error (inline message), and success states.

3. **Trend section redesign** — The existing trend section (BiomarkerTrendSection per unique biomarker) is enhanced with:
   - Section header showing biomarker name as an `<h3>` inside the chart area
   - Trend direction indicator: "↑ Increasing", "↓ Decreasing", or "→ Stable" derived from comparing the first and last values in the timeline. Uses health status colors (increasing concerning biomarker = orange/red, stable optimal = green).
   - "Not enough data" message when <2 data points (already handled by BiomarkerTrendChart disabled state, but wrap it consistently in the 98.css section pattern).

4. **Visual hierarchy** — Pattern alerts sit above the BiomarkerTable to catch attention first ("meaning before raw data" principle). Full trend charts sit below the table for detailed exploration. The dashboard active state layout order is: PatientSummaryBar → StatCardGrid → Pattern Alerts (if any) → BiomarkerTable → Trends.

5. **CSS follows established patterns** — New styles in `app.css` using `.hc-pattern-*` naming for pattern alerts and `.hc-trend-*` for trend section enhancements. 98.css sunken panel for both. No scoped styles.

6. **Tests** — Pattern alert section: renders when patterns exist, does not render when empty, loading skeleton, error state, correct pattern content (description + recommendation), axe audit. Trend section: trend direction indicator renders correctly (increasing/decreasing/stable), biomarker name header renders. Dashboard integration tests updated.

7. **WCAG Considerations** — Pattern alert has `role="alert"` only for urgent patterns (action_needed level). Trend direction uses text + symbol (not color-only). All new sections pass axe audits.

## Tasks / Subtasks

- [x] Task 1: Add pattern alert CSS to app.css (AC: #5)
  - [x] 1.1 Add `.hc-pattern-alert` card with orange left-border accent (uses .hc-dash-section container)
  - [x] 1.2 Add `.hc-pattern-alert-desc` description text (14px)
  - [x] 1.3 Add `.hc-pattern-alert-dates` date references (12px, muted)
  - [x] 1.4 Add `.hc-pattern-alert-rec` recommendation text (13px, italic)

- [x] Task 2: Add trend section enhancement CSS (AC: #5)
  - [x] 2.1 Add `.hc-trend-header` for biomarker name + direction indicator row
  - [x] 2.2 Add `.hc-trend-direction` for direction indicator text (12px, colored)
  - [x] 2.3 Add `.hc-trend-direction-up`, `.hc-trend-direction-down`, `.hc-trend-direction-stable` color variants

- [x] Task 3: Create PatternAlertSection component (AC: #1, #2)
  - [x] 3.1 Create `src/lib/components/health/PatternAlertSection.svelte` with typed props
  - [x] 3.2 Props: `patterns: PatternObservation[]`, `loading: boolean`, `error: boolean`
  - [x] 3.3 Render loading skeleton when `loading` is true
  - [x] 3.4 Render inline error message when `error` is true
  - [x] 3.5 Render each pattern as `.hc-pattern-alert` with description, dates, recommendation
  - [x] 3.6 Do not render anything when `patterns` is empty and not loading/error

- [x] Task 4: Enhance BiomarkerTrendSection with trend direction (AC: #3)
  - [x] 4.1 Add trend direction derivation: compare first and last timeline values (5% threshold)
  - [x] 4.2 Determine direction: "↑ Increasing" / "↓ Decreasing" / "→ Stable"
  - [x] 4.3 Render `.hc-trend-header` with biomarker name `<h2>` and direction indicator
  - [x] 4.4 Chart wrapped in padding div (consistent layout within .hc-dash-section)

- [x] Task 5: Integrate into dashboard page (AC: #4)
  - [x] 5.1 Add `getAiPatterns` import and TanStack Query with key `['ai_patterns']`
  - [x] 5.2 Render PatternAlertSection between StatCardGrid and BiomarkerTable section
  - [x] 5.3 Pass loading/error/data states to PatternAlertSection
  - [x] 5.4 Layout order verified: PatientSummaryBar → StatCardGrid → Patterns → BiomarkerTable → Trends

- [x] Task 6: Write PatternAlertSection tests (AC: #6, #7)
  - [x] 6.1 Test: renders pattern descriptions when patterns exist
  - [x] 6.2 Test: renders recommendation text for each pattern
  - [x] 6.3 Test: does not render when patterns array is empty
  - [x] 6.4 Test: renders loading skeleton
  - [x] 6.5 Test: renders error message
  - [x] 6.6 Test: axe accessibility audit passes

- [x] Task 7: Write trend direction tests (AC: #6)
  - [x] 7.1 Test: "↑ Increasing" shown when last value > first by >5%
  - [x] 7.2 Test: "↓ Decreasing" shown when last value < first by >5%
  - [x] 7.3 Test: "→ Stable" shown when change is within 5%
  - [x] 7.4 Test: biomarker name renders as `<h2>` heading

- [x] Task 8: Update dashboard page tests (AC: #6)
  - [x] 8.1 Test: pattern alert section renders when patterns API returns data
  - [x] 8.2 Test: pattern section not rendered when patterns empty
  - [x] 8.3 Test: layout order preserved (summary → stats → patterns → table → trends) via DOM position
  - [x] 8.4 Test: axe accessibility audit passes on active state with patterns

- [x] Task 9: Run full test suite (AC: #6)
  - [x] 9.1 Run `docker compose exec frontend npm run test:unit` — 418/419 pass (1 pre-existing failure in users.test.ts)
  - [x] 9.2 Run `docker compose exec frontend npm run check` — 0 errors, 2 pre-existing warnings

### Review Findings

- [x] [Review][Patch] Fixed `getTrendDirection` zero-denominator — replaced `first === 0` guard with `Math.abs(first) || Math.abs(last) || 1` fallback [BiomarkerTrendSection.svelte:23]
- [x] [Review][Patch] Added `role="status"` on pattern alert section container for screen reader notification [PatternAlertSection.svelte:52]
- [x] [Review][Defer] Missing `role="status"` on pattern loading skeleton — minor a11y gap, consistent with other loaders
- [x] [Review][Defer] Empty description/recommendation renders blank cards — API shouldn't return empty strings
- [x] [Review][Defer] Long unbroken text overflow in pattern alerts — cosmetic, low probability
- [x] [Review][Defer] Inconsistent heading hierarchy (h2 in trends vs div headers elsewhere) — broader architectural concern
- [x] [Review][Defer] Missing dedicated test for <2 data points "Not enough data" — logic works, indirectly tested

## Dev Notes

### Architecture Decisions

- **PatternAlertSection is a standalone component** — Receives pre-fetched data via props (`patterns`, `loading`, `error`). The dashboard page owns the TanStack Query and passes results. This keeps the component testable without QueryClient context.
- **BiomarkerTrendSection modification, not replacement** — Enhance the existing component rather than creating a new one. Add the trend direction header above the chart. This preserves the existing timeline query and chart rendering.
- **Pattern data from existing API** — `getAiPatterns()` already exists in `$lib/api/ai.ts` and returns `PatternObservation[]` with `description`, `document_dates`, `recommendation`. No new API calls needed.

### Component Specifications

**Pattern Alert Section (between StatCardGrid and BiomarkerTable):**
```
┌─ .hc-dash-section ───────────────────────────────────────┐
│ ┌─ .hc-dash-section-header ─────────────────────────────┐│
│ │ 📈 Pattern Alerts                                     ││
│ └───────────────────────────────────────────────────────┘│
│ ┌─ .hc-pattern-alert (orange left border) ──────────────┐│
│ │ TSH increased 3.2 → 4.1 → 5.8 mIU/L across last 3   ││
│ │ results. Consistent with undertreated Hashimoto's.    ││
│ │ Mar 2026, Jun 2026, Sep 2026                          ││
│ │ Consider discussing thyroid medication with doctor.    ││
│ └───────────────────────────────────────────────────────┘│
│ ┌─ .hc-pattern-alert ──────────────────────────────────┐ │
│ │ Ferritin declining steadily: 45 → 28 → 18 ng/mL     ││
│ │ Jan 2026, Apr 2026, Jul 2026                          ││
│ │ Iron supplementation may be worth discussing.          ││
│ └───────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────┘
```

**Enhanced Trend Section (per biomarker):**
```
┌─ .hc-trend-header ──────────────────────────────────────┐
│ TSH                                    ↑ Increasing     │
└─────────────────────────────────────────────────────────┘
┌─ [BiomarkerTrendChart full variant] ────────────────────┐
│ [existing SVG chart with reference band, axes, points]  │
└─────────────────────────────────────────────────────────┘
```

### Trend Direction Logic

```typescript
function getTrendDirection(values: HealthValue[]): { label: string; symbol: string; colorClass: string } {
  if (values.length < 2) return { label: 'Not enough data', symbol: '', colorClass: 'hc-trend-direction-stable' };
  const first = values[0].value;
  const last = values[values.length - 1].value;
  const changePercent = ((last - first) / first) * 100;
  if (changePercent > 5) return { label: 'Increasing', symbol: '↑', colorClass: 'hc-trend-direction-up' };
  if (changePercent < -5) return { label: 'Decreasing', symbol: '↓', colorClass: 'hc-trend-direction-down' };
  return { label: 'Stable', symbol: '→', colorClass: 'hc-trend-direction-stable' };
}
```

The 5% threshold distinguishes meaningful trends from measurement noise. Color is based on direction only (up = orange, down = blue/teal, stable = green), paired with text + symbol (never color-only).

### Pattern Alert Left Border

```css
.hc-pattern-alert {
  border-left: 4px solid var(--color-status-concerning);
  padding: 10px 12px;
  margin-bottom: 8px;
  background: var(--surface-sunken);
}
```

Orange left border (`--color-status-concerning`) signals attention without alarm, consistent with UX spec principle: "Recognition over alarm — even bad results are presented as data, not red flashing warnings."

### Dashboard Layout Order (after this story)

```
┌─ .hc-dash-header ─────────────────────── [Upload] ─┐
├─ PatientSummaryBar ─────────────────────────────────┤
├─ StatCardGrid (4 cards) ────────────────────────────┤
├─ Pattern Alerts (if any) ───────────────────────────┤
├─ Biomarker Results (.hc-dash-section + BiomarkerTable) ─┤
├─ Trends (.hc-dash-section + BiomarkerTrendSection per biomarker) ─┤
└─────────────────────────────────────────────────────┘
```

### Existing API to Use

```typescript
// $lib/api/ai.ts — already exists
export interface PatternObservation {
  description: string;       // "TSH increased 3.2 → 4.1 → 5.8 mIU/L across last 3 results"
  document_dates: string[];  // ["2026-03-15", "2026-06-20", "2026-09-10"]
  recommendation: string;    // "Consider discussing thyroid medication with doctor"
}

export interface AiPatternsResponse {
  patterns: PatternObservation[];
}

export async function getAiPatterns(): Promise<AiPatternsResponse>;
```

### Existing Components to Reuse

| Component | Import Path | Usage |
|-----------|-------------|-------|
| `BiomarkerTrendSection` | `$lib/components/health/BiomarkerTrendSection.svelte` | Modify to add trend direction header |
| `BiomarkerTrendChart` | `$lib/components/health/BiomarkerTrendChart.svelte` | Full chart variant (already used by BiomarkerTrendSection) |
| `Button` | `$lib/components/ui/button` | Not needed for this story |

### What to Modify

- `healthcabinet/frontend/src/app.css` — Add `.hc-pattern-*` and `.hc-trend-*` CSS
- `healthcabinet/frontend/src/lib/components/health/PatternAlertSection.svelte` — NEW
- `healthcabinet/frontend/src/lib/components/health/BiomarkerTrendSection.svelte` — MODIFY (add trend direction header)
- `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte` — MODIFY (add pattern query + PatternAlertSection)

### What NOT to Touch

- BiomarkerTable (story 10-3, complete)
- PatientSummaryBar / StatCardGrid (story 10-2, complete)
- Empty state rendering
- Loading and error states (dashboard-level)
- AppShell / AdminShell
- Any backend code

### Previous Story Intelligence

**From story 10-3:**
- Dashboard active state now uses: PatientSummaryBar → StatCardGrid → BiomarkerTable → Trends
- CSS namespacing: `.hc-bio-*` for BiomarkerTable, `.hc-dash-*` for page layout
- BiomarkerTrendSection already wrapped in `.hc-dash-section` sunken panel with section header
- `timelineByBiomarker` derived value already available in `+page.svelte`
- Test baseline: 404/405 pass (1 pre-existing failure in `users.test.ts`)
- Review fixed: row striping uses class-based approach, sort indicator empty for inactive columns

**From story 10-3 review deferred items:**
- `.hc-sort-button` class reused for expand button (cosmetic, not blocking)
- `lastUploadDate` string comparison (works for ISO 8601)

**Git intelligence (recent commits):**
- `367558d` feat(ui): add BiomarkerTable component with sorting, expansion, and timeline features
- `f16c010` feat(ui): implement dashboard layout with header, sections, and summary components
- Pattern: `feat(ui):` prefix for UI component commits

### Testing Patterns

- **Framework:** Vitest + jsdom + @testing-library/svelte + axe-core
- **PatternAlertSection tests:** Standalone render with props (no QueryClient needed — receives data via props)
- **BiomarkerTrendSection tests:** Already has tests in `BiomarkerTrendChart.test.ts` — add trend direction tests
- **Dashboard integration tests:** Use existing `DashboardPageTestWrapper.svelte` with QueryClient. Mock `getAiPatterns` alongside existing mocks.
- **Axe audit:** `const results = await axe.run(container); expect(results.violations).toHaveLength(0);`

### Project Structure Notes

- New component: `src/lib/components/health/PatternAlertSection.svelte` + test
- Modified component: `src/lib/components/health/BiomarkerTrendSection.svelte`
- CSS in `src/app.css` — append `.hc-pattern-*` and `.hc-trend-*` classes
- No new directories

### References

- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md, lines 504-508] — Pattern alert wireframe between stat cards and biomarker table
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md, lines 107-108] — "First trend arrow" and "AI pattern alert" as critical success moments
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md, lines 113-122] — Experience principles: "Density over whitespace", "Intelligence compounds visibly"
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md, line 176] — Story candidate: "Trend reveal experience for 2+ uploads"
- [Source: _bmad-output/planning-artifacts/prd.md, FR15] — Trend lines per biomarker across time
- [Source: _bmad-output/planning-artifacts/prd.md, FR22] — AI detects patterns across multiple uploads
- [Source: healthcabinet/frontend/src/lib/api/ai.ts] — PatternObservation, AiPatternsResponse, getAiPatterns()
- [Source: healthcabinet/frontend/src/lib/components/health/BiomarkerTrendSection.svelte] — Existing trend section to enhance
- [Source: healthcabinet/frontend/src/lib/components/health/BiomarkerTrendChart.svelte] — Full chart variant used by TrendSection

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- `docker compose exec frontend npm run test:unit`: 418/419 passed; 1 pre-existing failure in `users.test.ts`
- `docker compose exec frontend npm run check`: 0 errors, 2 pre-existing warnings
- Fixed heading-order axe violation: changed `<h3>` to `<h2>` in BiomarkerTrendSection to maintain proper heading hierarchy (`<h1>` → `<h2>`)

### Completion Notes List

- Created `PatternAlertSection.svelte` — standalone props-driven component rendering AI cross-upload pattern observations with orange left-border accent, description, dates, and recommendation
- Enhanced `BiomarkerTrendSection.svelte` — added `.hc-trend-header` with biomarker name `<h2>` and trend direction indicator (↑ Increasing / ↓ Decreasing / → Stable, 5% threshold), wrapped chart in padded container
- Integrated pattern alerts into dashboard: TanStack Query for `getAiPatterns()` with key `['ai_patterns']`, enabled when values exist, PatternAlertSection rendered between StatCardGrid and BiomarkerTable
- Added pattern query invalidation to dashboard retry function
- Dashboard active state layout order: PatientSummaryBar → StatCardGrid → Pattern Alerts → Biomarker Results → Trends
- Added `.hc-pattern-*` CSS (alert card, description, dates, recommendation) and `.hc-trend-*` CSS (header, direction with color variants)
- 6 PatternAlertSection tests (content, empty, loading, error, axe) + 4 BiomarkerTrendSection tests (increasing, decreasing, stable, heading) + 4 dashboard integration tests (pattern renders, empty, layout order, axe)
- Total new tests: 14

### File List

- `healthcabinet/frontend/src/app.css` (modified — added `.hc-pattern-*` and `.hc-trend-*` CSS)
- `healthcabinet/frontend/src/lib/components/health/PatternAlertSection.svelte` (new)
- `healthcabinet/frontend/src/lib/components/health/PatternAlertSection.test.ts` (new)
- `healthcabinet/frontend/src/lib/components/health/BiomarkerTrendSection.svelte` (modified — added trend direction header)
- `healthcabinet/frontend/src/lib/components/health/BiomarkerTrendSection.test.ts` (new)
- `healthcabinet/frontend/src/lib/components/health/BiomarkerTrendSectionTestWrapper.svelte` (new — test helper)
- `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte` (modified — added patterns query + PatternAlertSection)
- `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts` (modified — added pattern + layout tests)
- `_bmad-output/implementation-artifacts/10-4-trend-reveal-experience.md` (modified — tasks, status, dev record)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified — story status)

### Change Log

- 2026-04-04: Implemented story 10-4 Trend Reveal Experience — pattern alerts, trend direction indicators, dashboard integration
