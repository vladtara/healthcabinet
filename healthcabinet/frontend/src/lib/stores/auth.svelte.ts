/**
 * Auth state using Svelte 5 runes.
 * Access token stored in memory only — never localStorage or sessionStorage.
 * Inactivity timer: 30-min timeout clears session and redirects to /login.
 *
 * Bootstrap state (Story 15.1):
 * - 'unknown'       — no restore attempt has run yet
 * - 'restoring'     — a refresh-cookie-based restore is in-flight
 * - 'authenticated' — restore (or interactive login) produced an access token
 * - 'anonymous'     — restore has definitively failed; no session available
 *
 * Protected route layouts gate redirects on this state so a hard reload does
 * not redirect to /login while the refresh round-trip is still in flight.
 */

import { goto } from '$app/navigation';
import { tokenState, refreshToken, registerForceLogoutHandler } from '$lib/api/client.svelte';
import { logout as apiLogout, me } from '$lib/api/auth';

export interface User {
	id: string;
	email: string;
	role: 'user' | 'admin';
	tier: 'free' | 'paid';
}

export type BootstrapState = 'unknown' | 'restoring' | 'authenticated' | 'anonymous';

const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes

class AuthStore {
	user = $state<User | null>(null);
	isAuthenticated = $derived(tokenState.accessToken !== null);
	// Explicit bootstrap/session-restore state. Source of truth for startup
	// behavior — layouts must consult this before redirecting to /login so
	// they do not fire while refresh is still in-flight (Story 15.1, AC 1/3).
	bootstrapState = $state<BootstrapState>('unknown');

	private inactivityTimer: ReturnType<typeof setTimeout> | null = null;
	private boundResetTimer: (() => void) | null = null;
	// Deduplication guard: SvelteKit parallel route loading can call tryRefresh()
	// simultaneously. Without this singleton, concurrent calls each hit POST /auth/refresh;
	// once token rotation is added the 2nd call's cookie would be invalidated by the 1st,
	// forcing logout mid-session. The singleton ensures only one refresh is in-flight.
	private tryRefreshPromise: Promise<boolean> | null = null;
	// Singleton for the bootstrap restore flow. Deduplicates concurrent startup
	// calls so `(app)`, `(admin)`, and `(onboarding)` layouts can all await the
	// same in-flight restore without triggering independent refresh calls.
	private restoreSessionPromise: Promise<BootstrapState> | null = null;

	setUser(user: User | null) {
		this.user = user;
	}

	setAccessToken(token: string) {
		if (this.bootstrapState === 'anonymous' && this.restoreSessionPromise !== null) {
			// Race: an in-flight refresh resolved AFTER logout() or the
			// inactivity timeout definitively set bootstrap to 'anonymous'.
			// Honor the explicit anonymous signal and discard the stale token —
			// re-authenticating silently would defeat logout/inactivity.
			//
			// We scope this guard to the in-flight-restore window
			// (restoreSessionPromise !== null). A fresh interactive login
			// submitted AFTER a prior logout has bootstrapState='anonymous'
			// but no in-flight restore — that path must be allowed through,
			// otherwise the login form silently discards the new token and
			// the user is stuck in a login-loop deadlock.
			tokenState.clear();
			this.user = null;
			return;
		}
		tokenState.setToken(token);
		// An interactive login resolves bootstrap the same way a successful
		// restore does — subsequent layout mounts can trust this state directly
		// instead of waiting for an explicit restore attempt.
		this.bootstrapState = 'authenticated';
		this.startInactivityTimer();
	}

	clearAccessToken() {
		tokenState.clear();
		this.stopInactivityTimer();
	}

	getAccessToken(): string | null {
		return tokenState.accessToken;
	}

	/**
	 * Call the logout API to clear the httpOnly refresh cookie, then clear in-memory state.
	 * Must call the API — clearing only in-memory state leaves the 30-day cookie alive,
	 * allowing silent re-authentication on the next request (violates AC #3).
	 * Uses apiLogout() from auth.ts so it goes through apiFetch (RFC 7807 error handling,
	 * centralized API_BASE) instead of a raw fetch call that would duplicate the endpoint path.
	 */
	async logout() {
		// Clear local state immediately so isAuthenticated becomes false before any async work.
		// The online listener checks isAuthenticated to avoid calling apiLogout() against a
		// new session if the user logs back in while the device is offline.
		this.user = null;
		this.clearAccessToken();
		// Logout is a definitive anonymous resolution — subsequent guard effects
		// should redirect to /login without running another restore attempt.
		this.bootstrapState = 'anonymous';
		if (typeof window !== 'undefined') {
			if (navigator.onLine) {
				try {
					await apiLogout();
				} catch {
					// Best-effort — cookie may already be expired or server unreachable
				}
			} else {
				// Queue cookie clear for when connectivity restores, but only if the user
				// hasn't started a new session by then (isAuthenticated would be true again).
				window.addEventListener(
					'online',
					() => {
						if (!this.isAuthenticated) {
							apiLogout().catch(console.error);
						}
					},
					{ once: true }
				);
			}
		}
	}

