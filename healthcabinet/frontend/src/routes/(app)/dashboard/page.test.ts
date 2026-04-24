import { fireEvent, waitFor } from '@testing-library/svelte';
import axe from 'axe-core';
import { afterAll, describe, expect, test, vi, beforeEach } from 'vitest';
import { QueryClient } from '@tanstack/query-core';
import { render } from '@testing-library/svelte';
import DashboardPageTestWrapper from './DashboardPageTestWrapper.svelte';

vi.mock('$lib/api/health-values', () => ({
	getDashboardBaseline: vi.fn(),
	flagHealthValue: vi.fn(),
	getHealthValues: vi.fn(),
	getHealthValueTimeline: vi.fn()
}));

vi.mock('$lib/api/documents', () => ({
	listDocuments: vi.fn()
}));

vi.mock('$lib/api/ai', () => ({
	getAiPatterns: vi.fn(),
	getDocumentInterpretation: vi.fn(),
	getDashboardInterpretation: vi.fn(),
	streamAiChat: vi.fn(),
	streamDashboardChat: vi.fn()
}));

vi.mock('$lib/api/users', () => ({
	getProfile: vi.fn()
}));

vi.mock('$lib/api/client.svelte', () => ({
	tokenState: { accessToken: 'mock-token', setToken: vi.fn(), clear: vi.fn() },
	apiFetch: vi.fn(),
	apiStream: vi.fn()
}));

vi.mock('$lib/stores/auth.svelte', () => ({
	authStore: {
		user: { id: 'user-uuid', email: 'sofia@example.com', role: 'user', tier: 'free' },
		isAuthenticated: true
	}
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

import {
	getDashboardBaseline,
	getHealthValues,
	getHealthValueTimeline
} from '$lib/api/health-values';
import { listDocuments } from '$lib/api/documents';
import { getDashboardInterpretation, getDocumentInterpretation } from '$lib/api/ai';
import { getProfile } from '$lib/api/users';
import { goto } from '$app/navigation';
import { dashboardFilterStore } from '$lib/stores/dashboard-filter.svelte';
import { localeStore } from '$lib/stores/locale.svelte';
import { restoreNavigatorLocale, stubNavigatorLocale } from '$lib/test-utils/locale-env';

const mockGetDashboardBaseline = vi.mocked(getDashboardBaseline);
const mockGetHealthValues = vi.mocked(getHealthValues);
const mockGetHealthValueTimeline = vi.mocked(getHealthValueTimeline);
const mockListDocuments = vi.mocked(listDocuments);
const mockGetDocumentInterpretation = vi.mocked(getDocumentInterpretation);
const mockGetDashboardInterpretation = vi.mocked(getDashboardInterpretation);
const mockGetProfile = vi.mocked(getProfile);

const mockBaseline = {
	recommendations: [
		{
			test_name: 'Complete Blood Count (CBC)',
			rationale: 'Screens for anemia, infection, and immune system conditions.',
			frequency: 'Annually',
			category: 'general' as const
		},
		{
			test_name: 'Comprehensive Metabolic Panel',
			rationale: 'Checks kidney/liver function, electrolytes, and blood sugar.',
			frequency: 'Annually',
			category: 'general' as const
		},
		{
			test_name: 'TSH + Free T4 Panel',
			rationale: 'Monitors thyroid hormone levels to guide treatment and dose adjustments.',
			frequency: 'Every 6 months',
			category: 'condition_specific' as const
		}
	],
	has_uploads: false
};

const mockHealthValues = [
	{
		id: 'uuid-1',
		user_id: 'user-uuid',
		document_id: 'doc-uuid',
		biomarker_name: 'Glucose',
		canonical_biomarker_name: 'glucose',
		value: 91.0,
		unit: 'mg/dL',
		reference_range_low: 70.0,
		reference_range_high: 99.0,
		measured_at: null,
		confidence: 0.95,
		needs_review: false,
		is_flagged: false,
		flagged_at: null,
		created_at: '2026-01-01T00:00:00Z',
		status: 'optimal' as const
	},
	{
		id: 'uuid-2',
		user_id: 'user-uuid',
		document_id: 'doc-uuid',
		biomarker_name: 'Cholesterol',
		canonical_biomarker_name: 'cholesterol',
		value: 65.0,
		unit: 'mg/dL',
		reference_range_low: 70.0,
		reference_range_high: 99.0,
		measured_at: null,
		confidence: 0.55,
		needs_review: false,
		is_flagged: false,
		flagged_at: null,
		created_at: '2026-01-01T00:00:00Z',
		status: 'borderline' as const
	}
];

const mockAnalysisDocument = {
	id: 'doc-uuid',
	user_id: 'user-uuid',
	filename: 'analysis.pdf',
	file_size_bytes: 1024,
	file_type: 'application/pdf',
	status: 'completed' as const,
	arq_job_id: null,
	keep_partial: null,
	document_kind: 'analysis' as const,
	needs_date_confirmation: false,
	partial_measured_at_text: null,
	created_at: '2026-01-01T00:00:00Z',
	updated_at: '2026-01-01T00:00:00Z'
};

const mockPlainDocument = {
	id: 'doc-plain',
	user_id: 'user-uuid',
	filename: 'referral.pdf',
	file_size_bytes: 512,
	file_type: 'application/pdf',
	status: 'completed' as const,
	arq_job_id: null,
	keep_partial: null,
	document_kind: 'document' as const,
	needs_date_confirmation: false,
	partial_measured_at_text: null,
	created_at: '2026-01-02T00:00:00Z',
	updated_at: '2026-01-02T00:00:00Z'
};

function renderDashboard() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } }
	});
	return render(DashboardPageTestWrapper, { props: { queryClient } });
}

