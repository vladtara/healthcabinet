# Deferred Work

## Deferred from: spec-16-1 code review (2026-04-24)

- **Ukrainian safety validation gap** — The AI safety pipeline (`healthcabinet/backend/app/ai/safety.py`) uses English-only regex patterns (`validate_no_diagnostic`). Now that AI endpoints are instructed to respond in Ukrainian, Ukrainian diagnostic phrases will not be caught by the current patterns. Requires a focused story to add Ukrainian forbidden patterns OR a pre-safety normalization step (translate→check→respond). Spec-16-1 constraint "Never: change the safety forbidden-pattern list" was intentional to keep scope narrow; this is the follow-up. Medium urgency — the LLM's own instructions still discourage diagnoses; the regex is defense-in-depth.

## Deferred from: scope split at story-15-7 intake (2026-04-22)

- **AI-generated content localization (insights, interpretations, chat replies, patterns) in UA** — Story 15.6 AC 5 and 15.7 both keep backend-owned AI body text untranslated. User requested ("AI also generate insights and notes in UA" — 2026-04-22). Requires: (a) threading `locale` from frontend to `/api/v1/ai/documents/{id}/interpretation`, `/api/v1/ai/chat`, `/api/v1/ai/patterns`, `/api/v1/ai/dashboard/interpretation`, `/api/v1/ai/dashboard/chat`; (b) adding an output-language directive to the five prompt templates in `healthcabinet/backend/app/ai/service.py` (`INTERPRETATION_PROMPT_TEMPLATE`, `_FOLLOW_UP_PROMPT_TEMPLATE`, `_PATTERN_DETECTION_PROMPT_TEMPLATE`, `_DASHBOARD_INTERPRETATION_PROMPT_TEMPLATE`, `_PATTERN_RECOMMENDATION` sentence); (c) product decision on storage policy for `AiInterpretation.interpretation` generated under a non-EN locale — regenerate on locale-flip? store per-language? accept stale-language artefacts for documents processed before the switch?; (d) updating `_DISCLAIMER` and `_FOLLOW_UP_SCOPE_FALLBACK` / `_FOLLOW_UP_UNAVAILABLE_DETAIL` / `_FOLLOW_UP_STREAM_INTERRUPTED_FALLBACK` / `_PATTERN_RECOMMENDATION` to be locale-aware. Covers user items #5 (AI Clinical Note body) and #6 (AI-generates-in-UA).

## Deferred from: code review of story-6.3 (2026-04-18)

- **Settings page policy-version link is not URL-encoded** — `href="/privacy?version={log.privacy_policy_version}"` in `settings/+page.svelte:627` uses default Svelte interpolation. If a stored version contains `&`, `#`, space, or Unicode, the link breaks. Pre-existing Story 12-2 code, outside 6-3 "do NOT modify" scope; wrap in `encodeURIComponent(...)` in a follow-up. [`healthcabinet/frontend/src/routes/(app)/settings/+page.svelte:627`]
- **Backend does not validate `privacy_policy_version` against an allowlist** — a client can register with any string, so a malicious caller can claim consent to a non-existent version. Add a Pydantic `Literal[...]` or regex validator on `RegisterRequest.privacy_policy_version`. [`healthcabinet/backend/app/auth/schemas.py`]
- **No Playwright e2e for anonymous GET `/privacy?version=1.0`** — unit tests use component-isolated rendering which cannot validate `+layout.server.ts` redirects. Add a Playwright test that hits the dev server unauthenticated and asserts 200 + renders heading. [`healthcabinet/frontend/tests/` (Playwright)]
- **Expand XSS boundary tests for privacy page** — empty `?version=`, double-URL-encoded payloads, Unicode homoglyphs, exactly-20-character positive case, multi-value `?version=a&version=b`. Hardening. [`healthcabinet/frontend/src/routes/(marketing)/privacy/page.test.ts`]
- **`RegisterRequest.privacy_policy_version` has no whitespace guard** — trailing newline / leading space in a stored version breaks link round-trip (falls back to "current"). Add `.strip()` validator. [`healthcabinet/backend/app/auth/schemas.py`]
- **Axe audit runs against container fragment — `<svelte:head><title>` never validated** — document-scope axe run (or Playwright) would catch title/landmark regressions. [`healthcabinet/frontend/src/routes/(marketing)/privacy/page.test.ts:+72-79`]
- **AC3 regression test doesn't prove transactional atomicity** — a refactor that splits `create_user` and `create_consent_log` into two commits would pass. Inject a failure between the two writes to verify rollback. [`healthcabinet/backend/tests/users/test_router.py` registration integration test]
- **Task 1.3 mutation check (commenting out `create_consent_log`) was not documented** — next story should capture the mutation-check result as a Debug Log entry. Process gap. [`6-3-consent-history-view.md` Dev Agent Record]
- **Add `mailto:` link assertion to privacy page test** — `support@healthcabinet.local` would silently survive a typo rename today. [`healthcabinet/frontend/src/routes/(marketing)/privacy/page.test.ts`]
- **Repo-wide `npm run lint` prettier/svelte-plugin toolchain crash** (`getVisitorKeys is not a function`) across ~40 `.svelte` files. Pre-existing plugin-version mismatch; a toolchain-repair pass is needed separately. [`healthcabinet/frontend/package.json` — likely `prettier` / `prettier-plugin-svelte` versions]
- **Axe color-contrast validation for `.hc-privacy-*`** — skipped under jsdom (known canvas-getContext limitation). Must happen in Playwright visual tests. [`healthcabinet/frontend/src/routes/(marketing)/privacy/page.test.ts`]
- **Desktop manual smoke test at 1024 / 1440 / 2560 px deferred from 6-3 Task 6.4** — Dev Agent Record explicitly deferred to code review, but the box was checked. Follow-up: run the visual verification + capture screenshot at 1440 px. [Story 6-3 Task 6.4]
- **Centralise test password constant (`VALID_TEST_PASSWORD`)** — `"securepassword"` hardcoded in multiple tests including new registration test; a future password-strength validator could silently reject these. [`healthcabinet/backend/tests/users/test_router.py:+284` and other fixtures]

## Deferred from: story-6.3 implementation (2026-04-18)

- **Register-page Privacy Policy link is dead** — `src/routes/(auth)/register/+page.svelte:200` links to `/privacy-policy` which is not a registered route. Story 6-3 shipped `/privacy?version={v}` as a stub for the consent-history link; this separate path for the register-page link was not in 6-3 scope. Either retarget the register link to `/privacy?version=current`, or let product define a dedicated onboarding policy landing page. Pre-existing since Story 1-2 / 8-3. [`healthcabinet/frontend/src/routes/(auth)/register/+page.svelte:200`]
- **Replace `/privacy` placeholder body with legal-team-authored policy content** — Story 6-3 shipped `/privacy` as an MVP stub that renders the heading and version but not the full legal policy text. The `privacy_policy_version` currently accepted at registration is `"1.0"` (see `app/auth/service.py:118-165`). Once legal sign-off is complete, replace the placeholder paragraphs with the authored content and consider per-version rendering (e.g. show v1.0 text vs v2.0 text based on `?version=`). [`healthcabinet/frontend/src/routes/(marketing)/privacy/+page.svelte`]

## Deferred from: code review of story-6.2 (2026-04-18)

