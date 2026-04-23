import axe from 'axe-core';
import { describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import PatternAlertSection from './PatternAlertSection.svelte';
import type { PatternObservation } from '$lib/api/ai';

const mockPatterns: PatternObservation[] = [
	{
		description: 'TSH increased 3.2 → 4.1 → 5.8 mIU/L across last 3 results.',
		document_dates: ['2026-03-15', '2026-06-20', '2026-09-10'],
		recommendation: 'Consider discussing thyroid medication with your doctor.'
	},
	{
		description: 'Ferritin declining steadily: 45 → 28 → 18 ng/mL.',
		document_dates: ['2026-01-01', '2026-04-01'],
		recommendation: 'Iron supplementation may be worth discussing.'
	}
];

describe('PatternAlertSection', () => {
	test('renders pattern descriptions when patterns exist', () => {
		const { getByText } = renderComponent(PatternAlertSection, {
			patterns: mockPatterns,
			loading: false,
			error: false
		});

		expect(getByText(/TSH increased/)).toBeInTheDocument();
		expect(getByText(/Ferritin declining/)).toBeInTheDocument();
	});

	test('renders recommendation text for each pattern', () => {
		const { getByText } = renderComponent(PatternAlertSection, {
			patterns: mockPatterns,
			loading: false,
			error: false
		});

		expect(getByText(/thyroid medication/)).toBeInTheDocument();
		expect(getByText(/Iron supplementation/)).toBeInTheDocument();
	});

	test('does not render when patterns array is empty', () => {
		const { container } = renderComponent(PatternAlertSection, {
			patterns: [],
			loading: false,
			error: false
		});

		expect(container.querySelector('.hc-pattern-alert')).toBeNull();
		expect(container.querySelector('.hc-dash-section')).toBeNull();
	});

	test('renders loading skeleton', () => {
		const { container } = renderComponent(PatternAlertSection, {
			patterns: [],
			loading: true,
			error: false
		});

		const skeletons = container.querySelectorAll('[data-skeleton]');
		expect(skeletons.length).toBeGreaterThanOrEqual(1);
	});

	test('renders error message', () => {
		const { getByText } = renderComponent(PatternAlertSection, {
			patterns: [],
			loading: false,
			error: true
		});

		expect(getByText(/unable to load pattern/i)).toBeInTheDocument();
	});

	test('axe accessibility audit passes', async () => {
		const { container } = renderComponent(PatternAlertSection, {
			patterns: mockPatterns,
			loading: false,
			error: false
		});

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});
});
