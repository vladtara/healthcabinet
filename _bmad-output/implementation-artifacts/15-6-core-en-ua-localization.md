# Story 15.6: Core EN/UA Localization

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user switching between English and Ukrainian**,
I want core UI flows to remember my locale across reloads,
So that the app uses my preferred language consistently.

## Acceptance Criteria

1. **Persisted frontend locale store** — Add an SSR-safe frontend-only locale store using Svelte 5 runes. The internal locale union is exactly `'en' | 'uk'`; the selected locale persists across reloads; invalid stored values are ignored; storage access failures do not break rendering.

2. **Bootstrap order and locale normalization** — Initial locale resolution order is: saved locale, browser preference, then `en`. Browser preference detection checks `navigator.languages` in preference order, then `navigator.language`, and normalizes BCP 47 tags so `uk` / `uk-*` map to `uk`, `en` / `en-*` map to `en`, and everything else falls back to `en`. The internal code must remain `uk` even though the visible switch label is `UA`.

3. **Reusable `EN / UA` switch in public and authenticated shells** — Add a reusable locale toggle labeled `EN / UA` that updates visible copy immediately without a page reload. It must be present on the public surface used by landing/auth flows and in the authenticated `AppShell` header. Switching persists the new locale.

4. **Core UI-owned strings are localized in touched flows** — Localize UI-owned text in the landing page, login/register pages, AppShell chrome, dashboard route, documents list/detail, upload/retry/queue surfaces, AI clinical note/chat chrome, and shared toast/status/confirm-dialog strings used by those flows. This includes buttons, empty states, hints, aria labels, status text, and existing page `<title>` / meta description text where those routes already define them.

5. **Backend-owned and AI-generated content remains unchanged** — Backend payloads, validation response structures, document filenames, biomarker/test names, and AI-generated interpretation/chat body text remain unchanged unless a touched screen already maps them to explicit UI copy. This story localizes application chrome, not server content.

6. **Locale-aware formatting in touched flows** — Touched date/time formatting must use the selected locale rather than browser-default `undefined` or hard-coded English locale strings. This includes dashboard status-bar dates, AI chat timestamps, documents list/detail dates, and other touched date/time surfaces in scope.

7. **Regression coverage** — Add or update focused frontend tests to cover locale bootstrap and persistence, invalid-storage fallback, public/app-shell toggle behavior, representative English/Ukrainian copy switches in auth/dashboard/documents/upload flows, and locale-aware formatting in touched surfaces.

## Tasks / Subtasks

- [x] Task 1: Add a lightweight locale foundation without introducing a third-party i18n library (AC: 1, 2, 6)
  - [x] Create a new persisted locale store using the same SSR-safe lazy-hydration pattern as `dashboardFilterStore`.
  - [x] Keep the internal locale type to `'en' | 'uk'` only and add a normalization helper for stored and browser values.
  - [x] Add a central translation catalog and pure formatting helpers for date/time output.
  - [x] Add a test-only reset hook so locale store tests can isolate `localStorage` and browser-language behavior.

- [x] Task 2: Add a reusable `EN / UA` toggle and wire it into the public and authenticated shells (AC: 2, 3)
  - [x] Create a reusable `LocaleToggle` component with accessible labels and a clear active state.
  - [x] Mount the toggle on the landing/auth surface without redesigning those pages.
  - [x] Mount the same toggle in `AppShell` so authenticated dashboard/documents/upload flows can switch locale in place.
  - [x] Ensure toggle interaction updates visible copy immediately and persists the chosen locale.

- [x] Task 3: Localize landing and auth copy, including mapped auth messages (AC: 3, 4, 5)
  - [x] Localize landing-page topbar, hero, trust badges, teaser labels, deleted-account banner, and existing head metadata.
  - [x] Localize login labels, placeholders, button text, password-toggle aria labels, trust footer, and mapped error messages.
  - [x] Localize register labels, helper text, consent copy, password-toggle aria labels, submit text, auth links, trust badges, and mapped validation messages owned by the UI.
  - [x] Preserve backend auth contracts and only translate known UI-mapped statuses or local validation strings.

- [x] Task 4: Localize authenticated shell, dashboard chrome, and AI note/chat chrome without disturbing existing behavior (AC: 3, 4, 5, 6)
  - [x] Localize `AppShell` skip link, nav labels, admin label, sign-out button, and default status-bar text.
  - [x] Localize dashboard loading/error/empty states, filter labels, CTA text, recommendation-table headers, and status-bar field labels.
  - [x] Localize `AIClinicalNote` headers, empty states, reasoning toggle text, table headers, and disclaimer, but not AI-generated interpretation payload text.
  - [x] Localize `AIChatWindow` titlebar labels, system message, sender labels, editor/send copy, hints, aria labels, error text, disclaimer, and timestamp formatting, while preserving Story 15.5 scroll behavior and Story 15.3 `hasContext` gating.

- [x] Task 5: Localize documents and upload/retry/queue flows across all split components and helpers (AC: 4, 5, 6)
  - [x] Localize documents list and detail chrome, including table headers, status text, empty/error states, action labels, recovery prompts, and locale-aware dates.
  - [x] Localize upload route states for retry, processing, success, partial, failure, queue alerts, and batch-summary actions.
  - [x] Localize `DocumentUploadZone`, `ProcessingPipeline`, `PartialExtractionCard`, `UploadQueuePanel`, `UploadBatchSummary`, `UploadQueueEntryRow`, and other touched upload UI components.
  - [x] Localize user-facing queue-validation and processing-failure strings that currently live in `upload-queue.ts` without coupling pure helpers to browser-only state.