	/**
	 * Attempt a silent token refresh using the httpOnly refresh cookie.
	 * Called on page load to restore sessions after browser refresh without
	 * requiring the user to log in again (AC #1: "across browser sessions").
	 * Deduplicates concurrent calls so only one POST /auth/refresh is in-flight at a time.
	 */
	async tryRefresh(): Promise<boolean> {
		if (this.tryRefreshPromise) return this.tryRefreshPromise;
		this.tryRefreshPromise = this._doTryRefresh();
		try {
			return await this.tryRefreshPromise;
		} finally {
			this.tryRefreshPromise = null;
		}
	}

	/**
	 * Single bootstrap entrypoint for protected route groups (Story 15.1).
	 *
	 * Transitions:
	 *   unknown -> restoring -> authenticated (refresh cookie valid)
	 *   unknown -> restoring -> anonymous     (no/expired refresh cookie)
	 *
	 * - Short-circuits if already `authenticated` (interactive login already
	 *   populated state, no refresh round-trip needed).
	 * - Deduplicates concurrent startup calls so `(app)`, `(admin)`, and
	 *   `(onboarding)` layouts share one in-flight restore promise and one
	 *   resolution.
	 * - Wraps the existing `tryRefresh()` deduplication primitive — no new
	 *   refresh call is introduced.
	 */
	restoreSession(): Promise<BootstrapState> {
		// Short-circuit only when bootstrap state is still coherent with the
		// in-memory token. If the token was cleared out-of-band (e.g.,
		// client.svelte.ts force-logout on a definitive 401), the bootstrap
		// state may be stale; fall through and re-run the restore transition.
		if (this.bootstrapState === 'authenticated' && tokenState.accessToken !== null) {
			return Promise.resolve('authenticated');
		}
		// Short-circuit on a prior definitive anonymous resolution so repeated
		// layout mounts (three protected route groups on a single navigation)
		// do not each re-hit POST /auth/refresh. To re-run restore after this,
		// a code path must explicitly flip bootstrap back to 'unknown' — the
		// interactive login flow handles that implicitly via setAccessToken()
		// transitioning to 'authenticated'.
		if (this.bootstrapState === 'anonymous') {
			return Promise.resolve('anonymous');
		}
		// Singleton in-flight promise — concurrent callers get the SAME promise
		// reference (identity equality), guaranteeing only one refresh round-trip.
		// This method is intentionally NOT declared `async` so the cached promise
		// can be returned directly; `async` would wrap each return in a new
		// Promise, breaking identity.
		if (this.restoreSessionPromise) return this.restoreSessionPromise;

		// unknown -> restoring. Set synchronously so any layout that mounts on
		// the same tick sees 'restoring' and does not redirect to /login.
		this.bootstrapState = 'restoring';

		this.restoreSessionPromise = (async (): Promise<BootstrapState> => {
			try {
				const ok = await this.tryRefresh();
				// Re-check after await: a concurrent logout() may have flipped
				// bootstrap to 'anonymous' while the refresh was in-flight.
				// Respect that definitive signal rather than overriding it.
				if (this.bootstrapState === 'anonymous') return 'anonymous';
				this.bootstrapState = ok ? 'authenticated' : 'anonymous';
				return this.bootstrapState;
			} catch {
				// An unexpected rejection from the refresh pipeline (network failure,
				// abort, etc.) is treated as a definitive anonymous resolution so
				// protected layouts can redirect to /login instead of rendering a
				// permanent blank screen on a stuck 'restoring' state.
				if (this.bootstrapState !== 'anonymous') {
					this.bootstrapState = 'anonymous';
				}
				return 'anonymous';
			} finally {
				this.restoreSessionPromise = null;
			}
		})();

		return this.restoreSessionPromise;
	}

