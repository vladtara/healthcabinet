import axe from 'axe-core';
import { fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { QueryClient } from '@tanstack/query-core';
import { render } from '@testing-library/svelte';
import AdminUsersPageTestWrapper from './AdminUsersPageTestWrapper.svelte';
import { getAdminUsers, getFlaggedReports, markFlagReviewed } from '$lib/api/admin';
import { goto } from '$app/navigation';

const mockAuthStore = vi.hoisted(() => ({
	isAuthenticated: true,
	user: {
		id: 'admin-1',
		email: 'admin@example.com',
		role: 'admin' as const,
		tier: 'paid' as const
	}
}));

vi.mock('$lib/api/admin', () => ({
	getAdminUsers: vi.fn(),
	getFlaggedReports: vi.fn(),
	markFlagReviewed: vi.fn()
}));

vi.mock('$lib/stores/auth.svelte', () => ({
	authStore: mockAuthStore
}));

vi.mock('$lib/api/client.svelte', () => ({
	tokenState: { accessToken: 'mock-token', setToken: vi.fn(), clear: vi.fn() },
	apiFetch: vi.fn()
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

const mockGetAdminUsers = vi.mocked(getAdminUsers);
const mockGetFlaggedReports = vi.mocked(getFlaggedReports);
const mockMarkFlagReviewed = vi.mocked(markFlagReviewed);
const mockGoto = vi.mocked(goto);

const mockUsersData = {
	items: [
		{
			user_id: '00000000-0000-0000-0000-000000000001',
			email: 'alice@example.com',
			registration_date: '2026-01-15T10:00:00Z',
			upload_count: 5,
			account_status: 'active' as const
		},
		{
			user_id: '00000000-0000-0000-0000-000000000002',
			email: 'bob@example.com',
			registration_date: '2026-02-20T14:00:00Z',
			upload_count: 0,
			account_status: 'suspended' as const
		}
	],
	total: 2
};

const mockFlagsData = {
	items: [
		{
			health_value_id: '00000000-0000-0000-0000-000000000100',
			user_id: '11111111-0000-0000-0000-000000000001',
			document_id: '22222222-0000-0000-0000-000000000010',
			value_name: 'glucose',
			flagged_value: 999.0,
			flagged_at: '2026-03-01T08:00:00Z'
		}
	],
	total: 1
};

function renderPage() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } }
	});
	return {
		queryClient,
		...render(AdminUsersPageTestWrapper, { props: { queryClient } })
	};
}

