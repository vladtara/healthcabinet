import { describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import StatusRow from './status-row.svelte';

describe('StatusRow', () => {
	test('renders label', () => {
		const { container } = renderComponent(StatusRow, { label: 'TSH', value: '5.82 mIU/L' });
		expect(container.textContent).toContain('TSH');
	});

	test('renders value', () => {
		const { container } = renderComponent(StatusRow, { label: 'TSH', value: '5.82 mIU/L' });
		expect(container.textContent).toContain('5.82 mIU/L');
	});

	test('renders numeric value', () => {
		const { container } = renderComponent(StatusRow, { label: 'Count', value: 42 });
		expect(container.textContent).toContain('42');
	});

	test('renders status dot and text label when status provided', () => {
		const { container } = renderComponent(StatusRow, {
			label: 'TSH',
			value: '5.82',
			status: 'borderline'
		});
		const dot = container.querySelector('.hc-status-dot');
		expect(dot).toBeInTheDocument();
		expect(dot?.classList.contains('hc-status-dot-borderline')).toBe(true);
		expect(container.textContent).toContain('Borderline');
	});

	test('renders optimal status dot and label', () => {
		const { container } = renderComponent(StatusRow, {
			label: 'T3',
			value: '120',
			status: 'optimal'
		});
		const dot = container.querySelector('.hc-status-dot');
		expect(dot?.classList.contains('hc-status-dot-optimal')).toBe(true);
		expect(container.textContent).toContain('Optimal');
	});

	test('no dot when no status provided', () => {
		const { container } = renderComponent(StatusRow, { label: 'TSH', value: '5.82' });
		const dot = container.querySelector('.hc-status-dot');
		expect(dot).not.toBeInTheDocument();
	});

	test('applies hc-status-row class', () => {
		const { container } = renderComponent(StatusRow, { label: 'Test', value: '0' });
		const el = container.firstElementChild;
		expect(el?.classList.contains('hc-status-row')).toBe(true);
	});

	test('applies custom class', () => {
		const { container } = renderComponent(StatusRow, { label: 'Test', value: '0', class: 'mt-2' });
		const el = container.firstElementChild;
		expect(el?.classList.contains('mt-2')).toBe(true);
	});
});
