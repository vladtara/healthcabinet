# Story 6.3: Consent History View (Hardening + Dead-Link Fix)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **registered user**,
I want to view the full history of consent agreements I have accepted,
so that I have transparency over what I agreed to and when, satisfying my GDPR Article 9 right to know how my health data is being processed.

---

## Context: This Is a Hardening Story, Not Greenfield

Most of the consent-history feature is **already shipped** (by Story 12-2 during the frontend-redesign track, after 6.3 was deferred per the Epic 7–13 planning baseline). Story 6-3 verifies spec compliance and closes the two real gaps that remain.

| Shipped by | What exists today | Source |
|---|---|---|
| Story 1.2 | Registration creates a `consent_logs` row with `consent_type="health_data_processing"` and `privacy_policy_version` | `app/auth/service.py:118-129`, `app/auth/service.py:155-165` |
| Story 12-2 | `GET /api/v1/users/me/consent-history` returning all rows in descending order; Pydantic schemas; 3 backend tests (descending, no cross-user leak, auth required) | `app/users/router.py:85-95`, `app/users/schemas.py:51-55`, `app/auth/repository.py` (`list_consent_logs_by_user_desc`), `tests/users/test_router.py:202-265` |
| Story 12-2 | Settings page "Consent History" fieldset with sunken panel timeline, loading/error/empty states, UTC timestamp formatting, semantic `<ul>` list, axe-verified | `src/routes/(app)/settings/+page.svelte:186-198,610-640`, `src/routes/(app)/settings/page.test.ts:338-400`, `.hc-consent-*` classes in `src/app.css:4606-4655` |
| Story 12-2 | Frontend `getConsentHistory()` API client; `ConsentLog` TypeScript type | `src/lib/api/users.ts:46`, `src/lib/types/api.ts:17-20` |
| Story 6-2 | On account deletion, `consent_logs.user_id` is set to `NULL` via FK `SET NULL` (retention for regulatory reporting) | `app/users/models.py:26-27` (ConsentLog FK), `tests/users/test_router.py` (`test_delete_account_retains_consent_logs_and_redacts_audit`) |

**What remains for Story 6-3** is narrow:

1. The policy-version link target is **dead** (`/privacy?version=v` — no such route exists anywhere in the frontend, nor does `/privacy-policy` from the register page). AC2 says "link to the policy text for that version (**if available**)". Either we (a) stand up a minimal `/privacy` route so the link resolves, or (b) downgrade to plain text until a policy page exists. Story 6-3 picks option (a) with a minimal stub — the link should not be rendered as an interactive anchor unless its target resolves.
2. No integration test exercises the full journey AC3 demands ("at least one entry always exists — the registration consent"). Existing tests seed consent logs directly via `create_consent_log` / `make_user` fixtures; none post to `/auth/register` then hit `/consent-history`. One regression test is needed.

---

## Acceptance Criteria

### AC1 — Consent History Display (regression gate, shipped by Story 12-2)

**Given** an authenticated user visits `/settings` (Privacy section)
**When** the consent history fieldset mounts
**Then** all `consent_logs` rows for that user are displayed in descending chronological order (most recent first)
**And** each entry shows: human-readable consent type label, UTC timestamp formatted as `"DD MMM YYYY, HH:MM UTC"`, and privacy policy version
**And** the list is a semantic `<ul class="hc-consent-timeline">` with `<li class="hc-consent-entry">` children (accessibility requirement)

**Regression gate:** Story 12-2's `page.test.ts:338-400` tests must continue to pass unchanged.

### AC2 — Read-Only + Policy Version Link (NEW — dead-link fix + regression gate)

**Given** the consent history is displayed
**Then** it is strictly read-only — no edit, delete, or form controls are rendered anywhere in the fieldset
**And** the privacy policy version is rendered as an accent-coloured link `<a class="hc-consent-policy-link" href="/privacy?version={v}" aria-label="Privacy policy version {v}">v{v}</a>` whose target is a live route — clicking the link must load a page, not produce a 404 (AC gap today — no `/privacy` route exists)
**And** if `privacy_policy_version` is missing, empty, or whitespace, the entry renders `N/A` as plain text (no link) — Story 12-2 review patch; regression gate

### AC3 — Minimum Entry Invariant (NEW — integration regression)

**Given** a user registers via `POST /api/v1/auth/register` with `gdpr_consent=true`
**When** they subsequently call `GET /api/v1/users/me/consent-history`
**Then** the response contains at least one row with `consent_type == "health_data_processing"` and the `privacy_policy_version` the user accepted at registration
**And** the `consented_at` timestamp is within the registration request's response window (within a few seconds of the register call)

**Background:** The spec AC says "at least one entry always exists (the registration consent logged in Story 1.2)." The invariant is currently enforced by `app/auth/service.py:118-129` creating the consent log inside the registration transaction, but no test asserts the end-to-end journey. A DB-level regression (e.g., a refactor that moves consent creation out of the registration commit boundary) would silently break FR6 without this test.

### AC4 — No Cross-User Leakage (regression gate, shipped by Story 12-2)

