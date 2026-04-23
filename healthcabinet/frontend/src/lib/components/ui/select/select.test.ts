import { describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { textSnippet } from '$lib/test-utils/snippet';
import Select from './select.svelte';

describe('Select', () => {
	test('renders as select element', () => {
		const { container } = renderComponent(Select);
		const select = container.querySelector('select');
		expect(select).toBeInTheDocument();
		expect(select?.classList.contains('hc-select')).toBe(true);
	});

	test('renders children (option slots)', () => {
		const { container } = renderComponent(Select, {
			children: textSnippet('Option text')
		});
		const select = container.querySelector('select');
		expect(select?.textContent).toContain('Option text');
	});

	test('applies disabled state', () => {
		const { container } = renderComponent(Select, { disabled: true });
		const select = container.querySelector('select');
		expect(select?.disabled).toBe(true);
	});

	test('applies custom class', () => {
		const { container } = renderComponent(Select, { class: 'w-48' });
		const select = container.querySelector('select');
		expect(select?.classList.contains('w-48')).toBe(true);
	});

	test('passes through HTML attributes', () => {
		const { container } = renderComponent(Select, {
			id: 'my-select',
			name: 'country'
		});
		const select = container.querySelector('select');
		expect(select?.id).toBe('my-select');
		expect(select?.name).toBe('country');
	});
});
