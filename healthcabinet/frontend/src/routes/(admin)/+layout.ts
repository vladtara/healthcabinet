import { redirect } from '@sveltejs/kit';
import { authStore } from '$lib/stores/auth.svelte';

export const ssr = false;

export async function load() {
	// Story 15.1: admin route group now uses the same bootstrap semantics as
	// `(app)` and `(onboarding)`. Previously this layout had no restore step,
	// so a hard reload of an admin route would fall through to the layout
	// effect with isAuthenticated=false and redirect before the refresh cookie
	// round-trip completed.
	const state = await authStore.restoreSession();
	if (state !== 'authenticated') {
		throw redirect(302, '/login');
	}
}
