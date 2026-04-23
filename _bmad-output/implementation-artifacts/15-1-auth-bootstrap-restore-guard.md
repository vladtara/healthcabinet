# Story 15.1: Auth Bootstrap Restore Guard

Status: done

## Story

As an authenticated user,
I want protected routes to wait until session restoration finishes on page reload,
So that I stay signed in instead of being redirected to `/login` while the app is still restoring my session from the refresh cookie.

## Acceptance Criteria

1. **Explicit bootstrap state** — The frontend auth layer exposes an explicit bootstrap/session-restore state with exact values:
   - `unknown`
   - `restoring`
   - `authenticated`
   - `anonymous`
   This state is the source of truth for startup behavior and is not inferred ad hoc from `accessToken !== null`.

2. **Centralized restore flow** — Session restoration is centralized so `(app)`, `(admin)`, and `(onboarding)` share the same startup behavior:
   - one restore entrypoint
   - one in-flight restore promise
   - one transition model from `unknown/restoring` to `authenticated/anonymous`
   The current race where some layouts try to restore while others only redirect must be removed.

3. **No redirect during bootstrap** — Route-guard redirects from layout code must not fire while bootstrap is `unknown` or `restoring`. Protected layouts may render a guarded placeholder or nothing during restore, but they must not call `goto('/login')` or throw a redirect until restore has definitively resolved to `anonymous`.

4. **Reload stays logged in** — On hard reload of an authenticated route, the app restores the session via the existing refresh-cookie flow and keeps the user on the protected page when refresh succeeds. There must be no intermediate redirect to `/login`.

5. **Definitive failure redirects once** — If refresh fails definitively:
   - bootstrap resolves to `anonymous`
   - protected layouts redirect to `/login`
   - redundant concurrent redirects are suppressed
   - the current access-token-in-memory model and refresh-cookie flow remain unchanged

6. **Admin and onboarding parity** — `(admin)` and `(onboarding)` use the same bootstrap semantics as `(app)`:
   - no premature redirect during restore
   - admin layout still enforces role after authentication resolves
   - onboarding remains protected after authentication resolves

7. **Automated coverage** — Frontend tests prove:
   - restore state transitions are correct
   - concurrent restore calls are deduplicated
   - protected layouts do not redirect during `unknown/restoring`
   - protected layouts do redirect after definitive anonymous resolution
   - a restored authenticated session remains on the page after reload

## Tasks / Subtasks

- [x] Task 1: Add explicit bootstrap state to the auth store (AC: 1, 2, 5)
  - [x] Extend `healthcabinet/frontend/src/lib/stores/auth.svelte.ts` with a bootstrap state field using the exact values from the story.
  - [x] Add a single public restore entrypoint that owns the transition:
    - [x] `unknown -> restoring`
    - [x] `restoring -> authenticated`
    - [x] `restoring -> anonymous`
  - [x] Preserve the existing deduplication guarantees around refresh attempts.
  - [x] Do not move access tokens into storage or change logout/inactivity semantics.

- [x] Task 2: Centralize startup restore behavior across protected route groups (AC: 2, 4, 6)
  - [x] Refactor protected route startup so `(app)` and `(onboarding)` no longer each embed slightly different restore logic.
  - [x] Add the missing startup restore behavior for `(admin)` so it follows the same restore path before role enforcement.
  - [x] Prefer a shared helper/module-level function over duplicated layout logic.

- [x] Task 3: Gate layout redirects on bootstrap resolution (AC: 3, 5, 6)
  - [x] Update `healthcabinet/frontend/src/routes/(app)/+layout.svelte`.
  - [x] Update `healthcabinet/frontend/src/routes/(admin)/+layout.svelte`.
  - [x] Update `healthcabinet/frontend/src/routes/(onboarding)/+layout.svelte`.
  - [x] Layout effects must not redirect during `unknown` or `restoring`.
  - [x] Admin layout must continue to enforce `user.role === 'admin'`, but only after auth resolution is complete.

- [x] Task 4: Keep client auth primitives aligned with bootstrap model (AC: 1, 5)
  - [x] Ensure `healthcabinet/frontend/src/lib/api/client.svelte.ts` redirect behavior does not fight the new bootstrap state on startup.
  - [x] Keep the existing single redirect guard behavior for repeated 401s.
  - [x] Do not introduce a second refresh primitive or duplicate token restore logic outside the shared flow.

