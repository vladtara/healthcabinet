import axe from 'axe-core';
import { fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { QueryClient } from '@tanstack/query-core';
import { render } from '@testing-library/svelte';
import { goto } from '$app/navigation';
import AdminLayoutTestWrapper from '../AdminLayoutTestWrapper.svelte';
import AdminQueuePageTestWrapper from './AdminQueuePageTestWrapper.svelte';
import { getErrorQueue } from '$lib/api/admin';

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
	getErrorQueue: vi.fn()
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

const mockGetErrorQueue = vi.mocked(getErrorQueue);

const mockQueueData = {
	items: [
		{
			document_id: '00000000-0000-0000-0000-000000000001',
			user_id: '00000000-0000-0000-0000-000000000010',
			filename: 'blood_test.pdf',
			upload_date: '2026-03-15T10:00:00Z',
			status: 'failed',
			value_count: 12,
			low_confidence_count: 3,
			flagged_count: 1,
			failed: true
		},
		{
			document_id: '00000000-0000-0000-0000-000000000002',
			user_id: '00000000-0000-0000-0000-000000000020',
			filename: 'lipid_panel.pdf',
			upload_date: '2026-03-14T09:30:00Z',
			status: 'partial',
			value_count: 8,
			low_confidence_count: 2,
			flagged_count: 0,
			failed: false
		}
	],
	total: 2
};

function renderPage() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } }
	});
	return render(AdminQueuePageTestWrapper, { props: { queryClient } });
}

describe('Admin error queue page', () => {
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

	test('page container uses hc-admin-queue-page class', async () => {
		mockGetErrorQueue.mockResolvedValue(mockQueueData);
		const { container } = renderPage();
		await waitFor(() => {
			expect(container.querySelector('.hc-admin-queue-page')).toBeInTheDocument();
		});
	});

	test('shows loading skeleton while fetching', () => {
		mockGetErrorQueue.mockReturnValue(new Promise(() => {}));

		const { container, getByRole } = renderPage();

		expect(getByRole('status', { name: /loading/i })).toBeInTheDocument();
		expect(container.querySelector('.hc-admin-queue-skeleton')).toBeInTheDocument();
	});

	test('refresh button uses btn-standard and invalidates query on click', async () => {
		mockGetErrorQueue.mockResolvedValue(mockQueueData);
		const { getByRole, queryByRole } = renderPage();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const refreshBtn = getByRole('button', { name: /refresh queue/i });
		expect(refreshBtn).toHaveClass('btn-standard');
		expect(mockGetErrorQueue).toHaveBeenCalledTimes(1);

		await fireEvent.click(refreshBtn);
		await waitFor(() => {
			expect(mockGetErrorQueue).toHaveBeenCalledTimes(2);
		});
	});

	test('renders DataTable with correct columns and values', async () => {
		mockGetErrorQueue.mockResolvedValue(mockQueueData);

		const { container, getByText, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		// DataTable wrapper
		expect(container.querySelector('.hc-data-table')).toBeInTheDocument();

		// Check column headers (sortable buttons for many columns)
		expect(getByText('Document ID')).toBeInTheDocument();
		expect(getByText('User ID')).toBeInTheDocument();
		expect(getByText('Filename')).toBeInTheDocument();
		expect(getByText('Upload Date')).toBeInTheDocument();
		expect(getByText('Status')).toBeInTheDocument();
		expect(getByText('Values')).toBeInTheDocument();
		expect(getByText('Low Conf.')).toBeInTheDocument();
		expect(getByText('Flagged')).toBeInTheDocument();
		expect(getByText('Flag Reason')).toBeInTheDocument();

		// Row data rendered
		expect(getByText('blood_test.pdf')).toBeInTheDocument();
		expect(getByText('lipid_panel.pdf')).toBeInTheDocument();
	});

	test('status badges use hc-badge-danger and hc-badge-warning', async () => {
		mockGetErrorQueue.mockResolvedValue(mockQueueData);
		const { container, queryByRole } = renderPage();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const dangerBadge = container.querySelector('.hc-badge.hc-badge-danger');
		const warningBadge = container.querySelector('.hc-badge.hc-badge-warning');
		expect(dangerBadge).toBeInTheDocument();
		expect(dangerBadge?.textContent).toContain('Failed');
		expect(warningBadge).toBeInTheDocument();
		expect(warningBadge?.textContent).toContain('Partial');
	});

	test('low_confidence and flagged count cells apply concerning/action classes when > 0', async () => {
		mockGetErrorQueue.mockResolvedValue(mockQueueData);
		const { container, queryByRole } = renderPage();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		// First row has 3 low_confidence → concerning, 1 flagged → action
		expect(container.querySelector('.hc-admin-queue-count-concerning')).toBeInTheDocument();
		expect(container.querySelector('.hc-admin-queue-count-action')).toBeInTheDocument();
	});

	test('row click navigates to correction detail via goto', async () => {
		mockGetErrorQueue.mockResolvedValue(mockQueueData);
		const { container, queryByRole } = renderPage();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const firstRow = container.querySelector('.hc-data-table tbody tr') as HTMLElement;
		expect(firstRow).toBeInTheDocument();
		await fireEvent.click(firstRow);

		expect(vi.mocked(goto)).toHaveBeenCalledWith(
			'/admin/documents/00000000-0000-0000-0000-000000000001'
		);
	});

	test('shows error state on fetch failure', async () => {
		mockGetErrorQueue.mockRejectedValue(new Error('Network error'));

		const { container, getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		expect(getByRole('alert')).toBeInTheDocument();
		expect(container.querySelector('.hc-state.hc-state-error')).toBeInTheDocument();
		const retryBtn = getByRole('button', { name: /try again|retry/i });
		expect(retryBtn).toHaveClass('btn-standard');
	});

	test('shows empty state when queue is empty with hc-state-empty', async () => {
		mockGetErrorQueue.mockResolvedValue({ items: [], total: 0 });

		const { container, getByText, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		expect(getByText('No documents requiring review')).toBeInTheDocument();
		expect(container.querySelector('.hc-state.hc-state-empty')).toBeInTheDocument();
		expect(container.querySelector('.hc-admin-queue-empty-panel')).toBeInTheDocument();
	});

	test('footer count message uses hc-admin-queue-footer-count', async () => {
		mockGetErrorQueue.mockResolvedValue(mockQueueData);
		const { container, queryByRole } = renderPage();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const footer = container.querySelector('.hc-admin-queue-footer-count');
		expect(footer).toBeInTheDocument();
		expect(footer?.textContent).toContain('Showing 2 documents requiring review');
	});

	test('redirects non-admin users away from the admin area', async () => {
		mockAuthStore.isAuthenticated = true;
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

	test('axe accessibility audit passes', async () => {
		mockGetErrorQueue.mockResolvedValue(mockQueueData);
		const { container, queryByRole } = renderPage();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});

	test('no shadcn-svelte primitive imports exist in page source', async () => {
		// 98.css primitives (data-table, metric-card, etc.) under $lib/components/ui/ are allowed.
		// This guard only blocks the shadcn legacy components.
		const pageSource = await import('./+page.svelte?raw');
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/button['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/input['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/label['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/textarea['/]/);
	});
});