- **Orphan audit rows with all three subject FKs NULL escape redaction** — `user_id IS NULL AND document_id IS NULL AND health_value_id IS NULL` rows are not matched by either branch of the subject-redaction UPDATE; any legacy rows in that shape carry unredacted `original_value` / `new_value` forever. Requires one-time cleanup migration outside 6-2 scope. [`healthcabinet/backend/app/users/service.py:129-135`]
- **Self-correction audit row semantics undefined (admin_id == user_id == subject)** — When the deleted user is both subject and actor on the same row, UPDATE #1 redacts content and UPDATE #2 nulls `admin_id`, yielding a fully orphaned row with no accountability link. No test; likely acceptable but needs explicit product decision. [`healthcabinet/backend/app/users/service.py:141-154`]
- **No DB-level enforcement of "redact-first" invariant** — Any non-service `DELETE FROM users` (admin panel direct SQL, DB restore) triggers `audit_logs.user_id` CASCADE and erases the regulatory trail. Consider a trigger or check constraint. [`healthcabinet/backend/app/admin/models.py`]
- **Concurrent admin-correction + self-delete deadlock risk** — Rank-inversion between `audit_logs` row locks (deletion path) and `health_values` FOR UPDATE + `audit_logs` INSERT (correction path) can deadlock. No retry in the service function. Rare but real. [`healthcabinet/backend/app/users/service.py:141-154`]
- **Concurrent double-click self-delete enqueues two reconciliation jobs** — Both requests succeed, both enqueue same prefix; second ARQ job is a no-op on empty prefix but wastes queue. Second 204 is semantically misleading. [`healthcabinet/backend/app/users/service.py:102-176`]
- **`[REDACTED]` marker collides with legitimate user-entered values** — No tombstone column distinguishes marker from user input; downstream redaction reporting false-positive risk. [`healthcabinet/backend/app/users/service.py:27`]
- **Refresh cookie not cleared in the 204 deletion response** — Server correctly 401s on refresh attempts, but browser keeps cookie until access-token expiry (15 min) → stale "logged in" UX in other tabs. No `response.delete_cookie("refresh_token")`. [`healthcabinet/backend/app/users/router.py:98-107`]
- **No scale test for deletion of users with thousands of audit rows** — UPDATE acquires row locks on every matched row; power-admin deletion could stall. [`healthcabinet/backend/tests/users/test_router.py`]
- **No regression guards for `ai_memories` / `subscriptions` / `flag_reviewed_by_admin_id` FK-cascade semantics** — Docstring claims CASCADE handles these; no test asserts counts post-deletion. Alembic drift could silently break. [`healthcabinet/backend/tests/users/test_router.py`]
- **No safety check preventing deletion of the last admin** — `ensure_bootstrap_admin` runs only on lifespan, not per-request; system could become adminless until restart. [`healthcabinet/backend/app/users/service.py:102-176`]
- **No explicit `async with db.begin()` transaction boundary** — Atomicity relies on implicit session semantics + caller not committing mid-function; no code-level guard. [`healthcabinet/backend/app/users/service.py:102-176`]
- **AC3 rollback test asserts `status==500` + truthy `x-request-id` only** — Does not assert full RFC 7807 shape (`type`, `title`, `instance`); global handler emits all three, but regression gate thin. [`healthcabinet/backend/tests/users/test_router.py:600-604`]

## Deferred from: code review of story-14.5 (2026-04-17)

- **`monkeypatch.setattr(settings, "ENVIRONMENT", "production")` mutates module-level Pydantic singleton** — Works correctly in single-threaded pytest runs. Latent risk if concurrent async workers (e.g. pytest-xdist) are introduced — any test reading `settings.ENVIRONMENT` concurrently would observe `"production"`. Use `monkeypatch.setattr("app.main.settings", ...)` with a mock object for proper isolation. [`healthcabinet/backend/tests/test_main.py:64`]
- **No close button test for loading/error states** — `DocumentDetailPanel.svelte` now always renders the close button, but no test verifies it is present during `isLoading` or `isError` states, nor that clicking it calls `onClose` in those states. Add a `DocumentDetailPanel.test.ts` test case for the always-visible close button.
- **`detailQuery.data` can become undefined during background TanStack Query refetch while delete dialog is open** — TanStack Query may set `data` to `undefined` when transitioning to loading during a background refetch. If this happens while `showDeleteConfirm = true`, the dialog unmounts without user interaction. Consider capturing a snapshot of `detailQuery.data` when the dialog opens. Pre-existing architectural pattern. [`healthcabinet/frontend/src/lib/components/health/DocumentDetailPanel.svelte`]

## Re-deferred from: story-14.5 with inventory (2026-04-17)

- **Tailwind structural remnants — per-file inventory** — 9 component files still using Tailwind structural classes. Migration is Tier 2 (Epic 13 retro; during/after Epic 6). Full inventory in `14-5-desktop-qa-and-tailwind-remnant-sweep.md` Dev Notes. Summary below:
  - `AiInterpretationCard.svelte` — 0 `.hc-*` | ~20 TW class groups | **High effort**: full card layout, reasoning table, interactive button states (hover, focus-visible)
  - `AiFollowUpChat.svelte` — 0 `.hc-*` | ~10 TW class groups | **High effort**: also imports shadcn `Textarea` + `Button` from `$lib/components/ui/` — must replace with 98.css equivalents
  - `PatternCard.svelte` — 0 `.hc-*` | ~5 TW class groups | Low effort: structurally similar to AiInterpretationCard; can share CSS
  - `AIClinicalNote.svelte` — 7 `.hc-ai-note-*` | ~7 TW class groups | Low effort: skeleton loaders + error text only
  - `BiomarkerTrendChart.svelte` — 0 `.hc-*` | ~12 TW class groups | **High effort**: SVG chart with Tailwind on SVG elements (`fill-muted-foreground`, `text-[10px]`); disabled-state layout
  - `BiomarkerTrendSection.svelte` — 5 `.hc-trend-*` | ~4 TW class groups | Low effort: skeleton loaders + error text only
  - `HealthValueBadge.svelte` — 0 `.hc-*` | ~5 TW class groups | Medium: entire badge is Tailwind; dynamic health-status color classes map to design tokens
  - `PatternAlertSection.svelte` — 7 `.hc-*` | ~5 TW class groups | Low effort: skeleton loaders + error text only
  - `dashboard/+page.svelte` — 12 `.hc-*` | ~5 TW class groups | Low effort: skeleton + error text; also imports `Button` from shadcn — must replace

## Deferred from: code review of story-13.3 (2026-04-16)

- **Dialog closes on mutation failure — error shown outside dialog** — `confirmStatusChange()` sets `showConfirmDialog = false` in `finally` block regardless of success/failure. On error, user must reopen dialog to retry. Pre-existing behavior preserved per AC 1; consider keeping dialog open on failure in a future polish pass. [`(admin)/admin/users/[user_id]/+page.svelte:34-46`]
- **"Mark Reviewed" button has no double-click guard** — `handleReviewFlag()` doesn't gate on a loading state; rapid clicks fire concurrent `markFlagReviewed()` API calls. Pre-existing from Story 5.3; explicitly deferred to Story 13-5 per epic-12 retro Action 6 (async destructive-action double-click guard). [`(admin)/admin/users/+page.svelte:43-52`]
- **ConfirmDialog `previouslyFocused.focus()` on detached element** — Pre-existing in the ConfirmDialog primitive since Story 12-4 extraction. Also noted in epic-12 retro deferred items. Scheduled for 13-5 hardening. [`lib/components/ui/confirm-dialog/confirm-dialog.svelte:119-125`]

## Deferred from: spec-ui-alignment-fixes-epic12 review (2026-04-05)

- **Auth layout logic duplicated across route groups** — `(app)/+layout.ts` and `(onboarding)/+layout.ts` contain identical silent-refresh auth logic. Extract to shared utility.
- **Confirm password field has no blur validation** — Pre-existing: mismatch only caught on form submit, no inline feedback when user tabs away.
- **`getProfile()` rejection unhandled in settings page** — Pre-existing: if API call fails on mount, form loads empty with no error shown, save button shows "Saved" with no indication of failure.

## Deferred from: code review of story-11.2 (2026-04-05)

- **HealthValueRow and PartialExtractionCard use Tailwind structural classes** — Both components are entirely Tailwind-based but are rendered inside 98.css panels. Restyling should happen in a dedicated component migration story. [HealthValueRow.svelte, PartialExtractionCard.svelte]

## Deferred from: code review of 6-1-full-data-export (2026-04-02)