	private async _doTryRefresh(): Promise<boolean> {
		if (typeof window === 'undefined') return false;
		// Route through the shared refreshToken singleton in client.svelte.ts so that
		// tryRefresh() and apiFetch()'s 401 handler share a single deduplication primitive.
		// Without this, both paths independently call POST /auth/refresh on cold page load,
		// which will silently break once refresh token rotation is introduced.
		const newToken = await refreshToken();
		if (!newToken) return false;
		this.setAccessToken(newToken);
		// Populate user profile so (app)/ components have email/role/tier available
		// immediately after session restore — without this, authStore.user is null
		// even though isAuthenticated is true, causing blank user data in the UI.
		// me() is intentionally called here (session restore) AND in +page.svelte
		// (after login). These are separate code paths and both calls are safe.
		// retry=false: we just refreshed — if /me returns 401 the token is invalid
		// and we should clear state rather than triggering a second refresh loop.
		try {
			const userData = await me(false);
			this.setUser(userData);
		} catch (e: unknown) {
			const err = e as { status?: number };
			if (err?.status === 401) {
				// The fresh access token was rejected — clear auth state fully so
				// isAuthenticated becomes false and the guard redirects to /login.
				this.clearAccessToken();
				this.user = null;
				return false;
			}
			// Other errors (network, 5xx): stay authenticated, profile data unavailable
		}
		return true;
	}

	private startInactivityTimer() {
		this.stopInactivityTimer();
		if (typeof window === 'undefined') return;

		this.boundResetTimer = () => this.resetInactivityTimer();
		window.addEventListener('mousemove', this.boundResetTimer);
		window.addEventListener('keydown', this.boundResetTimer);
		window.addEventListener('click', this.boundResetTimer);

		this.scheduleTimeout();
	}

	private stopInactivityTimer() {
		if (this.inactivityTimer) {
			clearTimeout(this.inactivityTimer);
			this.inactivityTimer = null;
		}
		if (this.boundResetTimer && typeof window !== 'undefined') {
			window.removeEventListener('mousemove', this.boundResetTimer);
			window.removeEventListener('keydown', this.boundResetTimer);
			window.removeEventListener('click', this.boundResetTimer);
			this.boundResetTimer = null;
		}
	}

	private scheduleTimeout() {
		if (this.inactivityTimer) clearTimeout(this.inactivityTimer);
		this.inactivityTimer = setTimeout(() => {
			// Clear in-memory token immediately — user is timed out regardless of network.
			this.user = null;
			this.clearAccessToken();
			// Inactivity logout is a definitive anonymous resolution — route guards
			// should redirect to /login rather than trigger another restore attempt.
			this.bootstrapState = 'anonymous';
			// Clear the httpOnly refresh cookie server-side.
			// If offline, queue the API call for when connectivity restores so the cookie
			// is eventually cleared (prevents silent re-authentication on next online load).
			const clearCookie = () => {
				apiLogout().catch(console.error);
			};
			if (typeof window !== 'undefined') {
				if (navigator.onLine) {
					clearCookie();
				} else {
					// Guard against calling apiLogout() against a new session: only clear
					// the cookie if the user hasn't logged back in while offline.
					window.addEventListener(
						'online',
						() => {
							if (!this.isAuthenticated) {
								clearCookie();
							}
						},
						{ once: true }
					);
				}
				goto('/login')?.catch(console.error);
			}
		}, INACTIVITY_TIMEOUT_MS);
	}

	private resetInactivityTimer() {
		this.scheduleTimeout();
	}
}

export const authStore = new AuthStore();

// Register the force-logout handler once at module init. Invoked by client.svelte.ts
// whenever a definitive 401 is received and the refresh cookie is also invalid —
// bootstrapState flips to 'anonymous' in lockstep with tokenState.clear() so layout
// guards see a consistent view regardless of whether the redirect navigation lands.
// Optional-chained because older unit tests that mock `$lib/api/client.svelte` may
// not stub this export; those tests exercise other surfaces and the runtime wiring
// is covered by its own tests.
if (typeof registerForceLogoutHandler === 'function') {
	registerForceLogoutHandler(() => {
		// Also stops the inactivity timer + removes its activity listeners
		// via clearAccessToken's internal side-effect. tokenState.clear() was
		// already called by the caller in client.svelte.ts, so the token-clear
		// part is idempotent — the real purpose here is to cancel the pending
		// setTimeout and remove the mousemove/keydown/click listeners so they
		// don't fire against a re-authenticated session later (timer leak).
		authStore.clearAccessToken();
		authStore.user = null;
		authStore.bootstrapState = 'anonymous';
	});
}
