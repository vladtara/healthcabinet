import axe from 'axe-core';
import { describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import BiomarkerTable from './BiomarkerTable.svelte';
import type { HealthValue } from '$lib/api/health-values';
import { tick } from 'svelte';

function makeValue(overrides: Partial<HealthValue> = {}): HealthValue {
	return {
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
		status: 'optimal',
		...overrides
	};
}

const mockValues: HealthValue[] = [
	makeValue({
		id: 'uuid-1',
		biomarker_name: 'Glucose',
		canonical_biomarker_name: 'glucose',
		value: 91.0,
		status: 'optimal'
	}),
	makeValue({
		id: 'uuid-2',
		biomarker_name: 'Cholesterol',
		canonical_biomarker_name: 'cholesterol',
		value: 65.0,
		status: 'borderline'
	}),
	makeValue({
		id: 'uuid-3',
		biomarker_name: 'TSH',
		canonical_biomarker_name: 'tsh',
		value: 5.8,
		unit: 'mIU/L',
		reference_range_low: 0.4,
		reference_range_high: 4.0,
		status: 'concerning'
	})
];

const mockTimeline: Record<string, HealthValue[]> = {
	glucose: [
		makeValue({ measured_at: '2026-01-01T00:00:00Z', value: 88.0 }),
		makeValue({ measured_at: '2026-02-01T00:00:00Z', value: 91.0 })
	],
	cholesterol: [makeValue({ id: 'uuid-2', canonical_biomarker_name: 'cholesterol', value: 65.0 })],
	tsh: [
		makeValue({
			id: 'uuid-3',
			canonical_biomarker_name: 'tsh',
			value: 3.9,
			measured_at: '2026-01-01T00:00:00Z',
			status: 'optimal'
		}),
		makeValue({
			id: 'uuid-4',
			canonical_biomarker_name: 'tsh',
			value: 4.6,
			measured_at: '2026-03-01T00:00:00Z',
			status: 'borderline'
		}),
		makeValue({
			id: 'uuid-5',
			canonical_biomarker_name: 'tsh',
			value: 5.8,
			measured_at: '2026-06-01T00:00:00Z',
			status: 'concerning'
		})
	]
};

function renderTable(props: Record<string, unknown> = {}) {
	return renderComponent(BiomarkerTable, {
		values: mockValues,
		timelineByBiomarker: mockTimeline,
		...props
	});
}

describe('BiomarkerTable', () => {
	test('renders table with 8 column headers', () => {
		const { container } = renderTable();
		const headers = container.querySelectorAll('thead th');
		expect(headers.length).toBe(8);
	});

	test('renders one row per unique biomarker', () => {
		const { container } = renderTable();
		const rows = container.querySelectorAll<HTMLTableRowElement>('tbody tr.hc-row-interactive');
		expect(rows.length).toBe(3);
	});

	test('displays biomarker name, unit, value in each row', () => {
		const { getByText } = renderTable();
		expect(getByText('Glucose')).toBeInTheDocument();
		expect(getByText('TSH')).toBeInTheDocument();
		expect(getByText('5.8')).toBeInTheDocument();
		expect(getByText('mIU/L')).toBeInTheDocument();
	});

	test('shows status with symbol and label', () => {
		const { getByText } = renderTable();
		expect(getByText(/● Optimal/)).toBeInTheDocument();
		expect(getByText(/⚠ Borderline/)).toBeInTheDocument();
		expect(getByText(/◆ Concerning/)).toBeInTheDocument();
	});

	test('shows trend arrows based on timeline', () => {
		const { container } = renderTable();
		const trendCells = container.querySelectorAll('.hc-v2-trend-cell');
		const trendTexts = Array.from(trendCells).map((c) => c.textContent?.trim());
		// TSH: 3.9 → 5.8 = ~49% increase = ↑↑
		expect(trendTexts).toContain('↑↑');
		// Glucose: 88 → 91 = ~3.4% = →
		expect(trendTexts).toContain('→');
	});

	test('shows sparkline bars with point count', () => {
		const { getByText } = renderTable();
		expect(getByText('3 pts')).toBeInTheDocument(); // TSH has 3 points
		expect(getByText('2 pts')).toBeInTheDocument(); // Glucose has 2 points
	});

	test('shows row left border for non-optimal status', () => {
		const { container } = renderTable();
		expect(container.querySelector('.hc-v2-row-borderline')).toBeInTheDocument();
		expect(container.querySelector('.hc-v2-row-concerning')).toBeInTheDocument();
	});

	test('clicking row expands history table', async () => {
		const { container } = renderTable();
		const rows = container.querySelectorAll<HTMLTableRowElement>('tbody tr.hc-row-interactive');
		// Click TSH row (sorted: Cholesterol, Glucose, TSH — TSH is 3rd)
		rows[2].click();
		await tick();
		const historyPanel = container.querySelector('.hc-v2-history-panel');
		expect(historyPanel).toBeInTheDocument();
		// History table should show dates
		expect(historyPanel!.textContent).toContain('2026-');
	});

	test('only one row expanded at a time', async () => {
		const { container } = renderTable();
		const rows = container.querySelectorAll<HTMLTableRowElement>('tbody tr.hc-row-interactive');
		rows[0].click();
		await tick();
		expect(container.querySelectorAll('.hc-v2-history-panel').length).toBe(1);
		rows[1].click();
		await tick();
		expect(container.querySelectorAll('.hc-v2-history-panel').length).toBe(1);
	});

	test('expand icon toggles between + and −', async () => {
		const { container } = renderTable();
		const rows = container.querySelectorAll<HTMLTableRowElement>('tbody tr.hc-row-interactive');
		const expandIcon = rows[0].querySelector('.hc-v2-expand-icon');
		expect(expandIcon!.textContent?.trim()).toBe('+');
		rows[0].click();
		await tick();
		expect(expandIcon!.textContent?.trim()).toBe('−');
	});

	test('axe accessibility audit passes', async () => {
		const { container } = renderTable();
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});
});
