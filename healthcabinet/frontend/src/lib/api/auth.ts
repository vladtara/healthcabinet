import type { User } from '$lib/stores/auth.svelte';
import { apiFetch } from '$lib/api/client.svelte';
// Re-export User from the auth store — single source of truth for the user profile shape.
// MeResponse and the auth store's User had identical fields; consolidating avoids drift.
export type { User } from '$lib/stores/auth.svelte';

export interface RegisterResponse {
	id: string;
	email: string;
	access_token: string;
	token_type: string;
}

export interface LoginResponse {
	access_token: string;
	token_type: string;
}

export async function register(
	email: string,
	password: string,
	gdpr_consent: true, // Literal `true` — callers must explicitly pass `true`, not a boolean variable.
	// This prevents consent-bypassing calls at compile time (gdpr_consent: false would be a type error).
	// Pydantic validates the same constraint server-side; this is the frontend defence-in-depth.
	privacy_policy_version: string
): Promise<RegisterResponse> {
	// credentials: 'include' required so the browser stores the httpOnly refresh_token
	// Set-Cookie on cross-origin requests (same reason as login()).
	return apiFetch<RegisterResponse>('/api/v1/auth/register', {
		method: 'POST',
		body: JSON.stringify({ email, password, gdpr_consent, privacy_policy_version }),
		credentials: 'include'
	});
}

export async function login(email: string, password: string): Promise<LoginResponse> {
	// credentials: 'include' is required so the browser stores the httpOnly refresh_token
	// Set-Cookie on cross-origin requests (e.g. dev: localhost:5173 → localhost:8000).
	// Without it, AC #2 (auto token refresh) and AC #1 ("across browser sessions") silently fail.
	return apiFetch<LoginResponse>('/api/v1/auth/login', {
		method: 'POST',
		body: JSON.stringify({ email, password }),
		credentials: 'include'
	});
}

export async function me(retry = true): Promise<User> {
	return apiFetch<User>('/api/v1/auth/me', {}, retry);
}

export async function logout(): Promise<void> {
	return apiFetch<void>('/api/v1/auth/logout', {
		method: 'POST',
		credentials: 'include'
	});
}