- **GDPR audit logging not implemented** — export endpoint has no logging of who requested an export and when. GDPR compliance would benefit from an audit trail for data access events. Broader audit logging infrastructure decision needed; not scoped to this story. [backend/app/users/router.py]
- **No rate limiting on export endpoint** — any authenticated user can repeatedly call `POST /me/export`, building large in-memory ZIPs. Consistent with pre-existing gap across the codebase; apply rate limiting in a security hardening pass when warranted. [backend/app/users/router.py]

- **Suspension does not invalidate existing access tokens until natural expiry (15 min)** — `get_current_user` checks `account_status` per-request, but the JWT itself carries no embedded status and remains valid until its natural 15-min expiry. Per spec Dev Notes: "do not introduce Redis token blocklists." [backend/app/auth/service.py]
- **Suspended users re-registering see "email already registered"** — `create_user` has a `UNIQUE` constraint on email; suspended users hitting that endpoint get `DuplicateEmailError` → "Email already registered" message. Pre-existing behavior, out of scope for Story 5.3.
- **`last_login_at` not updated on token refresh** — `login_user` sets it on credential login only; `refresh_access_token` does not. Per spec: "updated only on successful credential login, not on silent refresh." [backend/app/auth/service.py]

## Deferred from: deep code review of story-5.3 (2026-04-02)

- **No pagination on admin user list or flagged reports** — `list_admin_users` and `get_flagged_reports` return all rows with no LIMIT/OFFSET. Admin-internal endpoints at MVP scale; add pagination when user count justifies it. [backend/app/admin/repository.py]
- **Dialog focus trapping not implemented** — Confirmation dialog in user detail page declares `aria-modal="true"` but does not trap keyboard focus. Pre-existing modal pattern used across admin pages. [frontend/admin/users/[user_id]/+page.svelte]
- **Rate limit masks 403 for suspended users** — `check_login_rate_limit` runs before login; a suspended user hitting the limit sees 429 instead of 403. Pre-existing auth flow behavior. [backend/app/auth/router.py]
- **403 from `get_current_user` doesn't auto-redirect** — Frontend `apiFetch` only auto-redirects on 401, not 403. Suspended user with open app sees generic error. Broader frontend auth concern. [frontend/src/lib/api/client.svelte.ts]

## Deferred from: code review of story-5.0 (2026-03-31)

- **`_iter_text_fragments` silently drops unknown content types** — New LangChain content block types (e.g., `thinking`, `tool_result`) would be silently lost with no logging. Pre-existing limitation (old code only checked `content[0].text`). [`app/ai/llm_client.py:33-55`]
- **Mid-stream exception after HTTP 200 — truncated response** — If the LLM errors mid-stream after the HTTP response has started, the client receives a truncated body with no error framing. Pre-existing behavior not introduced by this diff. [`app/ai/service.py:337-361`]
- ~~Integration test lacks `@pytest.mark.integration` marker~~ — FIXED in deep review pass (2026-03-31)

## Deferred from: deep code review of story-5.0 (2026-03-31)

- **Module-level cache has no eviction** — `_chat_model_cache` dict in `llm_client.py` has no TTL/max-size. Practically limited to ~2 entries (call/stream max_tokens), but stale entries persist if model name changes at runtime. Very low risk. [`app/ai/llm_client.py:20`]
- **`ModelPermanentError` propagates from `generate_interpretation`** — `call_model_text` raises `ModelPermanentError` for non-retriable provider errors (e.g., bad request, auth failure); `generate_interpretation` only catches `ModelTemporaryUnavailableError`, so permanent errors propagate to the caller as an unhandled exception. Pre-existing behavior pattern; affects `app/ai/service.py:generate_interpretation`. [`app/ai/service.py:104`]
- **`_extract_text` ValueError propagates from `generate_interpretation`** — Empty model response raises ValueError before safety pipeline runs. Pre-existing behavior. [`app/ai/service.py:104`]


## Deferred from: deep code review of story-5.0 (2026-04-01)

- **`surface_uncertainty` return value discarded in streaming path** — `await surface_uncertainty(next_cumulative)` result is ignored in `_validate_and_encode`. Currently a no-op so no bug exists, but when `surface_uncertainty` is implemented to mutate text, streaming and non-streaming paths will diverge silently. [`app/ai/service.py:388`]
- **Safety check cannot retroactively block already-streamed partial forbidden content** — Forbidden text split across two LLM deltas will have its first part sent before the cumulative check fires. Pre-existing architectural constraint of streaming safety validation. [`app/ai/service.py:381-389`]
- **`asyncio.Lock()` at module import — held-lock test teardown risk** — If a test is cancelled while holding `_cache_lock`, subsequent tests deadlock. `llm_client_module` fixture mitigates via reload-on-teardown. Python 3.10+ safe in production. [`app/ai/llm_client.py:21`]
- **TOCTOU: API key read twice between cache hash and `_build_chat_model`** — Key rotation between hash computation and model build could cache a model under the wrong key. Astronomically unlikely in practice. [`app/ai/llm_client.py:56`]
- **SHA-256 truncation to 16 hex chars in cache key** — 64-bit prefix sufficient for single-key use. Risk increases only if multi-tenant/per-user key scenarios are added. [`app/ai/llm_client.py:51-52`]
- **Integration test swallows provider errors with `pytest.skip()`** — Misconfigured-but-non-empty API key raises `ModelPermanentError` which the integration test catches and skips (updated in round-2 review from `anthropic.AuthenticationError`). Silently skips instead of failing on misconfiguration. Minor test quality issue. [`tests/ai/test_llm_client.py:243`]

## Deferred from: code review of 4-4-cross-upload-pattern-detection (Round 2, 2026-03-30)

- **Prompt injection via unescaped health document content** — interpretations injected verbatim into Claude pattern prompt; pre-existing design shared with follow-up Q&A. [`app/ai/service.py:_build_pattern_context`]
- **Rate limit has no per-IP secondary cap for `/patterns`** — `check_ai_patterns_rate_limit` is per-user only (10/min); consistent with `/ai/chat` design. [`app/core/rate_limit.py`]
- **`updated_at` on AiMemory is interpretation write time, not lab draw date** — pattern cards show AI generation dates, not actual lab dates; no `document.created_at` available. Pre-existing design. [`app/ai/repository.py:130`]
- **`list_user_ai_context` authorization relies on caller passing correct user_id** — repository-layer trust boundary; pre-existing from Story 4.1. [`app/ai/repository.py`]
- **`updated_at=None` rows sort to epoch timestamp 0** — non-deterministic ordering when multiple rows lack `updated_at`; low impact in prod. [`app/ai/repository.py`]
- **`AiInterpretationResponse.generated_at` non-optional but sourced from server_default column** — if `db.refresh()` is skipped in a non-standard path, Pydantic 422 at serialization. Pre-existing from Story 4.1. [`app/ai/router.py`]

## Deferred from: code review of 4-4-cross-upload-pattern-detection (2026-03-29)

- **`stream_follow_up_answer` disclaimer appended outside safety validation window** — `_DISCLAIMER` is appended after the stream ends, outside `validate_no_diagnostic`. Pre-existing in `service.py`. [`app/ai/service.py:stream_follow_up_answer`]
- **`apiStream` `isRedirectingToLogin` flag not reset on successful retry after 401** — unlike `apiFetch`, the flag is not cleared when `apiStream` successfully retries after token refresh. Pre-existing in `client.svelte.ts`. [`frontend/src/lib/api/client.svelte.ts:apiStream`]
- **`updated_at` date strips timezone info** — `row.updated_at.date().isoformat()` loses UTC offset; documents crossing UTC midnight get the wrong calendar date in the Claude pattern prompt. Pre-existing design. [`app/ai/repository.py:list_user_ai_context`]
- **`list_user_ai_context` Python `None` guard on `interpretation_encrypted` redundant** — SQL query already filters `is_not(None)`; the Python guard at line 109 can never fire under normal DB operation, producing misleading warning logs. [`app/ai/repository.py:109`]

## Deferred from: code review of 4-2-ai-reasoning-trail (2026-03-28)