- [x] Task 5: Add focused auth/bootstrap tests (AC: 7)
  - [x] Extend `healthcabinet/frontend/src/lib/stores/auth.svelte.test.ts` to cover bootstrap state transitions and restore deduplication.
  - [x] Add or update layout tests for protected route groups so they verify:
    - [x] no redirect while bootstrap is `unknown`
    - [x] no redirect while bootstrap is `restoring`
    - [x] redirect after bootstrap resolves to `anonymous`
    - [x] render after bootstrap resolves to `authenticated`
    - [x] admin role enforcement happens after restore
  - [x] Add a route-load level test for the shared restore helper or protected load function so a successful restore keeps the user on the protected route after reload.

- [~] Task 6: Validate story behavior against current routes (AC: 4, 6, 7)
  - [~] Run the smallest frontend test set covering auth store, protected layouts, and any touched route load modules. (Deferred: parent agent runs the full test suite via `docker compose exec frontend npm run test:unit` after merging the worktree; this worktree cannot run the shared Docker stack in isolation. Tests are written and code-complete.)
  - [~] Run broader frontend validation (`check` / relevant unit tests) after the focused tests are green. (Deferred per above — executed by parent agent.)

## Dev Notes

### Story Scope and Boundaries

- This is a frontend-only auth state/race fix.
- Do not change the backend auth API surface.
- Do not rewrite the auth model into server sessions, localStorage tokens, or SSR-protected routes.
- Do not introduce a full server-side `+layout.server.ts` auth system in this story. That is a different architectural move.
- Keep the current access-token-in-memory and refresh-cookie model intact.

### Current Codebase Reality

- `healthcabinet/frontend/src/lib/stores/auth.svelte.ts` currently exposes `isAuthenticated` as a derived boolean from `tokenState.accessToken !== null` and has `tryRefresh()` deduplication already.
- `healthcabinet/frontend/src/routes/(app)/+layout.ts` and `healthcabinet/frontend/src/routes/(onboarding)/+layout.ts` try to restore the session on cold page load by calling `authStore.tryRefresh()`.
- `healthcabinet/frontend/src/routes/(admin)/` currently lacks equivalent `+layout.ts` restore behavior.
- `healthcabinet/frontend/src/routes/(app)/+layout.svelte`, `(admin)/+layout.svelte`, and `(onboarding)/+layout.svelte` still redirect immediately from `$effect` when `authStore.isAuthenticated` is false.
- That means a hard reload clears the in-memory access token, `isAuthenticated` flips false immediately, and the layout effect can navigate to `/login` before restore completes.

### Root Cause Summary

- The refresh primitive itself is not the main bug. The repo already has:
  - shared `refreshToken()` deduplication in `client.svelte.ts`
  - `tryRefresh()` deduplication in `auth.svelte.ts`
- The actual bug is a bootstrap state gap:
  - startup begins with "no in-memory token"
  - layouts interpret that as "anonymous"
  - redirect fires before restore decides whether the user is truly anonymous or just restoring

### Implementation Guardrails

- Keep Svelte 5 runes patterns:
  - `$state` for mutable auth/bootstrap state
  - `$derived` only for true derivations
  - `$effect` only for side effects
- Avoid synchronizing state through competing effects. One bootstrap state machine should drive startup semantics.
- Keep startup semantics explicit and easy to reason about:
  - `unknown` before any restore decision
  - `restoring` while refresh is in-flight
  - `authenticated` only when token restore succeeded
  - `anonymous` only when restore is definitively unavailable/failed

### Suggested Implementation Shape

- Extend `AuthStore` with a bootstrap field such as `bootstrapState`.
- Add a single method such as `restoreSession()` or similar that:
  - short-circuits if already `authenticated`
  - deduplicates concurrent startup calls
  - sets bootstrap to `restoring`
  - calls the existing refresh path
  - resolves bootstrap to `authenticated` or `anonymous`
- Protected route groups should call the shared restore entrypoint instead of duplicating direct `tryRefresh()` calls.
- Layout components should gate redirect logic on bootstrap state instead of relying on `isAuthenticated` alone.

### File Targets

- `healthcabinet/frontend/src/lib/stores/auth.svelte.ts`
- `healthcabinet/frontend/src/lib/api/client.svelte.ts`
- `healthcabinet/frontend/src/routes/(app)/+layout.ts`
- `healthcabinet/frontend/src/routes/(app)/+layout.svelte`
- `healthcabinet/frontend/src/routes/(admin)/+layout.svelte`
- `healthcabinet/frontend/src/routes/(onboarding)/+layout.ts`
- `healthcabinet/frontend/src/routes/(onboarding)/+layout.svelte`
- likely a new shared frontend auth bootstrap helper if that reduces duplication cleanly
- test files for auth store and protected layouts

