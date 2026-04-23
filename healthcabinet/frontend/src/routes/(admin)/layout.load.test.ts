/**
 * Story 15.1: route-load test for the (admin) layout bootstrap entrypoint
 * (AC 4, 7).
 *
 * Mirrors `(app)/layout.load.test.ts`. Verifies that the load function:
 *  - resolves without throwing when restoreSession() returns 'authenticated'
 *  - throws a SvelteKit redirect(302, '/login') when it returns 'anonymous'
 *
 * The load function is the single point that enforces the post-bootstrap
 * redirect for the admin route group. The layout-level `$effect` is a
 * secondary guard; this test locks in the primary (load) contract.
 */

import { describe, expect, test, vi, beforeEach } from 'vitest';

vi.mock('$lib/stores/auth.svelte', () => ({
	authStore: {
		restoreSession: vi.fn()
	}
}));

import { authStore } from '$lib/stores/auth.svelte';
import { load } from './+layout';

const mockRestore = vi.mocked(authStore.restoreSession);

describe('(admin) +layout.ts load', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	test('keeps the user on the protected admin route when restore resolves to authenticated', async () => {
		mockRestore.mockResolvedValue('authenticated');

		// A resolved promise proves no redirect was thrown.
		await expect(load()).resolves.toBeUndefined();
		expect(mockRestore).toHaveBeenCalledTimes(1);
	});

	test('throws a 302 redirect when restore resolves to anonymous', async () => {
		mockRestore.mockResolvedValue('anonymous');

		// Match on the SvelteKit redirect shape rather than the instance so
		// the test stays decoupled from @sveltejs/kit internals.
		await expect(load()).rejects.toMatchObject({
			status: 302,
			location: '/login'
		});
	});
});
