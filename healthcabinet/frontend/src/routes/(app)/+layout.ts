import { redirect } from '@sveltejs/kit';
import { authStore } from '$lib/stores/auth.svelte';

export const ssr = false;

export async function load() {
	// Story 15.1: route through the shared bootstrap entrypoint so `(app)`,
	// `(admin)`, and `(onboarding)` share the same in-flight restore promise
	// and the same unknown -> restoring -> authenticated/anonymous transition.
	// restoreSession() short-circuits to 'authenticated' if an interactive
	// login already populated state, and deduplicates concurrent layout loads.
	const state = await authStore.restoreSession();
	if (state !== 'authenticated') {
		throw redirect(302, '/login');
	}
}
