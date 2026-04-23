---
title: 'EN/UA localization — onboarding, settings, recommendation table'
type: 'feature'
created: '2026-04-22'
status: 'done'
baseline_commit: 'b7b886800f54d4e955c7f53f822d0dd5300c76fa'
context:
  - '_bmad-output/implementation-artifacts/15-6-core-en-ua-localization.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story 15.6 localized landing, auth, AppShell, dashboard chrome, documents, upload, and AI chat/note chrome, but three surfaces still render English under `uk`: the onboarding wizard, the Medical Profile (Settings) page, and the dashboard "Recommended Tests" table body (`test_name` / `frequency` / `rationale` come verbatim from backend).

**Approach:** Extend `lib/i18n/messages.ts` with `onboarding` and `settings` bundles; add a frontend `recommendation-catalog.ts` keyed on the fixed backend catalog strings; mount the existing `LocaleToggle` in the onboarding header; resolve recommendation cells through the new helper in the dashboard. No new store, no locale-prefixed routes, no backend changes.

## Boundaries & Constraints

**Always:**
- Reuse `localeStore`, `t(locale)`, `formatDate`, `LocaleToggle` from 15.6. Internal codes stay `'en' | 'uk'`; visible label stays `EN / UA`.
- Type parity: new bundle keys in `en` must be satisfied in `uk` — `npm run check` enforces this.
- Copy must retranslate on toggle without page reload; do not freeze resolved strings in `$state`. Read via `$derived` or in-template.
- Settings dirty-state, unsaved-changes guard, onboarding step validation, and `known_conditions` submit payload (canonical English) must keep working.

**Ask First:**
- Adding a `?locale=` param or translations to `GET /api/v1/users/me/baseline` — do NOT; keep backend unchanged.

**Never:**
- Do not localize AI interpretation bodies, chat replies, backend `detail` strings, biomarker names, or filenames (that is the deferred AI-content-language goal).
- Do not translate `known_conditions` / `family_history` payload values — backend `_CONDITION_PANELS` matches on English keywords. Translate for display only.
- No redesign — copy/formatting only.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Onboarding under `uk` | `/onboarding` step 1 with `locale = 'uk'` | Header, step indicator, field labels, placeholder, Back/Continue, validation errors in Ukrainian | N/A |
| Toggle mid-onboarding | Step 2, condition checked, flip EN→UA | Copy retranslates; `selectedConditions[]` (English) preserved; checkbox stays checked | N/A |
| Settings under `uk` | Open `/settings` with saved profile | All 7 fieldsets, preset labels, Save states, export copy, Delete confirm dialog Ukrainian | Backend `detail` passthrough stays verbatim (15.6 AC 5) |
| Settings dirty-state after toggle | User edited age → flip locale | `isDirty` stays true; button flips to `Зберегти профіль`; no spurious baseline fetch | N/A |
| Dashboard recommendations under `uk` | Row: `{test_name: 'TSH + Free T4 Panel', frequency: 'Every 6 months', rationale: '…'}` | Ukrainian from `recommendationCatalog` | Unknown `test_name` → render backend string (English fallback); dev-only `console.warn` |

</frozen-after-approval>

## Code Map

- `healthcabinet/frontend/src/lib/i18n/messages.ts` — add `onboarding`, `settings` bundles (plus any missing validation keys) in `en`; mirror in `uk`.
- `healthcabinet/frontend/src/lib/i18n/recommendation-catalog.ts` — **new**: `translateTestName(locale, en)`, `translateFrequency(locale, en)`, `translateRationale(locale, en)`; full coverage of backend `_GENERAL_PANELS` and `_CONDITION_PANELS`; English fallthrough for `en` and unknown keys.
- `healthcabinet/frontend/src/lib/i18n/recommendation-catalog.test.ts` — **new**: assert full backend-catalog coverage and English fallback.
- `healthcabinet/frontend/src/routes/(onboarding)/onboarding/+page.svelte` — localize wizard header, step indicator label (`$derived` from locale), three step bodies, Back/Continue/Complete buttons, validation messages, submit error; mount `LocaleToggle` right-aligned in the wizard header row.
- `healthcabinet/frontend/src/routes/(onboarding)/onboarding/page.test.ts` — toggle presence, EN↔UA retranslation, validation-message locale, checked-state preservation across toggle.
- `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` — localize title, success/error banners, all fieldsets (Basic Info / Health Conditions / Medications / Family History / Data Export / Consent History / Delete Account), preset labels, Save button states, GDPR & export copy, consent list states, delete warning, `ConfirmDialog` props (`title`, `confirmLabel`, `loadingLabel`, email label), unsaved-changes `confirm()` prompt.
- `healthcabinet/frontend/src/routes/(app)/settings/page.test.ts` — toggle + retranslation; dirty-state preserved across toggle; ConfirmDialog text localized.
- `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte` — in the recommendations `{#each}`, route each cell through the new catalog helper using `localeStore.locale`.
- `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts` — UA recommendation row assertion + unknown-key fallback assertion.

