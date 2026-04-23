import axe from 'axe-core';
import { fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { QueryClient } from '@tanstack/query-core';
import { render } from '@testing-library/svelte';
import AdminCorrectionPageTestWrapper from './AdminCorrectionPageTestWrapper.svelte';
import { getDocumentForCorrection, submitCorrection } from '$lib/api/admin';

const mockAuthStore = vi.hoisted(() => ({
	isAuthenticated: true,
	user: {
		id: 'admin-1',
		email: 'admin@example.com',
		role: 'admin' as const,
		tier: 'paid' as const
	}
}));

// Create a mock store before vi.mock calls so it's available when vi.mock runs
const mockPageData = {
	params: { document_id: '00000000-0000-0000-0000-000000000001' },
	url: new URL('http://test/admin/documents/00000000-0000-0000-0000-000000000001')
};
const mockPageStore = vi.hoisted(() => {
	let subscriber: (value: typeof mockPageData) => void;
	return {
		subscribe: (fn: (value: typeof mockPageData) => void) => {
			subscriber = fn;
			fn(mockPageData);
			return () => {};
		}
	};
});

vi.mock('$lib/api/admin', () => ({
	getDocumentForCorrection: vi.fn(),
	submitCorrection: vi.fn()
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

const mockGetDocumentForCorrection = vi.mocked(getDocumentForCorrection);
const mockSubmitCorrection = vi.mocked(submitCorrection);

const mockDocumentDetail = {
	document_id: '00000000-0000-0000-0000-000000000001',
	user_id: '00000000-0000-0000-0000-000000000010',
	filename: 'blood_test.pdf',
	upload_date: '2026-03-15T10:00:00Z',
	status: 'partial',
	values: [
		{
			id: '00000000-0000-0000-0000-000000000100',
			biomarker_name: 'Cholesterol',
			canonical_biomarker_name: 'cholesterol_total',
			value: 5.4,
			unit: 'mmol/L',
			reference_range_low: 3.0,
			reference_range_high: 5.0,
			confidence: 0.45,
			needs_review: true,
			is_flagged: false,
			flagged_at: null
		},
		{
			id: '00000000-0000-0000-0000-000000000101',
			biomarker_name: 'HDL Cholesterol',
			canonical_biomarker_name: 'cholesterol_hdl',
			value: 1.2,
			unit: 'mmol/L',
			reference_range_low: 1.0,
			reference_range_high: 1.5,
			confidence: 0.92,
			needs_review: false,
			is_flagged: true,
			flagged_at: '2026-03-16T08:00:00Z'
		}
	]
};

function renderPage() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } }
	});
	return render(AdminCorrectionPageTestWrapper, { props: { queryClient } });
}

