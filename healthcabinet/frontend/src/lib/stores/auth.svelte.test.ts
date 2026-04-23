/**
 * Unit tests for AuthStore inactivity timer (AC #3) and bootstrap
 * session-restore state machine (Story 15.1, AC 1/2/5/7).
 */

import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$lib/api/auth', () => ({
	logout: vi.fn().mockResolvedValue(undefined),
	me: vi.fn().mockResolvedValue({ id: '1', email: 'user@example.com', role: 'user', tier: 'free' })
}));

// Captured at module load by the mocked registerForceLogoutHandler below so
// tests in the "force-logout wiring" suite can invoke the registered callback
// directly and verify its side-effects (inactivity-timer teardown, etc.).
// Must be declared via vi.hoisted() so the reference is live when the mock
// factory runs above the import of auth.svelte (hoisted to the top of the
// module by Vitest).
const forceLogoutCapture = vi.hoisted(() => ({ fn: null as (() => void) | null }));

vi.mock('$lib/api/client.svelte', () => ({
	API_BASE: 'http://localhost:8000',
	tokenState: {
		accessToken: null as string | null,
		setToken(t: string | null) {
			this.accessToken = t;
		},
		clear() {
			this.accessToken = null;
		}
	},
	refreshToken: vi.fn(),
	// auth.svelte.ts registers a force-logout callback at module init via this
	// inverse-dependency hook. Capture the callback reference so the
	// force-logout test can invoke it directly and assert its side-effects
	// (inactivity timer must be stopped, listeners removed). The broader
	// runtime wiring is covered by its own integration tests.
	registerForceLogoutHandler: vi.fn((fn: () => void) => {
		forceLogoutCapture.fn = fn;
	})
}));

import { goto } from '$app/navigation';
import { logout as apiLogout, me } from '$lib/api/auth';
import { refreshToken, tokenState } from '$lib/api/client.svelte';
import { authStore, type BootstrapState } from './auth.svelte';

const mockRefreshToken = vi.mocked(refreshToken);
const mockMe = vi.mocked(me);

const THIRTY_MINUTES_MS = 30 * 60 * 1000;

describe('AuthStore inactivity timer', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		vi.clearAllMocks();
		// Ensure clean state between tests. setAccessToken() now guards against
		// overriding 'anonymous', so reset bootstrapState to 'unknown' to let the
		// inactivity suite drive the normal login -> authenticated transition.
		authStore.clearAccessToken();
		authStore.bootstrapState = 'unknown';
	});

	afterEach(() => {
		authStore.clearAccessToken();
		authStore.bootstrapState = 'unknown';
		vi.useRealTimers();
	});

	test('registers mousemove, keydown and click listeners when token is set', () => {
		const addSpy = vi.spyOn(window, 'addEventListener');
		authStore.setAccessToken('tok');

		const events = addSpy.mock.calls.map((c) => c[0]);
		expect(events).toContain('mousemove');
		expect(events).toContain('keydown');
		expect(events).toContain('click');
	});

	test('removes event listeners when token is cleared', () => {
		authStore.setAccessToken('tok');
		const removeSpy = vi.spyOn(window, 'removeEventListener');
		authStore.clearAccessToken();

		const events = removeSpy.mock.calls.map((c) => c[0]);
		expect(events).toContain('mousemove');
		expect(events).toContain('keydown');
		expect(events).toContain('click');
	});

	test('calls apiLogout and goto("/login") after 30 minutes of inactivity', async () => {
		authStore.setAccessToken('tok');

		await vi.advanceTimersByTimeAsync(THIRTY_MINUTES_MS);

		expect(apiLogout).toHaveBeenCalledTimes(1);
		expect(goto).toHaveBeenCalledWith('/login');
		// Story 15.1: inactivity timeout is a definitive anonymous resolution so
		// subsequent layout guards can redirect without re-running restore.
		expect(authStore.bootstrapState).toBe('anonymous');
	});

	test('does not trigger timeout before 30 minutes elapse', async () => {
		authStore.setAccessToken('tok');

		await vi.advanceTimersByTimeAsync(THIRTY_MINUTES_MS - 1);

		expect(goto).not.toHaveBeenCalled();
	});

	test('resets timeout on mousemove — 30 min window restarts from activity', async () => {
		authStore.setAccessToken('tok');

		// Advance 25 minutes, then simulate user activity
		await vi.advanceTimersByTimeAsync(25 * 60 * 1000);
		window.dispatchEvent(new Event('mousemove'));

		// 10 more minutes (35 min total, but only 10 min since last activity)
		await vi.advanceTimersByTimeAsync(10 * 60 * 1000);

		// Timeout should NOT have fired — only 10 min since last activity
		expect(goto).not.toHaveBeenCalled();
	});

	test('fires after 30 minutes from last activity', async () => {
		authStore.setAccessToken('tok');

		// Advance 25 minutes, simulate activity, then advance 30 more
		await vi.advanceTimersByTimeAsync(25 * 60 * 1000);
		window.dispatchEvent(new Event('keydown'));
		await vi.advanceTimersByTimeAsync(THIRTY_MINUTES_MS);

		expect(goto).toHaveBeenCalledWith('/login');
	});
});

