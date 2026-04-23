import axe from 'axe-core';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/query-core';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import type { HealthValueItem } from '$lib/types/api';
import HealthValueRowTestWrapper from './HealthValueRowTestWrapper.svelte';

vi.mock('$lib/api/health-values', () => ({
	flagHealthValue: vi.fn()
}));

import { flagHealthValue } from '$lib/api/health-values';

const mockFlagHealthValue = vi.mocked(flagHealthValue);

const TEST_DOCUMENT_ID = 'doc-1';

function makeHealthValue(
	overrides: Partial<HealthValueItem> = {}
): HealthValueItem {
	return {
		id: 'hv-1',
		biomarker_name: 'Glucose',
		canonical_biomarker_name: 'glucose',
		value: 95,
		unit: 'mg/dL',
		measured_at: null,
		confidence: 0.95,
		reference_range_low: 70,
		reference_range_high: 100,
		needs_review: true,
		is_flagged: false,
		flagged_at: null,
		...overrides
	};
}

function renderComponent(hv: HealthValueItem = makeHealthValue()) {
	const queryClient = new QueryClient({
		defaultOptions: {
			queries: { retry: false },
			mutations: { retry: false }
		}
	});

	return {
		queryClient,
		...render(HealthValueRowTestWrapper, {
			props: {
				queryClient,
				hv,
				documentId: TEST_DOCUMENT_ID
			}
		})
	};
}

describe('HealthValueRow', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockFlagHealthValue.mockResolvedValue({
			id: 'hv-1',
			is_flagged: true,
			flagged_at: '2026-04-01T12:05:00Z'
		});
	});

	test('renders the reskinned class family for health values', () => {
		const { container } = renderComponent();

		expect(container.querySelector('.hc-health-value-row')).toBeInTheDocument();
		expect(container.querySelector('.hc-health-value-row-header')).toBeInTheDocument();
		expect(container.querySelector('.hc-health-value-row-value-line')).toBeInTheDocument();
		expect(container.querySelector('.hc-health-value-row-confidence')).toHaveTextContent(
			'High confidence'
		);
		expect(container.querySelector('.hc-health-value-row-pill-review')).toHaveTextContent(
			'Needs review'
		);
	});

	test('flagging announces success and invalidates the related queries', async () => {
		const { queryClient } = renderComponent();
		const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');

		await fireEvent.click(
			screen.getByRole('button', {
				name: /flag glucose as potentially incorrect/i
			})
		);

		await waitFor(() => {
			expect(mockFlagHealthValue).toHaveBeenCalledWith('hv-1');
		});

		await waitFor(() => {
			expect(screen.getByText("Thanks — we'll review this value")).toBeInTheDocument();
		});

		expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['documents', 'doc-1'] });
		expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['health_values'] });
		expect(
			screen.getByLabelText(/glucose flagged for review/i)
		).toHaveTextContent('Flagged');
	});

	test('passes axe accessibility audit', async () => {
		const { container } = renderComponent();
		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});

	test('source keeps the section-prefixed class family and no legacy hvr alias', async () => {
		const source = await import('./HealthValueRow.svelte?raw');

		expect(source.default).toContain('hc-health-value-row');
		expect(source.default).not.toContain('hc-hvr-');
		expect(source.default).not.toMatch(/class="[^"]*\b(?:inline-flex|gap-1|text-xs|font-medium)\b/);
	});
});