- **`upsert_ai_interpretation` SELECT-then-INSERT TOCTOU race** — two concurrent workers for the same (user_id, document_id) can both find no row and both INSERT, hitting the UNIQUE constraint as an unhandled IntegrityError 500. Fix with `INSERT ... ON CONFLICT DO UPDATE` dialect-level upsert.
- **Safety rejection permanently hides invalidated row** — if `invalidate_interpretation` is called before regeneration and Claude's output is rejected by the safety pipeline, `safety_validated` stays `False` with no recovery path (no retry, no fallback). Consider surfacing a "reprocessing failed" document state.
- **`memory.updated_at` for `generated_at` may be None on first insert** — router uses `memory.updated_at` (was `created_at`). If the column has only `onupdate` and no `server_default`, new rows have `updated_at=None`, causing Pydantic validation failure. Add fallback: `memory.updated_at or memory.created_at`.
- **Anthropic client initialised at module import** — `_client = anthropic.AsyncAnthropic(...)` runs at import time; requires `ANTHROPIC_API_KEY` in every environment that imports the module. Breaks test isolation if the key is absent. Consider restoring lazy init or using a test-mode sentinel.
- **Outer `aria-live="polite" aria-atomic="true"` wraps reasoning panel** — when reasoning is expanded, DOM mutations inside the atomic outer region could cause some screen readers to re-announce the entire interpretation card. Narrow the outer live region to wrap only the interpretation text `<div>`, not the reasoning section.

## Deferred from approved sprint change proposal (2026-03-25)

## Deferred from: code review of 4-1-plain-language-ai-interpretation-per-upload (2026-03-27)

- **`values_committed` flag not set on ambiguous commit** — if `db.commit()` raises after the server-side commit succeeds (network disconnect), Phase 1 values exist in DB but `values_committed` stays `False`. First-time upload exception falls back to `failed` instead of `partial`. Inherent distributed-commit limitation; unsolvable without 2PC.
- **Concurrent reprocessing race on `upsert_ai_interpretation`** — two workers on same document can interleave: Worker A invalidates (safety_validated=False), Worker B upserts (safety_validated=True), Worker A commits invalidation last. Result: valid interpretation hidden. Pre-existing select-then-mutate pattern; ARQ handles dedup at queue level for normal flows.
- **`state.user_id=None` silent no-op in `invalidate_interpretation`** — SQL `WHERE user_id = NULL` matches no rows; function returns without error. Affects all repository functions. Fix at data-integrity layer when user_id nullability is tightened.
- **Test cross-session visibility not exercised** — `test_invalidate_interpretation_hides_existing` uses same session; doesn't verify another session sees the committed `safety_validated=False`. Function flushes internally so test is not wrong — this is an enhancement.
- **Shared mock session across phases in `test_phase3_failure_after_value_commit_marks_partial`** — single mock instance shared by all `AsyncSession()` calls; fragile if worker's session-open count changes. Improve by using distinct mock instances per session.

## Deferred from: code review of 4-1-plain-language-ai-interpretation-per-upload (2026-03-26)

- **No audit record for safety-rejected AI output** — `service.py` logs a warning but discards raw rejected text. No audit trail for compliance or debugging. Deferred: design decision; spec only requires non-fatal failure.
- **Images hardcoded as `image/jpeg` in `call_claude`** — `claude_client.py` always sets `media_type: "image/jpeg"` regardless of actual format. Not exercised in story 4.1 (no images passed). Fix before enabling image-based lab parsing.
- **`updated_at` no server-level `ON UPDATE` trigger** — migration 008 only sets `server_default`; raw SQL updates won't refresh `updated_at`. Pre-existing ORM pattern; fix if raw SQL access is ever needed.
- **`generate_interpretation` with None reference ranges** — if a health value has no reference range, prompt renders `ref: None–None`. Pre-existing extraction data quality issue; address in a future extraction quality pass.
- **`model_version` hardcoded string** — `service.py` hardcodes `"claude-sonnet-4-6"` rather than reading from Pydantic Settings. Not a bug; extract to config for easier model upgrades.
- **`safety_validated=True` hardcoded in repository** — `create_ai_interpretation` always writes `True`; acceptable since the function is only called after safety passes. Consider passing as parameter for future multi-path safety flows.

## Deferred from: code review of 3-2-health-values-dashboard-with-context-indicators (2026-03-25)

- **Single-bound status always returns `"borderline"`** — `_compute_status()` in `service.py` does not apply severity scaling (borderline/concerning/action_needed) when only one of `ref_low`/`ref_high` is present. Spec-defined behavior for MVP; true one-sided severity scaling is a future enhancement.
- **`counts` omits `unknown` status** — summary stat tiles in `+page.svelte` cover only 4 statuses; biomarkers without reference ranges (status=`unknown`) are not counted. Summary numbers won't sum to total values. Design decision per spec; add unknown tile in a future pass.
- **Duplicate fetch logic in `$effect` and `retry`** — `+page.svelte` has identical `Promise.all` blocks in both `$effect` and `retry()`. Refactor to shared helper in a future cleanup.
- **Exact boundary values (`value == ref_low`, `value == ref_high`) untested** — `_compute_status` uses `>=`/`<=` so boundary behavior is correct, but no test exercises it. Add boundary tests in a future test pass.
- **WCAG 4.5:1 contrast ratio unverified statically** — `HealthValueBadge.svelte` uses design-system color tokens; contrast compliance requires a visual/browser audit rather than a code review.

- **[PLANNING] Billing and Stripe implementation are explicitly deferred from MVP** — no active Epic 3+ implementation should introduce subscription flows, paid-tier gating, upgrade CTAs, or Stripe integration until a later planning pass restores that scope.

## Deferred from: code review of 2-4-document-cabinet-individual-management (2026-03-24)

- **[HIGH] Worker-delete race** — ARQ job may write status/health values to a document deleted mid-processing. No guard on document status before delete. Architectural fix needed (check `arq_job_id`/status before delete, or worker must handle `DocumentNotFoundError` gracefully). [`service.py`]
- **[MEDIUM] `get_document_by_id` fetches full row then Python-checks `user_id`** — pre-existing: SQL query has no `user_id` predicate; authorization is done in Python after the DB round-trip. Should push `user_id` into the SQL `WHERE` clause. [`documents/repository.py:54`]
- **[LOW] Uncaught boto3 misconfiguration exceptions not RFC 7807** — `EndpointResolutionError` / `NoCredentialsError` propagate as unstructured 500s leaking internal boto3 detail. Cross-cutting concern for all S3 operations. [`documents/storage.py`]
- **[LOW] `showDeleteConfirm` state race on rapid sequential document open** — if a user opens a new document during an in-flight delete mutation, `onSuccess` resets `showDeleteConfirm` for the wrong document. Extremely unlikely in practice. [`+page.svelte`]
- **[LOW] `formatDate(undefined)` locale may cause SSR/CSR hydration mismatch** — `toLocaleDateString(undefined, ...)` uses runtime locale; Node.js vs. browser locale divergence causes a visual flicker on initial hydration. [`+page.svelte`]
- **[LOW] `HealthValueItem` lacks document provenance field** — no `source_document_id` in the schema; not needed now but limits future multi-document aggregation views. [`schemas.py`]


## Deferred from: code review of 1-3-user-login-authenticated-session (2026-03-21)

- **[MEDIUM] No CSRF tokens on state-mutating cookie endpoints** — `SameSite=Strict` is primary mitigation; full CSRF tokens are out-of-scope for this story. Revisit if subdomain architecture is introduced. [app/auth/router.py]
- **[HIGH] `register_user` only catches `IntegrityError`** — other DB exceptions from `create_consent_log` (e.g., `DataError`, `OperationalError`) may propagate past the savepoint rollback without explicit outer transaction rollback. Pre-existing story 1-2 code. [app/auth/service.py register_user]
- **[LOW] `request.completed` observability log removed** — new pure ASGI middleware replaced `BaseHTTPMiddleware` but lost per-request status code and response-time logging. Needs reinstatement for incident response and audit logging. [app/core/middleware.py]
- **[LOW] Logout endpoint accepts unauthenticated callers** — accepted design pattern for stateless logout; low risk with `SameSite=Strict`. Could optionally require access token to prove intent. [app/auth/router.py]
- **[LOW] `client.ts` renamed to `client.svelte.ts`** — spec names `client.ts` but Svelte 5 rune syntax requires `.svelte.ts` extension. Future story specs and documentation should reference the correct filename. [frontend/src/lib/api/]
- **[MEDIUM] Multiple browser tabs: inactivity logout in one tab does not clear other tabs' in-memory access tokens** — tokens remain valid for up to 15 minutes. Mitigation: `BroadcastChannel` or `storage` event to notify other tabs. Acknowledged accepted risk. [auth.svelte.ts]