/**
 * Story 15.1: Auth Bootstrap Restore Guard.
 *
 * Verifies the `bootstrapState` state machine and the public
 * `restoreSession()` entrypoint. Covers AC 1 (explicit bootstrap state),
 * AC 2 (centralized restore), AC 5 (definitive anonymous resolution), and
 * AC 7 (concurrent-call deduplication and state-transition coverage).
 */
describe('AuthStore bootstrap / restoreSession', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		// Reset auth state back to a pristine post-construction shape. We do
		// this explicitly rather than re-instantiating the store because the
		// module exports a singleton.
		authStore.clearAccessToken();
		authStore.setUser(null);
		authStore.bootstrapState = 'unknown';
		tokenState.accessToken = null;
		// Reset the private singleton promise fields. A failed test in this
		// suite can leave `restoreSessionPromise` or `tryRefreshPromise`
		// pending, which would make every subsequent test await a stuck
		// promise and time out. This cast is idiomatic for clearing private
		// state on a module-level singleton during tests.
		(authStore as unknown as { restoreSessionPromise: Promise<BootstrapState> | null }).restoreSessionPromise = null;
		(authStore as unknown as { tryRefreshPromise: Promise<boolean> | null }).tryRefreshPromise = null;
		mockMe.mockResolvedValue({ id: '1', email: 'user@example.com', role: 'user', tier: 'free' });
	});

	afterEach(() => {
		authStore.clearAccessToken();
		authStore.setUser(null);
		authStore.bootstrapState = 'unknown';
		(authStore as unknown as { restoreSessionPromise: Promise<BootstrapState> | null }).restoreSessionPromise = null;
		(authStore as unknown as { tryRefreshPromise: Promise<boolean> | null }).tryRefreshPromise = null;
	});

	test('starts in "unknown" before any restore attempt', () => {
		expect(authStore.bootstrapState).toBe('unknown');
	});

	test('unknown -> restoring -> authenticated on successful refresh', async () => {
		// Hold refresh open so we can observe the intermediate 'restoring'
		// state before resolution.
		let resolveRefresh: (value: string | null) => void = () => {};
		mockRefreshToken.mockImplementation(
			() => new Promise<string | null>((resolve) => { resolveRefresh = resolve; })
		);

		const restorePromise = authStore.restoreSession();

		// Synchronously observable: bootstrap flipped to 'restoring' before
		// awaiting the refresh. If this assertion fails, layouts would have
		// a frame where bootstrap is still 'unknown' while refresh is
		// in-flight, and the state machine contract is broken.
		expect(authStore.bootstrapState).toBe('restoring');

		resolveRefresh('new-access-token');
		const result = await restorePromise;

		expect(result).toBe('authenticated');
		expect(authStore.bootstrapState).toBe('authenticated');
		expect(tokenState.accessToken).toBe('new-access-token');
	});

	test('unknown -> restoring -> anonymous when refresh cookie is expired/missing', async () => {
		let resolveRefresh: (value: string | null) => void = () => {};
		mockRefreshToken.mockImplementation(
			() => new Promise<string | null>((resolve) => { resolveRefresh = resolve; })
		);

		const restorePromise = authStore.restoreSession();
		expect(authStore.bootstrapState).toBe('restoring');

		resolveRefresh(null);
		const result = await restorePromise;

		expect(result).toBe('anonymous');
		expect(authStore.bootstrapState).toBe('anonymous');
		expect(tokenState.accessToken).toBeNull();
		// Anonymous resolution leaves no authenticated-user artifacts behind.
		expect(authStore.user).toBeNull();
	});

	test('concurrent restoreSession() calls are deduplicated into a single in-flight promise', async () => {
		let resolveRefresh: (value: string | null) => void = () => {};
		mockRefreshToken.mockImplementation(
			() => new Promise<string | null>((resolve) => { resolveRefresh = resolve; })
		);

		// Simulate `(app)`, `(admin)`, and `(onboarding)` layouts all calling
		// restoreSession() on the same cold page load.
		const p1 = authStore.restoreSession();
		const p2 = authStore.restoreSession();
		const p3 = authStore.restoreSession();

		// Identity equality proves there is only one in-flight promise. This
		// is stricter than "eventually resolve to the same value" — it
		// guarantees no duplicate POST /auth/refresh was started.
		expect(p1).toBe(p2);
		expect(p2).toBe(p3);

		resolveRefresh('tok');
		const [r1, r2, r3] = await Promise.all([p1, p2, p3]);

		expect(r1).toBe('authenticated');
		expect(r2).toBe('authenticated');
		expect(r3).toBe('authenticated');
		// Single refresh call for three concurrent restore requests.
		expect(mockRefreshToken).toHaveBeenCalledTimes(1);
	});

	test('short-circuits when already authenticated — no refresh call issued', async () => {
		mockRefreshToken.mockResolvedValue('first-token');
		await authStore.restoreSession();
		expect(authStore.bootstrapState).toBe('authenticated');
		mockRefreshToken.mockClear();

		const result = await authStore.restoreSession();

		expect(result).toBe('authenticated');
		expect(mockRefreshToken).not.toHaveBeenCalled();
		// Short-circuit path must not disturb the already-authenticated state.
		expect(authStore.bootstrapState).toBe('authenticated');
	});

	test('re-runs restore when token was cleared out-of-band (stale authenticated)', async () => {
		// Simulate mid-session 401 path: client.svelte.ts calls tokenState.clear()
		// without going through the auth store, leaving bootstrapState stale.
		mockRefreshToken.mockResolvedValueOnce('tok-1');
		await authStore.restoreSession();
		expect(authStore.bootstrapState).toBe('authenticated');

		// Out-of-band clear.
		tokenState.accessToken = null;

		// Next restoreSession must not short-circuit; it has to re-run the
		// transition because the in-memory token is gone.
		mockRefreshToken.mockResolvedValueOnce(null);
		const result = await authStore.restoreSession();
		expect(result).toBe('anonymous');
		expect(authStore.bootstrapState).toBe('anonymous');
	});

	test('logout() flips bootstrap to "anonymous" so layout guard redirects', async () => {
		mockRefreshToken.mockResolvedValue('tok');
		await authStore.restoreSession();
		expect(authStore.bootstrapState).toBe('authenticated');

		await authStore.logout();

		expect(authStore.bootstrapState).toBe('anonymous');
		expect(tokenState.accessToken).toBeNull();
	});

	test('reload flow: restoreSession() keeps user on protected route when refresh succeeds', async () => {
		// Simulate the AC 4 scenario end-to-end: cold page load, no in-memory
		// token, refresh cookie is valid. Nothing should redirect.
		tokenState.accessToken = null;
		authStore.bootstrapState = 'unknown';
		mockRefreshToken.mockResolvedValue('restored-token');

		const state = await authStore.restoreSession();

		expect(state).toBe('authenticated');
		expect(authStore.bootstrapState).toBe('authenticated');
		// User profile was populated from /me so the app shell has data.
		expect(authStore.user).toEqual({
			id: '1',
			email: 'user@example.com',
			role: 'user',
			tier: 'free'
		});
		// The whole point of Story 15.1 — a successful restore must not redirect
		// to /login. The store itself never calls goto() on the success path;
		// this assertion documents that invariant.
		expect(goto).not.toHaveBeenCalled();
	});

	test('setAccessToken flips bootstrapState to "authenticated" (interactive login path)', () => {
		authStore.bootstrapState = 'unknown';
		authStore.setAccessToken('tok');
		expect(authStore.bootstrapState).toBe('authenticated');
	});

	test('setAccessToken discards token when bootstrapState is "anonymous" AND a restore is in-flight (logout/inactivity race)', () => {
		authStore.bootstrapState = 'anonymous';
		// The race-guard path is only active while a restore is in-flight —
		// that's the only scenario where a stale refresh can deliver a token
		// AFTER a definitive anonymous resolution. Simulate that pending-restore
		// state so this test exercises the guard branch (not the T-A1 path).
		(authStore as unknown as {
			restoreSessionPromise: Promise<BootstrapState> | null;
		}).restoreSessionPromise = Promise.resolve('anonymous' as BootstrapState);

		authStore.setAccessToken('leaked-from-in-flight-refresh');

		expect(authStore.bootstrapState).toBe('anonymous');
		expect(tokenState.accessToken).toBeNull();
	});

	// T-A1 (Round-2 regression guard): the Round-1 patch unconditionally
	// discarded the token whenever bootstrapState was 'anonymous'. That broke
	// the fresh-login-after-logout path — logout leaves bootstrapState at
	// 'anonymous' with no in-flight restore, and the subsequent interactive
	// login calls setAccessToken() from a clean, non-race context. Round-2
	// narrows the guard to only fire when there is an in-flight restore
	// promise. This test pins that behavior.
	test('setAccessToken succeeds when bootstrapState="anonymous" but no in-flight restore (fresh login after logout)', () => {
		authStore.bootstrapState = 'anonymous';
		// No restoreSessionPromise — the interactive-login code path is
		// synchronous wrt the store (login form POSTs, receives the token,
		// calls setAccessToken()). There is no concurrent refresh in flight.
		(authStore as unknown as {
			restoreSessionPromise: Promise<BootstrapState> | null;
		}).restoreSessionPromise = null;

		authStore.setAccessToken('fresh-login-token');

		expect(tokenState.accessToken).toBe('fresh-login-token');
		expect(authStore.bootstrapState).toBe('authenticated');
	});

	// T-A2: mirror of the updated race test, stated from the "still rejected"
	// angle for symmetry with T-A1. An in-flight restore + anonymous bootstrap
	// is the only combination that still trips the guard.
	test('setAccessToken still discards a stale token when bootstrapState="anonymous" AND a restore was in-flight', () => {
		authStore.bootstrapState = 'anonymous';
		(authStore as unknown as {
			restoreSessionPromise: Promise<BootstrapState> | null;
		}).restoreSessionPromise = Promise.resolve('anonymous' as BootstrapState);

		authStore.setAccessToken('stale-refresh-token');

		expect(authStore.bootstrapState).toBe('anonymous');
		expect(tokenState.accessToken).toBeNull();
	});

	test('concurrent logout() during in-flight refresh stays "anonymous" after refresh resolves with a token', async () => {
		// Race scenario: a hard reload kicks off restoreSession() → tryRefresh()
		// while the user clicks Logout in a second tab or the inactivity timer
		// fires mid-flight. The in-flight refresh MUST NOT silently
		// re-authenticate after the anonymous signal is definitive.
		let resolveRefresh: (value: string | null) => void = () => {};
		mockRefreshToken.mockImplementation(
			() => new Promise<string | null>((resolve) => { resolveRefresh = resolve; })
		);

		const restorePromise = authStore.restoreSession();
		expect(authStore.bootstrapState).toBe('restoring');

		// Definitive anonymous signal lands BEFORE the refresh resolves.
		await authStore.logout();
		expect(authStore.bootstrapState).toBe('anonymous');

		// Now the stale refresh comes back with a token — the setAccessToken
		// guard must reject it.
		resolveRefresh('stale-token');
		const result = await restorePromise;

		expect(result).toBe('anonymous');
		expect(authStore.bootstrapState).toBe('anonymous');
		expect(tokenState.accessToken).toBeNull();
	});

	test('concurrent restoreSession() calls are deduplicated under refresh FAILURE (single call, all resolve anonymous)', async () => {
		// Mirror the success-path dedup test for the failure path — the
		// singleton contract must hold regardless of the refresh outcome.
		let resolveRefresh: (value: string | null) => void = () => {};
		mockRefreshToken.mockImplementation(
			() => new Promise<string | null>((resolve) => { resolveRefresh = resolve; })
		);

		const p1 = authStore.restoreSession();
		const p2 = authStore.restoreSession();
		const p3 = authStore.restoreSession();

		// Identity equality — single in-flight promise across three callers.
		expect(p1).toBe(p2);
		expect(p2).toBe(p3);

		resolveRefresh(null);
		const [r1, r2, r3] = await Promise.all([p1, p2, p3]);

		expect(r1).toBe('anonymous');
		expect(r2).toBe('anonymous');
		expect(r3).toBe('anonymous');
		expect(mockRefreshToken).toHaveBeenCalledTimes(1);
	});

	test('restoreSession resolves to "anonymous" when tryRefresh rejects (no stuck "restoring")', async () => {
		// Network failures, AbortError, or any other rejection from the refresh
		// pipeline must not leave bootstrap stuck at 'restoring' — otherwise the
		// layout's {#if bootstrapState === 'authenticated'} gate never renders
		// and the anonymous-redirect $effect never fires: permanent blank page.
		mockRefreshToken.mockRejectedValue(new Error('network down'));

		const result = await authStore.restoreSession();

		expect(result).toBe('anonymous');
		expect(authStore.bootstrapState).toBe('anonymous');
	});

	test('restoreSession short-circuits when bootstrapState is "anonymous" (no re-attack on /auth/refresh)', async () => {
		// After a definitive anonymous resolution, every subsequent layout mount
		// must reuse the cached result instead of re-issuing POST /auth/refresh.
		// Three protected route groups mounting on one navigation would
		// otherwise produce three refresh calls.
		authStore.bootstrapState = 'anonymous';
		mockRefreshToken.mockClear();

		const result = await authStore.restoreSession();

		expect(result).toBe('anonymous');
		expect(mockRefreshToken).not.toHaveBeenCalled();
	});
});