describe('Admin document correction page', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockAuthStore.isAuthenticated = true;
		mockAuthStore.user = {
			id: 'admin-1',
			email: 'admin@example.com',
			role: 'admin',
			tier: 'paid'
		};
		mockPageData.url = new URL(
			'http://test/admin/documents/00000000-0000-0000-0000-000000000001'
		);
	});

	test('page container uses hc-admin-correction-page class', async () => {
		mockGetDocumentForCorrection.mockResolvedValue(mockDocumentDetail);
		const { container } = renderPage();
		await waitFor(() => {
			expect(container.querySelector('.hc-admin-correction-page')).toBeInTheDocument();
		});
	});

	test('back button uses btn-standard with plain text (no svg icon)', async () => {
		mockGetDocumentForCorrection.mockResolvedValue(mockDocumentDetail);
		const { container, getByRole } = renderPage();
		await waitFor(() => {
			expect(container.querySelector('.hc-admin-correction-back-row')).toBeInTheDocument();
		});
		const backBtn = getByRole('button', { name: /back to extraction error queue/i });
		expect(backBtn).toHaveClass('btn-standard');
		// No svg icons inside the back button
		expect(backBtn.querySelector('svg')).toBeNull();
	});

	test('metadata wrapped in hc-fieldset with Document legend', async () => {
		mockGetDocumentForCorrection.mockResolvedValue(mockDocumentDetail);
		const { container, queryByRole } = renderPage();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const legend = container.querySelector('.hc-fieldset > legend');
		expect(legend?.textContent).toContain('Document');
		expect(container.querySelector('.hc-admin-correction-meta-grid')).toBeInTheDocument();
	});

	test('renders document metadata and health values', async () => {
		mockGetDocumentForCorrection.mockResolvedValue(mockDocumentDetail);

		const { getByText, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		// Check document metadata
		expect(getByText('blood_test.pdf')).toBeInTheDocument();
		expect(getByText('Partial')).toBeInTheDocument();

		// Check health values
		expect(getByText('Cholesterol')).toBeInTheDocument();
		expect(getByText('HDL Cholesterol')).toBeInTheDocument();
	});

	test('shows loading skeleton while fetching', () => {
		mockGetDocumentForCorrection.mockReturnValue(new Promise(() => {}));

		const { container, getByRole } = renderPage();

		expect(getByRole('status', { name: /loading/i })).toBeInTheDocument();
		expect(container.querySelector('.hc-admin-correction-skeleton')).toBeInTheDocument();
	});

	test('shows error state on fetch failure with hc-state-error', async () => {
		mockGetDocumentForCorrection.mockRejectedValue(new Error('Network error'));

		const { container, getByRole, queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		expect(getByRole('alert')).toBeInTheDocument();
		expect(container.querySelector('.hc-state.hc-state-error')).toBeInTheDocument();
	});

	test('low confidence values use hc-badge-warning with percentage text', async () => {
		mockGetDocumentForCorrection.mockResolvedValue(mockDocumentDetail);
		const { container, queryByRole } = renderPage();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		// Cholesterol confidence 0.45 < 0.7 → warning badge with "45%"
		const warningBadges = container.querySelectorAll('.hc-badge.hc-badge-warning');
		const confidenceBadge = Array.from(warningBadges).find((el) =>
			el.textContent?.includes('45%')
		);
		expect(confidenceBadge).toBeTruthy();
	});

	test('flagged values use hc-badge-danger with User-flagged text', async () => {
		mockGetDocumentForCorrection.mockResolvedValue(mockDocumentDetail);
		const { container, queryByRole } = renderPage();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const flaggedBadge = container.querySelector('.hc-badge.hc-badge-danger');
		expect(flaggedBadge?.textContent).toContain('User-flagged');
	});

	test('highlights target row with hc-admin-correction-row-highlight when health_value_id query param matches', async () => {
		const targetValueId = '00000000-0000-0000-0000-000000000101';
		mockPageData.url = new URL(
			`http://test/admin/documents/00000000-0000-0000-0000-000000000001?health_value_id=${targetValueId}`
		);
		mockGetDocumentForCorrection.mockResolvedValue(mockDocumentDetail);

		const { queryByRole } = renderPage();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const highlightedRow = document.getElementById(`hv-row-${targetValueId}`);
		expect(highlightedRow).toBeTruthy();
		expect(highlightedRow?.className).toContain('hc-admin-correction-row-highlight');
	});

	test('correction inputs use hc-input class and have accessible labels', async () => {
		mockGetDocumentForCorrection.mockResolvedValue(mockDocumentDetail);
		const { container, getByLabelText, queryByRole } = renderPage();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		// 2 values → 2 rows → 2 new-value inputs + 2 reason inputs = 4 inputs total
		const valueInputs = container.querySelectorAll('.hc-admin-correction-input-value.hc-input');
		const reasonInputs = container.querySelectorAll('.hc-admin-correction-input-reason.hc-input');
		expect(valueInputs.length).toBe(2);
		expect(reasonInputs.length).toBe(2);

		const firstValueInput = getByLabelText('New value for Cholesterol') as HTMLInputElement;
		const firstReasonInput = getByLabelText(
			'Correction reason for Cholesterol'
		) as HTMLInputElement;
		expect(firstValueInput).toHaveClass('hc-input', 'hc-admin-correction-input-value');
		expect(firstReasonInput).toHaveClass('hc-input', 'hc-admin-correction-input-reason');
		expect(firstValueInput.getAttribute('aria-label')).toBe('New value for Cholesterol');
		expect(firstReasonInput.getAttribute('aria-label')).toBe(
			'Correction reason for Cholesterol'
		);
	});

	test('submit buttons use btn-primary and are disabled when reason is empty', async () => {
		mockGetDocumentForCorrection.mockResolvedValue(mockDocumentDetail);
		const { queryByRole } = renderPage();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const submitButtons = Array.from(document.querySelectorAll('button')).filter((btn) =>
			btn.textContent?.includes('Submit Correction')
		);
		expect(submitButtons.length).toBe(2);
		submitButtons.forEach((btn) => {
			expect(btn).toHaveClass('btn-primary');
			expect(btn).toBeDisabled();
		});
	});

	test('submit button enables when value + reason valid, submits via submitCorrection', async () => {
		mockGetDocumentForCorrection.mockResolvedValue(mockDocumentDetail);
		mockSubmitCorrection.mockResolvedValue({
			audit_log_id: '00000000-0000-0000-0000-000000000900',
			health_value_id: '00000000-0000-0000-0000-000000000100',
			value_name: 'Glucose',
			original_value: 4.5,
			new_value: 5.0,
			corrected_at: '2026-04-15T12:00:00Z'
		});

		const { container, queryByRole } = renderPage();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const valueInputs = container.querySelectorAll<HTMLInputElement>(
			'.hc-admin-correction-input-value'
		);
		const reasonInputs = container.querySelectorAll<HTMLInputElement>(
			'.hc-admin-correction-input-reason'
		);
		await fireEvent.input(valueInputs[0], { target: { value: '5.0' } });
		await fireEvent.input(reasonInputs[0], { target: { value: 'OCR misread' } });

		const submitButtons = Array.from(document.querySelectorAll('button')).filter((btn) =>
			btn.textContent?.includes('Submit Correction')
		) as HTMLButtonElement[];

		await waitFor(() => {
			expect(submitButtons[0]).not.toBeDisabled();
		});

		await fireEvent.click(submitButtons[0]);

		await waitFor(() => {
			expect(mockSubmitCorrection).toHaveBeenCalledWith(
				'00000000-0000-0000-0000-000000000001',
				'00000000-0000-0000-0000-000000000100',
				{ new_value: 5.0, reason: 'OCR misread' }
			);
		});

		// After success, the correction column should show .hc-admin-correction-success
		await waitFor(() => {
			expect(container.querySelector('.hc-admin-correction-success')).toBeInTheDocument();
		});
	});

	test('submit error renders in hc-admin-correction-field-error with role=alert', async () => {
		mockGetDocumentForCorrection.mockResolvedValue(mockDocumentDetail);
		mockSubmitCorrection.mockRejectedValue(new Error('Backend exploded'));

		const { container, queryByRole } = renderPage();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const valueInputs = container.querySelectorAll<HTMLInputElement>(
			'.hc-admin-correction-input-value'
		);
		const reasonInputs = container.querySelectorAll<HTMLInputElement>(
			'.hc-admin-correction-input-reason'
		);
		await fireEvent.input(valueInputs[0], { target: { value: '5.0' } });
		await fireEvent.input(reasonInputs[0], { target: { value: 'Fix' } });

		const submitButtons = Array.from(document.querySelectorAll('button')).filter((btn) =>
			btn.textContent?.includes('Submit Correction')
		) as HTMLButtonElement[];

		await waitFor(() => {
			expect(submitButtons[0]).not.toBeDisabled();
		});

		await fireEvent.click(submitButtons[0]);

		await waitFor(() => {
			const errorEl = container.querySelector('.hc-admin-correction-field-error');
			expect(errorEl).toBeInTheDocument();
			expect(errorEl).toHaveAttribute('role', 'alert');
			expect(errorEl?.textContent).toContain('Backend exploded');
		});
	});

	test('axe accessibility audit passes', async () => {
		mockGetDocumentForCorrection.mockResolvedValue(mockDocumentDetail);
		const { container, queryByRole } = renderPage();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});

	test('no shadcn-svelte primitive imports exist in page source', async () => {
		// 98.css primitives under $lib/components/ui/ (confirm-dialog, data-table, etc.) are allowed.
		const pageSource = await import('./+page.svelte?raw');
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/button['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/input['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/label['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/textarea['/]/);
		expect(pageSource.default).not.toMatch(/style=["']text-align:/);
	});
});
