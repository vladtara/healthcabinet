import { describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { textSnippet } from '$lib/test-utils/snippet';
import MetricCard from './metric-card.svelte';

describe('MetricCard', () => {
	test('renders label', () => {
		const { container } = renderComponent(MetricCard, { label: 'Total Uploads', value: 42 });
		expect(container.textContent).toContain('Total Uploads');
	});

	test('renders numeric value', () => {
		const { container } = renderComponent(MetricCard, { label: 'Count', value: 1234 });
		expect(container.textContent).toContain('1234');
	});

	test('renders string value', () => {
		const { container } = renderComponent(MetricCard, { label: 'Rate', value: '95.2%' });
		expect(container.textContent).toContain('95.2%');
	});

	test('renders children snippet', () => {
		const { container } = renderComponent(MetricCard, {
			label: 'Trend',
			value: 42,
			children: textSnippet('↑ 12%')
		});
		expect(container.textContent).toContain('↑ 12%');
	});

	test('applies hc-metric-card class', () => {
		const { container } = renderComponent(MetricCard, { label: 'Test', value: 0 });
		const el = container.firstElementChild;
		expect(el?.classList.contains('hc-metric-card')).toBe(true);
	});

	test('has label and value elements with correct classes', () => {
		const { container } = renderComponent(MetricCard, { label: 'Metric', value: 99 });
		expect(container.querySelector('.hc-metric-label')).toBeInTheDocument();
		expect(container.querySelector('.hc-metric-value')).toBeInTheDocument();
	});

	test('applies custom class', () => {
		const { container } = renderComponent(MetricCard, { label: 'Test', value: 0, class: 'my-card' });
		const el = container.firstElementChild;
		expect(el?.classList.contains('my-card')).toBe(true);
	});
});