## Deferred from: code review of 1-3-user-login-authenticated-session backend auth core (2026-03-21)

- **[HIGH] No server-side refresh token revocation on logout** — stolen refresh cookie remains usable for 30 days post-logout; no Redis blocklist or DB revocation. Accepted risk for MVP; implement in a future story during reviews. [app/auth/router.py]
- **[MEDIUM] Per-IP rate limit not reset on successful login** — intentional design to prevent bypass via interleaved valid logins; documents that legitimate users on shared NAT can be blocked for up to 60s by an attacker on the same IP. [app/auth/router.py]
- **[MEDIUM] Email lockout via rate limiting** — attacker with a known valid email can consume 10 login attempts in 60s, locking out the legitimate user for that window. Known trade-off with per-email rate limits. [app/core/rate_limit.py]
- **[MEDIUM] No rate limit on `/register`** — registration endpoint has no email or IP throttling, enabling unbounded account creation and email enumeration via timing difference between 409 and 201 paths. Out of scope for story 1.3. [app/auth/router.py]
- **[LOW] No refresh token rotation on `/refresh`** — refresh token hard-expires 30 days from initial issuance; users active for 30+ continuous days will be silently forced to re-login. Not required by spec; common rotation practice for sliding window not implemented. [app/auth/router.py]
- **[LOW] Token error distinction not surfaced** — RFC 6750 §3.1 recommends `error="expired_token"` vs `error="invalid_token"` in `WWW-Authenticate` header; all failures collapse to same 401, forcing frontend to always attempt a refresh. [app/core/security.py / app/auth/dependencies.py]
- **[LOW] No request-scoped user caching in `get_current_user`** — full DB lookup per authenticated request; no `request.state` cache. Relevant at scale for endpoints that make multiple downstream service calls. [app/auth/dependencies.py]
- **[LOW] Double-commit risk in `register_user`** — service calls `db.commit()` explicitly; `get_db` teardown may attempt a second commit on an already-committed session. Safe today (no-op), but breaks single-responsibility. [app/auth/service.py]

## Deferred from: code review of 1-3-user-login-authenticated-session and 1-4-medical-profile-setup (2026-03-21)

- **No +layout.server.ts auth guard for (app)/ routes** — auth protection is client-side only via `$effect` + `goto('/login')`. A server-side redirect in `+layout.server.ts` would prevent protected page rendering before auth check and eliminate the brief flash risk. Out of scope; server-side session management not in Epic 1. [frontend/src/routes/(app)/+layout.svelte]

## Deferred from: code review of 1-3-user-login-authenticated-session (2026-03-21, round 2)

- Rate limit counter increments before credential validation — by design; legitimate users can be locked out after 10 consecutive correct-but-throttled attempts. Acceptable trade-off for now. [backend/app/auth/router.py]
- `/api/docs` and `/api/redoc` exposed in non-production environments — acceptable risk for dev/staging environments. [backend/app/main.py]
- TOCTOU pre-check in `register_user` is redundant — `IntegrityError` catch is the real guard; no functional bug. Pre-existing from story 1-2. [backend/app/auth/service.py]
- `get_current_user` does not differentiate DB error vs missing user — returns 500 on DB outage rather than a retryable error; no retry/backoff path on frontend. [backend/app/auth/dependencies.py]
- Inactivity timeout listener not cleaned on tab close while offline — requires server-side token revocation to fix; architectural limitation. [frontend/src/lib/stores/auth.svelte.ts]
- `authStore.tryRefreshPromise` and module-level `refreshPromise` are independent deduplication layers — non-critical edge case; parallel SvelteKit route loads are deduplicated by `tryRefreshPromise`. [frontend/src/lib/stores/auth.svelte.ts]
- `test_logout_clears_cookie` does not verify revocation of a captured refresh token — no server-side revocation by accepted design. [backend/tests/auth/test_router.py]
- Login form does not clear `password` $state field on error — minor UX; `type="password"` masks display. [frontend/src/routes/(auth)/login/+page.svelte]
- `me()` missing `credentials: 'include'` is harmless until refresh token rotation is added. [frontend/src/lib/api/auth.ts]
- Inactivity timer HMR stale closure risk — dev-only concern, not reproducible in production builds. [frontend/src/lib/stores/auth.svelte.ts]
- Dual auth guard in `+layout.ts` + `+layout.svelte` `$effect` — defensive redundancy, not a bug. [frontend/src/routes/(app)/]
- Rate limit `Retry-After` value duplicated in RFC 7807 `detail` string — value is already in the RFC-compliant header; minor. [backend/app/core/rate_limit.py]

## Deferred from: code review of 2-1-document-upload-minio-storage (2026-03-21)

- **[MEDIUM] `rate_limit_upload` fails open on Redis outage** — deliberate design choice per code comment; consistent with Story 1.3 pattern; free-tier quota disabled during Redis outage. [backend/app/documents/dependencies.py]
- **[LOW] Presigned URL expiry not tracked server-side** — URL is self-expiring via HMAC in query params; adding a `presigned_url_expires_at` DB column is out of scope for this story.
- **[LOW] Touch target coverage on upload zone div for very narrow viewports** — borderline; zone is full-width in all practical layouts; revisit if narrow breakpoints are added.
- **[HIGH] Notify endpoint: no MinIO file-existence check before ARQ enqueue** — deferred to Story 2.2; handle missing-object in the worker when the processing pipeline is implemented. [backend/app/documents/service.py `notify_upload_complete`]
- **[MEDIUM] Rate-limit semantics: counter at request time vs completion time** — AC3 says "uploaded 5 documents" but keeping counter at `upload-url` time is simpler and harder to abuse; accepted trade-off. [backend/app/documents/dependencies.py]
- **[MEDIUM] Retry creates orphaned `pending` document rows** — each mid-transfer failure + retry leaves an unresolvable `pending` row; a background cleanup sweep deferred to a future story. [frontend DocumentUploadZone.svelte / backend documents table]

## Deferred from: code review of 2-1-document-upload-minio-storage (2026-03-22, round 2)

- **Orphaned document row when boto3 raises after DB flush** — if presigned URL generation throws after `create_document()` flushes, the document row persists unreferenceable; same class as retry-orphan accepted risk. [backend/app/documents/service.py `generate_upload_url`]
- **Concurrent `notify_upload_complete` calls can both enqueue** — idempotency guard is sequential-safe only; fixing requires `SELECT FOR UPDATE` or advisory lock; out of scope for this story. [backend/app/documents/service.py `notify_upload_complete`]
- **Lost `arq_job_id` when DB update fails after successful ARQ enqueue** — job runs correctly (uses `document_id`); only the tracking ID is unrecorded; low operational impact. [backend/app/documents/service.py `notify_upload_complete`]
- **`isMobile` initialises to `false`, causing SSR/hydration layout shift** — mobile users briefly see desktop layout; fixing requires SSR media-query hints (out of scope). [frontend/src/lib/components/health/DocumentUploadZone.svelte]

## Deferred from: code review of 2-2-real-time-processing-pipeline-status Round 2 (2026-03-22)