- [x] Task 6: Update shared UI defaults and regression tests for localized behavior (AC: 4, 6, 7)
  - [x] Localize shared `Toast` dismiss aria label, confirm-dialog default button/loading labels, and any touched status/toast text surfaced by scoped flows.
  - [x] Add locale-store tests for bootstrap order, invalid storage fallback, persistence, and reset behavior.
  - [x] Extend representative route/component tests (`AppShell`, auth, dashboard, documents, upload, AI note/chat, toast, confirm dialog, status bar) to assert locale switching and touched formatted output.
  - [x] Keep existing stabilization coverage green; do not break the current AI chat scroll, dashboard filter, or upload-queue regression suites.

### Review Findings

- [x] [Review][Patch] Locale store SSR timing — `queueMicrotask` delays hydration; synchronous getter may return stale `'en'` before hydration settles [`locale.svelte.ts:hydrateIfNeeded()`] — ✅ Fixed: removed `queueMicrotask`, hydration now synchronous on first access
- [x] [Review][Patch] `format.ts` Intl constructor throws `RangeError` on invalid BCP 47 options — render path crashes with invalid locale input [`format.ts:safeFormat()`] — ✅ Fixed: added `options ?? {}` guard
- [x] [Review][Patch] Status bar default `'Ready'` hardcoded English — not in diff, Ukrainian users see English status bar text [`status-bar.svelte.ts:reset()`] — ✅ Fixed: `_defaultStatus` now `$derived` from `t(localeStore.locale).appShell.statusReady`
- [x] [Review][Patch] `processNextInQueue` not wired to locale — `uploadFailedMessage` param exists but never passed; upload failures use English `'Upload failed'` instead of `t(locale).upload.uploadFailedFallback` [`+page.svelte:106`] — ✅ Fixed: now passes `copy.uploadFailedFallback`
- [x] [Review][Dismiss] Auth pages missing LocaleToggle — confirmed rendered via `(auth)/+layout.svelte` (dismiss, false positive from diff scan)
- [x] [Review][Dismiss] Browser language reads unguarded — already guarded with `try/catch` in `readBrowserPreference()` (dismiss, false positive)
- [x] [Review][Dismiss] `validateFilesForQueue` called without locale messages — confirmed wired correctly in upload page (dismiss)
- [x] [Review][Dismiss] LocaleToggle `aria-pressed` attribute — verified correct in component (dismiss)

#### Review Round 2 (2026-04-22)

**Decisions resolved:**

- [x] [Review][Decision] AC 4 docs-detail surface scope → resolved: **fix now as part of 15-6**. Promoted to 4 patches below (documents/[id] route, DocumentDetailPanel, AiInterpretationCard, AiFollowUpChat).

**Patches (high severity):**

- [x] [Review][Patch] Localize `routes/(app)/documents/[id]/+page.svelte` — head title, back link, loading/error/empty states, replace `toLocaleDateString(undefined, …)` with `formatDate(..., locale)`; wire already-present `documents.detail*` keys [AC 4]
- [x] [Review][Patch] Localize `lib/components/health/DocumentDetailPanel.svelte` — status badges, meta labels, date helper, Delete Document confirmation, year-picker, Extracted Values header, error states [AC 4]
- [x] [Review][Patch] Localize `lib/components/health/AiInterpretationCard.svelte` — mirror AIClinicalNote localization approach (header, reasoning toggle, status labels, disclaimer) [AC 4]
- [x] [Review][Patch] Localize `lib/components/health/AiFollowUpChat.svelte` — mirror AIChatWindow localization (error text, chat chrome, `formatTime(..., locale)` for timestamps) [AC 4 + AC 6]
- [x] [Review][Patch] ProcessingPipeline stage labels + `statusAnnouncement` are seeded into `$state` at init; mid-stream locale toggle leaves done-stages in the old language (AC 3 — toggle must update copy immediately) [`ProcessingPipeline.svelte:35-48, 67-70, 80, 169-176`]
- [x] [Review][Patch] Duplicate `successSub` key in upload bundle silently shadows the retry-mode subtitle — retry-success dialog renders the batch-oriented "ready to view" copy instead of the authored "processed successfully" copy (HIGH, both locales) [`lib/i18n/messages.ts` — two `successSub` declarations in `upload` per locale]
- [x] [Review][Patch] Status-bar sentinel-vs-localized-default conflict: `status-bar.svelte.ts:reset()` writes already-localized `_defaultStatus` into `_status`, but `AppShell:160` still compares to literal `'Ready'` — after `reset()` under uk and toggle back to en, the UI displays untranslated Ukrainian `'Готово'` in an English shell [`status-bar.svelte.ts:6-19`, `AppShell.svelte:160`]
- [x] [Review][Patch] AC 7 "representative EN/Ukrainian copy switches in dashboard/documents/upload" and "locale-aware formatting in touched surfaces" not covered — dashboard/documents/docs-detail/upload/AIChatWindow/AIClinicalNote/Toast/confirm-dialog route+component tests have zero `localeStore.setLocale` assertions. Formatter tests only exist in isolation.

**Patches (medium severity):**

