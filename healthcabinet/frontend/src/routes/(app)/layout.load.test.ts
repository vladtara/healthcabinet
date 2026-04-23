/**
 * Story 15.1: route-load test for the shared restore entrypoint (AC 4, 7).
 *
 * Verifies that a successful restore keeps the user on the protected route
 * after a hard reload (no thrown redirect) and that a definitive anonymous
 * resolution throws the expected SvelteKit redirect.
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

describe('(app) +layout.ts load', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	test('keeps the user on the protected route when restore resolves to authenticated', async () => {
		mockRestore.mockResolvedValue('authenticated');

		// If the load function throws, awaiting it here would reject. A
		// resolved promise proves no redirect was thrown.
		await expect(load()).resolves.toBeUndefined();
		expect(mockRestore).toHaveBeenCalledTimes(1);
	});

	test('throws a 302 redirect when restore resolves to anonymous', async () => {
		mockRestore.mockResolvedValue('anonymous');

		// SvelteKit's `redirect()` helper throws an object with a status and
		// location. Match on shape rather than instance to stay decoupled
		// from @sveltejs/kit internals.
		await expect(load()).rejects.toMatchObject({
			status: 302,
			location: '/login'
		});
	});
});
