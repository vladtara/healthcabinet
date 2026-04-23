# Story 3.1: Profile-Based Baseline & Test Recommendations

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a registered user,
I want to see a personalized health baseline and panel recommendations immediately after completing my profile — before uploading any documents,
so that the product delivers value from my first session and I know exactly what tests are worth tracking for me.

## Acceptance Criteria

1. **Given** a user has completed their medical profile (Story 1.4) **When** they visit the dashboard with no uploaded documents after the Epic 3 UI refinement baseline is in place **Then** a baseline view is displayed showing 3–5 personalized test recommendations with suggested testing frequency **And** the recommendations are tailored to the user's profile (e.g., thyroid panels for a user with Hashimoto's; lipid panel for a healthy 28-year-old male) **And** the view is generated from profile data only — no `health_values` query is made

2. **Given** a user with no diagnosed conditions **When** the baseline loads **Then** age- and sex-appropriate general health panel recommendations are shown

3. **Given** a user with one or more diagnosed conditions **When** the baseline loads **Then** condition-specific recommendations are shown alongside general recommendations

4. **Given** the baseline view is displayed **When** the user has no uploads **Then** an "Upload your first document" CTA is prominently shown **And** chart areas display an empty-state overlay (never blank axes or broken charts)

5. **Given** the dashboard renders after authentication **When** the page loads **Then** the baseline content appears within 2 seconds (NFR2) **And** skeleton loaders are shown during the data fetch (never a blank flash)

## Tasks / Subtasks