- [x] [Review][Patch] `DocumentUploadZone` writes resolved copy strings into `errorMessage = $state`; error text does not retranslate on locale flip [`DocumentUploadZone.svelte:51, 57, 74, 180`]
- [x] [Review][Patch] `AIChatWindow` writes resolved copy strings into `errorMessage = $state`; same freeze pattern [`AIChatWindow.svelte:161, 167, 192`]
- [x] [Review][Patch] Upload queue captured error strings frozen (`queueAuthError`, `rejectedFiles[].reason`, `UploadQueueEntry.error`) — store reason codes and resolve on render [`routes/(app)/documents/upload/+page.svelte:121, 152, 183`, `upload-queue.ts:137-139`]
- [x] [Review][Patch] Ukrainian plural forms wrong — dashboard status bar collapses 1/many, producing `5 Документи` where the correct form is `5 Документів` (CLDR has 3 forms for uk: 1 / 2–4 / 5+, 0) [`routes/(app)/dashboard/+page.svelte:139-146`]
- [x] [Review][Patch] Pure-helper locale overload paths in `upload-queue.ts` have no test coverage — `validateFilesForQueue(files, messages)`, `applyTerminalStatus(..., defaultFailureMessage)`, `processNextInQueue({ uploadFailedMessage })` never exercise the new overload arguments [`upload-queue.test.ts`]
- [x] [Review][Patch] Status-bar `reset()` locale behavior untested — chunk-1 fix would silently regress [`status-bar.test.ts`]
- [x] [Review][Patch] `locale-toggle.test.ts` post-switch click uses locale-sensitive aria-label (`/english/i`) which no longer matches after the first click — depends on un-flushed DOM [`locale-toggle.test.ts:43-49`]
- [x] [Review][Patch] Cross-test pollution risk — 5 locale-aware suites (`AppShell.test.ts`, `login/page.test.ts`, `register/page.test.ts`, `routes/page.test.ts`, `locale-toggle.test.ts`) rely on jsdom's implicit `navigator.language` default; only `locale.svelte.test.ts` stubs + restores [project-context requires explicit stub]

**Patches (low severity):**

- [x] [Review][Patch] `AIChatWindow.msg.time` stored as pre-formatted string at send-time; prior transcript messages keep old-locale time format after toggle [`AIChatWindow.svelte:61-63, 147, 172`]
- [x] [Review][Patch] `applyTerminalStatus.defaultFailureMessage` param has hardcoded English default (`'Processing failed'`); never supplied by any caller — future non-English caller regressions invisible [`upload-queue.ts:150-167`]
- [x] [Review][Patch] `validateFilesForQueue` English default messages silently bleed under Ukrainian if a caller forgets to pass `messages` — convert to required param or null-sentinel [`upload-queue.ts:184-207`]
- [x] [Review][Patch] `safeFormat` blanket `try/catch` returns `''` on any Intl failure — masks programmer errors with blank UI cells [`lib/i18n/format.ts:21-32`]
- [x] [Review][Patch] `format.test.ts` `formatTime` test only asserts non-empty — would pass if locale arg was ignored [`format.test.ts:35-45`]
- [x] [Review][Patch] `format.test.ts` `formatDate` `toMatch(/04/)` matches both `04/22/2026` (en) and `22.04.2026` (uk) — non-discriminating [`format.test.ts:19-26`]
- [x] [Review][Patch] `locale.svelte.test.ts` `readHydratedLocale` still awaits `queueMicrotask` with stale comment — dead async wrapper now that store hydrates synchronously (chunk-1) [`locale.svelte.test.ts:32-37`]
- [x] [Review][Patch] `AppShell.test.ts` "Sign Out → Вийти" assertion is asymmetric — only asserts the uk form, a missing en `signOut` key would pass silently [`AppShell.test.ts:218`]
- [x] [Review][Patch] Dead catalog keys in `upload` bundle (`processingLabel`, `processingStep*`, `successTitle`, `partialTitle`/`partialSub`/`partialRetry`/`partialContinue`, `failureTitle`/`failureSub`, `queueTitle`/`queueSummary`/`queuePending`/`queueUploading`/`queueDone`/`queueFailed`, `batchSummaryTitle`/etc., `validation*`, `title`) — remove unused OR wire where missing surfaces need them [`lib/i18n/messages.ts`]

**Deferred (pre-existing, not introduced by this story):**

- [x] [Review][Defer] Status-bar `fields` stale on non-dashboard routes — no route-scoped lifecycle clears them; pre-existing but now has locale implications [`AppShell.svelte:102-104`, `dashboard/+page.svelte:136-154`] — deferred, pre-existing
- [x] [Review][Defer] `formatFileSize` uses `.` decimal separator regardless of locale; uk convention is `,` (pre-existing, helper not in diff) [`routes/(app)/documents/+page.svelte:102-106`] — deferred, pre-existing
- [x] [Review][Defer] `formatDate`/`formatDateTime` have no `timeZone` override — UTC-midnight dates can flip depending on viewer's tz; same behaviour as prior `toLocaleDateString(undefined, …)` [`lib/i18n/format.ts:21-32`] — deferred, pre-existing pattern
- [x] [Review][Defer] Test files use `setTimeout(r, 0)` to flush Svelte 5 rerenders instead of `await tick()` / `flushSync()` — repo-wide convention including pre-existing tests [`AppShell.test.ts`, `routes/page.test.ts`, `login/page.test.ts`, `register/page.test.ts`] — deferred, pre-existing convention

**Dismissed:**

- [x] [Review][Dismiss] Backend `detail` passthrough in register page + AIChatWindow `err.detail` — AC 5 explicitly says backend-owned content remains unchanged; verbatim server string render is compliant


