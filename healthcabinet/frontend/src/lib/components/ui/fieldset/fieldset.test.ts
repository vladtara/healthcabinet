import { describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { textSnippet } from '$lib/test-utils/snippet';
import Fieldset from './fieldset.svelte';

describe('Fieldset', () => {
	test('renders as fieldset element', () => {
		const { container } = renderComponent(Fieldset, {
			children: textSnippet('Form fields')
		});
		const fieldset = container.querySelector('fieldset');
		expect(fieldset).toBeInTheDocument();
		expect(fieldset?.classList.contains('hc-fieldset')).toBe(true);
	});

	test('renders legend text', () => {
		const { container } = renderComponent(Fieldset, {
			legend: 'Personal Info',
			children: textSnippet('Fields')
		});
		const legend = container.querySelector('legend');
		expect(legend).toBeInTheDocument();
		expect(legend?.textContent).toBe('Personal Info');
	});

	test('omits legend when not provided', () => {
		const { container } = renderComponent(Fieldset, {
			children: textSnippet('Fields')
		});
		const legend = container.querySelector('legend');
		expect(legend).not.toBeInTheDocument();
	});

	test('renders children content', () => {
		const { getByText } = renderComponent(Fieldset, {
			children: textSnippet('Child content')
		});
		expect(getByText('Child content')).toBeInTheDocument();
	});

	test('supports disabled state', () => {
		const { container } = renderComponent(Fieldset, {
			disabled: true,
			children: textSnippet('Fields')
		});
		const fieldset = container.querySelector('fieldset') as HTMLFieldSetElement;
		expect(fieldset?.disabled).toBe(true);
	});

	test('applies custom class', () => {
		const { container } = renderComponent(Fieldset, {
			class: 'mb-4',
			children: textSnippet('Fields')
		});
		const fieldset = container.querySelector('fieldset');
		expect(fieldset?.classList.contains('mb-4')).toBe(true);
	});
});
