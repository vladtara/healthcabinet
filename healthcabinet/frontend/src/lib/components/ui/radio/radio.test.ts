import { describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { textSnippet } from '$lib/test-utils/snippet';
import Radio from './radio.svelte';
import RadioGroup from './radio-group.svelte';

describe('Radio', () => {
	test('renders as radio input', () => {
		const { container } = renderComponent(Radio, { name: 'sex', value: 'male' });
		const radio = container.querySelector('input[type="radio"]');
		expect(radio).toBeInTheDocument();
		expect(radio?.classList.contains('hc-radio')).toBe(true);
	});

	test('applies custom class', () => {
		const { container } = renderComponent(Radio, { class: 'mr-2' });
		const radio = container.querySelector('input[type="radio"]');
		expect(radio?.classList.contains('mr-2')).toBe(true);
	});

	test('supports disabled state', () => {
		const { container } = renderComponent(Radio, { disabled: true });
		const radio = container.querySelector('input[type="radio"]') as HTMLInputElement;
		expect(radio?.disabled).toBe(true);
	});

	test('passes through name and value attributes', () => {
		const { container } = renderComponent(Radio, { name: 'color', value: 'blue' });
		const radio = container.querySelector('input[type="radio"]') as HTMLInputElement;
		expect(radio?.name).toBe('color');
		expect(radio?.value).toBe('blue');
	});
});

describe('RadioGroup', () => {
	test('renders as fieldset', () => {
		const { container } = renderComponent(RadioGroup, {
			children: textSnippet('Radio options')
		});
		const fieldset = container.querySelector('fieldset');
		expect(fieldset).toBeInTheDocument();
		expect(fieldset?.classList.contains('hc-radio-group')).toBe(true);
	});

	test('renders legend text', () => {
		const { container } = renderComponent(RadioGroup, {
			legend: 'Choose one',
			children: textSnippet('Options')
		});
		const legend = container.querySelector('legend');
		expect(legend).toBeInTheDocument();
		expect(legend?.textContent).toBe('Choose one');
	});

	test('omits legend when not provided', () => {
		const { container } = renderComponent(RadioGroup, {
			children: textSnippet('Options')
		});
		const legend = container.querySelector('legend');
		expect(legend).not.toBeInTheDocument();
	});

	test('defaults to vertical direction', () => {
		const { container } = renderComponent(RadioGroup, {
			children: textSnippet('Options')
		});
		const fieldset = container.querySelector('fieldset');
		expect(fieldset?.classList.contains('hc-radio-group-vertical')).toBe(true);
	});

	test('supports horizontal direction', () => {
		const { container } = renderComponent(RadioGroup, {
			direction: 'horizontal',
			children: textSnippet('Options')
		});
		const fieldset = container.querySelector('fieldset');
		expect(fieldset?.classList.contains('hc-radio-group-horizontal')).toBe(true);
	});

	test('applies custom class', () => {
		const { container } = renderComponent(RadioGroup, {
			class: 'mt-4',
			children: textSnippet('Options')
		});
		const fieldset = container.querySelector('fieldset');
		expect(fieldset?.classList.contains('mt-4')).toBe(true);
	});

	test('supports disabled state', () => {
		const { container } = renderComponent(RadioGroup, {
			disabled: true,
			children: textSnippet('Options')
		});
		const fieldset = container.querySelector('fieldset') as HTMLFieldSetElement;
		expect(fieldset?.disabled).toBe(true);
	});
});