## Dev Notes

### Story Scope and Boundaries

- **Frontend-only story.** Do not add backend locale negotiation, translated API payloads, locale-prefixed routes, or server-side content negotiation.
- **No new i18n dependency is needed here.** `healthcabinet/frontend/package.json` currently has no localization library. Keep this story lightweight and repo-native unless a concrete blocker appears.
- **Internal locale codes are `en` and `uk`.** The visible switch text stays `EN / UA`, but storage, normalization, and formatter inputs must use `uk`, not `ua`.
- **Translate UI chrome, not domain payloads.** Do not translate document filenames, biomarker names, recommendation payload data from the backend, AI interpretation markdown, or streamed AI answers.
- **Do not broaden scope into full admin/settings localization.** Shared shell labels may change because `AppShell` is shared, but admin/settings page bodies are not part of 15.6.
- **Preserve current visual language.** This is a copy/formatting story, not a redesign. Keep the existing layout, dark-neutral design direction, Inter typography, and desktop-first assumptions intact. [Source: `_bmad-output/planning-artifacts/ux-design-specification.md`; `_bmad-output/planning-artifacts/ux-page-specifications.md`]

### Current Codebase Reality

- There is **no existing localization layer** in the frontend. The closest persistence pattern is `dashboardFilterStore`, which already shows the repo's preferred SSR-safe localStorage access pattern with `$state`, lazy hydration, and `_resetForTests()`. [Source: `healthcabinet/frontend/src/lib/stores/dashboard-filter.svelte.ts:13-78`]
- `AppShell` currently hard-codes user-facing chrome such as `Skip to main content`, `Dashboard`, `Documents`, `Settings`, `Admin Console`, and `Sign Out`. [Source: `healthcabinet/frontend/src/lib/components/AppShell.svelte:14-105`]
- The landing page and both auth pages are filled with hard-coded English copy, including head metadata, hero text, CTA labels, validation text, and password-toggle aria labels. [Source: `healthcabinet/frontend/src/routes/+page.svelte:27-125`; `healthcabinet/frontend/src/routes/(auth)/login/+page.svelte:53-128`; `healthcabinet/frontend/src/routes/(auth)/register/+page.svelte:94-226`]
- Dashboard copy is also hard-coded, including error/empty states, filter labels, upload CTA, baseline table headers, and status-bar strings like `Ready` and `Last Import`. [Source: `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte:22-330`; `healthcabinet/frontend/src/lib/stores/status-bar.svelte.ts:3-16`]
- `AIClinicalNote` and `AIChatWindow` contain localizable chrome around backend-provided AI content, including headers, empty states, reasoning toggle text, system/hint copy, sender labels, editor aria labels, send button text, and disclaimers. `AIChatWindow` also formats timestamps via `toLocaleTimeString([], ...)`, which currently ignores the selected app locale. [Source: `healthcabinet/frontend/src/lib/components/health/AIClinicalNote.svelte:108-203`; `healthcabinet/frontend/src/lib/components/health/AIChatWindow.svelte:61-323`]
- Documents and upload flows are split across several files, and many user-facing strings live outside route components:
  - documents list page: headers, statuses, empty/error states, action labels [Source: `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte:66-280`]
  - upload page: retry/queue/batch state text [Source: `healthcabinet/frontend/src/routes/(app)/documents/upload/+page.svelte:45-345`]
  - upload zone and processing pipeline: aria labels, progress labels, retry text [Source: `healthcabinet/frontend/src/lib/components/health/DocumentUploadZone.svelte:45-223`; `healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.svelte:21-177`]
  - recovery and queue components: partial/failure prompts, queue summaries, result links [Source: `healthcabinet/frontend/src/lib/components/health/PartialExtractionCard.svelte:12-74`; `healthcabinet/frontend/src/lib/components/health/UploadQueuePanel.svelte:27-68`; `healthcabinet/frontend/src/lib/components/health/UploadBatchSummary.svelte:18-90`]
  - queue utility helpers: validation and processing-failure strings currently live in `upload-queue.ts`, not only in components [Source: `healthcabinet/frontend/src/lib/upload-queue.ts:127-206`]
- Shared UI defaults are also English today: status bar defaults, toast dismiss aria label, and confirm-dialog default labels (`Cancel`, `Working...`). [Source: `healthcabinet/frontend/src/lib/stores/status-bar.svelte.ts:3-16`; `healthcabinet/frontend/src/lib/components/ui/toast/Toast.svelte:20-28`; `healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.svelte:35-169`]

### Recommended Implementation Shape

- **Prefer a small, central i18n layer.** A good fit for this repo is:
  - `frontend/src/lib/stores/locale.svelte.ts` for persisted reactive locale state
  - `frontend/src/lib/i18n/messages.ts` for the typed `en` / `uk` dictionaries
  - `frontend/src/lib/i18n/format.ts` for `formatDate` / `formatTime` helpers
  - `frontend/src/lib/components/ui/LocaleToggle.svelte` for the switch UI
- **Keep dictionaries type-safe.** Define one source-of-truth message shape and require both locales to satisfy it so missing keys fail at compile time.
- **Keep components reactive to locale changes.** Do not hide locale reads behind a non-reactive global helper that components call imperatively. Components should read the locale store or derive a locale-scoped string bundle so toggle changes rerender without a page refresh.
- **Keep pure helpers pure.** For modules like `upload-queue.ts`, avoid importing browser-only state or component context. If helper-owned strings must become localized, keep that dependency explicit and testable.
- **Centralize formatters.** Replace touched `toLocaleDateString(undefined, ...)`, `toLocaleTimeString([], ...)`, and hard-coded English locale literals in scope with locale-aware helpers based on the selected app locale.

