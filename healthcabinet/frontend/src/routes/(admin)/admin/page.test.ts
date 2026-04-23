import { fireEvent, waitFor } from '@testing-library/svelte';
import axe from 'axe-core';
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { QueryClient } from '@tanstack/query-core';
import { render } from '@testing-library/svelte';
import { goto } from '$app/navigation';
import AdminLayoutTestWrapper from './AdminLayoutTestWrapper.svelte';
import AdminMetricsPageTestWrapper from './AdminMetricsPageTestWrapper.svelte';

const mockAuthStore = vi.hoisted(() => ({
	isAuthenticated: true,
	bootstrapState: 'authenticated' as 'unknown' | 'restoring' | 'authenticated' | 'anonymous',
	user: {
		id: 'admin-1',
		email: 'admin@example.com',
		role: 'admin' as 'user' | 'admin',
		tier: 'paid' as 'free' | 'paid'
	}
}));

vi.mock('$lib/api/admin', () => ({
	getAdminMetrics: vi.fn()
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

import { getAdminMetrics } from '$lib/api/admin';

const mockGetAdminMetrics = vi.mocked(getAdminMetrics);

const mockMetrics = {
	total_signups: 42,
	total_uploads: 15,
	upload_success_rate: 0.8,
	documents_error_or_partial: 3,
	ai_interpretation_completion_rate: 0.6
};

function renderPage() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } }
	});
	return {
		queryClient,
		...render(AdminMetricsPageTestWrapper, { props: { queryClient } })
	};
}

describe('Admin metrics page', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockAuthStore.isAuthenticated = true;
		mockAuthStore.bootstrapState = 'authenticated';
		mockAuthStore.user = {
			id: 'admin-1',
			email: 'admin@example.com',
			role: 'admin',
			tier: 'paid'
		};
	});

	test('shows loading skeleton while fetching', () => {
		// Never resolve so we stay in loading state
		mockGetAdminMetrics.mockReturnValue(new Promise(() => {}));

		const { getByRole, container } = renderPage();

		const status = getByRole('status', { name: /loading metrics/i });
		expect(status).toHaveClass('hc-admin-overview-skeleton');
		expect(container.querySelectorAll('.hc-admin-overview-skeleton-card')).toHaveLength(5);
	});

	test('renders the admin overview layout and all 5 metric cards after successful fetch', async () => {
		mockGetAdminMetrics.mockResolvedValue(mockMetrics);

		const { container, getByRole, getByText, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading metrics/i })).toBeNull();
		});

		expect(container.querySelector('.hc-admin-overview-page')).toBeInTheDocument();
		expect(container.querySelector('header')).toHaveClass('hc-admin-overview-header');
		expect(getByRole('heading', { level: 1, name: 'Platform Metrics' })).toHaveClass(
			'hc-admin-overview-title'
		);
		expect(container.querySelector('.hc-admin-overview-stats')).toBeInTheDocument();
		expect(container.querySelector('.hc-admin-overview-sections')).toBeInTheDocument();
		expect(container.querySelectorAll('.hc-metric-card')).toHaveLength(5);

		expect(getByText('Total Signups')).toBeInTheDocument();
		expect(getByText('42')).toBeInTheDocument();

		expect(getByText('Total Uploads')).toBeInTheDocument();
		expect(getByText('15')).toBeInTheDocument();

		expect(getByText('Upload Success Rate')).toBeInTheDocument();
		expect(getByText('80.0%')).toBeInTheDocument();

		expect(getByText('Error / Partial Documents')).toBeInTheDocument();
		expect(getByText('3')).toBeInTheDocument();

		expect(getByText('AI Interpretation Rate')).toBeInTheDocument();
		expect(getByText('60.0%')).toBeInTheDocument();
		expect(container.querySelectorAll('svg')).toHaveLength(0);
	});

	test('shows N/A for null upload_success_rate', async () => {
		mockGetAdminMetrics.mockResolvedValue({
			...mockMetrics,
			total_uploads: 0,
			upload_success_rate: null,
			ai_interpretation_completion_rate: null
		});

		const { getAllByText, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading metrics/i })).toBeNull();
		});

		const naElements = getAllByText('N/A');
		expect(naElements.length).toBe(2); // both rate fields
	});

	test('shows error state on fetch failure', async () => {
		mockGetAdminMetrics.mockRejectedValue(new Error('Network error'));

		const { container, getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading metrics/i })).toBeNull();
		});

		expect(getByRole('alert')).toBeInTheDocument();
		expect(container.querySelector('.hc-state.hc-state-error')).toBeInTheDocument();
		expect(getByRole('button', { name: /try again/i })).toHaveClass('btn-standard');
	});

	test('refresh button uses btn-standard and invalidates the metrics query', async () => {
		mockGetAdminMetrics.mockResolvedValue(mockMetrics);

		const { queryClient, getByRole, queryByRole } = renderPage();
		const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading metrics/i })).toBeNull();
		});

		const refreshButton = getByRole('button', { name: /refresh metrics/i });
		expect(refreshButton).toHaveClass('btn-standard');

		await fireEvent.click(refreshButton);

		expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['admin', 'metrics'] });
	});

	test('user management fieldset renders with a legend and navigates to /admin/users', async () => {
		mockGetAdminMetrics.mockResolvedValue(mockMetrics);

		const { container, getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading metrics/i })).toBeNull();
		});

		const legends = Array.from(container.querySelectorAll('fieldset.hc-fieldset > legend')).map(
			(legend) => legend.textContent?.trim()
		);
		expect(legends).toContain('User Management');

		const button = getByRole('button', { name: /open user management/i });
		expect(button).toHaveClass('btn-standard');

		await fireEvent.click(button);

		expect(vi.mocked(goto)).toHaveBeenCalledWith('/admin/users');
	});

	test('extraction error queue fieldset renders with a legend and navigates to /admin/documents', async () => {
		mockGetAdminMetrics.mockResolvedValue(mockMetrics);

		const { container, getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading metrics/i })).toBeNull();
		});

		const legends = Array.from(container.querySelectorAll('fieldset.hc-fieldset > legend')).map(
			(legend) => legend.textContent?.trim()
		);
		expect(legends).toContain('Extraction Error Queue');

		const button = getByRole('button', { name: /open extraction error queue/i });
		expect(button).toHaveClass('btn-standard');

		await fireEvent.click(button);

		expect(vi.mocked(goto)).toHaveBeenCalledWith('/admin/documents');
	});

	test('passes axe accessibility audit after metrics load', async () => {
		mockGetAdminMetrics.mockResolvedValue(mockMetrics);

		const { container, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading metrics/i })).toBeNull();
		});

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	test('no shadcn-svelte primitive imports exist in page source', async () => {
		const pageSource = await import('./+page.svelte?raw');
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/button['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/input['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/label['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/textarea['/]/);
	});

	test('redirects non-admin users away from the admin area', async () => {
		mockAuthStore.isAuthenticated = true;
		// Story 15.1: role enforcement is gated on bootstrap resolution, so
		// we must mark restore as complete for the non-admin redirect to fire.
		mockAuthStore.bootstrapState = 'authenticated';
		mockAuthStore.user = {
			id: 'user-1',
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
});