- **[MEDIUM] No rate limiting on SSE endpoint** — SSE streams have no per-user or per-IP cap; rate limiting strategy for streaming endpoints is an Epic concern. [backend/app/processing/router.py]
- **[LOW] Worker opens new DB session per stage boundary** — no full pipeline transaction; design choice for MVP simplicity. Revisit if atomicity becomes a concern in Story 2.3. [backend/app/processing/worker.py]
- **[LOW] `WorkerSettings.queues` processes priority queue without tier auth** — queue access control is Epic 5 (billing) scope; ensure enqueue-side enforces tier checks before this worker processes priority jobs. [backend/app/processing/worker.py]
- **[MEDIUM] Non-atomic Redis SET+PUBLISH** — if SET succeeds but PUBLISH fails, `doc:latest` holds an event never delivered to subscribers; fixing requires MULTI/EXEC; low risk at MVP scale. [backend/app/processing/events.py]
- **[LOW] DB commit failure between stages publishes `upload_started` before abort** — no atomic publish+commit primitive; accepted trade-off. [backend/app/processing/worker.py]
- **[LOW] `doc:latest` TTL expiry causes late-reconnecting client to miss cached progress** — 3600s TTL is generous; at-risk only for very long-running jobs. [backend/app/processing/events.py]
- **[LOW] `get_latest_event` result forwarded without schema validation** — internal Redis key written only by `publish_event`; low poisoning risk for MVP. [backend/app/processing/router.py]

## Deferred from: code review of 2-2-real-time-processing-pipeline-status (2026-03-22)

- **[MEDIUM] `document.partial` never emitted by worker** — only `completed`/`failed` are produced; `partial` reserved for Story 2.3 extraction results when real LangGraph calls replace stubs. [backend/app/processing/worker.py]
- **[MEDIUM] Per-request Redis connection creation, no pooling** — 2 new Redis connections opened per SSE stream; no cap on concurrent connections; performance concern at scale. Revisit when SSE connection volume grows. [backend/app/processing/router.py:event_generator]
- **[LOW] `publish_event`/`get_latest_event` typed as `redis: object` with type: ignore** — mypy blind to incorrect usage; typing debt. Resolve when redis.asyncio typing stubs mature or a Protocol is introduced. [backend/app/processing/events.py]
- **[LOW] `health_values` query key casing unverified** — `['health_values']` invalidation in `handleComplete` silently fails if TanStack Query fetching hooks register a different casing; needs broader codebase search to verify. [frontend/src/routes/(app)/documents/upload/+page.svelte]
- **[LOW] `event_generator` missing return type annotation** — `# type: ignore[return]` suppresses mypy; typing debt for later cleanup. [backend/app/processing/router.py]

## Deferred from: code review of 2-6-value-flagging (2026-03-25)

- **[LOW] No index on is_flagged column for future admin queue queries** — Queue queries will filter `WHERE is_flagged = TRUE` but no index exists on the `health_values` table. Should be added when implementing Story 5-2 (extraction-error-queue-manual-value-correction). [`healthcabinet/backend/app/health_data/models.py:32`]

## Deferred from: code review of 2-6-value-flagging Round 2 (2026-03-25)

- **[LOW] No unflag/undo mechanism** — Story scope only covers flagging, not unflagging. Users who accidentally flag have no recourse. Consider adding an unflag endpoint in a future story if user feedback warrants it.
- **[LOW] No rate limiting on flag endpoint** — The flag endpoint has no per-user or per-IP rate limit. An authenticated user could brute-force enumerate health value UUIDs. Cross-cutting concern for a future security hardening pass. [`healthcabinet/backend/app/health_data/router.py`]
- **[LOW] No DB check constraint for is_flagged/flagged_at invariant** — Application code always sets both together, but a direct DB update could set `is_flagged=true` with `flagged_at=null`. A check constraint (`NOT is_flagged OR flagged_at IS NOT NULL`) would enforce the invariant at the DB level. Defense-in-depth for future stories. [`healthcabinet/backend/alembic/versions/007_health_values_flagging.py`]
- **[LOW] Partial reference range hidden when only one bound is null** — `HealthValueRow.svelte` only shows the reference range when both `reference_range_low` and `reference_range_high` are non-null. If only one bound is present, no range info is displayed. Pre-existing behavior from original inline rendering. [`healthcabinet/frontend/src/lib/components/health/HealthValueRow.svelte:78-81`]

## Deferred from: code review of 2-6-value-flagging (2026-03-25)

- HealthValueDecryptionError not caught in flag endpoint — if `_to_record` raises `HealthValueDecryptionError` during the flag operation, it escapes as unhandled 500. Pre-existing, not introduced by the current change.
- No structured logging on exception catch-and-rewrap in router — the flag endpoint catches and re-raises with no structured log entry. Pre-existing pattern.
- RFC 7807 instance field inconsistency between handler patterns — HTTPException handler uses full URL for `instance`; domain handlers use path only. Pre-existing.

## Deferred from: code review of 3-3-biomarker-trend-visualization (2026-03-26)

- **[LOW] Date timezone ambiguity in chart date parsing** — `new Date("ISO-date")` is parsed as UTC midnight and displayed in local time; users west of UTC may see the previous calendar day for date-only strings. Systemic; fix by using explicit timezone handling across all date formatters. [`BiomarkerTrendChart.svelte:29-37`]
- **[LOW] X-axis label overlap for 6–9 data points** — the `i % Math.floor(N/3) === 0` label condition can produce adjacent labels at indices N-2 and N-1 that visually overlap at shorter date strings. [`BiomarkerTrendChart.svelte:179`]
- **[LOW] Backend test ISO string comparison is lexicographic** — `measured_at` ordering test compares ISO strings lexicographically; works correctly for UTC zero-padded timestamps but would give wrong result silently if the serializer emits non-UTC offsets. [`test_router.py:804`]
- **[LOW] `hasValues` always `true` inside `uniqueBiomarkers` loop** — the `hasValues={values.length > 0}` prop passed to `BiomarkerTrendSection` is always true because the loop only renders when `uniqueBiomarkers.length > 0` (which requires `values.length > 0`). No functional impact; code smell. [`+page.svelte:184`]
- **[LOW] `make_document(status="completed")` fixture contract** — test passes `status="completed"` kwarg without confirming the fixture sets this field on the DB model; confirm fixture contract if adding similar backend tests. [`test_router.py`]

## Deferred from: code review of 4-2-ai-reasoning-trail (2026-03-27)

- **[LOW] `upsert_ai_interpretation(reasoning_json=None)` overwrites previously-stored reasoning** — update branch sets `context_json_encrypted = None`, erasing prior reasoning. Safe today (only caller always passes reasoning), but fragile if callers diverge. [`app/ai/repository.py`]
- **[LOW] Bare `except Exception` degrades silently without re-raise or counter** — both `ai.reasoning_decrypt_failed` (repository.py) and `ai.reasoning_schema_mismatch` (router.py) log a warning but have no metrics/alerting hook. Intentional per spec graceful-degradation design. Add a Prometheus counter in a future observability pass. [`app/ai/repository.py`, `app/ai/router.py`]
- **[LOW] `json.dumps` permits NaN/Infinity — round-trip `json.loads` would fail** — Python default encoder emits non-standard `NaN`/`Infinity`; `json.loads` later raises `JSONDecodeError`. Mitigate with `json.dumps(..., allow_nan=False)` when hardening data integrity. [`app/ai/repository.py:31`]
- **[LOW] `decrypt_bytes(memory.interpretation_encrypted)` has no exception guard (pre-existing)** — corruption of the interpretation column raises an unhandled exception → 500. Not introduced by 4.2; fix in a future defensive layer pass. [`app/ai/repository.py`]
- **[LOW] `prior_documents_referenced: list[str]` will render raw strings without formatting** — Story 4.4 will populate this field; the rendering code (`join(', ')`) will show raw IDs/dates with no linking or formatting. Story 4.4 owns presentation. [`AiInterpretationCard.svelte`]

## Deferred from: code review of 3-1-profile-based-baseline-test-recommendations (2026-03-25)