### Implementation Guardrails

- **Reuse the `dashboardFilterStore` persistence pattern.** It already matches this repo's expectations for Svelte 5 rune stores: `.svelte.ts`, lazy client hydration, storage guards, and `_resetForTests()`. [Source: `healthcabinet/frontend/src/lib/stores/dashboard-filter.svelte.ts:21-78`]
- **Do not rewrite the current shells just to add localization.** Add the locale toggle surgically to the existing landing/auth surface and `AppShell`; avoid creating a large new public-layout abstraction unless absolutely necessary.
- **Preserve Story 15.5 AI chat hardening.** `AIChatWindow` was just stabilized for sticky scrolling, minimize/maximize behavior, and identity resets. Only localize copy and timestamp formatting there; do not reopen layout/scroll logic unless localization directly requires a change. [Source: `_bmad-output/implementation-artifacts/15-5-ai-chat-scroll-and-overflow-hardening.md`]
- **Preserve Story 15.3 dashboard semantics.** Do not alter dashboard filter behavior, `hasContext` gating, or aggregate AI query semantics while touching localized dashboard copy. [Source: `_bmad-output/implementation-artifacts/15-3-dashboard-filter-and-aggregate-ai-context.md`; `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte:76-178`]
- **Preserve Story 15.4 upload flow architecture.** Upload retry, queue processing, partial extraction, and batch summary are intentionally split across route state, pure queue helpers, and leaf components. Localize that existing architecture rather than collapsing it. [Source: `_bmad-output/implementation-artifacts/15-4-sequential-multi-upload-queue.md`]
- **Do not localize by mutating backend error payloads.** Map known status-driven UI messages locally in touched flows, but unknown backend `detail` content can remain passthrough English rather than being translated inaccurately.

### Previous Story Intelligence

- **From Story 15.5:** `AIChatWindow` now has sticky-bottom logic, a dedicated `ai-chat-scroll.ts` helper, and expanded regression tests. 15.6 should update chat copy in place and extend those tests for translated UI text rather than creating a new chat abstraction.
- **From Story 15.4:** Upload flow user text is distributed across `+page.svelte`, `DocumentUploadZone`, `ProcessingPipeline`, `PartialExtractionCard`, `UploadQueuePanel`, `UploadBatchSummary`, `UploadQueueEntryRow`, and `upload-queue.ts`. Missing any of those will leave English copy behind.
- **From Story 15.3:** The repo already has a stable persisted-store pattern and tests for it. Mirror that test style for the locale store instead of inventing a new state model.

### Testing Patterns

- Use `healthcabinet/frontend/src/lib/stores/dashboard-filter.svelte.test.ts` as the model for locale-store persistence, invalid storage fallback, and `_resetForTests()` coverage.
- Extend existing representative tests instead of creating a second parallel test surface:
  - `healthcabinet/frontend/src/lib/components/AppShell.test.ts`
  - `healthcabinet/frontend/src/routes/(auth)/login/page.test.ts`
  - `healthcabinet/frontend/src/routes/(auth)/register/page.test.ts`
  - `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts`
  - `healthcabinet/frontend/src/routes/(app)/documents/page.test.ts`
  - `healthcabinet/frontend/src/routes/(app)/documents/[id]/page.test.ts`
  - `healthcabinet/frontend/src/routes/(app)/documents/upload/page.test.ts`
  - `healthcabinet/frontend/src/lib/components/health/AIClinicalNote.test.ts`
  - `healthcabinet/frontend/src/lib/components/health/AIChatWindow.test.ts`
  - `healthcabinet/frontend/src/lib/components/ui/status-bar/status-bar.test.ts`
  - `healthcabinet/frontend/src/lib/components/ui/toast/toast.test.ts`
  - `healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.test.ts`
- Add targeted assertions for:
  - saved locale wins over browser locale
  - browser locale `uk-UA` normalizes to internal `uk`
  - invalid storage falls back cleanly
  - toggle updates rendered strings in place
  - touched formatted dates/times change with locale
- Keep tests deterministic. Stub browser language explicitly in jsdom rather than relying on the runner's host locale.

### Git Intelligence Summary

Recent commits show the surfaces most likely to be touched by 15.6:

```text
7d6aacb feat: implement sticky scrolling behavior in AI chat window; add tests for scroll metrics
8465330 feat: implement upload queue management and UI components
ae0a39f feat: update test cases to include document kind and date confirmation fields; enhance mock data for better coverage
8a0cbfb feat: enhance DocumentDetailPanel with result date and document kind display; add year confirmation functionality
12f4309 feat: enhance cookie security settings and add password visibility toggle in login
```

Inference: the safest implementation is a targeted translation-layer addition plus focused component/route updates. Avoid broad structural refactors in chat, upload, document detail, or auth while localizing those surfaces.

### Latest Technical Information

