/**
 * Story 15.1: (admin) layout bootstrap redirect-guard tests (AC 3, 6, 7).
 *
 * Verifies:
 *  - no goto('/login') while bootstrap is 'unknown'
 *  - no goto('/login') while bootstrap is 'restoring'
 *  - goto('/login') fires after bootstrap resolves to 'anonymous'
 *  - admin role enforcement only runs after bootstrap resolves to 'authenticated'
 *  - admin content renders when bootstrap is authenticated AND role === 'admin'
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
			fn({ url: new URL('http://localhost/admin') });
			return () => {};
		}
	};
	return { page };
});

vi.mock('$lib/api/client.svelte', () => ({
	tokenState: { accessToken: 'test', setToken: vi.fn(), clear: vi.fn() },
	apiFetch: vi.fn()
}));

import { goto } from '$app/navigation';
import AdminLayoutTestWrapper from './admin/AdminLayoutTestWrapper.svelte';

describe('(admin) +layout.svelte bootstrap guard', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockAuthStore.bootstrapState = 'unknown';
		mockAuthStore.isAuthenticated = false;
		mockAuthStore.user = null;
	});

	test('does not redirect while bootstrap is "unknown"', async () => {
		mockAuthStore.bootstrapState = 'unknown';
		// Even with no user loaded yet, the admin layout must not redirect —
		// restore is still in flight.
		mockAuthStore.user = null;

		const { queryByTestId } = render(AdminLayoutTestWrapper);
		await tick();

		expect(vi.mocked(goto)).not.toHaveBeenCalled();
		expect(queryByTestId('admin-layout-child')).toBeNull();
	});

	test('does not redirect while bootstrap is "restoring"', async () => {
		mockAuthStore.bootstrapState = 'restoring';

		const { queryByTestId } = render(AdminLayoutTestWrapper);
		await tick();

		expect(vi.mocked(goto)).not.toHaveBeenCalled();
		expect(queryByTestId('admin-layout-child')).toBeNull();
	});

	test('redirects to /login when bootstrap resolves to "anonymous"', async () => {
		mockAuthStore.bootstrapState = 'anonymous';

		render(AdminLayoutTestWrapper);

		await waitFor(() => {
			expect(vi.mocked(goto)).toHaveBeenCalledWith('/login');
		});
		// A single `return` guard in the effect should fire exactly once on the
		// anonymous path — the role-check branch must not also execute.
		expect(vi.mocked(goto)).toHaveBeenCalledTimes(1);
	});

	test('enforces admin role only after bootstrap resolves to "authenticated"', async () => {
		// Non-admin user, but bootstrap is 'authenticated' — this is the
		// post-restore role check path. Must redirect.
		mockAuthStore.bootstrapState = 'authenticated';
		mockAuthStore.isAuthenticated = true;
		mockAuthStore.user = {
			id: 'u1',
			email: 'user@example.com',
			role: 'user',
			tier: 'free'
		};

		const { queryByTestId } = render(AdminLayoutTestWrapper);

		await waitFor(() => {
			expect(vi.mocked(goto)).toHaveBeenCalledWith('/login');
		});
		expect(queryByTestId('admin-layout-child')).toBeNull();
	});

	test('does NOT run role enforcement during restore even if user is null', async () => {
		mockAuthStore.bootstrapState = 'restoring';
		// user is null here but that should NOT trigger the non-admin redirect
		// because role is only enforced after authenticated resolution.
		mockAuthStore.user = null;

		const { queryByTestId } = render(AdminLayoutTestWrapper);
		await tick();

		expect(vi.mocked(goto)).not.toHaveBeenCalled();
		// The layout's content gate requires bootstrap === 'authenticated' AND
		// role === 'admin', so restore should render nothing.
		expect(queryByTestId('admin-layout-child')).toBeNull();
	});

	test('does NOT enforce role during "restoring" even when user has a non-admin role', async () => {
		// Edge case: tryRefresh() populates authStore.user before bootstrap
		// transitions to 'authenticated' (the me() call happens inside
		// _doTryRefresh before the restoreSession() IIFE flips bootstrap).
		// If bootstrap is still 'restoring' the role check must not run.
		mockAuthStore.bootstrapState = 'restoring';
		mockAuthStore.user = {
			id: '1',
			email: 'u@example.com',
			role: 'user',
			tier: 'free'
		};

		render(AdminLayoutTestWrapper);
		await tick();

		expect(vi.mocked(goto)).not.toHaveBeenCalled();
	});

	test('does NOT enforce role when bootstrap is "authenticated" but user is still null (me() transient failure)', async () => {
		// _doTryRefresh() catches non-401 errors from me() and leaves user null
		// while returning true, so bootstrap can be 'authenticated' with no
		// user. The old effect read user?.role as undefined !== 'admin' → true
		// and redirected a legitimate admin to /login. The fix requires
		// authStore.user to be populated before enforcing role.
		mockAuthStore.bootstrapState = 'authenticated';
		mockAuthStore.user = null;

		render(AdminLayoutTestWrapper);
		await tick();

		expect(vi.mocked(goto)).not.toHaveBeenCalled();
	});

	test('renders admin content when bootstrap is authenticated and role is admin', async () => {
		mockAuthStore.bootstrapState = 'authenticated';
		mockAuthStore.isAuthenticated = true;
		mockAuthStore.user = {
			id: 'admin-1',
			email: 'admin@example.com',
			role: 'admin',
			tier: 'paid'
		};

		const { queryByTestId } = render(AdminLayoutTestWrapper);
		await tick();

		expect(vi.mocked(goto)).not.toHaveBeenCalled();
		expect(queryByTestId('admin-layout-child')).not.toBeNull();
	});

	// T-B (Round-2): when _doTryRefresh resolves bootstrap to 'authenticated'
	// but /me failed with a non-401 (5xx / network / abort), authStore.user
	// stays null. The role-check effect correctly skips (user && gate), and
	// the admin-content branch can't render either — without a third
	// loading branch the user sees a permanent blank screen with zero
	// feedback. Round-2 adds an {:else if} branch that renders a visible
	// loading indicator; this test pins both that the indicator renders and
	// that we do NOT redirect in this transient window.
	test('renders loading indicator (and does NOT redirect) when bootstrap is "authenticated" but user is still null', async () => {
		mockAuthStore.bootstrapState = 'authenticated';
		// user stays null: _doTryRefresh catches non-401 errors from me()
		// and leaves user unpopulated while bootstrap was already flipped
		// to 'authenticated'. This is the transient-me-failure scenario.
		mockAuthStore.user = null;

		const { queryByTestId } = render(AdminLayoutTestWrapper);
		await tick();

		// The new loading branch is visible — user sees feedback, not a
		// blank screen.
		expect(queryByTestId('admin-loading')).not.toBeNull();
		// Admin children MUST NOT render in this state — role hasn't been
		// confirmed yet.
		expect(queryByTestId('admin-layout-child')).toBeNull();
		// And critically: no spurious redirect. Round-1's user-gated role
		// check handles "user is null" by not enforcing role; Round-2's job
		// is just to give that state a visible representation without
		// changing the redirect contract.
		expect(vi.mocked(goto)).not.toHaveBeenCalled();
	});
});
