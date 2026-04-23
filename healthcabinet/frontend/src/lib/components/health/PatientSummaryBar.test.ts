import axe from 'axe-core';
import { describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import PatientSummaryBar from './PatientSummaryBar.svelte';

function renderSummaryBar(props: Record<string, unknown> = {}) {
	return renderComponent(PatientSummaryBar, {
		email: 'sofia@example.com',
		profile: {
			id: 'p-1', user_id: 'u-1', age: 34, sex: 'female',
			height_cm: 165, weight_kg: 60,
			known_conditions: ['Hashimoto\'s', 'Anemia'],
			medications: [], family_history: null,
			onboarding_step: 3, created_at: '2026-01-01', updated_at: '2026-01-01'
		},
		documentCount: 4,
		biomarkerCount: 18,
		...props
	});
}

describe('PatientSummaryBar', () => {
	test('renders patient name derived from email', () => {
		const { getByText } = renderSummaryBar();
		expect(getByText('Sofia')).toBeInTheDocument();
	});

	test('renders age from profile', () => {
		const { getByText } = renderSummaryBar();
		expect(getByText('34')).toBeInTheDocument();
	});

	test('renders sex from profile', () => {
		const { getByText } = renderSummaryBar();
		expect(getByText('F')).toBeInTheDocument();
	});

	test('renders conditions count', () => {
		const { getByText } = renderSummaryBar();
		expect(getByText(/2 ▼/)).toBeInTheDocument();
	});

	test('renders document count', () => {
		const { getByText } = renderSummaryBar();
		expect(getByText('4')).toBeInTheDocument();
	});

	test('renders biomarker count', () => {
		const { getByText } = renderSummaryBar();
		expect(getByText('18')).toBeInTheDocument();
	});

	test('renders dash when profile is null', () => {
		const { getAllByText } = renderSummaryBar({ profile: null });
		expect(getAllByText('—').length).toBeGreaterThanOrEqual(2);
	});

	test('axe accessibility audit passes', async () => {
		const { container } = renderSummaryBar();
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});
});
