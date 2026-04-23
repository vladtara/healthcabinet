import { describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { textSnippet } from '$lib/test-utils/snippet';
import Panel from './panel.svelte';

describe('Panel', () => {
	test('renders with sunken variant by default', () => {
		const { container, getByText } = renderComponent(Panel, {
			children: textSnippet('Panel content')
		});
		const panel = container.querySelector('.hc-panel');
		expect(panel).toBeInTheDocument();
		expect(panel?.classList.contains('hc-panel-sunken')).toBe(true);
		expect(panel).toContainElement(getByText('Panel content'));
	});

	test('renders with raised variant', () => {
		const { container } = renderComponent(Panel, { variant: 'raised' });
		const panel = container.querySelector('.hc-panel');
		expect(panel?.classList.contains('hc-panel-raised')).toBe(true);
	});

	test('applies custom class', () => {
		const { container } = renderComponent(Panel, { class: 'flex-1' });
		const panel = container.querySelector('.hc-panel');
		expect(panel?.classList.contains('flex-1')).toBe(true);
	});
});