## Tasks & Acceptance

**Execution:**
- [x] `healthcabinet/frontend/src/lib/i18n/messages.ts` -- add `onboarding`, `settings`, `presets` bundles to `en`, satisfy in `uk` -- type parity enforces completeness.
- [x] `healthcabinet/frontend/src/lib/i18n/recommendation-catalog.ts` -- new helper with three translate functions and English fallthrough -- keep backend unchanged.
- [x] `healthcabinet/frontend/src/lib/i18n/recommendation-catalog.test.ts` -- cover every `_GENERAL_PANELS` and `_CONDITION_PANELS` entry plus unknown-key fallback.
- [x] `healthcabinet/frontend/src/routes/(onboarding)/onboarding/+page.svelte` -- swap hardcoded strings to `t(localeStore.locale).onboarding.*`; mount `LocaleToggle`.
- [x] `healthcabinet/frontend/src/routes/(onboarding)/onboarding/page.test.ts` -- extend with toggle + retranslation coverage.
- [x] `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` -- swap hardcoded strings to `t(localeStore.locale).settings.*`; localize validation messages and `ConfirmDialog` props.
- [x] `healthcabinet/frontend/src/routes/(app)/settings/page.test.ts` -- extend with toggle + retranslation + dirty-state coverage.
- [x] `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte` -- resolve recommendation cells via `recommendationCatalog`.
- [x] `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts` -- extend with UA recommendation + fallback assertions.
- [x] `healthcabinet/frontend/src/app.css` -- flex `.hc-wizard-header` so the locale toggle can sit right-aligned without a redesign.

**Acceptance Criteria:**
- Given `locale === 'uk'`, when a user walks `/onboarding` 1→3, then every visible string renders Ukrainian without a reload and validation errors respect the locale.
- Given `locale === 'uk'` and a saved profile, when `/settings` loads, then every fieldset / preset label / Save state / export / consent / delete-account UI renders Ukrainian while the submitted payload preserves canonical English `known_conditions` and `family_history`.
- Given loaded baseline recommendations, when `locale === 'uk'`, then `test_name` / `frequency` / `rationale` render Ukrainian from the frontend map; when a `test_name` is absent from the map, then the row renders the English fallback without error.
- Given a mid-flow locale toggle in onboarding or settings, then checked checkboxes stay checked, `isDirty` stays preserved, and only visible copy retranslates.
- Given `npm run check`, a partial `uk` bundle fails type-checking.
- Given the 15.6 suite, new tests added, `docker compose exec frontend npm run test:unit` passes with zero regressions.

## Design Notes

**Recommendation catalog** — flat `Record<Locale, Record<EnglishKey, UkrainianLabel>>` with English fallthrough for `en` and unknown keys. Unit test locks in full backend coverage so a new catalog entry can't silently regress to English in production.

**Why frontend-only for recommendations** — 15.6 invariant: UI owns copy, backend owns data. Backend `_CONDITION_PANELS` keyword matching depends on English `known_conditions`; translating on the backend would require a dual canonical/display contract or reverse-mapping, both larger than the ask.

**Onboarding toggle** — mount `LocaleToggle` inside `.hc-wizard-header`, right-aligned; reuse the same component/store/CSS family as AppShell and `(auth)/+layout.svelte`.

## Verification

**Commands:**
- `docker compose exec frontend npm run check` — 0 type errors.
- `docker compose exec frontend npm run test:unit` — baseline 764 tests + new additions all green.

**Manual checks:**
- Walk `/onboarding` → `/settings` → `/dashboard` in `uk`; toggle EN↔UA on each; confirm no English leaks, checked-state preserved, unsaved-changes guard still fires, recommendation rows switch languages.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context)

### Completion Notes

