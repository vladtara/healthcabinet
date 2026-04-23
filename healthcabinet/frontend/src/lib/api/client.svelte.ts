/**
 * Base API client with auth headers, RFC 7807 error parsing, and token refresh.
 * Access token stored in $state rune — never in localStorage.
 *
 * PUBLIC_API_URL is read at runtime via $env/dynamic/public so that Docker
 * runtime env vars (set in docker-compose) take effect without a rebuild.
 */
import { goto } from '$app/navigation';
import { env } from '$env/dynamic/public';

export const API_BASE = env.PUBLIC_API_URL ?? 'http://localhost:8000';

export interface ApiError {
	type: string;
	title: string;
	status: number;
	detail?: string | Array<Record<string, unknown>>;
	instance?: string;
}

class AuthState {
	accessToken = $state<string | null>(null);

	setToken(token: string | null) {
		this.accessToken = token;
	}

	clear() {
		this.accessToken = null;
	}
}

export const tokenState = new AuthState();

// Guard against multiple concurrent 401s each independently calling goto('/login').
// Without this, N in-flight requests that all fail refresh each call goto() separately.
// SvelteKit deduplicates navigation so no loop occurs, but it's redundant and can
// interfere with transition state.
let isRedirectingToLogin = false;

// Force-logout callback registered by the auth store at module init. client.svelte.ts
// cannot import from auth.svelte.ts (auth.svelte.ts already imports from this module),
// so we invert the dependency: the auth store registers a callback that flips
// bootstrapState to 'anonymous' and clears user. This keeps bootstrapState consistent
// when a definitive 401 forces logout — otherwise the layout-level guard would rely
// solely on goto('/login') and leave stale 'authenticated' state if the navigation
// were cancelled or failed.
let onForceLogout: (() => void) | null = null;

export function registerForceLogoutHandler(fn: () => void): void {
	onForceLogout = fn;
}

// Singleton promise for in-flight refresh — ensures only one POST /auth/refresh is made
// when multiple concurrent requests receive 401 simultaneously. Without this, each 401
// independently calls /auth/refresh; if token rotation is ever added, the 2nd/3rd calls
// would get 401 from an already-rotated cookie and force logout mid-session.
// Exported so auth.svelte.ts can route its tryRefresh through the same deduplication
// primitive, preventing two independent refresh calls on cold page load.
let refreshPromise: Promise<string | null> | null = null;

export async function refreshToken(): Promise<string | null> {
	if (refreshPromise) return refreshPromise;
	refreshPromise = (async () => {
		try {
			const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
				method: 'POST',
				credentials: 'include'
			});
			if (!response.ok) return null;
			const data = await response.json();
			return data.access_token ?? null;
		} catch {
			return null;
		} finally {
			refreshPromise = null;
		}
	})();
	return refreshPromise;
}

export async function apiStream(
	path: string,
	options: RequestInit = {},
	retry = true
): Promise<Response> {
	const callerHeaders = (options.headers as Record<string, string>) ?? {};
	const headers: Record<string, string> = { ...callerHeaders };
	if (!('Content-Type' in headers) && !('content-type' in headers)) {
		headers['Content-Type'] = 'application/json';
	}

	if (tokenState.accessToken) {
		headers['Authorization'] = `Bearer ${tokenState.accessToken}`;
	}

	let response: Response;
	try {
		response = await fetch(`${API_BASE}${path}`, { ...options, headers });
	} catch (error) {
		if ((error as { name?: string })?.name === 'AbortError') {
			throw error;
		}
		throw { type: 'about:blank', title: 'Network Error', status: 0 } satisfies ApiError;
	}

	if (response.status === 401 && retry) {
		const newToken = await refreshToken();
		if (newToken) {
			tokenState.setToken(newToken);
			return apiStream(path, options, false);
		}
		tokenState.clear();
		// Notify the auth store so bootstrapState flips to 'anonymous' in lockstep
		// with the token clear. Without this, layout-level $effects continue to see
		// 'authenticated' and the redirect depends solely on the goto() below.
		onForceLogout?.();
		if (typeof window !== 'undefined' && !isRedirectingToLogin) {
			isRedirectingToLogin = true;
			goto('/login')
				.catch(() => { isRedirectingToLogin = false; })
				.finally(() => { isRedirectingToLogin = false; });
		}
		throw { type: 'about:blank', title: 'Unauthorized', status: 401 } satisfies ApiError;
	}

	return response;
}

export async function apiFetch<T>(
	path: string,
	options: RequestInit = {},
	retry = true
): Promise<T> {
	const callerHeaders = (options.headers as Record<string, string>) ?? {};
	const headers: Record<string, string> = { ...callerHeaders };
	// Only inject Content-Type when the caller hasn't set one and the body is not FormData.
	// When body is FormData the browser must set Content-Type itself to include the
	// multipart boundary; manually setting it would break the boundary and the upload.
	if (!('Content-Type' in headers) && !('content-type' in headers) && !(options.body instanceof FormData)) {
		headers['Content-Type'] = 'application/json';
	}

	if (tokenState.accessToken) {
		headers['Authorization'] = `Bearer ${tokenState.accessToken}`;
	}

	let response: Response;
	try {
		response = await fetch(`${API_BASE}${path}`, { ...options, headers });
	} catch {
		// Network failure (DNS, connection refused, etc.) — surface as RFC 7807 ApiError shape
		// so callers receive the same error type regardless of failure mode.
		throw { type: 'about:blank', title: 'Network Error', status: 0 } satisfies ApiError;
	}

	// A successful response means the user is active and authenticated — clear any stale
	// redirect flag so future 401s (e.g. after token expiry) are not silently swallowed.
	if (response.ok || response.status !== 401) {
		isRedirectingToLogin = false;
	}

	if (response.status === 401 && retry) {
		const newToken = await refreshToken();
		if (newToken) {
			tokenState.setToken(newToken);
			return apiFetch<T>(path, options, false);
		}
		tokenState.clear();
		// Notify the auth store so bootstrapState flips to 'anonymous' in lockstep
		// with the token clear. Keeps layout-level guards in sync even if the goto()
		// below is cancelled or fails.
		onForceLogout?.();
		// SSR guard: goto() is a browser-only API and will throw if called during
		// server-side rendering. apiFetch is used client-side only (all callers set
		// credentials: 'include' which requires a browser context), but guarding here
		// keeps the module safe if it is ever imported from a server-side load function.
		// isRedirectingToLogin guard prevents N concurrent 401s from each calling goto().
		if (typeof window !== 'undefined' && !isRedirectingToLogin) {
			isRedirectingToLogin = true;
			goto('/login')
				.catch(() => { isRedirectingToLogin = false; })
				.finally(() => { isRedirectingToLogin = false; });
		}
		throw { type: 'about:blank', title: 'Unauthorized', status: 401 } satisfies ApiError;
	}

	if (!response.ok) {
		const error: ApiError = await response.json().catch(() => ({
			type: 'about:blank',
			title: response.statusText,
			status: response.status
		}));
		throw error;
	}

	if (response.status === 204) {
		return undefined as T;
	}

	return response.json() as Promise<T>;
}