- **[LOW] Upload CTA absent during loading/error states** — AC#4 says CTA "prominently shown"; loading/error are transient states so CTA absence is acceptable for MVP. Revisit if UX testing shows users missing the CTA. [`+page.svelte` — loading/error branches]
- **[LOW] Iron & Ferritin sex=None gate includes unknown-sex users** — `sex not in (None, "female")` passes `None`, so users with no profile set receive a female-targeted recommendation. Intentional heuristic; consider explicit "unknown sex" handling in a future heuristics pass. [`service.py:419`]
- **[LOW] Fallback _MIN_RECS has no _MAX_RECS upper-bound guard** — fallback fires only when combined < 3, making overflow theoretically impossible with current data, but the loop has no defensive cap. Fragile if `_GENERAL_PANELS` grows. [`service.py:436–450`]
- **[LOW] No rate limiting on /baseline endpoint** — consistent with current health-data module pattern; Redis rate limiting exists but not applied to this or other health-data routes. Add as part of a security hardening pass. [`router.py:get_dashboard_baseline`]
- **[LOW] API returns no profile-completeness signal** — recommendations are generic when profile is incomplete (age/sex null) but the response gives no indication of this to the consumer. Add a `profile_complete` field in a future story. [`service.py:get_dashboard_baseline`]

## Deferred from: code review of 6-1-full-data-export (2026-04-02)

- **[MEDIUM] Unbounded in-memory ZIP** — No aggregate size cap on document bytes fetched into BytesIO buffer during export. A user with 100+ large documents could exhaust worker memory. Acceptable at MVP scale per spec; add streaming ZIP or size guard before public launch. [`export_service.py:build_export_zip`]
- **[MEDIUM] No rate limiting on export endpoint** — `POST /me/export` performs N S3 downloads, multiple DB queries, decryption, and ZIP compression per call. No per-endpoint rate limiter applied, consistent with other user module routes. Add as part of security hardening. [`users/router.py:export_my_data`]
- **[LOW] Sequential data fetching in export** — Five independent DB queries awaited sequentially in `build_export_zip`. Could use `asyncio.gather()` for parallel execution. Performance optimization only; no correctness impact. [`export_service.py:build_export_zip`]
- **[LOW] Pre-migration orphaned audit logs remain unrecoverable** — `audit_logs.user_id` now preserves attribution for new rows and best-effort backfills existing rows, but any rows that had already lost both foreign keys before the migration cannot be attributed retroactively. Manual data repair would be required if such rows exist. [`alembic/versions/012_audit_logs_user_attribution.py`]

## Deferred from: code review of 7-3-ui-primitive-migration (2026-04-03)

- **Checkbox label adjacency conflict** — 98.css `input[type=checkbox]+label` renders a `::before` pseudo-element that creates a ghost checkbox visual when a `<label>` is placed as an adjacent sibling to `.hc-checkbox`. Pre-existing since Story 7-1.
- **WindowFrame close/minimize/maximize buttons non-functional** — `window-frame.svelte` renders enabled Close, Minimize, and Maximize buttons that do nothing on click. `onClose` is optional and no handlers exist for min/max. Pre-existing since Story 7-2.
- **Admin formatDate null guard missing in list page** — `formatDate(dateStr: string)` in `admin/users/+page.svelte` does not handle null/undefined (unlike the detail page variant). `new Date(null)` would display epoch date.

## Deferred from: code review of 9-3-admin-shell-variant (2026-04-04)

- **No test for handleSignOut click behavior in AdminShell** — Sign out button exists but no test verifies it calls authStore.logout() and navigates to /login. Pre-existing gap carried from AppShell (story 9-1). [AdminShell.test.ts]

## Deferred from: code review of 10-2-active-dashboard-header-patient-summary-bar (2026-04-04)

- Empty recommendations branch can render blank dashboard guidance state when no recommendations are available. Detected in `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte:204-217`; deferred as pre-existing and outside story 10-2 scope.
- **Email text has no overflow/truncation** — Long email addresses in PatientSummaryBar could push the Upload button off-screen. Pre-existing pattern: no component in the project truncates email. Consider adding `overflow: hidden; text-overflow: ellipsis; max-width` to `.hc-summary-email`. [PatientSummaryBar.svelte]
- **`HealthValue.status` includes `unknown` but StatCardGrid and dashboard counts ignore it** — Dashboard `counts` derivation (story 3.2) filters only 4 statuses, silently dropping `unknown` values. StatCardGrid has no "Unknown" card. Pre-existing gap from Epic 3. [+page.svelte:40-45, StatCardGrid.svelte]

## Deferred from: code review of 10-3-biomarker-table-redesign (2026-04-04)

- **`.hc-sort-button` class reused for expand button** — The name cell button reuses `.hc-sort-button` CSS class, causing hover underline on biomarker names that misleadingly suggests a link action. Cosmetic — consider a dedicated `.hc-bio-name-button` class. [BiomarkerTable.svelte:159]
- **`lastUploadDate` uses string comparison** — `+page.svelte` compares date strings lexicographically. Works correctly for ISO 8601 (current API format) but fragile if formats change. Pre-existing pattern. [+page.svelte:72-78]
- **`.hc-sort-button` semantic reuse** — Expand trigger button in table rows has sort-button class. Semantically misleading but functionally harmless. [BiomarkerTable.svelte:159]

## Deferred from: code review of confirm-dialog-extraction (2026-04-15)

- **`previouslyFocused` element may be detached from DOM when restore runs** — In ConfirmDialog's `$effect`, `previouslyFocused.focus()` is called when `open` goes from `true` → `false`. If the opener element was removed from the DOM (common after successful account deletion navigation), `focus()` is a no-op in most browsers but may throw in some JSDOM configs. Matches the pre-existing pattern in `slide-over.svelte:79` — fragile but not a regression. [confirm-dialog.svelte:104-108]
- **Async `onConfirm` double-click race not guarded at component level** — If a user double-clicks the confirm button before the parent sets `loading=true`, the async handler fires twice. Pre-existing from Story 12-4 (originally deferred as "unlikely with disabled guard"). Carried forward into ConfirmDialog. Could be addressed by gating onConfirm at the component level if `loading` is already true. [confirm-dialog.svelte:150, settings/+page.svelte:handleDeleteAccount]

## Deferred from: code review of 13-1-admin-overview-redesign (2026-04-15)

- **Nested `<main>` element creates invalid HTML landmark** — Both AppShell (`AppShell.svelte:93`) and AdminShell (`AdminShell.svelte:85`) wrap their `{@render children()}` slot inside `<main class="hc-app-content" id="main-content">`, but page components (`settings/+page.svelte:349`, `(admin)/admin/+page.svelte:27`, likely others) also use `<main>` as their container. HTML5 spec allows only ONE non-hidden `<main>` per document. Axe tests don't catch this because test wrappers render pages in isolation without the shell. Fix: audit all `(app)/` and `(admin)/` page components and swap inner `<main>` → `<div>` or `<section>`. Belongs in Story 13-5 frontend hardening (a11y audit). [AdminShell.svelte:85, AppShell.svelte:93, multiple page components]
- **Refresh button has no disabled-during-fetch state** — `(admin)/admin/+page.svelte:30-37` `handleRefresh` invalidates the query but the button has no `disabled={metricsQuery.isFetching}` guard. TanStack Query deduplicates concurrent queries so there's no correctness bug, but UX would be better with a disabled state. Parity with pre-13-1 Tailwind version (also had no guard). Belongs in Story 13-5 hardening or a separate polish pass.
- **`role="alert"` banner wraps action button** — `.hc-state-error` banner pattern places `role="alert"` on the outer div containing the "Try again" button, which can cause screen readers to announce the button label as part of the alert content. Project-wide pattern — would need a sweep of all `.hc-state-*` usage to fix. Belongs in Story 13-5 a11y audit.
- **Empty success-state fallback** — Pages gated on `query.data` truthy (e.g., `(admin)/admin/+page.svelte:58`) render empty if the API returns a falsy success response. Theoretical given TypeScript + apiFetch contracts, but defensive `{:else}` fallbacks would close the gap. Not a regression.

## Deferred from: code review of 15-1 and 15-2 (2026-04-19)

### 15-1 (auth bootstrap)

