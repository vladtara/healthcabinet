import { describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { textSnippet } from '$lib/test-utils/snippet';
import Toolbar from './toolbar.svelte';

describe('Toolbar', () => {
	test('renders with hc-toolbar class', () => {
		const { container, getByText } = renderComponent(Toolbar, {
			children: textSnippet('Toolbar action')
		});
		const toolbar = container.querySelector('.hc-toolbar');
		expect(toolbar).toBeInTheDocument();
		expect(toolbar).toContainElement(getByText('Toolbar action'));
	});

	test('has toolbar role for accessibility', () => {
		const { getByRole } = renderComponent(Toolbar);
		expect(getByRole('toolbar')).toBeInTheDocument();
	});

	test('applies custom class', () => {
		const { container } = renderComponent(Toolbar, { class: 'mb-2' });
		const toolbar = container.querySelector('.hc-toolbar');
		expect(toolbar?.classList.contains('mb-2')).toBe(true);
	});
});
