import { render } from '@testing-library/svelte';
import axe from 'axe-core';
import { describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import BiomarkerTrendChart from './BiomarkerTrendChart.svelte';

const twoPoints = [
	{ date: '2026-01-01T00:00:00Z', value: 91.0, unit: 'mg/dL' },
	{ date: '2026-02-01T00:00:00Z', value: 88.0, unit: 'mg/dL' }
];

const onePoint = [{ date: '2026-01-01T00:00:00Z', value: 91.0, unit: 'mg/dL' }];

describe('BiomarkerTrendChart', () => {
	// ── Disabled state (< 2 points) ──────────────────────────────────────────

	test('renders disabled state with fewer than 2 points', () => {
		const { getByText } = renderComponent(BiomarkerTrendChart, {
			points: onePoint,
			biomarkerName: 'Glucose'
		});

		expect(getByText(/upload another document to unlock trends/i)).toBeInTheDocument();
	});

	test('disabled state has no NaN in SVG', () => {
		const { container } = renderComponent(BiomarkerTrendChart, {
			points: onePoint,
			biomarkerName: 'Glucose'
		});

		const svgs = container.querySelectorAll('svg');
		svgs.forEach((svg) => {
			expect(svg.innerHTML).not.toContain('NaN');
		});
	});

	test('disabled state has no real chart axes', () => {
		const { container } = renderComponent(BiomarkerTrendChart, {
			points: onePoint,
			biomarkerName: 'Glucose'
		});

		// Should not contain polyline (real chart data line)
		const polylines = container.querySelectorAll('polyline');
		expect(polylines.length).toBe(0);
	});

	// ── Active state (≥ 2 points) ────────────────────────────────────────────

	test('renders active state with 2+ points — figure element present', () => {
		const { container } = renderComponent(BiomarkerTrendChart, {
			points: twoPoints,
			biomarkerName: 'Glucose'
		});

		const figure = container.querySelector('figure');
		expect(figure).toBeInTheDocument();
	});

	test('renders active state with 2+ points — figcaption present', () => {
		const { container } = renderComponent(BiomarkerTrendChart, {
			points: twoPoints,
			biomarkerName: 'Glucose'
		});

		const figcaption = container.querySelector('figcaption');
		expect(figcaption).toBeInTheDocument();
		expect(figcaption?.textContent).toContain('Glucose');
	});

	test('active state renders polyline (trend line)', () => {
		const { container } = renderComponent(BiomarkerTrendChart, {
			points: twoPoints,
			biomarkerName: 'Glucose'
		});

		const polyline = container.querySelector('polyline');
		expect(polyline).toBeInTheDocument();

		// No NaN in coordinates
		const points = polyline?.getAttribute('points') ?? '';
		expect(points).not.toContain('NaN');
	});

	test('active state has no NaN in SVG', () => {
		const { container } = renderComponent(BiomarkerTrendChart, {
			points: twoPoints,
			biomarkerName: 'Glucose'
		});

		const svgs = container.querySelectorAll('svg');
		svgs.forEach((svg) => {
			expect(svg.innerHTML).not.toContain('NaN');
		});
	});

	// ── Accessible data table ────────────────────────────────────────────────

	test('accessible data table exists in details element (active state)', () => {
		const { container } = renderComponent(BiomarkerTrendChart, {
			points: twoPoints,
			biomarkerName: 'Glucose'
		});

		const details = container.querySelector('details');
		expect(details).toBeInTheDocument();

		const table = details?.querySelector('table');
		expect(table).toBeInTheDocument();

		const rows = table?.querySelectorAll('tbody tr');
		expect(rows?.length).toBe(2);
	});

	test('accessible data table exists in details element (disabled state)', () => {
		const { container } = renderComponent(BiomarkerTrendChart, {
			points: onePoint,
			biomarkerName: 'Glucose'
		});

		const details = container.querySelector('details');
		expect(details).toBeInTheDocument();

		const table = details?.querySelector('table');
		expect(table).toBeInTheDocument();

		const rows = table?.querySelectorAll('tbody tr');
		expect(rows?.length).toBe(1);
	});

	// ── Accessibility (axe-core) ─────────────────────────────────────────────

	test('passes axe-core audit on disabled state', async () => {
		const { container } = renderComponent(BiomarkerTrendChart, {
			points: onePoint,
			biomarkerName: 'Glucose'
		});

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	test('passes axe-core audit on active state', async () => {
		const { container } = renderComponent(BiomarkerTrendChart, {
			points: twoPoints,
			biomarkerName: 'Glucose',
			referenceRangeLow: 70,
			referenceRangeHigh: 99,
			unit: 'mg/dL'
		});

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	// ── Sparkline variant ────────────────────────────────────────────────────

	test('sparkline variant renders SVG with aria-hidden', () => {
		const { container } = renderComponent(BiomarkerTrendChart, {
			points: twoPoints,
			biomarkerName: 'Glucose',
			variant: 'sparkline'
		});

		const svg = container.querySelector('svg');
		expect(svg).toBeInTheDocument();
		expect(svg?.getAttribute('aria-hidden')).toBe('true');
	});

	test('sparkline variant renders polyline with no NaN', () => {
		const { container } = renderComponent(BiomarkerTrendChart, {
			points: twoPoints,
			biomarkerName: 'Glucose',
			variant: 'sparkline'
		});

		const polyline = container.querySelector('polyline');
		expect(polyline).toBeInTheDocument();
		const pts = polyline?.getAttribute('points') ?? '';
		expect(pts).not.toContain('NaN');
	});
});
