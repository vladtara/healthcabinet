import axe from 'axe-core';
import { fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { QueryClient } from '@tanstack/query-core';
import { render } from '@testing-library/svelte';
import AdminUserDetailTestWrapper from './AdminUserDetailTestWrapper.svelte';
import { getAdminUserDetail, updateAdminUserStatus } from '$lib/api/admin';
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

const mockPageData = vi.hoisted(() => ({
	params: { user_id: '00000000-0000-0000-0000-000000000001' },
	url: new URL('http://test/admin/users/00000000-0000-0000-0000-000000000001')
}));

const mockPageStore = vi.hoisted(() => ({
	subscribe: (fn: (value: typeof mockPageData) => void) => {
		fn(mockPageData);
		return () => {};
	}
}));

vi.mock('$lib/api/admin', () => ({
	getAdminUserDetail: vi.fn(),
	updateAdminUserStatus: vi.fn()
}));

vi.mock('$lib/stores/auth.svelte', () => ({
	authStore: mockAuthStore
}));

vi.mock('$lib/api/client.svelte', () => ({
	tokenState: { accessToken: 'mock-token', setToken: vi.fn(), clear: vi.fn() },
	apiFetch: vi.fn()
}));

vi.mock('$app/stores', () => ({
	page: mockPageStore
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

const mockGetAdminUserDetail = vi.mocked(getAdminUserDetail);
const mockUpdateAdminUserStatus = vi.mocked(updateAdminUserStatus);
const mockGoto = vi.mocked(goto);

const mockUserDetail = {
	user_id: '00000000-0000-0000-0000-000000000001',
	email: 'alice@example.com',
	registration_date: '2026-01-15T10:00:00Z',
	last_login: '2026-03-20T14:30:00Z',
	upload_count: 5,
	account_status: 'active' as const
};

function renderPage() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } }
	});
	return {
		queryClient,
		...render(AdminUserDetailTestWrapper, { props: { queryClient } })
	};
}