describe('Dashboard page', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		window.localStorage.clear();
		stubNavigatorLocale(['en-US']);
		localeStore._resetForTests();
		mockGetHealthValues.mockResolvedValue([]);
		mockListDocuments.mockResolvedValue([]);
		mockGetHealthValueTimeline.mockResolvedValue({
			biomarker_name: 'glucose',
			canonical_biomarker_name: 'glucose',
			skipped_corrupt_records: 0,
			values: []
		});
		mockGetDocumentInterpretation.mockResolvedValue({
			document_id: 'doc-uuid',
			interpretation: 'Your results look good.',
			model_version: 'claude-4',
			generated_at: '2026-04-04T12:00:00Z',
			reasoning: null
		});
		mockGetDashboardInterpretation.mockResolvedValue({
			document_id: null,
			document_kind: 'analysis',
			source_document_ids: ['doc-uuid'],
			interpretation: 'Dashboard-wide summary.',
			model_version: 'claude-4',
			generated_at: '2026-04-20T12:00:00Z',
			reasoning: null
		});
		mockGetProfile.mockResolvedValue(null);
		// Reset dashboard filter to default between tests so each starts fresh.
		dashboardFilterStore._resetForTests();
	});

	afterAll(() => {
		restoreNavigatorLocale();
	});

	test('shows skeleton loader while data is loading', () => {
		// Never resolve so we stay in loading state
		mockGetDashboardBaseline.mockReturnValue(new Promise(() => {}));

		const { getByRole } = renderDashboard();

		expect(getByRole('status', { name: /loading/i })).toBeInTheDocument();
	});

	test('renders recommendation cards after successful fetch in empty state', async () => {
		mockGetDashboardBaseline.mockResolvedValue(mockBaseline);
		mockGetHealthValues.mockResolvedValue([]);

		const { getByText, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		expect(getByText('Complete Blood Count (CBC)')).toBeInTheDocument();
		expect(getByText('Comprehensive Metabolic Panel')).toBeInTheDocument();
		expect(getByText('TSH + Free T4 Panel')).toBeInTheDocument();
	});

	test('shows upload CTA in empty state after fetch', async () => {
		mockGetDashboardBaseline.mockResolvedValue(mockBaseline);
		mockGetHealthValues.mockResolvedValue([]);

		const { getByText, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		expect(getByText('Upload your first lab result')).toBeInTheDocument();
		expect(getByText(/trends and insights will appear here/i)).toBeInTheDocument();
	});

	test('empty state shows disclaimer text', async () => {
		mockGetDashboardBaseline.mockResolvedValue(mockBaseline);
		mockGetHealthValues.mockResolvedValue([]);

		const { getByText, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		expect(getByText(/not a medical diagnosis/i)).toBeInTheDocument();
	});

	test('baseline recommendations render inside AI panel', async () => {
		mockGetDashboardBaseline.mockResolvedValue(mockBaseline);
		mockGetHealthValues.mockResolvedValue([]);

		const { container, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const panel = container.querySelector('.hc-dash-section');
		expect(panel).toBeInTheDocument();
		const panelHeader = container.querySelector('.hc-dash-section-header');
		expect(panelHeader).toBeInTheDocument();
		expect(panelHeader!.textContent).toContain('Recommended Tests');
	});

	test('handles fetch error gracefully when both requests fail', async () => {
		mockGetDashboardBaseline.mockRejectedValue(new Error('Network error'));
		mockGetHealthValues.mockRejectedValue(new Error('Network error'));

		const { getByText, getByRole, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		expect(getByText(/unable to load your health data/i)).toBeInTheDocument();
		expect(getByRole('button', { name: /try again/i })).toBeInTheDocument();
	});

	test('passes accessibility audit on loaded empty state', async () => {
		mockGetDashboardBaseline.mockResolvedValue(mockBaseline);
		mockGetHealthValues.mockResolvedValue([]);

		const { container, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	// ── Active state tests (v2 mockup layout) ───────────────────────────────────

	test('renders biomarker table in active state', async () => {
		mockGetDashboardBaseline.mockResolvedValue({ ...mockBaseline, has_uploads: true });
		mockGetHealthValues.mockResolvedValue(mockHealthValues);
		mockListDocuments.mockResolvedValue([mockAnalysisDocument]);

		const { container, getByText, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		expect(getByText('Glucose')).toBeInTheDocument();
		expect(getByText('Cholesterol')).toBeInTheDocument();
		expect(container.querySelector('.hc-data-table')).toBeInTheDocument();
	});

	test('does not render baseline recommendations in active state', async () => {
		mockGetDashboardBaseline.mockResolvedValue({ ...mockBaseline, has_uploads: true });
		mockGetHealthValues.mockResolvedValue(mockHealthValues);
		mockListDocuments.mockResolvedValue([mockAnalysisDocument]);

		const { queryByText, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		expect(queryByText('Complete Blood Count (CBC)')).toBeNull();
	});

	test('PatientSummaryBar renders in active state', async () => {
		mockGetDashboardBaseline.mockResolvedValue({ ...mockBaseline, has_uploads: true });
		mockGetHealthValues.mockResolvedValue(mockHealthValues);
		mockListDocuments.mockResolvedValue([mockAnalysisDocument]);

		const { container, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const summaryBar = container.querySelector('.hc-summary-bar');
		expect(summaryBar).toBeInTheDocument();
	});

	test('Import Document button renders in active state', async () => {
		mockGetDashboardBaseline.mockResolvedValue({ ...mockBaseline, has_uploads: true });
		mockGetHealthValues.mockResolvedValue(mockHealthValues);
		mockListDocuments.mockResolvedValue([mockAnalysisDocument]);

		const { getByText, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		expect(getByText(/Import Document/)).toBeInTheDocument();
	});

	test('Import Document button uses client-side navigation', async () => {
		mockGetDashboardBaseline.mockResolvedValue(mockBaseline);
		mockGetHealthValues.mockResolvedValue([]);

		const { getByText, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const btn = getByText(/Upload Health Document/);
		await fireEvent.click(btn);
		expect(goto).toHaveBeenCalledWith('/documents/upload');
	});

	test('passes accessibility audit on active state', async () => {
		mockGetDashboardBaseline.mockResolvedValue({ ...mockBaseline, has_uploads: true });
		mockGetHealthValues.mockResolvedValue(mockHealthValues);
		mockListDocuments.mockResolvedValue([mockAnalysisDocument]);

		const { container, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	// ── Story 15.3 — dashboard filter, filter-empty state, cache invalidation ──

	test('renders filter radio group with default "analysis" selected in active state', async () => {
		mockGetDashboardBaseline.mockResolvedValue({ ...mockBaseline, has_uploads: true });
		mockGetHealthValues.mockResolvedValue(mockHealthValues);
		mockListDocuments.mockResolvedValue([mockAnalysisDocument]);

		const { getByTestId, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const fieldset = getByTestId('dashboard-filter');
		expect(fieldset).toBeInTheDocument();
		const analysisRadio = fieldset.querySelector(
			'input[value="analysis"]'
		) as HTMLInputElement | null;
		expect(analysisRadio?.checked).toBe(true);
	});

	test('initial load sends document_kind=analysis to getHealthValues', async () => {
		mockGetDashboardBaseline.mockResolvedValue({ ...mockBaseline, has_uploads: true });
		mockGetHealthValues.mockResolvedValue(mockHealthValues);
		mockListDocuments.mockResolvedValue([mockAnalysisDocument]);

		renderDashboard();

		await waitFor(() => {
			expect(mockGetHealthValues).toHaveBeenCalledWith('analysis');
		});
	});

	test('changing filter re-fetches getHealthValues with the new kind', async () => {
		mockGetDashboardBaseline.mockResolvedValue({ ...mockBaseline, has_uploads: true });
		mockGetHealthValues.mockResolvedValue(mockHealthValues);
		mockListDocuments.mockResolvedValue([mockAnalysisDocument, mockPlainDocument]);

		const { getByTestId, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const fieldset = getByTestId('dashboard-filter');
		const allRadio = fieldset.querySelector('input[value="all"]') as HTMLInputElement;
		await fireEvent.change(allRadio, { target: { checked: true, value: 'all' } });
		await fireEvent.click(allRadio);

		await waitFor(() => {
			expect(mockGetHealthValues).toHaveBeenCalledWith('all');
		});
	});

	test('all filter counts matching documents, not only documents with biomarker rows', async () => {
		mockGetDashboardBaseline.mockResolvedValue({ ...mockBaseline, has_uploads: true });
		mockGetHealthValues.mockResolvedValue(mockHealthValues);
		mockListDocuments.mockResolvedValue([mockAnalysisDocument, mockPlainDocument]);

		const { getByTestId, container, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const fieldset = getByTestId('dashboard-filter');
		const allRadio = fieldset.querySelector('input[value="all"]') as HTMLInputElement;
		await fireEvent.change(allRadio, { target: { checked: true, value: 'all' } });
		await fireEvent.click(allRadio);

		await waitFor(() => {
			const summaryText =
				container.querySelector('.hc-summary-bar')?.textContent?.replace(/\s+/g, ' ') ?? '';
			expect(summaryText).toMatch(/Documents:\s*2/);
		});
	});

	test('document filter stays in active mode for plain documents without biomarker rows', async () => {
		dashboardFilterStore.setFilter('document');
		mockGetDashboardBaseline.mockResolvedValue({ ...mockBaseline, has_uploads: true });
		mockGetHealthValues.mockResolvedValue([]);
		mockListDocuments.mockResolvedValue([mockPlainDocument]);
		mockGetDashboardInterpretation.mockResolvedValue({
			document_id: null,
			document_kind: 'document',
			source_document_ids: ['doc-plain'],
			interpretation: 'Referral documents emphasize follow-up with your clinician.',
			model_version: 'claude-4',
			generated_at: '2026-04-20T12:00:00Z',
			reasoning: null
		});

		const { container, getByTestId, getByText, queryByRole, queryByTestId } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		expect(queryByTestId('dashboard-filter-empty')).toBeNull();
		expect(getByTestId('dashboard-biomarker-empty')).toBeInTheDocument();
		expect(
			getByText(/plain documents do not contain extracted biomarker values/i)
		).toBeInTheDocument();
		expect(getByText(/follow-up with your clinician/i)).toBeInTheDocument();
		expect(queryByTestId('dashboard-chat-no-context-hint')).toBeNull();

		const summaryText =
			container.querySelector('.hc-summary-bar')?.textContent?.replace(/\s+/g, ' ') ?? '';
		expect(summaryText).toMatch(/Documents:\s*1/);
		expect(summaryText).toMatch(/Biomarkers:\s*0/);
	});

	test('filter-empty state renders filter-specific copy, not the first-time empty', async () => {
		// User has documents (has_uploads=true) but the active filter matches none.
		mockGetDashboardBaseline.mockResolvedValue({ ...mockBaseline, has_uploads: true });
		mockGetHealthValues.mockResolvedValue([]);

		const { getByTestId, queryByText, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		expect(getByTestId('dashboard-filter-empty')).toBeInTheDocument();
		// First-time copy must NOT appear.
		expect(queryByText('Upload your first lab result')).toBeNull();
	});

	test('filter=analysis with zero rows shows kind-specific copy (not first-time empty)', async () => {
		// Story 15.7 AC2 — when the analysis filter excludes every row, the empty
		// surface must use the analysis-specific copy from messages.ts
		// (`emptyAnalysis`), not the generic filter copy and not the first-time
		// empty CTA. This pins `filterEmptyCopy('analysis')` behavior end-to-end.
		dashboardFilterStore.setFilter('analysis');
		mockGetDashboardBaseline.mockResolvedValue({ ...mockBaseline, has_uploads: true });
		mockGetHealthValues.mockResolvedValue([]);

		const { getByTestId, getByText, queryByText, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		expect(getByTestId('dashboard-filter-empty')).toBeInTheDocument();
		// Kind-specific copy from messages.ts emptyAnalysis.
		expect(
			getByText('No analyses yet — upload a lab result to populate this view')
		).toBeInTheDocument();
		// Generic all-kinds copy must NOT be present under the analysis filter.
		expect(queryByText('No documents match this filter yet')).toBeNull();
		// First-time empty CTA must NOT appear.
		expect(queryByText('Upload your first lab result')).toBeNull();
	});

	test('first-time empty state (no documents at all) still shows upload CTA with filter default', async () => {
		mockGetDashboardBaseline.mockResolvedValue({ ...mockBaseline, has_uploads: false });
		mockGetHealthValues.mockResolvedValue([]);

		const { getByText, queryByTestId, queryByRole } = renderDashboard();

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		// First-time empty (NOT filter-empty).
		expect(getByText('Upload your first lab result')).toBeInTheDocument();
		expect(queryByTestId('dashboard-filter-empty')).toBeNull();
	});

	test('retry() invalidates the dashboard AI query alongside health_values', async () => {
		mockGetDashboardBaseline.mockRejectedValue(new Error('Network error'));
		mockGetHealthValues.mockRejectedValue(new Error('Network error'));

		const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
		const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
		const { getByRole, queryByRole } = render(DashboardPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		const retryBtn = getByRole('button', { name: /try again/i });
		await fireEvent.click(retryBtn);

		expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['ai_dashboard_interpretation'] });
	});

	// ── Story 15.6 — locale coverage (Review Round 2) ─────────────────────────

	test('error message retranslates after setLocale(uk)', async () => {
		mockGetDashboardBaseline.mockRejectedValue(new Error('Network error'));
		mockGetHealthValues.mockRejectedValue(new Error('Network error'));

		const { getByText, findByText } = renderDashboard();

		// en baseline
		await findByText(/unable to load your health data/i);

		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));

		expect(getByText(/Не вдалося завантажити дані/i)).toBeInTheDocument();
	});

	// ── Story 15.7 — recommendation catalog localization ──────────────────────

	test('recommendation rows render Ukrainian under uk and English under en', async () => {
		mockGetDashboardBaseline.mockResolvedValue(mockBaseline);
		mockGetHealthValues.mockResolvedValue([]);

		const { container, queryByRole } = renderDashboard();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		// en baseline — backend English
		const tableEn = container.querySelector('.hc-small-table')!;
		expect(tableEn.textContent).toContain('TSH + Free T4 Panel');
		expect(tableEn.textContent).toContain('Every 6 months');
		expect(tableEn.textContent).toContain(
			'Monitors thyroid hormone levels to guide treatment and dose adjustments.'
		);

		// Flip to uk
		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));

		const tableUk = container.querySelector('.hc-small-table')!;
		expect(tableUk.textContent).toContain('Панель ТТГ + вільний T4');
		expect(tableUk.textContent).toContain('Кожні 6 місяців');
		expect(tableUk.textContent).toContain(
			'Моніторинг рівня гормонів щитоподібної залози для корекції лікування і дози.'
		);
		// English source strings should not leak through.
		expect(tableUk.textContent).not.toContain('TSH + Free T4 Panel');
		expect(tableUk.textContent).not.toContain('Every 6 months');
	});

	test('unknown recommendation test_name falls back to backend English string', async () => {
		const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
		mockGetDashboardBaseline.mockResolvedValue({
			recommendations: [
				{
					test_name: 'Unknown Future Panel',
					rationale: 'A totally new rationale string.',
					frequency: 'Every 90 years',
					category: 'general' as const
				}
			],
			has_uploads: false
		});
		mockGetHealthValues.mockResolvedValue([]);

		const { container, queryByRole } = renderDashboard();
		await waitFor(() => {
			expect(queryByRole('status', { name: /loading/i })).toBeNull();
		});

		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));

		const table = container.querySelector('.hc-small-table')!;
		// Fallback: original English strings render under uk without throwing.
		expect(table.textContent).toContain('Unknown Future Panel');
		expect(table.textContent).toContain('Every 90 years');
		expect(table.textContent).toContain('A totally new rationale string.');
		expect(warnSpy).toHaveBeenCalledWith(
			expect.stringContaining('Missing test_name translation for "Unknown Future Panel"')
		);
	});
});