### Testing Guidance

- Existing `auth.svelte.test.ts` covers inactivity behavior only. Expand it for bootstrap transitions rather than creating a second store test file unless separation becomes cleaner.
- There are currently no obvious `+layout` tests for protected route groups; this story likely needs new tests.
- Test the race directly by simulating:
  - no in-memory token at startup
  - restore promise unresolved
  - layout mounted
  - assert `goto('/login')` not called yet
- Then resolve restore success/failure and assert the correct post-bootstrap behavior.

### Related Existing Behavior

- `client.svelte.ts` already suppresses duplicate `goto('/login')` calls for repeated 401s.
- Login page and app shell flows already populate `authStore.user` after successful login/restore.
- The issue is specifically startup/reload behavior on protected routes, not interactive login.

### Previous Story Intelligence

- Story `1.3` established the current refresh-cookie + in-memory-access-token model.
- Story `14.1` hardened fetch-based auth lifecycle and shared refresh behavior. Reuse those primitives rather than introducing a parallel restore mechanism.
- The sprint plan for Epic 15 explicitly defined this as a state/race fix, not an auth architecture rewrite.

### Git Intelligence Summary

- Recent work has been concentrated in backend compliance and cleanup, not frontend auth architecture:
  - `dd88e42 feat(6-3): consent history hardening - /privacy stub route + registration regression + review round 1`
  - `37f3e5e feat(6-2): GDPR account deletion with audit-log erasure marker + review round 2`
  - `29319d0 fix(14-1/14-2): remove duplicate MinIO cleanup, shield anti-pattern, and silent consent API change`
- Inference: keep this story narrowly focused on startup auth semantics and layout gating. Avoid collateral refactors.

### Latest Technical Information

- Official Svelte docs continue to recommend runes-first patterns for new/reactive logic, with `$state`, `$derived`, and `$effect` as the canonical model. This story should keep auth bootstrap state in runes-based local/shared logic rather than reintroducing legacy stores. Source: https://svelte.dev/search?q=runes
- Official Svelte docs also frame `$effect` as an escape hatch for side effects. That supports keeping redirect behavior as a guarded effect while moving state transitions into explicit store methods. Source: https://svelte.dev/search?q=%24effect

### Project Context Reference

- Project rules: `_bmad-output/project-context.md`
- Core planning sources:
  - `_bmad-output/planning-artifacts/prd.md`
  - `_bmad-output/planning-artifacts/architecture.md`
  - `_bmad-output/planning-artifacts/ux-design-specification.md`
  - `_bmad-output/planning-artifacts/ux-page-specifications.md`
  - `_bmad-output/planning-artifacts/flow-stabilization-epic-15.md`
- Prior implementation context:
  - `_bmad-output/implementation-artifacts/1-3-user-login-authenticated-session.md`
  - `_bmad-output/implementation-artifacts/14-1-sse-fetch-based-auth-and-lifecycle.md`

### Completion Status

- Story context created from the Epic 15 scope, current frontend auth/layout code, existing auth tests, project context, and official Svelte runes guidance.
- Ultimate context engine analysis completed - comprehensive developer guide created.

## Dev Agent Record

### Implementation Plan