/**
 * Story 15.1 Round-2: force-logout callback wiring.
 *
 * The callback registered at module init (via registerForceLogoutHandler)
 * must not only flip bootstrapState to 'anonymous' — it must also cancel the
 * pending inactivity setTimeout and remove the mousemove/keydown/click
 * listeners. Otherwise the timer keeps ticking against a user who logs back
 * in, and fires a spurious logout redirect later. This suite captures the
 * registered callback (see forceLogoutCapture) and exercises it directly.
 */
describe('AuthStore force-logout callback wiring', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		vi.clearAllMocks();
		authStore.clearAccessToken();
		authStore.setUser(null);
		authStore.bootstrapState = 'unknown';
		tokenState.accessToken = null;
	});

	afterEach(() => {
		authStore.clearAccessToken();
		authStore.setUser(null);
		authStore.bootstrapState = 'unknown';
		vi.useRealTimers();
	});

	test('force-logout callback is registered at module load', () => {
		// Sanity check — without a captured callback the rest of the suite
		// cannot pin the Round-2 fix.
		expect(forceLogoutCapture.fn).not.toBeNull();
	});

	test('registered force-logout callback stops the inactivity timer (removes listeners)', () => {
		// Start the timer + listeners via the normal login path.
		authStore.setAccessToken('tok');
		expect(tokenState.accessToken).toBe('tok');
		expect(authStore.bootstrapState).toBe('authenticated');

		// Capture which events get unregistered when the callback fires.
		const removeSpy = vi.spyOn(window, 'removeEventListener');

		// Invoke the callback exactly as client.svelte.ts would on a
		// definitive mid-session 401.
		forceLogoutCapture.fn?.();

		const removedEvents = removeSpy.mock.calls.map((c) => c[0]);
		// The core Round-2 assertion: all three inactivity-activity listeners
		// must be torn down so a later session's activity doesn't feed a
		// stale timer.
		expect(removedEvents).toContain('mousemove');
		expect(removedEvents).toContain('keydown');
		expect(removedEvents).toContain('click');

		// And the broader state invariants the callback promises:
		expect(authStore.user).toBeNull();
		expect(authStore.bootstrapState).toBe('anonymous');
		expect(tokenState.accessToken).toBeNull();
	});

	test('force-logout callback cancels the pending inactivity setTimeout', async () => {
		// Concrete leak scenario: setAccessToken schedules a 30-min timeout
		// that calls goto('/login') on fire. If force-logout does not cancel
		// the setTimeout, advancing 30 minutes would fire that callback even
		// though we are already logged out. The Round-2 fix routes through
		// clearAccessToken() which calls stopInactivityTimer(), cancelling
		// the pending setTimeout.
		authStore.setAccessToken('tok-1');

		// Force-logout lands mid-session.
		forceLogoutCapture.fn?.();
		expect(authStore.bootstrapState).toBe('anonymous');

		// Advance 30 minutes — if the original timer had leaked, the stale
		// inactivity callback would fire goto('/login') here. With the fix
		// the timer is cancelled, so nothing happens.
		await vi.advanceTimersByTimeAsync(THIRTY_MINUTES_MS);
		expect(goto).not.toHaveBeenCalled();
	});
});
