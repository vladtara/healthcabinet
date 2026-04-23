import { describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { textSnippet } from '$lib/test-utils/snippet';
import Badge from './badge.svelte';

describe('Badge', () => {
	test('renders with default variant', () => {
		const { container, getByText } = renderComponent(Badge, {
			children: textSnippet('Active')
		});
		const badge = container.querySelector('.hc-badge');
		expect(badge).toBeInTheDocument();
		expect(badge?.classList.contains('hc-badge-default')).toBe(true);
		expect(badge).toContainElement(getByText('Active'));
	});

	test('renders info variant', () => {
		const { container } = renderComponent(Badge, {
			variant: 'info',
			children: textSnippet('Info')
		});
		const badge = container.querySelector('.hc-badge');
		expect(badge?.classList.contains('hc-badge-info')).toBe(true);
	});

	test('renders success variant', () => {
		const { container } = renderComponent(Badge, {
			variant: 'success',
			children: textSnippet('Optimal')
		});
		const badge = container.querySelector('.hc-badge');
		expect(badge?.classList.contains('hc-badge-success')).toBe(true);
	});

	test('renders warning variant', () => {
		const { container } = renderComponent(Badge, {
			variant: 'warning',
			children: textSnippet('Borderline')
		});
		const badge = container.querySelector('.hc-badge');
		expect(badge?.classList.contains('hc-badge-warning')).toBe(true);
	});

	test('renders danger variant', () => {
		const { container } = renderComponent(Badge, {
			variant: 'danger',
			children: textSnippet('Action')
		});
		const badge = container.querySelector('.hc-badge');
		expect(badge?.classList.contains('hc-badge-danger')).toBe(true);
	});

	test('applies custom class', () => {
		const { container } = renderComponent(Badge, {
			class: 'ml-2',
			children: textSnippet('Custom')
		});
		const badge = container.querySelector('.hc-badge');
		expect(badge?.classList.contains('ml-2')).toBe(true);
	});

	test('renders as span element', () => {
		const { container } = renderComponent(Badge, {
			children: textSnippet('Tag')
		});
		const badge = container.querySelector('.hc-badge');
		expect(badge?.tagName).toBe('SPAN');
	});
});
