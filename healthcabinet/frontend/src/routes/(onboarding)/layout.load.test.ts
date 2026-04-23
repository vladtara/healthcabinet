/**
 * Story 15.1: route-load test for the (onboarding) layout bootstrap
 * entrypoint (AC 4, 7).
 *
 * Mirrors `(app)/layout.load.test.ts`. Verifies that the load function:
 *  - resolves without throwing when restoreSession() returns 'authenticated'
 *  - throws a SvelteKit redirect(302, '/login') when it returns 'anonymous'
 *
 * All three protected route groups (`(app)`, `(admin)`, `(onboarding)`)
 * share the same bootstrap contract, so each has its own load test to lock
 * it in.
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

describe('(onboarding) +layout.ts load', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	test('keeps the user on the protected onboarding route when restore resolves to authenticated', async () => {
		mockRestore.mockResolvedValue('authenticated');

		await expect(load()).resolves.toBeUndefined();
		expect(mockRestore).toHaveBeenCalledTimes(1);
	});

	test('throws a 302 redirect when restore resolves to anonymous', async () => {
		mockRestore.mockResolvedValue('anonymous');

		await expect(load()).rejects.toMatchObject({
			status: 302,
			location: '/login'
		});
	});
});