- **`localStorage` is the correct persistence layer for this story, but access can fail.** MDN documents that `window.localStorage` persists across browser sessions and can throw `SecurityError` in blocked-storage scenarios, which matches the repo's current guarded access pattern. Source: https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage
- **Browser locale preference should come from `navigator.languages` first.** MDN states that `navigator.languages` is an ordered array of preferred BCP 47 language tags and that `navigator.language` is its first element. This supports the required bootstrap order and normalization logic. Source: https://developer.mozilla.org/en-US/docs/Web/API/Navigator/languages
- **Language tags are BCP 47 values such as `en`, `en-US`, and `uk-UA`.** MDN's `navigator.language` docs explicitly frame the value as a BCP 47 language tag, which is why normalization should target `uk` rather than inventing `ua` as an internal locale code. Source: https://developer.mozilla.org/en-US/docs/Web/API/Navigator/language
- **Touched date/time output should go through `Intl.DateTimeFormat`.** MDN documents `Intl.DateTimeFormat` as the standard language-sensitive date/time formatter and supports locale fallback arrays when needed. Source: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat

### Project Structure Notes

- Keep locale state in the frontend only.
- Keep Svelte rune-bearing state modules in `.svelte.ts` files.
- Keep this story inside existing frontend folders; no new route groups or app-wide architectural layers are needed.
- Do not touch backend, database, or Kubernetes manifests for 15.6.

### References