describe('Admin users management page', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	test('page container uses hc-admin-users-page class', async () => {
		mockGetAdminUsers.mockResolvedValue(mockUsersData);
		mockGetFlaggedReports.mockResolvedValue(mockFlagsData);

		const { container } = renderPage();

		await waitFor(() => {
			expect(container.querySelector('.hc-admin-users-page')).toBeInTheDocument();
		});
	});

	test('shows users and flags loading skeletons while fetching', () => {
		mockGetAdminUsers.mockReturnValue(new Promise(() => {}));
		mockGetFlaggedReports.mockReturnValue(new Promise(() => {}));

		const { container, getByRole } = renderPage();

		expect(getByRole('status', { name: /loading users/i })).toBeInTheDocument();
		expect(getByRole('status', { name: /loading flagged reports/i })).toBeInTheDocument();
		expect(container.querySelector('.hc-admin-users-skeleton')).toBeInTheDocument();
		expect(container.querySelector('.hc-admin-users-flags-skeleton')).toBeInTheDocument();
	});

	test('renders DataTable user list and flagged reports section with 98.css classes', async () => {
		mockGetAdminUsers.mockResolvedValue(mockUsersData);
		mockGetFlaggedReports.mockResolvedValue(mockFlagsData);

		const { container, getAllByRole, getAllByText, getByText, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading users/i })).toBeNull();
		});

		expect(container.querySelector('.hc-data-table')).toBeInTheDocument();
		expect(getAllByRole('table')).toHaveLength(2);
		expect(getByText('Email')).toBeInTheDocument();
		expect(getAllByText('User ID').length).toBeGreaterThan(0);
		expect(getByText('Flagged Value Reports')).toBeInTheDocument();
		expect(container.querySelector('.hc-admin-users-flags-section')).toBeInTheDocument();
		expect(container.querySelector('.hc-admin-users-flags-table')).toBeInTheDocument();
		expect(container.querySelector('.hc-admin-users-flag-value')?.textContent).toContain('999');
		expect(container.querySelector('.hc-admin-users-flag-userlink')?.textContent).toContain(
			'11111111…'
		);
	});

	test('clicking a user row navigates to the user detail page', async () => {
		mockGetAdminUsers.mockResolvedValue(mockUsersData);
		mockGetFlaggedReports.mockResolvedValue({ items: [], total: 0 });

		const { getByText, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading users/i })).toBeNull();
		});

		await fireEvent.click(getByText('alice@example.com'));

		expect(mockGoto).toHaveBeenCalledWith(
			'/admin/users/00000000-0000-0000-0000-000000000001'
		);
	});

	test('refresh button invalidates both users and flags queries', async () => {
		mockGetAdminUsers.mockResolvedValue(mockUsersData);
		mockGetFlaggedReports.mockResolvedValue(mockFlagsData);

		const { queryClient, getByRole, queryByRole } = renderPage();
		const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading users/i })).toBeNull();
		});

		await fireEvent.click(getByRole('button', { name: /refresh user list/i }));

		expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['admin', 'users'] });
		expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['admin', 'flags'] });
	});

	test('shows empty-state copy for no users and no-search-results variants', async () => {
		mockGetAdminUsers
			.mockResolvedValueOnce({ items: [], total: 0 })
			.mockResolvedValueOnce({ items: [], total: 0 });
		mockGetFlaggedReports.mockResolvedValue({ items: [], total: 0 });

		const { getByLabelText, getByText, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading users/i })).toBeNull();
		});

		expect(getByText('No users found')).toBeInTheDocument();

		await fireEvent.input(getByLabelText('Search users'), { target: { value: 'nomatch' } });

		await waitFor(
			() => {
				expect(mockGetAdminUsers).toHaveBeenLastCalledWith('nomatch');
			},
			{ timeout: 600 }
		);

		await waitFor(() => {
			expect(getByText('No users match your search')).toBeInTheDocument();
		});
	});

	test('shows user-list error state with hc-state-error', async () => {
		mockGetAdminUsers.mockRejectedValue(new Error('Network error'));
		mockGetFlaggedReports.mockResolvedValue({ items: [], total: 0 });

		const { container, getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading users/i })).toBeNull();
		});

		expect(getByRole('alert')).toBeInTheDocument();
		expect(container.querySelector('.hc-state.hc-state-error')).toBeInTheDocument();
		expect(getByRole('button', { name: /try again/i })).toHaveClass('btn-standard');
	});

	test('mark reviewed calls API and invalidates flags and queue queries', async () => {
		mockGetAdminUsers.mockResolvedValue(mockUsersData);
		mockGetFlaggedReports.mockResolvedValue(mockFlagsData);
		mockMarkFlagReviewed.mockResolvedValue({ health_value_id: 'hv-1', reviewed_at: new Date().toISOString() });

		const { queryClient, getByText, queryByRole } = renderPage();
		const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading users/i })).toBeNull();
		});

		await fireEvent.click(getByText('Mark Reviewed'));

		await waitFor(() => {
			expect(mockMarkFlagReviewed).toHaveBeenCalledWith(
				'00000000-0000-0000-0000-000000000100'
			);
		});
		expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['admin', 'flags'] });
		expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['admin', 'queue'] });
	});

	test('open correction flow navigates with the health_value_id query param', async () => {
		mockGetAdminUsers.mockResolvedValue(mockUsersData);
		mockGetFlaggedReports.mockResolvedValue(mockFlagsData);

		const { getByText, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading users/i })).toBeNull();
		});

		await fireEvent.click(getByText('Open correction flow'));

		expect(mockGoto).toHaveBeenCalledWith(
			'/admin/documents/22222222-0000-0000-0000-000000000010?health_value_id=00000000-0000-0000-0000-000000000100'
		);
	});

	test('search input remains accessible and debounces getAdminUsers at 300ms', async () => {
		mockGetAdminUsers.mockResolvedValue(mockUsersData);
		mockGetFlaggedReports.mockResolvedValue({ items: [], total: 0 });

		const { getByLabelText, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading users/i })).toBeNull();
		});

		const searchInput = getByLabelText('Search users');
		await fireEvent.input(searchInput, { target: { value: 'alice' } });

		await waitFor(
			() => {
				expect(mockGetAdminUsers).toHaveBeenLastCalledWith('alice');
			},
			{ timeout: 600 }
		);
	});

	test('axe accessibility audit passes', async () => {
		mockGetAdminUsers.mockResolvedValue(mockUsersData);
		mockGetFlaggedReports.mockResolvedValue(mockFlagsData);

		const { container, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading users/i })).toBeNull();
		});

		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});

	test('no shadcn-svelte primitive imports exist in page source', async () => {
		const pageSource = await import('./+page.svelte?raw');
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/button['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/input['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/label['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/textarea['/]/);
	});
});