describe('Admin user detail page', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockPageData.params.user_id = '00000000-0000-0000-0000-000000000001';
		mockPageData.url = new URL('http://test/admin/users/00000000-0000-0000-0000-000000000001');
	});

	test('page container uses hc-admin-user-detail-page class', async () => {
		mockGetAdminUserDetail.mockResolvedValue(mockUserDetail);

		const { container } = renderPage();

		await waitFor(() => {
			expect(container.querySelector('.hc-admin-user-detail-page')).toBeInTheDocument();
		});
	});

	test('shows hc-admin-user-detail-skeleton while fetching', () => {
		mockGetAdminUserDetail.mockReturnValue(new Promise(() => {}));

		const { container, getByRole } = renderPage();

		expect(getByRole('status', { name: /loading user details/i })).toBeInTheDocument();
		expect(container.querySelector('.hc-admin-user-detail-skeleton')).toBeInTheDocument();
	});

	test('back button uses btn-standard and navigates to /admin/users', async () => {
		mockGetAdminUserDetail.mockResolvedValue(mockUserDetail);

		const { getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading user details/i })).toBeNull();
		});

		const backButton = getByRole('button', { name: /back to users/i });
		expect(backButton).toHaveClass('btn-standard');

		await fireEvent.click(backButton);

		expect(mockGoto).toHaveBeenCalledWith('/admin/users');
	});

	test('renders account metadata in a fieldset with Account Information legend', async () => {
		mockGetAdminUserDetail.mockResolvedValue(mockUserDetail);

		const { container, getByText, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading user details/i })).toBeNull();
		});

		expect(container.querySelector('.hc-fieldset > legend')).toHaveTextContent(
			'Account Information'
		);
		expect(container.querySelector('.hc-admin-user-detail-meta-grid')).toBeInTheDocument();
		expect(getByText('alice@example.com')).toBeInTheDocument();
		expect(getByText('Active')).toBeInTheDocument();
		expect(getByText('5')).toBeInTheDocument();
	});

	test('refresh button invalidates the user detail query', async () => {
		mockGetAdminUserDetail.mockResolvedValue(mockUserDetail);

		const { queryClient, getByRole, queryByRole } = renderPage();
		const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading user details/i })).toBeNull();
		});

		await fireEvent.click(getByRole('button', { name: /refresh user details/i }));

		expect(invalidateSpy).toHaveBeenCalledWith({
			queryKey: ['admin', 'users', '00000000-0000-0000-0000-000000000001']
		});
	});

	test('shows error state on fetch failure with hc-state-error', async () => {
		mockGetAdminUserDetail.mockRejectedValue(new Error('Not found'));

		const { container, getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading user details/i })).toBeNull();
		});

		expect(getByRole('alert')).toBeInTheDocument();
		expect(container.querySelector('.hc-state.hc-state-error')).toBeInTheDocument();
		expect(getByRole('button', { name: /try again/i })).toHaveClass('btn-standard');
	});

	test('shows suspend button with btn-destructive class for active users', async () => {
		mockGetAdminUserDetail.mockResolvedValue(mockUserDetail);

		const { getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading user details/i })).toBeNull();
		});

		expect(getByRole('button', { name: 'Suspend Account' })).toHaveClass('btn-destructive');
	});

	test('shows reactivate button with btn-primary class for suspended users', async () => {
		mockGetAdminUserDetail.mockResolvedValue({
			...mockUserDetail,
			account_status: 'suspended'
		});

		const { getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading user details/i })).toBeNull();
		});

		expect(getByRole('button', { name: 'Reactivate Account' })).toHaveClass('btn-primary');
	});

	test('clicking suspend opens ConfirmDialog with the expected aria contract', async () => {
		mockGetAdminUserDetail.mockResolvedValue(mockUserDetail);

		const { getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading user details/i })).toBeNull();
		});

		await fireEvent.click(getByRole('button', { name: 'Suspend Account' }));

		const dialog = getByRole('dialog', { name: 'Suspend Account?' });
		expect(dialog).toHaveAttribute('aria-modal', 'true');
		expect(getByRole('button', { name: 'Suspend' })).toHaveClass('btn-destructive');
	});

	test('confirming suspend calls updateAdminUserStatus', async () => {
		mockGetAdminUserDetail.mockResolvedValue(mockUserDetail);
		mockUpdateAdminUserStatus.mockResolvedValue(mockUserDetail);

		const { getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading user details/i })).toBeNull();
		});

		await fireEvent.click(getByRole('button', { name: 'Suspend Account' }));
		await fireEvent.click(getByRole('button', { name: 'Suspend' }));

		expect(mockUpdateAdminUserStatus).toHaveBeenCalledWith(
			'00000000-0000-0000-0000-000000000001',
			'suspended'
		);
	});

	test('Escape closes the confirmation dialog', async () => {
		mockGetAdminUserDetail.mockResolvedValue(mockUserDetail);

		const { getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading user details/i })).toBeNull();
		});

		await fireEvent.click(getByRole('button', { name: 'Suspend Account' }));

		const dialog = getByRole('dialog', { name: 'Suspend Account?' });
		await fireEvent.keyDown(dialog, { key: 'Escape' });

		await waitFor(() => {
			expect(queryByRole('dialog', { name: 'Suspend Account?' })).toBeNull();
		});
	});

	test('backdrop click closes the confirmation dialog when not loading', async () => {
		mockGetAdminUserDetail.mockResolvedValue(mockUserDetail);

		const { container, getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading user details/i })).toBeNull();
		});

		await fireEvent.click(getByRole('button', { name: 'Suspend Account' }));

		const backdrop = container.querySelector('.hc-dialog-backdrop');
		expect(backdrop).toBeInTheDocument();

		await fireEvent.click(backdrop as HTMLDivElement);

		await waitFor(() => {
			expect(queryByRole('dialog', { name: 'Suspend Account?' })).toBeNull();
		});
	});

	test('mutation rejection renders updateError in hc-state-error', async () => {
		mockGetAdminUserDetail.mockResolvedValue(mockUserDetail);
		mockUpdateAdminUserStatus.mockRejectedValue(new Error('Request failed'));

		const { container, getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading user details/i })).toBeNull();
		});

		await fireEvent.click(getByRole('button', { name: 'Suspend Account' }));
		await fireEvent.click(getByRole('button', { name: 'Suspend' }));

		await waitFor(() => {
			const errorBanner = container.querySelector('.hc-state.hc-state-error');
			expect(errorBanner).toBeInTheDocument();
			expect(errorBanner?.textContent).toContain('Failed to suspend account. Please try again.');
		});
	});

	test('axe accessibility audit passes', async () => {
		mockGetAdminUserDetail.mockResolvedValue(mockUserDetail);

		const { container, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading user details/i })).toBeNull();
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