- [x] Task 1: Establish a profile-only baseline contract in backend health-data APIs (AC: #1, #2, #3, #5)
  - [x] Add response schemas under `backend/app/health_data/schemas.py` for baseline summary and recommendation items
  - [x] Add a new authenticated route in `backend/app/health_data/router.py` for profile-based dashboard baseline data
  - [x] Implement service logic in `backend/app/health_data/service.py` that derives recommendations strictly from `users` profile data and does not query `health_values`
  - [x] Keep the baseline logic deterministic and MVP-bounded; do not introduce LLM calls, LangGraph dependencies, or billing gates in this story

- [x] Task 2: Define baseline recommendation heuristics for generic and condition-aware cases (AC: #1, #2, #3)
  - [x] Cover users with no known conditions using age/sex-appropriate general recommendations
  - [x] Layer condition-specific recommendations for known conditions without removing the general baseline
  - [x] Return 3–5 recommendations total with concise rationale and suggested testing frequency
  - [x] Keep recommendation language informational and non-diagnostic, aligned with product tone and MVP constraints

- [x] Task 3: Replace the dashboard placeholder with the empty-state baseline experience (AC: #1, #4, #5)
  - [x] Implement `frontend/src/routes/(app)/dashboard/+page.svelte` using the approved dashboard empty-state direction from the UX specs
  - [x] Fetch profile and baseline data with existing frontend API patterns and render loading skeletons during fetch
  - [x] Show a prominent upload CTA and an intentional empty-state visualization instead of blank chart/table placeholders
  - [x] Preserve authenticated-route behavior and avoid introducing the full FR14/FR15 uploaded-data dashboard in this story

- [x] Task 4: Introduce minimal frontend helpers only where they reduce duplication cleanly (AC: #1, #4)
  - [x] Prefer implementing the page directly first
  - [x] If needed, extract only small presentation helpers under `frontend/src/lib/components/health/` or nearby dashboard-local files
  - [x] Do not create speculative charting, trend, or AI-summary abstractions before Stories 3.2 and 3.3

- [x] Task 5: Add targeted backend and frontend coverage for the new baseline flow (AC: #1, #2, #3, #4, #5)
  - [x] Extend `backend/tests/health_data/test_router.py` for the new baseline endpoint, including no-condition and condition-aware cases
  - [x] Add a dashboard route test at `frontend/src/routes/(app)/dashboard/page.test.ts` covering skeleton/loading, baseline recommendations, and upload CTA rendering
  - [x] Verify the route remains accessible and keyboard-usable in the empty state
  - [x] Run the smallest relevant test scope first, then the broader relevant suites per project rules

## Dev Notes

### Story Intent

This story is the first functional dashboard story in Epic 3. It should solve the cold-start problem by making the dashboard valuable before any uploads exist, using onboarding profile data alone. It is not the story for uploaded health values, trend lines, or AI interpretation of lab results.

### Current State Intelligence

- The current dashboard route is still a stub with only placeholder copy in `frontend/src/routes/(app)/dashboard/+page.svelte`. [Source: `/Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte`]
- The backend `health_data` module currently exposes value list, timeline, and flagging endpoints only; there is no baseline/dashboard summary endpoint yet. [Source: `/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/health_data/router.py`]
- The user profile API already exposes the key inputs for profile-based recommendations: `age`, `sex`, `known_conditions`, `medications`, and `family_history`. [Source: `/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/users/schemas.py`]
- Story 3.0 already raised the visual quality of register/onboarding and explicitly prepared the UX foundation for dashboard work. Preserve that design language when implementing this story. [Source: `/Users/vladtara/dev/set-bmad/_bmad-output/implementation-artifacts/3-0-registration-onboarding-ui-refinement.md`]

### Technical Requirements

- Profile-based baseline generation must use profile data only; do not call or depend on `health_values` queries for this story. [Source: `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/epics.md#Story-31-Profile-Based-Baseline--Test-Recommendations`]
- Keep the recommendation engine deterministic and local to backend service logic for MVP. Do not route baseline generation through `app/ai/` or external models in this story.
- New backend behavior should live under `app/health_data/`, consistent with FR14-FR17 module ownership. [Source: `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/architecture.md#Project-Structure--Boundaries`]
- New frontend data fetching should continue using `apiFetch<T>()` and current Svelte 5 runes patterns already established in the repo. [Source: `/Users/vladtara/dev/set-bmad/_bmad-output/project-context.md`]
- Avoid introducing monetization, upgrade prompts, or Stripe-related UX. MVP scope still excludes billing. [Source: `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/epics.md`]

### Architecture Compliance

- Backend remains router/service/repository separated. If baseline generation needs persistence reads, keep them inside service/repository boundaries rather than in the router. [Source: `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/architecture.md`]
- `user_id` must come from `Depends(get_current_user)` only. No request-body user identifiers. [Source: `/Users/vladtara/dev/set-bmad/_bmad-output/project-context.md`]
- Frontend `(app)` routes are authenticated and currently wrapped by `QueryClientProvider` in `frontend/src/routes/(app)/+layout.svelte`; new dashboard data loading should fit that structure. [Source: `/Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/+layout.svelte`]
- Treat the current architecture doc as directional, but prefer the actual repo tree where it differs. Example: the architecture references `(app)/dashboard/+page.ts` and `frontend/src/lib/api/health-data.ts`, but those files do not exist yet in the real codebase.

### Library / Framework Requirements

- Frontend: SvelteKit 2, Svelte 5 runes, Tailwind CSS v4, existing shadcn-svelte primitives. [Source: `/Users/vladtara/dev/set-bmad/_bmad-output/project-context.md`]
- Backend: FastAPI, async SQLAlchemy 2.0, Pydantic v2 response models. [Source: `/Users/vladtara/dev/set-bmad/_bmad-output/project-context.md`]
- Testing: Vitest + Testing Library + axe-core on frontend; httpx `AsyncClient` + ASGITransport on backend route tests. [Source: `/Users/vladtara/dev/set-bmad/healthcabinet/backend/tests/health_data/test_router.py`, `/Users/vladtara/dev/set-bmad/_bmad-output/project-context.md`]

### File Structure Requirements

- Primary backend files likely to change:
  - `healthcabinet/backend/app/health_data/router.py`
  - `healthcabinet/backend/app/health_data/service.py`
  - `healthcabinet/backend/app/health_data/schemas.py`
  - Optional: `healthcabinet/backend/app/health_data/repository.py` if profile lookup support is needed cleanly
- Primary frontend files likely to change:
  - `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte`
  - Optional: `healthcabinet/frontend/src/lib/api/health-values.ts` or a new adjacent API helper if dashboard baseline fetch needs a dedicated client wrapper
  - Optional: small new components under `healthcabinet/frontend/src/lib/components/health/`
- Primary tests to add/update:
  - `healthcabinet/backend/tests/health_data/test_router.py`
  - `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts`

### Testing Requirements

- Backend tests must run in Docker Compose per project rules, using the existing async API-test pattern.
- Frontend tests must also run in Docker Compose per project rules; if the current frontend runtime image still excludes source tests, note that environment limitation explicitly rather than claiming the command worked.
- Minimum functional verification should cover:
  - no-condition profile returns general recommendations
  - condition-bearing profile returns general + condition-specific recommendations
  - recommendation count is constrained to 3-5 items
  - dashboard empty state shows loading skeletons first, then baseline cards/sections and upload CTA
  - empty-state visuals remain accessible and intentional rather than blank placeholders

### Previous Story Intelligence

- Story 3.0 established the visual language that the dashboard should now inherit: dark restrained surfaces, trust-first tone, and polished auth/onboarding groundwork. [Source: `/Users/vladtara/dev/set-bmad/_bmad-output/implementation-artifacts/3-0-registration-onboarding-ui-refinement.md`]
- Story 1.4 already guarantees onboarding profile capture and redirect to `/dashboard`; 3.1 should capitalize on that handoff rather than altering onboarding flow logic. [Source: `/Users/vladtara/dev/set-bmad/_bmad-output/implementation-artifacts/1-4-medical-profile-setup.md`]

### Git Intelligence Summary

- Recent work has been frontend refinement and accessibility hardening, not broad architectural churn. Keep this story similarly bounded: add the minimum backend contract and dashboard UI needed to deliver the cold-start baseline cleanly.
- Recent commits suggest UI polish and accessibility are active quality bars, so dashboard baseline work should include loading-state polish and semantic structure from the start. [Source: `git log --oneline -n 5`]

### Project Structure Notes

- The actual repo currently has `(app)/dashboard/+page.svelte` but no colocated `+page.ts` or `page.test.ts`; creating a new `page.test.ts` next to the route matches the project’s route-test convention.
- Existing frontend API helpers include `src/lib/api/users.ts`; no health-data client helper exists yet in the current tree, so adding one is reasonable if it keeps the route code clean.
- Existing backend tests for `health_data` already use authenticated route tests with seeded data; extend that pattern instead of inventing a new test harness.

### References

- Epic source: `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/epics.md`
- PRD source: `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/prd.md`
- Architecture source: `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/architecture.md`
- UX source: `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/ux-design-specification.md`
- UX page spec source: `/Users/vladtara/dev/set-bmad/_bmad-output/planning-artifacts/ux-page-specifications.md`
- Project context source: `/Users/vladtara/dev/set-bmad/_bmad-output/project-context.md`
- Previous story source: `/Users/vladtara/dev/set-bmad/_bmad-output/implementation-artifacts/3-0-registration-onboarding-ui-refinement.md`
- Dashboard implementation source: `/Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte`
- Health data router source: `/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/health_data/router.py`
- Health data service source: `/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/health_data/service.py`
- User profile schema source: `/Users/vladtara/dev/set-bmad/healthcabinet/backend/app/users/schemas.py`
- App layout source: `/Users/vladtara/dev/set-bmad/healthcabinet/frontend/src/routes/(app)/+layout.svelte`
- Backend health-data test pattern: `/Users/vladtara/dev/set-bmad/healthcabinet/backend/tests/health_data/test_router.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Loaded sprint status to auto-select the first backlog story in order: `3-1-profile-based-baseline-test-recommendations`
- Extracted the exact story contract from Epic 3 acceptance criteria
- Compared architecture intent with the actual repo tree to avoid handing the dev agent nonexistent file paths
- Used Story 3.0 and current dashboard/health-data modules to ground implementation guidance in real code

### Completion Notes List

- Story created for Epic 3 cold-start baseline/dashboard work
- Story scope intentionally excludes uploaded-value dashboard cards, trend lines, and AI interpretation beyond deterministic profile-based recommendations
- Story guidance explicitly calls out the current mismatch between some architecture placeholders and the actual repo tree so the dev agent does not chase nonexistent files
- **Implemented by claude-sonnet-4-6 (2026-03-25):**
  - Added `RecommendationItem` and `BaselineSummaryResponse` Pydantic v2 schemas to `health_data/schemas.py`
  - Implemented `_generate_baseline_recommendations()` pure heuristics function in `service.py` covering 8 general panels (age/sex-gated) and 8 condition-specific panels with keyword matching and deduplication; output clamped to 3–5 items
  - Added `GET /api/v1/health-values/baseline` endpoint in `router.py`; uses `user_repository.get_user_profile()` to fetch profile without querying `health_values`
  - Replaced dashboard stub with full empty-state page: skeleton loaders, recommendation cards with category badges, upload CTA; uses `$state`+`$effect` runes and `apiFetch<T>()`
  - Added `getDashboardBaseline()` API helper with TypeScript types to `health-values.ts`
  - Backend: 7 new tests; all 162 tests pass, ruff clean
  - Frontend: 6 new tests (including axe accessibility); all 103 tests pass, ESLint clean
  - One lint fix during implementation: deduplication logic for `HbA1c` when diabetes condition present; nested if → compound condition for ruff SIM102

### Change Log

- 2026-03-25: Implemented story 3.1 — profile-based baseline endpoint + empty-state dashboard UI

### File List

- _bmad-output/implementation-artifacts/3-1-profile-based-baseline-test-recommendations.md
- healthcabinet/backend/app/health_data/schemas.py
- healthcabinet/backend/app/health_data/service.py
- healthcabinet/backend/app/health_data/router.py
- healthcabinet/backend/tests/health_data/test_router.py
- healthcabinet/frontend/src/lib/api/health-values.ts
- healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte
- healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts

### Review Findings

_Code review performed 2026-03-25 — review_mode: full, layers: Blind Hunter + Edge Case Hunter + Acceptance Auditor_

**Decision Needed:**

- [x] [Review][Decision] `has_uploads` is hardcoded `False` and frontend ignores it entirely — **Resolved (Option B):** backend now queries `document_repository.has_user_documents()`; frontend reads `data.has_uploads` and gates the upload CTA conditionally. [service.py, +page.svelte]

**Patches:**

- [x] [Review][Patch] Keyword matching too permissive — fixed with `re.search(rf"\b{re.escape(kw)}\b", cond)` word-boundary matching [`service.py`]
- [x] [Review][Patch] `retry()` in Svelte component lacks cancellation guard — fixed; `retry()` now uses the same `cancelled` flag pattern as `$effect` [`+page.svelte`]
- [x] [Review][Patch] Redundant dead-code check for Lipid Panel — removed [`service.py`]
- [x] [Review][Patch] Empty/whitespace strings in `known_conditions` not filtered — fixed with `if c and c.strip()` guard [`service.py`]
- [x] [Review][Patch] PSA sex gate case-sensitive — fixed; `sex_lower = sex.lower() if sex is not None else None` computed before loop [`service.py`]

**Deferred (pre-existing or out of scope):**

- [x] [Review][Defer] Upload CTA absent during loading and error states — AC#4 says "prominently shown" but loading/error are transient states; CTA present in the main success path [`+page.svelte:789`] — deferred, design choice within story scope
- [x] [Review][Defer] Iron & Ferritin sex=None gate includes unknown-sex users in a female-targeted recommendation — male users with no profile set receive it due to `sex not in (None, "female")` passing for `None` [`service.py:419`] — deferred, acceptable MVP heuristic ambiguity
- [x] [Review][Defer] Fallback to `_MIN_RECS` has no upper-bound guard of its own and theoretically could under-deliver if all `_GENERAL_PANELS` are exhausted — unreachable with current data but fragile invariant [`service.py:436–450`] — deferred, pre-existing heuristic limitation
- [x] [Review][Defer] No rate limiting on `/baseline` endpoint — consistent with current health-data router pattern; Redis rate limiting exists in `core/rate_limit.py` but not applied here — deferred, pre-existing gap across module
- [x] [Review][Defer] API response gives no indication that recommendations are generic due to incomplete profile (no `profile_complete` flag) — deferred, future enhancement outside story scope
