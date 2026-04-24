import axe from 'axe-core';
import { describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import StatCardGrid from './StatCardGrid.svelte';

function renderStatGrid(
	counts: {
		optimal: number;
		borderline: number;
		concerning: number;
		action_needed: number;
	} = {
		optimal: 18,
		borderline: 3,
		concerning: 1,
		action_needed: 0
	}
) {
	return renderComponent(StatCardGrid, { counts });
}

describe('StatCardGrid', () => {
	test('renders all 4 stat cards with labels and status classes', () => {
		const { getByText } = renderStatGrid();

		const optimalCard = getByText('Optimal').closest('.hc-stat-card');
		const borderlineCard = getByText('Borderline').closest('.hc-stat-card');
		const concerningCard = getByText('Concerning').closest('.hc-stat-card');
		const actionCard = getByText('Action Needed').closest('.hc-stat-card');

		expect(optimalCard).toHaveClass('hc-stat-card-optimal');
		expect(borderlineCard).toHaveClass('hc-stat-card-borderline');
		expect(concerningCard).toHaveClass('hc-stat-card-concerning');
		expect(actionCard).toHaveClass('hc-stat-card-action');
	});

	test('displays correct counts', () => {
		const { getByText } = renderStatGrid({
			optimal: 12,
			borderline: 4,
			concerning: 2,
			action_needed: 1
		});

		expect(getByText('12')).toBeInTheDocument();
		expect(getByText('4')).toBeInTheDocument();
		expect(getByText('2')).toBeInTheDocument();
		expect(getByText('1')).toBeInTheDocument();
	});

	test('handles zero counts gracefully', () => {
		const { container } = renderStatGrid({
			optimal: 0,
			borderline: 0,
			concerning: 0,
			action_needed: 0
		});

		const countValues = Array.from(container.querySelectorAll('.hc-stat-card-count')).map(
			(element) => element.textContent?.trim()
		);
		expect(countValues).toEqual(['0', '0', '0', '0']);
	});

	test('handles missing counts prop values safely', () => {
		const { container } = renderComponent(StatCardGrid, {
			counts: { optimal: 3 }
		});
		const countValues = Array.from(container.querySelectorAll('.hc-stat-card-count')).map(
			(element) => element.textContent?.trim()
		);
		expect(countValues).toEqual(['3', '0', '0', '0']);
	});

	test('normalizes invalid count values', () => {
		const { container } = renderComponent(StatCardGrid, {
			counts: {
				optimal: -2,
				borderline: Number.NaN,
				concerning: 3.9,
				action_needed: Number.POSITIVE_INFINITY
			}
		});
		const countValues = Array.from(container.querySelectorAll('.hc-stat-card-count')).map(
			(element) => element.textContent?.trim()
		);
		expect(countValues).toEqual(['0', '0', '3', '0']);
	});

	test('axe accessibility audit passes', async () => {
		const { container } = renderStatGrid();
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});
});