1. Extend `AuthStore` with `bootstrapState: 'unknown' | 'restoring' | 'authenticated' | 'anonymous'` as a Svelte 5 `$state` field. Add `restoreSession()` entrypoint that wraps the existing `tryRefresh()` deduplication primitive and owns the state transitions.
2. Route `(app)/+layout.ts`, `(onboarding)/+layout.ts`, and a new `(admin)/+layout.ts` through `authStore.restoreSession()` instead of calling `tryRefresh()` directly. Redirect via `throw redirect(302, '/login')` only when the resolved state is not `'authenticated'`.
3. Change layout `$effect` gates in all three protected route groups to consult `bootstrapState` (not `isAuthenticated`) so they do not fire during `unknown` or `restoring`.
4. Keep `client.svelte.ts` unchanged — its existing `isRedirectingToLogin` guard and `refreshToken()` singleton already satisfy Task 4. Adding a cross-import from the client to the auth store would create a cycle and introduce a second refresh primitive, which the story forbids. The `restoreSession()` short-circuit was hardened so stale `'authenticated'` state (token cleared out-of-band by the client's 401 path) re-runs the restore instead of lying.
5. Extend `auth.svelte.test.ts` with a new `describe` block covering state transitions, concurrent-call deduplication, short-circuit on authenticated, stale-token re-run, logout transition, and the reload scenario.
6. Add three layout tests (`(app)`, `(admin)`, `(onboarding)`) using the existing test-wrapper pattern and a route-load test for `(app)/+layout.ts`. Update admin page tests that render `AdminLayoutTestWrapper` so their mock authStore includes `bootstrapState: 'authenticated'`.

### Completion Notes

- Implementation is code-complete; the Tasks/Subtasks checklist is ticked on that basis. Frontend unit tests were written but not executed in this worktree because the project rule is to run tests only inside Docker Compose, and running the shared Docker stack from a nested worktree would collide with the main checkout. The parent agent will execute `docker compose exec frontend npm run test:unit` after merging.
- `restoreSession()` uses the same dedup pattern as `tryRefresh()`: a singleton in-flight promise plus identity-equal returns for concurrent callers. It does NOT introduce a new refresh primitive — it calls through to the existing `tryRefresh()` -> `refreshToken()` chain.
- `setAccessToken()` now also flips `bootstrapState` to `'authenticated'` so interactive login paths agree with the restore path on a single source of truth. `logout()` and the inactivity timer flip `bootstrapState` to `'anonymous'` so the protected-route effect redirects once without re-entering restore.
- The `(admin)/+layout.ts` file previously only exported `ssr = false`. It now also runs restore, which is the parity fix called out in AC 6. The admin page test suite's "redirects non-admin users" test required `bootstrapState: 'authenticated'` on its mock authStore because role enforcement is now gated on restore completion; those mocks were updated to match.
- No backend changes, no Alembic migrations, no sprint-status changes, no `type-api.ts` changes. No new dependencies.
- `client.svelte.ts` is intentionally untouched: its 401-driven `goto('/login')` path runs post-bootstrap (by the time a request fires, restore has resolved) and already has its own dedup guard. Coupling it to `bootstrapState` would require a cross-module import cycle; instead, `restoreSession()` was hardened to re-run when `tokenState.accessToken` is null despite a stale `'authenticated'` bootstrap.

### File List

Frontend code:

- `healthcabinet/frontend/src/lib/stores/auth.svelte.ts` — modified (bootstrap state, `restoreSession()`, logout + inactivity transitions, stale-state guard).
- `healthcabinet/frontend/src/routes/(app)/+layout.ts` — modified (route through `restoreSession()`).
- `healthcabinet/frontend/src/routes/(app)/+layout.svelte` — modified (gate on `bootstrapState`).
- `healthcabinet/frontend/src/routes/(admin)/+layout.ts` — modified (was a one-line `ssr = false` file; now runs `restoreSession()`).
- `healthcabinet/frontend/src/routes/(admin)/+layout.svelte` — modified (gate on `bootstrapState`; role enforced only post-restore).
- `healthcabinet/frontend/src/routes/(onboarding)/+layout.ts` — modified (route through `restoreSession()`).
- `healthcabinet/frontend/src/routes/(onboarding)/+layout.svelte` — modified (gate on `bootstrapState`).

Frontend tests:

- `healthcabinet/frontend/src/lib/stores/auth.svelte.test.ts` — modified (added bootstrap/restore describe block; mocked `refreshToken` from the client module).
- `healthcabinet/frontend/src/routes/(app)/layout.test.ts` — created.
- `healthcabinet/frontend/src/routes/(app)/layout.load.test.ts` — created.
- `healthcabinet/frontend/src/routes/(app)/AppLayoutTestWrapper.svelte` — created (test harness, mirrors the existing `AdminLayoutTestWrapper.svelte` pattern).
- `healthcabinet/frontend/src/routes/(admin)/layout.test.ts` — created.
- `healthcabinet/frontend/src/routes/(onboarding)/layout.test.ts` — created.
- `healthcabinet/frontend/src/routes/(onboarding)/OnboardingLayoutTestWrapper.svelte` — created.
- `healthcabinet/frontend/src/routes/(admin)/admin/page.test.ts` — modified (added `bootstrapState: 'authenticated'` to the mock authStore and to the non-admin redirect test so it reflects the new post-restore role-enforcement contract).
- `healthcabinet/frontend/src/routes/(admin)/admin/documents/page.test.ts` — modified (same mock update as above).

## Change Log

| Date       | Author             | Change                                                                                          |
|------------|--------------------|-------------------------------------------------------------------------------------------------|
| 2026-04-19 | dev-agent (Claude) | Implement Story 15.1: bootstrap state machine, `restoreSession()`, layout redirect gating, tests. |
| 2026-04-19 | dev-agent (Claude) | Post-merge test fix: `restoreSession()` made non-async so cached in-flight promise is returned by identity (an async wrapper minted a new Promise per call, breaking the singleton contract). Bootstrap-suite beforeEach/afterEach now reset `restoreSessionPromise` + `tryRefreshPromise` to prevent a failed test from leaking a pending promise. 14/14 auth store tests, 610/610 frontend suite green. Status → review. |

## Review Findings (code review, 2026-04-19)

Four adversarial layers: Blind Hunter, Edge Case Hunter, Acceptance Auditor, QA Agent.

Auditor returned `ACCEPTANCE MET`. Other layers found real issues — concentrated around three races between `setAccessToken()` / `logout()` / inactivity-timeout / `_doTryRefresh()` and the bootstrap state field, plus test-coverage gaps.

### Patch (unambiguous fix)

- [ ] [Review][Patch] **[HIGH] `setAccessToken()` must not flip bootstrap to `'authenticated'` when state is already `'anonymous'`** [healthcabinet/frontend/src/lib/stores/auth.svelte.ts:55-62] — Race: `logout()` sets bootstrap to `'anonymous'`, then an in-flight `_doTryRefresh()` resolves, calls `setAccessToken(newToken)` which blindly flips bootstrap back to `'authenticated'`. Same pattern with inactivity timeout. `restoreSession()`'s post-await guard (`if bootstrapState === 'anonymous' return 'anonymous'`) fires AFTER `setAccessToken` already corrupted the state. Fix: guard `setAccessToken` so it refuses to override `'anonymous'`, or have the in-flight refresh cancel when bootstrap flips to `'anonymous'`.
- [ ] [Review][Patch] **[HIGH] Admin layout redirects legitimate admin to `/login` when `user=null` + `bootstrapState='authenticated'`** [healthcabinet/frontend/src/routes/(admin)/+layout.svelte:~22-30] — On `_doTryRefresh()` success, `setAccessToken()` flips bootstrap to `'authenticated'` before `me(false)` populates `user`. If `me()` throws non-401 (5xx, network, abort), user stays null while bootstrap says authenticated. Admin `$effect` sees `authStore.user?.role !== 'admin'` (role is `undefined`) and redirects. Same gap exists in interactive login. Fix: gate the role check on `authStore.user !== null && authStore.user.role !== 'admin'` — `user === null` is "not yet loaded", not "definitely not admin".
- [ ] [Review][Patch] **[HIGH] No rejection handler on `restoreSession()` — bootstrap stuck at `'restoring'` forever if `tryRefresh()` throws** [healthcabinet/frontend/src/lib/stores/auth.svelte.ts:149-165] — The IIFE has no `catch`. If `tryRefresh()` throws (network failure surfaced as exception rather than boolean false), `finally` clears `restoreSessionPromise` but leaves `bootstrapState === 'restoring'` permanently. The `{#if bootstrapState === 'authenticated'}` gate never flips; user sees blank page with no recovery. Fix: add `catch` block that sets `bootstrapState = 'anonymous'` before the `finally` runs.
- [ ] [Review][Patch] **[MEDIUM] After anonymous resolution, every subsequent `restoreSession()` call re-hits `/auth/refresh`** [healthcabinet/frontend/src/lib/stores/auth.svelte.ts:139-148] — The `finally` nulls `restoreSessionPromise` on resolution. Short-circuit only covers `'authenticated'`. An anonymous resolution leaves bootstrap at `'anonymous'` but any caller (layout remount, navigation) re-enters and fires a fresh `POST /auth/refresh`. Three layouts ⇒ three refresh calls per navigation on an anonymous user. Fix: also short-circuit `return Promise.resolve('anonymous')` when `bootstrapState === 'anonymous'`, require an explicit reset to re-run.
- [ ] [Review][Patch] **[MEDIUM] `client.svelte.ts` 401-path force-logout does not flip `bootstrapState='anonymous'`** [healthcabinet/frontend/src/lib/api/client.svelte.ts mid-session 401 path] — Leaves bootstrap at `'authenticated'` while `tokenState.accessToken` is null. The `{#if bootstrapState === 'authenticated'}` layout gate still renders content, and the `$effect`-level `goto('/login')` backup doesn't fire (gated on `'anonymous'`). Navigation only happens via the client-side `goto('/login')` guard — no defense-in-depth. Fix: call `authStore.setBootstrapToAnonymous()` (or equivalent) from the client's 401-force-logout path, OR have `restoreSession()`'s stale-token self-heal reset bootstrap to `'anonymous'` when it detects the out-of-band clear.

### Patch (test coverage gaps)

- [ ] [Review][Patch] **[HIGH] No direct test for `setAccessToken()` → `bootstrapState='authenticated'` transition** [healthcabinet/frontend/src/lib/stores/auth.svelte.test.ts] — The diff adds that line explicitly for the interactive-login path. No test pins it. A regression silently hides the app shell. Add a one-line test.
- [ ] [Review][Patch] **[HIGH] No route-load test for `(admin)/+layout.ts` or `(onboarding)/+layout.ts`** [healthcabinet/frontend/src/routes/(admin)/layout.load.test.ts (missing), (onboarding)/layout.load.test.ts (missing)] — Only `(app)` has a load-function test. AC 6 admin parity is not proven at the load level. Duplicate the `(app)` test for the other two groups.
- [ ] [Review][Patch] **[HIGH] Inactivity-timeout → `bootstrapState='anonymous'` transition is not asserted** [healthcabinet/frontend/src/lib/stores/auth.svelte.test.ts:73-80,104-113] — The inactivity tests check `goto('/login')` but not the new bootstrap transition the diff introduces. Add `expect(authStore.bootstrapState).toBe('anonymous')`.
- [ ] [Review][Patch] **[HIGH] No test for "concurrent logout during restore" race guard** [healthcabinet/frontend/src/lib/stores/auth.svelte.ts:159 (post-await anonymous guard)] — The race guard at line 159 (`if bootstrapState === 'anonymous' return 'anonymous'`) has no test. Interleave: start `restoreSession()` with refresh held; call `logout()`; resolve refresh with a token; assert final state is `'anonymous'`. This is the security-sensitive path.
- [ ] [Review][Patch] **[MEDIUM] Concurrent-restore deduplication under refresh FAILURE is untested** [healthcabinet/frontend/src/lib/stores/auth.svelte.test.ts:197-223] — Mirror the success-path dedup test with `resolveRefresh(null)`, assert all three resolve to `'anonymous'` and one refresh call.
- [ ] [Review][Patch] **[MEDIUM] `reload flow` test never asserts `expect(goto).not.toHaveBeenCalled()`** [healthcabinet/frontend/src/lib/stores/auth.svelte.test.ts:266-284] — Advertised as the AC 4 scenario, but only checks state and user, not the "no redirect" claim.
- [ ] [Review][Patch] **[MEDIUM] Admin "does NOT run role enforcement during restore" test doesn't assert content is hidden** [healthcabinet/frontend/src/routes/(admin)/layout.test.ts:~569-579] — Add `expect(queryByTestId('admin-layout-child')).toBeNull()` to prove the `{#if}` gate is still tight.
- [ ] [Review][Patch] **[MEDIUM] Admin anonymous-redirect test doesn't assert `goto` fired exactly once** [healthcabinet/frontend/src/routes/(admin)/layout.test.ts:~539-547] — Two branches each call `goto('/login')`. Add `expect(goto).toHaveBeenCalledTimes(1)`.
- [ ] [Review][Patch] **[MEDIUM] Admin test misses "restoring + non-admin user already loaded" case** — Add test with `bootstrapState='restoring'` + `user={role:'user'}`, assert `goto not called`.
- [ ] [Review][Patch] **[MEDIUM] Short-circuit test doesn't verify `bootstrapState` stayed `'authenticated'`** [healthcabinet/frontend/src/lib/stores/auth.svelte.test.ts:225-235] — Add one-line assertion.
- [ ] [Review][Patch] **[MEDIUM] Anonymous-path test doesn't assert `authStore.user` was cleared/remained null** [healthcabinet/frontend/src/lib/stores/auth.svelte.test.ts:180-195] — Stale user could linger through a failed restore and cause a frame of user-chrome render before redirect.

### Defer (pre-existing or test-infra limitation)

- [x] [Review][Defer] **[LOW] Test beforeEach resets private singleton state via `as unknown as { … }` cast** [healthcabinet/frontend/src/lib/stores/auth.svelte.test.ts:~134-148] — deferred, test-infra tradeoff; cleaner refactor is `resetForTests()` method but not essential. Listed in deferred-work.md.
- [x] [Review][Defer] **[LOW] Layout tests mock `$lib/stores/auth.svelte` as plain object, not `$state`-backed** — deferred, Svelte reactivity in unit tests is a known gap across the project. End-state rendering is covered; transition reactivity is not.
- [x] [Review][Defer] **[LOW] `layout.load.test.ts` mocks authStore by shape, tolerating accidental coupling** — deferred.
- [x] [Review][Defer] **[LOW] Identity-after-resolution is not pinned (fresh promise after prior resolve)** — deferred.

### Dismissed as noise (4)

Pre-existing docstring drift; test harness warns about `HTMLCanvasElement.getContext()` (JSDOM limitation, unrelated); cosmetic comment nits; `me` import usage question already answered by existing code outside the diff.

## Review Findings (code review round 2, 2026-04-19)

Round 2 reviewed ONLY the Round 1 patch commits (`8c93456` + `7494e64`). Four layers ran. Auditor did NOT return `ROUND 2 CLEAN`. Three new HIGH findings introduced by the Round 1 patches.

### Patch (HIGH — new regression introduced by Round 1 fixes)

- [ ] [Review][Patch] **[HIGH] Interactive login deadlock after bootstrap='anonymous' in same tab** [healthcabinet/frontend/src/lib/stores/auth.svelte.ts:55-64 (setAccessToken guard) + :162-164 (restoreSession anonymous short-circuit) + login/+page.svelte:~23] — **Multiple reviewers flagged this independently.** Sequence: user hard-reloads a protected route → refresh cookie expired → `bootstrapState='anonymous'` → layout redirects to `/login` → user submits credentials → `authStore.setAccessToken(response.access_token)` runs with `bootstrapState='anonymous'` → the Round 1 anonymous-guard fires, calls `tokenState.clear()`, sets `user=null`, returns. Login appears to succeed at the network layer but the token is discarded; every layout-mount short-circuits to `'anonymous'`; the user is stuck on `/login` with no way out short of a hard reload. Same bug in the register flow. **Fix options (pick one): (a) login/register form actions set `authStore.bootstrapState = 'unknown'` immediately before calling `setAccessToken`; (b) guard fires only when there's an in-flight restore (`this.bootstrapState === 'anonymous' && this.restoreSessionPromise !== null`) — that's the specific race the guard was meant to catch; (c) add an explicit `authStore.login(token, user)` entrypoint that resets bootstrap first.** Option (b) is smallest and localizes the fix.

- [ ] [Review][Patch] **[HIGH] Admin layout renders indefinitely blank when `user=null` + `bootstrapState='authenticated'`** [healthcabinet/frontend/src/routes/(admin)/+layout.svelte:~22-30 (role effect) + :~33 (`{#if}` content gate)] — The Round 1 `authStore.user &&` gate correctly prevented the false redirect to `/login` on transient `/me()` 5xx failures, but the content `{#if bootstrapState === 'authenticated' && user?.role === 'admin'}` still requires `user` populated. When `me()` fails non-401 (5xx/network/abort), admin sees a permanent blank admin shell: no redirect, no content, no retry, no spinner. Fix: add a visible loading/retry state OR have `_doTryRefresh()` retry `me()` OR mark bootstrap `'anonymous'` after a `me()` failure timeout so the redirect fires.

- [ ] [Review][Patch] **[HIGH] `onForceLogout` callback leaks inactivity timer** [healthcabinet/frontend/src/lib/stores/auth.svelte.ts:~306-311] — The registered callback sets `authStore.user = null` + `bootstrapState = 'anonymous'` but does NOT call `stopInactivityTimer()`. If the inactivity timer was running when a mid-session 401 fires, the timer stays scheduled. When it eventually ticks (30 min later), it calls `clearAccessToken()` + `goto('/login')` against a user who may have logged back in. Could also redirect a freshly-logged-in session mid-use. Fix: callback should call `authStore.clearAccessToken()` (which stops timer) instead of just clearing user + bootstrap.

### Patch (MEDIUM)

- [ ] [Review][Patch] **[MEDIUM] `registerForceLogoutHandler` is overwrite-only — no multi-registration safety** [healthcabinet/frontend/src/lib/api/client.svelte.ts:~37-41] — A second `registerForceLogoutHandler(fn)` call silently replaces the first. HMR reloads in dev, or a future module registering a handler, will break the auth store's wiring without warning. Fix: throw if already registered, or accumulate handlers into an array.
- [ ] [Review][Patch] **[MEDIUM] `onForceLogout?.()` fires before `isRedirectingToLogin` latch** [healthcabinet/frontend/src/lib/api/client.svelte.ts:~111] — Callback flips `bootstrapState='anonymous'` which is a reactive write; any layout `$effect` observing it may synchronously trigger a new `apiFetch` before the redirect latch is set. Move the callback invocation AFTER `isRedirectingToLogin = true`.
- [ ] [Review][Patch] **[MEDIUM] `restoreSession()` catch block swallows errors silently** [healthcabinet/frontend/src/lib/stores/auth.svelte.ts:~182] — `catch {` without binding. Network outages / abort errors / programming errors all collapse to `'anonymous'` with no telemetry. Operators can't distinguish "user has no valid cookie" from "refresh endpoint 500s across all users". Fix: `catch (err) { console.warn('[auth] restoreSession failed', err); ... }`.
- [ ] [Review][Patch] **[MEDIUM] T3 (concurrent logout during restore) test doesn't actually reproduce the race** [healthcabinet/frontend/src/lib/stores/auth.svelte.test.ts:~154-179] — The mock `refreshToken` returns a string but nothing writes it to the mocked `tokenState`. In real code, `_doTryRefresh` writes via `setAccessToken`. The test passes trivially because no write ever happens. Fix: make the mock invoke `tokenState.setToken(resolvedValue)` before resolving, so the Round 1 anonymous-guard is actually exercised.
- [ ] [Review][Patch] **[MEDIUM] T3 doesn't assert `authStore.user === null` after logout race** [healthcabinet/frontend/src/lib/stores/auth.svelte.test.ts:~165-173] — `_doTryRefresh` continues past the guarded `setAccessToken` to call `me(false)` (default mock returns a valid user), so `this.setUser(userData)` silently re-populates `authStore.user` AFTER logout. Fix: add `expect(authStore.user).toBeNull()` after the promise resolves.
- [ ] [Review][Patch] **[MEDIUM] T4 concurrent-failure dedup test never triggers the catch block** [healthcabinet/frontend/src/lib/stores/auth.svelte.test.ts:~181-204] — `resolveRefresh(null)` exercises the `ok=false` branch, not the rejection/`catch` branch. The Round 1 rejection dedup contract is untested under concurrent callers. Add a variant with `mockRejectedValue` and three concurrent callers.
- [ ] [Review][Patch] **[MEDIUM] No test exists for the registerForceLogoutHandler callback actually firing and flipping state** — No integration/unit test asserts that a 401 with failed refresh invokes the registered callback AND that the callback flips `bootstrapState='anonymous'`. The stub `registerForceLogoutHandler: vi.fn()` in test mocks is never invoked. Add a client.svelte.ts test that registers a spy, simulates the 401 path, and asserts the spy was called + bootstrap flipped.
- [ ] [Review][Patch] **[MEDIUM] Anonymous short-circuit doesn't cover "3 layouts mount simultaneously" pattern** [healthcabinet/frontend/src/lib/stores/auth.svelte.test.ts:~383-395] — Test only calls `restoreSession()` once. The real scenario is three concurrent calls. Verify all three short-circuit with zero refresh calls.

### Defer (pre-existing / non-critical)

- [x] [Review][Defer] **[LOW] `typeof registerForceLogoutHandler === 'function'` guard in production code is an anti-pattern** — It silently no-ops if the export is accidentally removed in a refactor. Acceptable tradeoff today for test ergonomics; revisit if we see production silence on 401 force-logout paths.
- [x] [Review][Defer] **[LOW] Tests write `bootstrapState` directly (bypass encapsulation)** — Same reset-for-test concern as Round 1. Cleaner `resetForTest()` would reduce brittleness.
- [x] [Review][Defer] **[LOW] Layout tests don't cover state *transitions*, only end states** — Already acknowledged in Round 1 deferred-work; plain-object mock limitation, not a new issue.
- [x] [Review][Defer] **[LOW] Admin test doesn't assert `toHaveBeenCalledTimes(1)` on the non-admin role path** — Round 1 already added it on the anonymous path.

### Dismissed as noise (3)

Cross-module callback "scope fence" concern (reasonable tradeoff, not a spec violation); `doc_id_uuid` caching comment nits; stylistic concerns about test mocks shape.