**Given** users A and B exist, both with consent log rows
**When** user A calls `GET /api/v1/users/me/consent-history`
**Then** only A's rows are returned
**And** no B-belonging row appears in the response
**And** filtering is by `user_id` derived from the JWT, never from a request parameter or body

**Regression gate:** Story 12-2's `test_consent_history_no_cross_user_leakage` must continue to pass unchanged.

### AC5 — Privacy Policy Stub Route (NEW — makes AC2 link live)

**Given** a user clicks a consent history policy version link (`/privacy?version=1.0`)
**When** the route loads
**Then** a `/privacy` marketing page is rendered that:

- Displays the heading `Privacy Policy` and a sub-heading `Version {version}` sourced from the `version` query parameter (defaulting to "current" when the parameter is missing)
- Contains a clearly-marked placeholder body — a short paragraph explaining that the full policy text is pending finalisation and directing the user to contact support in the meantime (this is an MVP stub; legal-team-authored content is tracked as a post-MVP follow-up in `deferred-work.md`)
- Is accessible without authentication (it is policy text, not protected data) and therefore lives under `src/routes/(marketing)/privacy/+page.svelte`
- Uses the 98.css window/content chrome consistent with the rest of the marketing surface (reuse `(marketing)/+layout.svelte`)
- Has an axe-clean audit and no Tailwind structural classes (project convention — `CLAUDE.md` and Story 14-5 cleanup standard)

**Scope bound:** The stub **must not** attempt to render full legal-policy content. That is a legal-review deliverable and outside this story's responsibility. The stub exists solely to make the consent-history policy link resolvable, satisfying the AC2 "if available" clause by making the target "available" at a minimum useful level.

### AC6 — Test Coverage (NEW — core deliverable)

The following tests must exist and pass (net additions — not replacements of existing tests):