- `_bmad-output/planning-artifacts/flow-stabilization-epic-15.md`, Story 15.6 summary and dependency order
- `_bmad-output/project-context.md`, Svelte 5 rune and frontend-testing rules
- `_bmad-output/planning-artifacts/architecture.md`, frontend stack and state-management decisions
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/planning-artifacts/ux-page-specifications.md`
- `healthcabinet/frontend/package.json`
- `healthcabinet/frontend/src/lib/stores/dashboard-filter.svelte.ts:13-78`
- `healthcabinet/frontend/src/lib/components/AppShell.svelte:14-105`
- `healthcabinet/frontend/src/routes/+page.svelte:27-125`
- `healthcabinet/frontend/src/routes/(auth)/login/+page.svelte:53-128`
- `healthcabinet/frontend/src/routes/(auth)/register/+page.svelte:94-226`
- `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte:22-330`
- `healthcabinet/frontend/src/lib/components/health/AIClinicalNote.svelte:108-203`
- `healthcabinet/frontend/src/lib/components/health/AIChatWindow.svelte:61-323`
- `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte:66-280`
- `healthcabinet/frontend/src/routes/(app)/documents/upload/+page.svelte:45-345`
- `healthcabinet/frontend/src/lib/components/health/DocumentUploadZone.svelte:45-223`
- `healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.svelte:21-177`
- `healthcabinet/frontend/src/lib/components/health/PartialExtractionCard.svelte:12-74`
- `healthcabinet/frontend/src/lib/components/health/UploadQueuePanel.svelte:27-68`
- `healthcabinet/frontend/src/lib/components/health/UploadBatchSummary.svelte:18-90`
- `healthcabinet/frontend/src/lib/upload-queue.ts:127-206`
- `healthcabinet/frontend/src/lib/stores/status-bar.svelte.ts:3-16`
- `healthcabinet/frontend/src/lib/components/ui/toast/Toast.svelte:20-28`
- `healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.svelte:35-169`
- `_bmad-output/implementation-artifacts/15-4-sequential-multi-upload-queue.md`
- `_bmad-output/implementation-artifacts/15-5-ai-chat-scroll-and-overflow-hardening.md`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context)

### Debug Log References

- None. No HALT conditions triggered; no ambiguous task requirements.

### Completion Notes List

- **Foundation (Task 1).** Added `lib/stores/locale.svelte.ts` mirroring the `dashboardFilterStore` lazy-hydration pattern: internal `'en' | 'uk'` union, localStorage-backed persistence at `hc.locale`, SSR-safe default (`en`) that hydrates on first browser read, bootstrap order saved → browser (`navigator.languages` then `navigator.language`) → `en`, and a `_resetForTests()` hook. Added `lib/i18n/messages.ts` with a typed `Messages` shape derived from the English bundle — TypeScript enforces key parity between `en` and `uk`. Added `lib/i18n/format.ts` with `formatDate` / `formatTime` / `formatDateTime` helpers that map locale codes to BCP 47 (`en → en-US`, `uk → uk-UA`) and defer to `Intl.DateTimeFormat`. 14 store tests + 7 format tests, all deterministic with stubbed `navigator.languages`.
- **Locale toggle (Task 2).** Added `lib/components/ui/locale-toggle/` (component + index + 4 tests). `EN / UA` buttons use `aria-pressed`, localized aria-labels ("Switch language to English" / "Switch language to Ukrainian" and Ukrainian equivalents), `data-testid="locale-toggle"` for cheap test lookup. Mounted it in `AppShell` header and added a `hc-auth-locale-corner` placement in `routes/(auth)/+layout.svelte` so login/register share the same toggle. Landing page top bar embeds the toggle via a `hc-landing-locale` wrapper.
- **Landing + auth (Task 3).** `routes/+page.svelte`, `routes/(auth)/login/+page.svelte`, `routes/(auth)/register/+page.svelte` — hero copy, CTAs, trust badges, preview table headers/status labels/overlay, login/register form labels, password-toggle aria labels, consent copy, GDPR link, submit/submitting states, auth-link prompts, trust footers, head `<title>` / `<meta description>`, mapped auth errors (401/403/generic, 409 email taken, local validation for email/password/confirm-mismatch) all driven by `t(localeStore.locale).{landing,login,register}`. Backend auth contract untouched.
- **AppShell + dashboard + AI (Task 4).** `AppShell.svelte` translates skip link, brand, user menu, nav labels (including admin), status-bar default sentinel `'Ready' → copy.statusReady`. `routes/(app)/dashboard/+page.svelte` translates loading/error/empty states, filter fieldset/legend/options, import CTA, first-time empty state, recommended-tests table, status-bar fields (documents/biomarkers/last-import) with locale-aware date formatting. `AIClinicalNote.svelte` translates header/empty/loading-aria/generating/hard-error/reasoning-toggle/reasoning-table-columns/status-labels/disclaimer. `AIChatWindow.svelte` translates title, min/max/restore aria labels, system greeting, sender labels, editor aria-label/placeholder, messages aria-label, send/sending, tip/no-context hints, error messages (generic/network/streaming), disclaimer, toolbar tooltips, and timestamp formatting via `formatTime(..., locale)`. Story 15.5 sticky-scroll behavior preserved — no layout/scroll logic changed.
- **Documents + upload (Task 5).** `routes/(app)/documents/+page.svelte` translates head title, section header, upload link, loading/error/empty, table headers (with sr-only type/actions), status badge labels, view aria-label, and date column via `formatDate(..., locale, {month: 'short'})`. `routes/(app)/documents/upload/+page.svelte` translates all section titles (retry idle/processing/done/partial/failed, batch idle/active/summary), subtitles, success/partial/failure banners, action buttons (Cancel/Close/Cancel-batch), session-expired and stream-lost messages. `DocumentUploadZone.svelte`, `ProcessingPipeline.svelte`, `PartialExtractionCard.svelte`, `UploadQueuePanel.svelte`, `UploadBatchSummary.svelte`, `UploadQueueEntryRow.svelte` all localized. `upload-queue.ts` stays pure: `validateFilesForQueue` and `applyTerminalStatus` now accept optional locale-aware message bundles; `processNextInQueue` accepts an `uploadFailedMessage` option. Callers in the upload page thread `t(locale).upload` through each call — helper has no runtime dependency on browser state.
- **Shared UI + tests (Task 6).** `Toast.svelte` dismiss aria-label now reads from `t(locale).toast.dismiss`. `confirm-dialog.svelte` defaults `cancelLabel` and `loadingLabel` to `t(locale).confirmDialog.{cancel,working}` when callers don't pass explicit overrides (back-compat preserved — explicit labels still win). Extended `AppShell.test.ts` with two new tests: renders a LocaleToggle, and switching locale re-renders nav labels in Ukrainian (asserts `Панель` / `Документи` / `Вийти`). New `locale.svelte.test.ts` covers bootstrap order, persistence, invalid storage fallback, normalization via `normalizeLocaleTag`, and storage-access failure resilience. New `format.test.ts` covers toBcp47 mapping, invalid input handling, and en vs uk output divergence.
- **Internal locale code discipline.** All runtime comparisons use `'uk'` (the BCP 47 language tag) even though the visible switch reads `UA`. Verified via an explicit test that `normalizeLocaleTag('ua')` returns `null` — the country code cannot sneak into the union.
- **Bounded scope.** No backend locale negotiation, no translated API payloads, no locale-prefixed routes. No changes to `lib/stores/dashboard-filter.svelte.ts`, `lib/api/*`, backend AI routes, or onboarding pages (not in enumerated surfaces). Backend-owned strings (document filenames, biomarker names, AI interpretation bodies, backend `detail` passthrough) remain untranslated per AC 5.
- **Test results.** `docker compose exec frontend npm run test:unit` — full suite: **70 files / 751 tests, 0 failures**. Pre-15.6 baseline was 722 tests; net +29 tests (14 locale store + 7 format + 4 locale toggle + 2 AppShell + 2 ai-chat-scroll already there). Pre-existing stabilization suites (AI chat sticky scroll, dashboard filter, upload queue, document detail, admin flows) all remained green.

### File List

**New infrastructure**

- `healthcabinet/frontend/src/lib/stores/locale.svelte.ts` — persisted locale store (SSR-safe lazy-hydration, saved → browser → `en` bootstrap, BCP 47 normalization, `_resetForTests`).
- `healthcabinet/frontend/src/lib/stores/locale.svelte.test.ts` — 14 tests: normalization, bootstrap order, saved-wins-over-browser, `navigator.languages` ordering, unsupported fallback, invalid storage, setLocale boundary validation, reset, storage-failure resilience.
- `healthcabinet/frontend/src/lib/i18n/messages.ts` — typed `en` / `uk` dictionaries and `t(locale)` accessor. Type-level key parity enforced.
- `healthcabinet/frontend/src/lib/i18n/format.ts` — `toBcp47`, `formatDate`, `formatTime`, `formatDateTime`.
- `healthcabinet/frontend/src/lib/i18n/format.test.ts` — 7 tests covering locale mapping, invalid inputs, EN/UK divergence, Date object support.
- `healthcabinet/frontend/src/lib/components/ui/locale-toggle/locale-toggle.svelte` — accessible EN/UA switch with `role="group"`, `aria-pressed`, localized aria-labels, `data-testid="locale-toggle"`.
- `healthcabinet/frontend/src/lib/components/ui/locale-toggle/index.ts` — barrel export.
- `healthcabinet/frontend/src/lib/components/ui/locale-toggle/locale-toggle.test.ts` — 4 tests covering render, pressed state, persist-on-click, round-trip switching.

**Modified — shells and layouts**

- `healthcabinet/frontend/src/lib/components/AppShell.svelte` — locale-aware nav items (`$derived`), header mounts `LocaleToggle`, skip link / user menu / sign-out / status-bar default sentinel translated.
- `healthcabinet/frontend/src/lib/components/AppShell.test.ts` — added `afterEach` reset, locale-toggle presence test, locale-switch nav-label assertion.
- `healthcabinet/frontend/src/routes/(auth)/+layout.svelte` — corner-placed `LocaleToggle`.
- `healthcabinet/frontend/src/app.css` — `.hc-locale-toggle*`, `.hc-auth-locale-corner`, `.hc-landing-locale` styles.

**Modified — routes**

- `healthcabinet/frontend/src/routes/+page.svelte` — landing hero, topbar, trust badges, preview table, deleted-account banner, head metadata all driven by `t(locale).landing`.
- `healthcabinet/frontend/src/routes/(auth)/login/+page.svelte` — labels, placeholders, head metadata, trust footer, link prompts, mapped 401/403/generic errors.
- `healthcabinet/frontend/src/routes/(auth)/register/+page.svelte` — labels, consent copy, password-toggle aria labels, mapped 409 / local validation errors, trust badges.
- `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte` — loading/error/empty/filter/CTA/recommendations/status-bar with locale-aware dates; dashboard sentinel `'Ready'` passed unchanged and translated in `AppShell`.
- `healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` — title, table headers, status badges, empty state, load-error, view-aria.
- `healthcabinet/frontend/src/routes/(app)/documents/upload/+page.svelte` — all section titles, subtitles, success/partial/failure banners, cancel/close actions, session-expired and stream-lost messages.

**Modified — components**

- `healthcabinet/frontend/src/lib/components/health/AIClinicalNote.svelte` — header, empty states, loading aria, generating/unable copy, reasoning toggle, reasoning table, status labels, disclaimer.
- `healthcabinet/frontend/src/lib/components/health/AIChatWindow.svelte` — title, min/max/restore aria, messages aria, system greeting, sender labels, editor aria+placeholder, send/sending, hints, errors, disclaimer, toolbar tooltips, `formatTime(..., locale)` for timestamps. Story 15.5 scroll logic untouched.
- `healthcabinet/frontend/src/lib/components/health/DocumentUploadZone.svelte` — aria single/multi, drag copy, browse button, max-size, uploading/complete/retry states, validation errors.
- `healthcabinet/frontend/src/lib/components/health/ProcessingPipeline.svelte` — stage labels (`$derived` so they retranslate on switch), status announcements, stream-lost / session-expired copy, per-stage status chips.
- `healthcabinet/frontend/src/lib/components/health/PartialExtractionCard.svelte` — partial/failed headings + desc, photo tips, action buttons, saving state.
- `healthcabinet/frontend/src/lib/components/health/UploadQueuePanel.svelte` — queue aria, header, count labels (complete/partial/failed/pending), active aria + "Currently processing" + "Uploading".
- `healthcabinet/frontend/src/lib/components/health/UploadBatchSummary.svelte` — batch header, count labels, successful/failed section headers, entry status chips, view-result link, upload-another button.
- `healthcabinet/frontend/src/lib/components/health/UploadQueueEntryRow.svelte` — status labels (`$derived`), view-result link, retry-this-file button.

**Modified — shared UI**

- `healthcabinet/frontend/src/lib/components/ui/toast/Toast.svelte` — dismiss aria localized via `t(locale).toast.dismiss`.
- `healthcabinet/frontend/src/lib/components/ui/confirm-dialog/confirm-dialog.svelte` — `cancelLabel` and `loadingLabel` now default to `t(locale).confirmDialog.{cancel,working}` when callers don't override; explicit callers still win.

**Modified — pure helpers (locale-aware via optional args)**

- `healthcabinet/frontend/src/lib/upload-queue.ts` — `validateFilesForQueue(files, messages?)` accepts a `ValidationMessages` bundle; `applyTerminalStatus(..., errorMessage?, defaultFailureMessage?)` accepts a locale-aware fallback; `processNextInQueue` options accept `uploadFailedMessage`. Default English strings retained for callers that don't pass locale bundles, keeping the helper importable outside component context per the Story 15.6 guardrail.

**Modified — sprint-status and story file**

- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 15-6 status `ready-for-dev → in-progress → review`; `last_updated` bumped.
- `_bmad-output/implementation-artifacts/15-6-core-en-ua-localization.md` — all 6 task groups + subtasks checked, Dev Agent Record populated, Change Log entry appended, Status set to `review`.

## Change Log

| Date       | Change                                                                                                                                          | Author |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| 2026-04-22 | Initial story created and moved to ready-for-dev.                                                                                               | SM     |
| 2026-04-22 | Implemented core EN/UA localization: locale store + toggle + translations + locale-aware formatting across enumerated surfaces; +29 tests, 751/751 green. | Dev    |
| 2026-04-22 | Code review Round 2: applied 25 patches — docs-detail surface localization (4 files), state-freeze → key-derived refactors for error messages / chat timestamps / upload queue, Ukrainian 3-form plurals via new `plural.ts`, status-bar sentinel revert, ProcessingPipeline stage retranslation on locale flip, test coverage additions (plural, status-bar reset, dashboard error retranslation, upload-queue overloads). 4 deferred as pre-existing. 1 dismissed (AC 5 backend passthrough). 764/764 green. | Dev    |
| 2026-04-21 | Code review batch-apply: fixed locale store SSR timing, Intl guard, status bar default, and upload-queue locale wiring. | QA    |
