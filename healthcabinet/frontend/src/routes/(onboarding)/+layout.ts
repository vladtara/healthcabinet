import { redirect } from '@sveltejs/kit';
import { authStore } from '$lib/stores/auth.svelte';

export const ssr = false;

export async function load() {
	// Story 15.1: shares the same bootstrap entrypoint as `(app)` and `(admin)`
	// so all protected route groups agree on a single restore transition.
	const state = await authStore.restoreSession();
	if (state !== 'authenticated') {
		throw redirect(302, '/login');
	}
}