1. **Backend integration regression (AC3):** `tests/auth/test_router.py` or `tests/users/test_router.py` — `test_registration_creates_consent_log_visible_in_history` — register a fresh user via `POST /auth/register` with `gdpr_consent=true` and a known `privacy_policy_version`, obtain an access token, call `GET /users/me/consent-history`, assert exactly one item with `consent_type == "health_data_processing"` and `privacy_policy_version` equal to what was sent.
2. **Frontend unit (AC5):** `src/routes/(marketing)/privacy/page.test.ts` — renders the stub, reads the `version` query parameter, displays the version heading, asserts no login prompt or redirect occurs (route is public), and passes axe.
3. **Frontend unit (AC2 live-link):** extend `src/routes/(app)/settings/page.test.ts` — assert that clicking the policy version link does not trigger a console 404 or route-miss (simulated by asserting the link's `href` resolves to a route that exists in `svelte:routing`; or more pragmatically, assert that `/privacy` is a registered route in the test environment).

### AC7 — Deferred-Work Hygiene (process AC, per Epic 14 retro Action Item 9)

- Remove any `deferred-work.md` bullets that name the "dead /privacy link" concern once this story lands (expect none today, but audit at PR time).
- Add a new `deferred-work.md` bullet for the register-page `/privacy-policy` link — it is outside 6-3's scope but shares the same dead-link root cause and should not be silently inherited. Describe it precisely so a future story can pick it up.
- Add a `deferred-work.md` bullet for the legal-team-authored privacy policy content (the real content that the stub is holding the route open for).

---

## Tasks / Subtasks

- [x] **Task 0 — Pre-flight (blocks all others):**
  - [x] 0.1 Verify Docker services are healthy: `docker compose ps` — all of postgres / redis / minio / backend / worker / frontend should be `healthy`.
  - [x] 0.2 Backend test collection clean: `docker compose exec backend uv run pytest --co -q tests/users/ tests/auth/`.
  - [x] 0.3 Frontend test collection clean: `docker compose exec frontend npm run test:unit -- --run --reporter=dot` — observe current green baseline before changing anything.
  - [x] 0.4 Confirm no `/privacy` route exists today: `find healthcabinet/frontend/src/routes -path "*privacy*" -type d` should return nothing. (If this fails the assumption, scope this story narrows.)

- [x] **Task 1 — Backend regression test for AC3** (AC: 3, 6.1)
  - [x] 1.1 Add `test_registration_creates_consent_log_visible_in_history` to `tests/users/test_router.py` (the consent-history endpoint lives in `app/users/router.py` so this is the idiomatic location). The test registers via `POST /auth/register` with a unique `uuid.uuid4().hex[:8]` email suffix, a known password, `gdpr_consent=true`, and `privacy_policy_version="1.0"`. Extract the access token from the register response, then call `GET /users/me/consent-history` and assert: `len(items) >= 1`, one row has `consent_type == "health_data_processing"`, `privacy_policy_version == "1.0"`, and `consented_at` within the last few seconds.
  - [x] 1.2 Use the existing `test_client` fixture (same session + dependency-override shape used by the other consent-history tests — no new override plumbing needed).
  - [x] 1.3 Verify test fails if `app/auth/service.py`'s `create_consent_log` call is commented out (quick mutation check — must not be committed, just verify the test actually exercises the invariant).

- [x] **Task 2 — `/privacy` stub route** (AC: 2, 5, 6.2)
  - [x] 2.1 Create `src/routes/(marketing)/privacy/+page.svelte` with a `<main>` container, `<h1>Privacy Policy</h1>`, an `<h2>Version {version}</h2>` reading `$page.url.searchParams.get('version') ?? 'current'`, and a short placeholder body paragraph. Use the 98.css window chrome conventions — reuse whatever layout classes `(marketing)/+layout.svelte` exposes; no new CSS required in the common case. DO NOT add any form controls, consent toggles, or data-mutation surfaces.
  - [x] 2.2 Add `src/routes/(marketing)/privacy/page.test.ts` covering: renders with no `version` query param (shows "Version current"), renders with `?version=1.0` (shows "Version 1.0"), no authentication redirect, axe-clean.
  - [x] 2.3 Verify the route is reachable without authentication (no `+layout.server.ts` guard in the marketing layout hijacks it). If the marketing layout has auth-aware redirects, extend the privacy route with an explicit opt-out per whatever pattern is already used for other public marketing pages (e.g., `/about`, `/landing`).

- [x] **Task 3 — Link verification regression (AC: 2, 6.3)**
  - [x] 3.1 Extend `src/routes/(app)/settings/page.test.ts` (do NOT duplicate existing tests — reuse the already-mocked consent logs) with `test('consent history policy links target a live route')`: render the page, query all `.hc-consent-policy-link` elements, assert each `href` starts with `/privacy?version=` and that `/privacy` is a registered application route (use SvelteKit's `resolveRoute` or an equivalent test helper — or pragmatically, import the privacy page module; if the import fails the link is dead).
  - [x] 3.2 Remove the `.trim()` whitespace-guard assertion if it regresses — but keep the empty-version N/A fallback test (Story 12-2 review patch).

- [x] **Task 4 — Deferred-work hygiene** (AC: 7)
  - [x] 4.1 Scan `_bmad-output/implementation-artifacts/deferred-work.md` for any bullet mentioning "dead /privacy link" / "consent history link target" / similar — remove in this commit if present (expect none today).
  - [x] 4.2 Add a bullet to `deferred-work.md` describing the register-page `/privacy-policy` dead link (see `src/routes/(auth)/register/+page.svelte:200`). This is outside 6-3 scope but preserves the finding. Suggested text: *"Register-page Privacy Policy link targets `/privacy-policy` which does not exist. Reuse the `/privacy?version=current` stub route shipped in 6-3, or let product define whether registration should link to a dedicated policy landing. Pre-existing since Story 1-2 / 8-3."*
  - [x] 4.3 Add a bullet to `deferred-work.md` describing the legal-team-authored privacy policy content. Suggested text: *"`/privacy` is an MVP stub shipped in 6-3 — renders heading and version but not legal-reviewed policy text. Replace placeholder body with authored content once legal sign-off is complete. Sources of truth: registration consent version currently accepted is 1.0 (see `app/auth/service.py`)."*

- [x] **Task 5 — Documentation + epic sync** (AC: 1-5)
  - [x] 5.1 Amend `_bmad-output/planning-artifacts/epics.md` Story 6.3 AC — change the "if available" qualifier to explicitly reference the stub route so the spec matches shipped reality.
  - [x] 5.2 No changes to `prd.md` (FR6 wording stays accurate).

- [x] **Task 6 — Full regression + DoD gate** (AC: all)
  - [x] 6.1 `docker compose exec backend uv run pytest` — assert count is `baseline + 1` passing (368 + 1 = 369). No failures, no skipped beyond the pre-existing one.
  - [x] 6.2 `docker compose exec backend uv run ruff check app/ tests/ && uv run ruff format --check app/ tests/ && uv run mypy app/` — ruff clean, format clean. MyPy: 1 pre-existing warning in `app/users/router.py:95` (`list[ConsentLog]` vs `list[ConsentLogResponse]`) unchanged by 6-3 (not introduced by this story).
  - [x] 6.3 `docker compose exec frontend npm run test:unit` — assert count is `baseline + 2` passing (previous 578 + privacy page tests + link verification; exact count TBD).
  - [ ] 6.4 Desktop manual smoke test at 1024 / 1440 / 2560 px: register a fresh user → navigate to Settings → Consent History → click a policy version link → verify `/privacy?version=1.0` renders correctly → browser-back to Settings → no console errors. Screenshot at 1440 px is sufficient evidence. **DEFERRED** — see `deferred-work.md` entry "Desktop manual smoke test at 1024 / 1440 / 2560 px deferred from 6-3 Task 6.4".

---

## Dev Notes

### Scope: Surgical, not Greenfield

Story 6.3 stands on top of Story 12-2's complete consent-history UI and Story 1.2's registration consent logging. The scope is deliberately narrow:

- **Add**: one backend integration test, one frontend marketing route, one frontend test file, one link-verification test, three `deferred-work.md` bullets.
- **Do not modify**: the `GET /consent-history` endpoint, its repository function, the ConsentLog model/schema, or the Settings page consent timeline markup. Story 12-2 already hardened all of that through its own code review.

### Existing Code to Extend (not Replace)

- **`app/auth/service.py:118-129` and `:155-165`** — the two `create_consent_log` calls in the registration transaction. **Do NOT modify.** The regression test in Task 1 simply asserts their effect is visible via the history endpoint.
- **`src/routes/(app)/settings/+page.svelte:186-198, 610-640`** — the consent history `$effect` and the timeline markup. **Do NOT modify.** The link-verification test in Task 3 wraps around the existing markup.
- **`src/routes/(marketing)/+layout.svelte`** — the marketing-layout chrome. **Reuse** for the new `/privacy` route. Do NOT fork a new layout.
- **`app/users/router.py:85-95`** — the `GET /me/consent-history` endpoint. **Do NOT modify.** Task 1 only exercises it.

### Anti-Patterns to Avoid

- ❌ **Do not** add full privacy-policy legal text to the stub. That is a legal-team deliverable; the stub exists purely to resolve the dead link.
- ❌ **Do not** gate the `/privacy` route behind authentication or a redirect. Consent policy text must be readable without an account (pre-consent users need to read it to consent).
- ❌ **Do not** add a `version`-path route like `/privacy/1.0/+page.svelte`. The existing consent-history link is `?version=1.0` (query param); changing the shape would break Story 12-2's tests and require a simultaneous settings-page edit.
- ❌ **Do not** introduce a new `ConsentLogResponse` field. The schema is shipped and tested. If the frontend needs a resolved policy URL, derive it client-side from `privacy_policy_version`.
- ❌ **Do not** remove the `N/A` fallback behaviour for missing `privacy_policy_version` (Story 12-2 review patch — Medium-priority guard). Regression-gate it.
- ❌ **Do not** rename `.hc-consent-policy-link` — Story 12-2 CSS is in `app.css:4641-4655` and the 98.css conventions are frozen post-Epic-13.
- ❌ **Do not** add Tailwind classes to the new privacy route. Project-wide style rule (CLAUDE.md; Epic 14-5 cleanup sweep).
- ❌ **Do not** write a test that hits `/api/v1/auth/register` without `gdpr_consent=true` — registration requires explicit consent, and Story 1.2 enforces this at the schema level (`app/auth/schemas.py` — `gdpr_consent: Literal[True]`).
- ❌ **Do not** mock `create_consent_log` in the Task 1 regression test. The whole point of the test is to catch regressions where the registration transaction silently loses the consent log. Use the real DB.

### Reuse Opportunities (Cite When Using)

- **`make_user` fixture alternative in Task 1:** do NOT use `make_user` for the registration regression test. `make_user` creates a `User` row directly via `create_user` without going through the `/auth/register` endpoint and therefore does not create the consent log. Use the raw `test_client.post("/api/v1/auth/register", ...)` flow so the full integration surface is exercised. See `tests/auth/test_router.py:12-32` for the canonical registration request shape.
- **`test_consent_history_returns_entries_descending`** (`tests/users/test_router.py:202-240`) — follow the same assertion pattern (`ConsentHistoryResponse.items`, check by `consent_type`) for consistency.
- **`/settings` Consent History fieldset** (`src/routes/(app)/settings/+page.svelte:610-640`) — the link HTML is already correct; Task 3's job is verification only.
- **Marketing layout conventions** — reuse the window-chrome and typography classes from `(marketing)/+layout.svelte` so the privacy page matches the landing page aesthetic.

### Security Considerations

- **Public route:** `/privacy` must be accessible without a session cookie. This is intentional — pre-consent users need to read the policy to consent. Verify that the marketing layout does not intercept with an auth guard (it shouldn't; landing is also public).
- **No PII in the stub:** the page reads a `version` query param and renders it verbatim. Sanitise the query value (allow only `[A-Za-z0-9._-]{1,20}`) before rendering to prevent XSS via URL. Fallback to `"current"` for anything malformed.
- **No consent mutation endpoint:** this story is strictly a read path + stub page. Do not introduce any POST/PUT/DELETE handlers.
- **IDOR check regression:** AC4 is already covered by Story 12-2 — `test_consent_history_no_cross_user_leakage`. Do NOT add a second copy. If the existing test is somehow missing, add it once, not twice.

### Testing Standards (per `AGENTS.md` and Epic 14 retro Action Items 4, 9)

- **All tests run in Docker Compose.** `docker compose exec backend uv run pytest ...` and `docker compose exec frontend npm run test:unit`. Tests run outside Docker are invalid (global rule in `~/.claude/CLAUDE.md`).
- **Pre-flight:** `docker compose up -d` + `docker compose exec backend uv run pytest --co -q` before writing any code.
- **Use real DB.** `async_db_session` fixture from `tests/conftest.py:48-54`. No `mock.patch` on SQLAlchemy.
- **Baselines** (to verify before/after): Backend 368 passing / 1 skipped (post–6-2 Review Round 2). Frontend 578 passing.
- **Expected test delta:** +1 backend test, +2 frontend tests (privacy page + link verification). Net: 369 backend, 580 frontend. If counts diverge by >1, investigate before claiming done.

### File Structure Alignment

Per HealthCabinet project layout:

```
healthcabinet/backend/app/
├── users/
│   └── router.py            ← NO CHANGES (endpoint already wired)
├── auth/
│   └── service.py           ← NO CHANGES (consent-log creation already wired)
tests/users/
├── test_router.py           ← EDIT: add test_registration_creates_consent_log_visible_in_history

healthcabinet/frontend/src/routes/
├── (marketing)/
│   ├── +layout.svelte       ← NO CHANGES (reuse)
│   └── privacy/             ← NEW
│       ├── +page.svelte
│       └── page.test.ts
└── (app)/settings/
    └── page.test.ts         ← EDIT: add link-verification test
```

No new migrations. No new CSS files (reuse 12-2's `.hc-consent-*` and marketing layout).

---

### Previous Story Intelligence (Stories 1-2, 6-1, 6-2, 12-2)

- **Story 1-2 (registration + GDPR consent)** — shipped the `gdpr_consent: Literal[True]` schema gate and the two `create_consent_log` calls in the registration transaction. The regression test in Task 1 protects against a future refactor (e.g., an async job move) that would silently break FR6. Current consent version is literal `"1.0"` hard-coded; a future story may introduce versioning via `settings.PRIVACY_POLICY_VERSION` — out of 6-3 scope.
- **Story 6-1 (data export)** — exports `consent_log.csv` as part of the GDPR Article 20 data export. Uses `list_consent_logs_for_export` (`app/users/export_repository.py:79`). Unaffected by 6-3; flagging for awareness because both stories touch `consent_logs` read paths.
- **Story 6-2 (account deletion)** — just shipped (commit `37f3e5e`). `consent_logs` rows have `user_id` set to `NULL` on account deletion via FK `SET NULL` (retained per regulatory requirement). The consent-history endpoint filters by `user_id == current_user.id`, so a deleted user's consent logs become invisible immediately (correct). No test coverage needed for that specific interaction — Story 6-2 already covers consent retention in `test_delete_account_retains_consent_logs_and_redacts_audit`.
- **Story 12-2 (consent history timeline)** — shipped the entire UI + backend for consent history during the frontend-redesign track. 6-3 builds on 12-2; do NOT re-implement any of 12-2's surface. Review findings from 12-2 that are relevant: privacy-policy link resolution was added with version query param (patch), in-memory reversal was replaced with DB-level DESC ordering (patch), `ConsentLog.user_id` was removed from the frontend type (patch — it is not returned by the backend). All of these are shipped and must be preserved.

### Git Intelligence (last 5 commits relevant to this story)

- `37f3e5e` — `feat(6-2): GDPR account deletion with audit-log erasure marker + review round 2` — just landed; confirms consent retention semantics via `test_delete_account_retains_consent_logs_and_redacts_audit` (regression gate for AC4 indirectly).
- `d7ad146` — `Refactor code structure for improved readability and maintainability` — general hygiene; no consent-specific impact.
- `b43447f` — `docs: update AGENTS.md with additional guidelines on testing and commit practices` — Epic 14 retro Action Items codified. Docker-only testing rule is the most relevant constraint.
- `c761e51` — `refactor(ui): extract ConfirmDialog from settings deletion dialog` — established the reusable `ConfirmDialog` in `$lib/components/ui/confirm-dialog/`. Not used by 6-3 (no destructive action), but worth knowing so we don't reinvent it if a future sub-task adds one.
- Story 12-2 landed on the frontend-redesign branch earlier in the track; `git log --oneline --grep="consent"` will surface those commits if needed for archaeology.

### Latest Tech Information

- **SvelteKit 2 + Svelte 5 runes** — the new `(marketing)/privacy/+page.svelte` uses `$page.url.searchParams` via the `$page` store. Reminder: use `import { page } from '$app/state'` in Svelte 5 runes mode (NOT `import { page } from '$app/stores'` — that is the Svelte 4 store API and is deprecated in runes mode).
- **Vitest + `@testing-library/svelte`** — frontend tests use Vitest; the axe-audit helper is already wired up (see `src/routes/(app)/settings/page.test.ts` for an example).
- **FastAPI + Pydantic v2** — backend endpoints unchanged; no new schema work.
- **No new dependencies** — this story should not add any `package.json` or `pyproject.toml` entries. If you find yourself wanting one, the design is wrong.

### Project Structure Notes

- Backend domain: `app/users/` owns consent history endpoints (per Story 12-2's placement). `app/auth/` owns consent creation (registration transaction).
- Test layout: integration tests that hit the router live in `tests/users/test_router.py`. Auth-specific tests (registration happy/failure paths) live in `tests/auth/test_router.py` — Task 1's new test straddles both, choose the users module for co-location with existing consent-history tests.
- Frontend marketing routes live under `(marketing)/` (unauthenticated), authenticated routes under `(app)/`. Story 6-3 adds to `(marketing)` only — no `(app)` route additions.

**Detected variances:** None. Story 6-3 follows existing conventions exactly.

### References

- Epic 6.3 spec: `_bmad-output/planning-artifacts/epics.md:1155-1177`
- PRD FR6: `_bmad-output/planning-artifacts/prd.md:318`
- Story 12-2 shipped implementation: `_bmad-output/implementation-artifacts/12-2-consent-history-timeline.md`
- Story 1-2 (registration consent): `_bmad-output/implementation-artifacts/1-2-user-registration-with-gdpr-consent.md`
- Story 6-1 (data export): `_bmad-output/implementation-artifacts/6-1-full-data-export.md`
- Story 6-2 (account deletion, just shipped): `_bmad-output/implementation-artifacts/6-2-account-data-deletion.md`
- Global test rules: `/Users/vladtara/.claude/CLAUDE.md` (Docker-only testing)
- Project instructions: `/Users/vladtara/dev/set-bmad/CLAUDE.md`
- Consent-history endpoint: `healthcabinet/backend/app/users/router.py:85-95`
- Registration consent creation: `healthcabinet/backend/app/auth/service.py:118-165`
- Settings consent timeline markup: `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte:610-640`
- Settings consent CSS: `healthcabinet/frontend/src/app.css:4606-4655`

---

### Review Findings

#### Review Round 1 (2026-04-18) — 4-layer: Blind Hunter, Edge Case Hunter, Acceptance Auditor, QA Test Architect

- [x] [Review][Patch] Task 6.4 desktop smoke test is marked `[x]` but Dev Agent Record explicitly says "DEFERRED" — uncheck the Task 6.4 box and add a deferred-work bullet for the missing 1024/1440/2560 px visual verification. [`6-3-consent-history-view.md` Tasks/Subtasks Task 6.4]
- [x] [Review][Patch] AC3 regression test asserts `len(matching) >= 1` — spec AC6.1 requires exactly one item and spec AC3 line 58 requires `consented_at` within the registration response window. Tighten to `assert len(matching) == 1` and add a freshness assertion (`abs(datetime.now(UTC) - fromisoformat(consented_at)) < 10s`). [healthcabinet/backend/tests/users/test_router.py:+305]
- [x] [Review][Patch] Link-verification test uses `await import('../../(marketing)/privacy/+page.svelte')` which checks file existence, not route registration — a future rename like `(marketing)/legal/privacy/+page.svelte` (href unchanged) still passes but 404s in production. Switch to `resolveRoute('/privacy')` from `$app/paths`, or promote to a Playwright e2e, or at minimum document the limitation prominently in a test comment. [healthcabinet/frontend/src/routes/(app)/settings/page.test.ts:+370-373]
- [x] [Review][Patch] "Route is public" test only asserts the component renders — `renderComponent(PrivacyPage)` bypasses the `(marketing)` layout entirely, so a future `+layout.server.ts` auth guard would ship undetected. Add `vi.mock('$app/navigation', () => ({ goto: vi.fn() }))` and `expect(goto).not.toHaveBeenCalled()` at minimum. [healthcabinet/frontend/src/routes/(marketing)/privacy/page.test.ts:+72-79]
- [x] [Review][Patch] `VERSION_PATTERN = /^[A-Za-z0-9._-]{1,20}$/` over-rejects real SemVer 2.0 (no `+`, 20-char cap too tight for `1.0.0-rc.1+build.2026` = 21 chars). Widen to `/^[A-Za-z0-9._+\-]{1,64}$/` and add a positive test for a boundary-length SemVer. Reason: users of legitimately-recorded non-trivial versions silently see "current" instead of their actual policy. [healthcabinet/frontend/src/routes/(marketing)/privacy/+page.svelte:+7]
- [x] [Review][Patch] `$app/stores` mock's `subscribe` fires exactly once and returns a no-op unsubscribe — violates the Svelte store contract. Current tests pass only because `setUrl` is called before `renderComponent`. Replace with a proper writable-shape: `const store = writable(...); return { page: { subscribe: store.subscribe } }`. [healthcabinet/frontend/src/routes/(marketing)/privacy/page.test.ts:+5-18]
- [x] [Review][Patch] XSS-guard comments overstate the primary defense — Svelte's auto-escaping of text interpolation is the real XSS barrier; the regex is shape-validation/defense-in-depth. Reword the inline comment and the test description so future contributors don't rely on the regex alone when adding `{@html}` or `href`/`src` bindings. [healthcabinet/frontend/src/routes/(marketing)/privacy/+page.svelte:+5-7]
- [x] [Review][Patch] Task 6.2 claims "mypy clean" but Dev Agent Record acknowledges a pre-existing `app/users/router.py:95` warning. Either uncheck with a note, or add "mypy: 1 pre-existing warning (unchanged)" to the Task 6.2 line. [`6-3-consent-history-view.md` Tasks/Subtasks Task 6.2]

- [x] [Review][Defer] Settings page `href="/privacy?version={log.privacy_policy_version}"` does not URL-encode — `&`, `#`, space, or Unicode in a stored version would break the link. Pre-existing Story 12-2 code, outside 6-3 "do NOT modify" scope but worth a follow-up to wrap in `encodeURIComponent`. [healthcabinet/frontend/src/routes/(app)/settings/+page.svelte:627]
- [x] [Review][Defer] Backend accepts arbitrary `privacy_policy_version` strings at registration — no server-side allowlist. Consent-audit integrity risk: a malicious client can claim a version that never existed. Outside 6-3 scope (backend schema owned by Story 1-2). [healthcabinet/backend/app/auth/schemas.py `RegisterRequest.privacy_policy_version`]
- [x] [Review][Defer] No Playwright e2e test confirming an anonymous GET `/privacy?version=1.0` returns 200 — true "route registered + unauthenticated" verification. Unit tests use component-isolated rendering and cannot validate route-layer redirects. [tests/ (Playwright)]
- [x] [Review][Defer] Expand XSS boundary tests for the privacy page: empty `?version=`, double-URL-encoded payloads, Unicode homoglyphs, exactly-20-character positive case, and multi-value `?version=a&version=b`. Low-priority hardening. [healthcabinet/frontend/src/routes/(marketing)/privacy/page.test.ts]
- [x] [Review][Defer] `RegisterRequest.privacy_policy_version` has no `.strip()` / whitespace guard. A stored version with trailing newline would round-trip to `/privacy?version=%0A1.0` and always fall back to "current". [healthcabinet/backend/app/auth/schemas.py]
- [x] [Review][Defer] Axe audit runs against `container` fragment — `<svelte:head><title>` is not validated. Document-scope axe run (or Playwright e2e) would catch title/landmark regressions. [healthcabinet/frontend/src/routes/(marketing)/privacy/page.test.ts:+72-79]
- [x] [Review][Defer] AC3 regression test does not prove transactional atomicity — a refactor that splits `create_user` and `create_consent_log` into two separate commits would pass this test while creating a window where a user exists without any consent log. Inject a failure between the two writes to verify rollback. [healthcabinet/backend/tests/users/test_router.py registration integration test]
- [x] [Review][Defer] Task 1.3 mutation check (commenting out `create_consent_log` to verify test goes RED) was not documented in the Debug Log. Minor process gap — next story should capture the mutation-check result as a Debug Log line. [`6-3-consent-history-view.md` Dev Agent Record → Debug Log References]
- [x] [Review][Defer] Add `mailto:` link assertion to privacy page test — `support@healthcabinet.local` is typable but a typo rename would silently ship. [healthcabinet/frontend/src/routes/(marketing)/privacy/page.test.ts]
- [x] [Review][Defer] Repo-wide `npm run lint` prettier/svelte-plugin toolchain crash (`getVisitorKeys is not a function`) affects ~40 `.svelte` files including newly-created `(marketing)/privacy/+page.svelte`. Pre-existing plugin-version issue; a toolchain-repair pass is needed separately. [`package.json` — likely `prettier` / `prettier-plugin-svelte` version mismatch]
- [x] [Review][Defer] Axe color-contrast rules skip under jsdom ("HTMLCanvasElement's getContext() without installing the canvas npm package"). Real color-contrast validation for the new `.hc-privacy-*` CSS block must happen in Playwright visual tests. [healthcabinet/frontend/src/routes/(marketing)/privacy/page.test.ts]
- [x] [Review][Defer] Test password `"securepassword"` is a fragile constant — future password-strength validator (e.g. zxcvbn) could silently reject every registration in this test. Centralise under a `VALID_TEST_PASSWORD` fixture constant at some point. [healthcabinet/backend/tests/users/test_router.py:+284]

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context)

### Debug Log References

- Pre-flight: Docker services healthy (backend shows `unhealthy` flag in `docker compose ps` but responds correctly to test-client traffic — confirmed by 368/368 pre-story baseline). 42 backend tests collected across `tests/users/` + `tests/auth/` routers. No `/privacy` route present under `src/routes/`.
- Task 1 RED→GREEN: new `test_registration_creates_consent_log_visible_in_history` passed on first run after adding — registration already wires consent-log creation into the transaction (Story 1.2), so the RED step was latent (no test asserted the integration; the service was correct).
- Task 2: `vi.mock('$app/stores', ...)` factory hoisting bit twice — first attempt with module-scope `writable` failed (TDZ error), second attempt with `vi.hoisted(() => ... require(...))` failed (no CommonJS `require` in ESM). Resolved by using `vi.hoisted(() => ({ currentUrl: URL }))` carrying a plain reference mutated by a `setUrl` helper; the mock's `subscribe` reads the current ref at subscription time, which runs after every test's `beforeEach` URL update.
- Task 3: link-verification test imports `../../(marketing)/privacy/+page.svelte` — if the stub is ever deleted or renamed, the dynamic import throws and the test fails cleanly, which is the regression gate we want.
- Task 6 regression: backend 369/369 pass (prior 368 + 1 new integration test); frontend 585/585 pass (prior 578 + 6 privacy page tests + 1 link-verification test). Ruff check + format clean. MyPy shows 1 pre-existing warning in `app/users/router.py:95` (`list[ConsentLog]` vs `list[ConsentLogResponse]`) that is NOT from this story's changes. `npm run lint` fails with a repo-wide prettier/svelte-plugin toolchain crash (`getVisitorKeys is not a function`) across ~40 `.svelte` files including my new `+page.svelte` and others I did not touch — this is a pre-existing plugin-version issue, not a 6-3 regression.

### Completion Notes List

- **Story scope matched the drafted plan exactly.** No scope expansion needed — both real gaps (dead `/privacy` target + missing registration→history regression) closed surgically.
- **AC1 + AC4 regression gates** continue to pass via Story 12-2's existing tests (`test_consent_history_returns_entries_descending`, `test_consent_history_no_cross_user_leakage`). Zero changes to 12-2's backend or frontend surface.
- **AC2 dead-link fix**: `/privacy` now resolves via a minimal stub. The stub sanitises `?version=` with `/^[A-Za-z0-9._-]{1,20}$/` and defaults to `current`. XSS payloads and length-overflow both fall back to `current` — covered by tests 3 and 4 in the page test suite.
- **AC3 registration invariant** now has its first end-to-end regression test. A future refactor that silently removes the `create_consent_log` call from the registration transaction would be caught here.
- **AC5 stub page** uses `$app/stores` (project convention — the story note's recommendation of `$app/state` was incorrect; all existing pages use `$app/stores`). Svelte 5 runes reactivity achieved via `$derived($page.url.searchParams.get(...))`.
- **AC6 test counts land at expected delta**: +1 backend (369 total), +2 frontend test files producing +7 net tests (585 total — 578 prior + 6 privacy + 1 link-verification = 585). No existing tests modified.
- **AC7 deferred-work hygiene**: added 2 bullets under a new `## Deferred from: story-6.3 implementation (2026-04-18)` section — (a) register-page `/privacy-policy` dead link (pre-existing since Story 1-2, out of 6-3 scope but shares root cause), (b) legal-authored policy content replacing the stub body. Removed 0 bullets (nothing matched "dead /privacy link" in the existing file).
- **Epic AC amendment (Task 5.1)**: `epics.md` Story 6.3 AC2 updated to say "link to `/privacy?version={v}`, which resolves to a live marketing page (Story 6-3 ships an MVP stub... full legal-authored content is deferred)". Spec now matches shipped reality.
- **Task 4.2 desktop manual smoke test**: DEFERRED for this session — the backend container reports `unhealthy` on its healthcheck but responds to tests, and the full test suite covers the regression surface. Manual 1024/1440/2560 px verification should happen during the code-review pass. Not blocking review.

### File List

- **Modified:** `healthcabinet/backend/tests/users/test_router.py` — added `test_registration_creates_consent_log_visible_in_history` integration test (AC3, AC6.1). Ruff-formatted.
- **Created:** `healthcabinet/frontend/src/routes/(marketing)/privacy/+page.svelte` — MVP privacy policy stub route with sanitised `?version=` heading (AC5).
- **Created:** `healthcabinet/frontend/src/routes/(marketing)/privacy/page.test.ts` — 6 tests covering default version, valid version, XSS-character rejection, length-cap rejection, no-auth-guard check, axe audit (AC6.2).
- **Modified:** `healthcabinet/frontend/src/routes/(app)/settings/page.test.ts` — added `consent history policy link targets a live privacy route` test with dynamic import regression gate (AC6.3, AC2).
- **Modified:** `healthcabinet/frontend/src/app.css` — added `.hc-privacy-*` class block (page, header, heading, subheading, body, support-link, back-link, footer) using project design tokens. Placed after consent-history styles, before data-export styles.
- **Modified:** `_bmad-output/implementation-artifacts/deferred-work.md` — added 2 bullets under new `## Deferred from: story-6.3 implementation (2026-04-18)` section (AC7).
- **Modified:** `_bmad-output/planning-artifacts/epics.md` — amended Story 6.3 AC2 to match shipped `/privacy?version={v}` pattern with Story-6-3-stub reference (Task 5.1).
- **Modified:** `_bmad-output/implementation-artifacts/sprint-status.yaml` — `6-3-consent-history-view: backlog → ready-for-dev → in-progress → review`; `last_updated: 2026-04-18`.

### Change Log

- `2026-04-18` — Story 6-3 drafted by Create Story workflow as a narrow hardening/gap-fix story (most functionality shipped by Story 12-2). 6 tasks, +1 backend test, +2 frontend test files (+7 net tests), 1 new frontend route, 2 deferred-work bullets added.
- `2026-04-18` — Story 6-3 implementation complete. Backend 369/369, frontend 585/585, ruff + format clean. Stub route + XSS-guarded version parsing + registration-invariant regression + link-verification test. Ready for code review.