- **Foundation extension.** Added a shared `presets` bundle (conditions / familyHistory / sex) plus `onboarding` and `settings` bundles to `lib/i18n/messages.ts`, mirrored in `uk`. Type parity (`type Messages = typeof en`) enforces key-completeness at `npm run check`.
- **Recommendation catalog.** New `lib/i18n/recommendation-catalog.ts` exports `translateTestName` / `translateFrequency` / `translateRationale`. Keys cover every entry in backend `_GENERAL_PANELS` and `_CONDITION_PANELS`. English fallthrough applies for `locale === 'en'` and for unknown keys — a new backend row renders verbatim rather than throwing. Dev-only sanity: the `_catalogKeysForTests` export lets the test suite verify coverage. Acronym-identical entries like `HbA1c` and `PCOS` are legitimate — test uses `.toContain(name)` against the key set plus targeted `.not.toBe(…)` assertions on prose entries to catch catalog-drop regressions.
- **Onboarding wizard.** `routes/(onboarding)/onboarding/+page.svelte` now reads all copy from `t(localeStore.locale).onboarding` and `t(…).presets`. Validation errors are stored as sentinel keys (`'age' | 'height' | 'weight'`) and resolved at render so a mid-flow locale flip retranslates the error message without losing the validation state. `LocaleToggle` mounted in the wizard header, styled via an additive flex rule on `.hc-wizard-header`.
- **Settings / Medical Profile.** `routes/(app)/settings/+page.svelte` localizes all 7 fieldsets, the save-button tri-state (`Save Profile` / `Saving...` / `Saved`), the GDPR/export copy, the consent-history loading/empty/error states, the delete-account warning, the `ConfirmDialog` props (title / ariaLabel / confirmLabel / cancelLabel / loadingLabel / emailLabel), and the unsaved-changes `confirm()` prompt. Success/error banners and export/delete error states store sentinel booleans + optional backend `detail` passthrough (preserves Story 15.6 AC 5 invariant). `isDirty` tracking is unchanged — preset condition checkboxes stay bound to the canonical English strings so `known_conditions` / `family_history` payloads remain backend-compatible.
- **Dashboard recommendations.** `routes/(app)/dashboard/+page.svelte` resolves the three recommendation cells through the catalog helpers using `localeStore.locale`. Backend catalog is untouched.
- **Tests.** +23 new tests across 4 suites (recommendation-catalog: +13; onboarding page: +4; settings page: +4; dashboard page: +2). `beforeEach` / `afterEach` clear `window.localStorage` and call `localeStore._resetForTests()` to prevent cross-test locale pollution. Full suite 787/787 green inside Docker.
- **Scope held.** No backend changes. AI-generated content language deferred to a follow-up (see `deferred-work.md` entry "AI-generated content localization"). Covers user follow-up items #1 onboarding, #2 recommendations body, #3 settings, #4 dashboard gap; items #5 (AI Clinical Note body) and #6 (AI generation in UA) are deferred.

### File List

**New**
- `healthcabinet/frontend/src/lib/i18n/recommendation-catalog.ts`
- `healthcabinet/frontend/src/lib/i18n/recommendation-catalog.test.ts`

**Modified**
- `healthcabinet/frontend/src/lib/i18n/messages.ts`
- `healthcabinet/frontend/src/routes/(onboarding)/onboarding/+page.svelte`
- `healthcabinet/frontend/src/routes/(onboarding)/onboarding/page.test.ts`
- `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte`
- `healthcabinet/frontend/src/routes/(app)/settings/page.test.ts`
- `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte`
- `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts`
- `healthcabinet/frontend/src/app.css`
- `_bmad-output/implementation-artifacts/deferred-work.md` (appended AI-content-language deferred entry)

### Verification

- `docker compose exec frontend npm run check` — 0 errors, 0 warnings.
- `docker compose exec frontend npm run test:unit` — 72 files / 787 tests / 0 failures. Baseline was 764; net +23.

## Change Log

| Date       | Change                                                                                                                                          | Author |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| 2026-04-22 | Spec created (split from user's 6-item follow-up request; AI-content-language items #5 and #6 deferred).                                         | SM     |
| 2026-04-22 | Implemented onboarding + settings + recommendation-catalog localization; +23 tests, 787/787 green. Status → in-review.                          | Dev    |
| 2026-04-22 | Code review follow-up fixes applied (settings family-history preset parity, localized consent-history rows, dev-only recommendation fallback warnings). Status → done. | Codex  |
