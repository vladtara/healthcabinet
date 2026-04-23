import { waitFor } from '@testing-library/svelte';
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/query-core';
import BiomarkerTrendSectionTestWrapper from './BiomarkerTrendSectionTestWrapper.svelte';

vi.mock('$lib/api/health-values', () => ({
	getHealthValues: vi.fn(),
	getDashboardBaseline: vi.fn(),
	getHealthValueTimeline: vi.fn(),
	flagHealthValue: vi.fn()
}));

vi.mock('$lib/api/client.svelte', () => ({
	tokenState: { accessToken: 'mock-token', setToken: vi.fn(), clear: vi.fn() },
	apiFetch: vi.fn()
}));

import { getHealthValueTimeline } from '$lib/api/health-values';
const mockGetTimeline = vi.mocked(getHealthValueTimeline);

function makeTimelineResponse(values: { value: number; measured_at: string }[]) {
	return {
		biomarker_name: 'TSH',
		canonical_biomarker_name: 'tsh',
		skipped_corrupt_records: 0,
		values: values.map((v, i) => ({
			id: `uuid-${i}`,
			user_id: 'user-uuid',
			document_id: 'doc-uuid',
			biomarker_name: 'TSH',
			canonical_biomarker_name: 'tsh',
			value: v.value,
			unit: 'mIU/L',
			reference_range_low: 0.4,
			reference_range_high: 4.0,
			measured_at: v.measured_at,
			confidence: 0.95,
			needs_review: false,
			is_flagged: false,
			flagged_at: null,
			created_at: v.measured_at,
			status: 'concerning' as const
		}))
	};
}

function renderTrendSection(queryClient?: QueryClient) {
	const qc = queryClient ?? new QueryClient({ defaultOptions: { queries: { retry: false } } });
	return render(BiomarkerTrendSectionTestWrapper, {
		props: { queryClient: qc, canonicalName: 'tsh', hasValues: true }
	});
}

describe('BiomarkerTrendSection', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	test('shows ↑ Increasing when last value > first by >5%', async () => {
		mockGetTimeline.mockResolvedValue(
			makeTimelineResponse([
				{ value: 3.2, measured_at: '2026-01-01T00:00:00Z' },
				{ value: 4.1, measured_at: '2026-04-01T00:00:00Z' },
				{ value: 5.8, measured_at: '2026-07-01T00:00:00Z' }
			])
		);

		const { getByText } = renderTrendSection();

		await waitFor(() => {
			expect(getByText(/Increasing/)).toBeInTheDocument();
		});
		expect(getByText('↑ Increasing')).toBeInTheDocument();
	});

	test('shows ↓ Decreasing when last value < first by >5%', async () => {
		mockGetTimeline.mockResolvedValue(
			makeTimelineResponse([
				{ value: 45.0, measured_at: '2026-01-01T00:00:00Z' },
				{ value: 28.0, measured_at: '2026-04-01T00:00:00Z' },
				{ value: 18.0, measured_at: '2026-07-01T00:00:00Z' }
			])
		);

		const { getByText } = renderTrendSection();

		await waitFor(() => {
			expect(getByText(/Decreasing/)).toBeInTheDocument();
		});
		expect(getByText('↓ Decreasing')).toBeInTheDocument();
	});

	test('shows → Stable when change is within 5%', async () => {
		mockGetTimeline.mockResolvedValue(
			makeTimelineResponse([
				{ value: 100.0, measured_at: '2026-01-01T00:00:00Z' },
				{ value: 101.0, measured_at: '2026-04-01T00:00:00Z' },
				{ value: 103.0, measured_at: '2026-07-01T00:00:00Z' }
			])
		);

		const { getByText } = renderTrendSection();

		await waitFor(() => {
			expect(getByText(/Stable/)).toBeInTheDocument();
		});
		expect(getByText('→ Stable')).toBeInTheDocument();
	});

	test('biomarker name renders as heading', async () => {
		mockGetTimeline.mockResolvedValue(
			makeTimelineResponse([
				{ value: 3.2, measured_at: '2026-01-01T00:00:00Z' },
				{ value: 5.8, measured_at: '2026-07-01T00:00:00Z' }
			])
		);

		const { getByRole } = renderTrendSection();

		await waitFor(() => {
			expect(getByRole('heading', { level: 2 })).toBeInTheDocument();
		});
		expect(getByRole('heading', { level: 2 }).textContent).toBe('TSH');
	});
});
