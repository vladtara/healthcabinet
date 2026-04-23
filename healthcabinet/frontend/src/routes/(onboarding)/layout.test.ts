/**
 * Story 15.1: (onboarding) layout bootstrap redirect-guard tests (AC 3, 6, 7).
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

vi.mock('$lib/api/client.svelte', () => ({
	tokenState: { accessToken: 'test', setToken: vi.fn(), clear: vi.fn() },
	apiFetch: vi.fn()
}));

import { goto } from '$app/navigation';
import OnboardingLayoutTestWrapper from './OnboardingLayoutTestWrapper.svelte';

describe('(onboarding) +layout.svelte bootstrap guard', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockAuthStore.bootstrapState = 'unknown';
		mockAuthStore.isAuthenticated = false;
		mockAuthStore.user = null;
	});

	test('does not redirect while bootstrap is "unknown"', async () => {
		mockAuthStore.bootstrapState = 'unknown';

		const { queryByTestId } = render(OnboardingLayoutTestWrapper);
		await tick();

		expect(vi.mocked(goto)).not.toHaveBeenCalled();
		expect(queryByTestId('onboarding-layout-child')).toBeNull();
	});

	test('does not redirect while bootstrap is "restoring"', async () => {
		mockAuthStore.bootstrapState = 'restoring';

		const { queryByTestId } = render(OnboardingLayoutTestWrapper);
		await tick();

		expect(vi.mocked(goto)).not.toHaveBeenCalled();
		expect(queryByTestId('onboarding-layout-child')).toBeNull();
	});

	test('redirects to /login after bootstrap resolves to "anonymous"', async () => {
		mockAuthStore.bootstrapState = 'anonymous';

		render(OnboardingLayoutTestWrapper);

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

		const { queryByTestId } = render(OnboardingLayoutTestWrapper);
		await tick();

		expect(vi.mocked(goto)).not.toHaveBeenCalled();
		expect(queryByTestId('onboarding-layout-child')).not.toBeNull();
	});
});