- Test beforeEach resets private singleton state via `as unknown as {...}` cast — test-infra tradeoff; cleaner refactor would expose a `resetForTests()` method or use a factory-based non-singleton.
- Layout tests mock `$lib/stores/auth.svelte` as a plain object rather than a `$state`-backed proxy, so transition reactivity isn't exercised in unit tests. End-state coverage only. Project-wide Svelte-reactivity-in-unit-tests gap.
- `layout.load.test.ts` mocks authStore by minimal shape, tolerating accidental coupling if `load()` starts reading other properties.
- `restoreSession()` identity-after-resolution (fresh promise is returned after prior resolve) is not pinned by test.

### 15-2 (document intelligence)

- Migration 016 lock duration on very large `documents` tables — acceptable for current data size, revisit before production rollout with >1M rows. No batched-UPDATE / non-transactional migration variant today.
- Test fixture isolation risk: confirm-date-year tests commit rows; session fixture relies on `rollback()` for cleanup which may or may not fully clean depending on SQLAlchemy driver semantics. Related to the flaky first-run backend failures already observed on the main-branch test pass.
- Worker retry-failure path does not reset stale `partial_measured_at_text` when values were replaced. Narrow edge case.
- Two concurrent `confirm_date_year` requests for the same document race on the AI memory UNIQUE constraint — narrow window, no data corruption, just logs the loser as `ai_regeneration_failed`.
- Extractor state serialization compatibility (old states missing `partial_measured_at_text` default to None via Pydantic — untested).
- Response-time `DocumentKind` Literal validation of legacy bad DB values — belongs in Story 15.3 admin hardening.

## Deferred from: code review of story-15.3 (2026-04-20)

- **Streaming safety pipeline leaks unsafe chunks before validation fires** — In both `stream_follow_up_answer` (pre-existing Story 4.3) and the new `stream_dashboard_follow_up`, each delta is yielded first and only then does the cumulative buffer get run through `validate_no_diagnostic`. Unsafe text reaches the wire before the validator trips. Fix requires buffering until the validator resolves — a cross-path rewrite. [`healthcabinet/backend/app/ai/service.py` — `stream_follow_up_answer`, `stream_dashboard_follow_up`]
- **Dashboard interpretation + chat tests mock `call_model_text` at the boundary the safety pipeline wraps** — Violates the project-wide "no mocking AI responses" rule inherited from the Story 4.4 incident. Requires the same real-LLM test-gate infra Story 4.4 uses. Add one real-LLM dashboard interpretation + one dashboard chat integration test. [`healthcabinet/backend/tests/ai/test_router.py`]
- **`validate_no_diagnostic` runs O(n²) on cumulative buffer** — Per-chunk safety validation re-scans the entire running buffer. Pre-existing pattern in `stream_follow_up_answer`; now inherited by `stream_dashboard_follow_up`. A 400-word response does ~600 redundant scans. Incremental/windowed validation needed. [`healthcabinet/backend/app/ai/service.py::_validate_and_encode`]
- **`surface_uncertainty` in chat streaming is not wrapped in the safety try/except** — Only `validate_no_diagnostic` catches `SafetyValidationError`; if `surface_uncertainty` ever raises mid-stream, the generator crashes. Pre-existing pattern. [`healthcabinet/backend/app/ai/service.py::_validate_and_encode`]
- **Fixture-isolation risk in `_seed_user_with_kinded_ai_memories`** — Tests flush AiMemory rows under the session-scoped `async_db_session`. Same pattern flagged in Story 15.2 review; needs a SAVEPOINT-based fixture or per-test cleanup. [`healthcabinet/backend/tests/ai/test_router.py`]
- **Upload-SSE `completed` can fire before the per-document `AiMemory` row is persisted** — Currently safe because the processing graph writes AI interpretation inside the same transaction that flips status to `completed`. If processing ever detaches async, the dashboard will 409 until the AI write commits. [`healthcabinet/backend/app/processing/graph.py` + dashboard invalidation sites]
- **`failed` SSE terminal doesn't invalidate the dashboard AI query even when reprocessing invalidated a prior `AiMemory`** — A reprocess that invalidates AI then fails leaves the frontend cache serving a pre-invalidation aggregate. Reupload eventually regenerates. [`healthcabinet/frontend/src/routes/(app)/documents/+page.svelte` SSE terminal handler]
- **`hasAnyDocuments` (baseline `has_uploads`) can disagree with `documentsQuery.data`** — Transient during upload/delete races. Shows filter-empty for a few hundred ms. [`healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte`]
- **`document_kind` admin-mutation scenario can drop AiMemory rows from the dashboard aggregate** — No admin UI for editing `document_kind` today; field is only set during processing. Edge case. [`healthcabinet/backend/app/ai/repository.py` JOIN on document_kind]
- **Dashboard `reasoning: null` field assertion inconsistent across tests** — Only one test asserts the field's presence; a schema drift would slip through. Add a shared `_assert_dashboard_interpretation_shape` helper. [`healthcabinet/backend/tests/ai/test_router.py`]
- **`dashboardFilterStore` localStorage key is not per-user** — Two users on the same device inherit each other's filter preference. Clear on logout. [`healthcabinet/frontend/src/lib/stores/dashboard-filter.svelte.ts`]
- **`listDocuments()` on the dashboard is unpaginated** — Used only for kind classification + latest-date. Revisit at scale. [`healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte`]
- **Frontend `matchesDashboardFilter` duplicates backend classification logic** — Future kind additions require coordinated updates. [`healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte`]
- **`hasAnyDocuments` stays `true` for a user whose only documents are `document_kind=unknown`** — Filter-empty is shown instead of the first-time CTA; by spec-interpretation it's correct, but the user has no clean recovery UX. [`healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte`]
- **Decrypt-mass-failure collapses dashboard interpretation to 409** — A corrupt AiMemory row set returns `[]` from `list_user_ai_context`; endpoint 409s as "no analyses available" instead of surfacing the real decryption failure. [`healthcabinet/backend/app/ai/service.py::generate_dashboard_interpretation`]
- **`AIChatWindow` retains minimized/maximized state across filter changes** — Identity effect resets messages/question but not window state. Cosmetic. [`healthcabinet/frontend/src/lib/components/health/AIChatWindow.svelte`]
- **`writeToStorage` swallows `QuotaExceededError`** — Filter fails to persist with no diagnostic. [`healthcabinet/frontend/src/lib/stores/dashboard-filter.svelte.ts`]

## Deferred from: code review of story-15.6 (2026-04-22)

- **Status-bar `fields` stale on non-dashboard routes** — Only the dashboard `$effect` writes the status-bar fields. Navigate dashboard → documents → toggle locale: AppShell keeps rendering "2 Documents · 5 Biomarkers · Last Import: 04/22/2026" alongside now-Ukrainian navigation chrome. Pre-existing lifecycle gap; the locale implications are a side effect of Story 15-6. [`healthcabinet/frontend/src/lib/components/AppShell.svelte:102-104`, `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte:136-154`]
- **`formatFileSize` uses `.` decimal separator regardless of locale** — uk convention is `,`. Would need `Intl.NumberFormat(toBcp47(locale), { maximumFractionDigits: 1 })`. Pre-existing helper, not modified by 15-6. [`healthcabinet/frontend/src/routes/(app)/documents/+page.svelte:102-106`]
- **`formatDate` / `formatDateTime` have no `timeZone` override** — ISO UTC-midnight dates can flip around midnight for users west of UTC. Same behaviour as prior `toLocaleDateString(undefined, …)`; centralized helper is now the natural place to settle the policy (probably `timeZone: 'UTC'` for day-level labels). [`healthcabinet/frontend/src/lib/i18n/format.ts:21-32`]
- **Svelte 5 test flush convention uses `setTimeout(r, 0)` rather than `await tick()` / `flushSync()`** — macrotask-based flush couples tests to runtime scheduling order; deadlocks under `vi.useFakeTimers`. Repo-wide convention including pre-existing tests (AIChatWindow, dashboard, documents); migration is a cross-cutting sweep, not scoped to 15-6. [`AppShell.test.ts`, `routes/page.test.ts`, `login/page.test.ts`, `register/page.test.ts`]
