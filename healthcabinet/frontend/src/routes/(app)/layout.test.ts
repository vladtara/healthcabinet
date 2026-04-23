/**
 * Story 15.1: (app) layout bootstrap redirect-guard tests (AC 3, 4, 7).
 *
 * Verifies:
 *  - no goto('/login') while bootstrap is 'unknown'
 *  - no goto('/login') while bootstrap is 'restoring'
 *  - goto('/login') fires only after bootstrap resolves to 'anonymous'
 *  - content renders after bootstrap resolves to 'authenticated'
 */

import { beforeEach, describe, expect, test, vi } from 'vitest';
import { render, waitFor } from '@testing-library/svelte';
import { tick } from 'svelte';

const mockAuthStore = vi.hoisted(() => ({
	bootstrapState: 'unknown' as 'unknown' | 'restoring' | 'authenticated' | 'anonymous',
	isAuthenticated: false,
	user: null as null | {
		id: string;
		email: string;
		role: 'user' | 'admin';
		tier: 'free' | 'paid';
	}
}));

vi.mock('$lib/stores/auth.svelte', () => ({
	authStore: mockAuthStore
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

vi.mock('$app/stores', () => {
	const page = {
		subscribe: (fn: (val: unknown) => void) => {
			fn({ url: new URL('http://localhost/dashboard') });
			return () => {};
		}
	};
	return { page };
});

vi.mock('$lib/api/client.svelte', () => ({
	tokenState: { accessToken: 'test', setToken: vi.fn(), clear: vi.fn() },
	apiFetch: vi.fn()
}));

vi.mock('$lib/stores/status-bar.svelte', () => ({
	statusBarStore: {
		status: 'Ready',
		fields: [] as string[],
		set: vi.fn(),
		reset: vi.fn()
	}
}));

import { goto } from '$app/navigation';
import AppLayoutTestWrapper from './AppLayoutTestWrapper.svelte';

describe('(app) +layout.svelte bootstrap guard', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockAuthStore.bootstrapState = 'unknown';
		mockAuthStore.isAuthenticated = false;
		mockAuthStore.user = null;
	});

	test('does not redirect while bootstrap is "unknown"', async () => {
		mockAuthStore.bootstrapState = 'unknown';

		const { queryByTestId } = render(AppLayoutTestWrapper);
		await tick();

		expect(vi.mocked(goto)).not.toHaveBeenCalled();
		// Content is NOT rendered during restore — the shell is hidden behind
		// the `bootstrapState === 'authenticated'` gate.
		expect(queryByTestId('app-layout-child')).toBeNull();
	});

	test('does not redirect while bootstrap is "restoring"', async () => {
		mockAuthStore.bootstrapState = 'restoring';

		const { queryByTestId } = render(AppLayoutTestWrapper);
		await tick();

		expect(vi.mocked(goto)).not.toHaveBeenCalled();
		expect(queryByTestId('app-layout-child')).toBeNull();
	});

	test('redirects to /login after bootstrap resolves to "anonymous"', async () => {
		mockAuthStore.bootstrapState = 'anonymous';

		render(AppLayoutTestWrapper);

		await waitFor(() => {
			expect(vi.mocked(goto)).toHaveBeenCalledWith('/login');
		});
	});

	test('renders content when bootstrap is "authenticated"', async () => {
		mockAuthStore.bootstrapState = 'authenticated';
		mockAuthStore.isAuthenticated = true;
		mockAuthStore.user = {
			id: '1',
			email: 'user@example.com',
			role: 'user',
			tier: 'free'
		};

		const { queryByTestId } = render(AppLayoutTestWrapper);
		await tick();

		expect(vi.mocked(goto)).not.toHaveBeenCalled();
		expect(queryByTestId('app-layout-child')).not.toBeNull();
	});
});
