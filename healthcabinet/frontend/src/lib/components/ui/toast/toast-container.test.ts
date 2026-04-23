import axe from 'axe-core';
import { describe, expect, test, afterEach } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import ToastContainer from './ToastContainer.svelte';
import { feedbackStore, showSuccess, showError, clearAll } from '$lib/stores/feedback.svelte';

describe('ToastContainer', () => {
	afterEach(() => {
		clearAll();
	});

	test('renders always-present aria-live container', () => {
		const { container } = renderComponent(ToastContainer);
		const wrapper = container.querySelector('[aria-live="polite"]');
		expect(wrapper).toBeInTheDocument();
		expect(wrapper!.getAttribute('aria-label')).toBe('Notifications');
	});

	test('renders no toasts when store is empty', () => {
		const { container } = renderComponent(ToastContainer);
		expect(container.querySelectorAll('.hc-toast')).toHaveLength(0);
	});

	test('renders multiple toasts from store', () => {
		showSuccess('First');
		showError('Second');

		const { container } = renderComponent(ToastContainer);
		const toasts = container.querySelectorAll('.hc-toast');
		expect(toasts).toHaveLength(2);
	});

	test('renders correct toast types', () => {
		showSuccess('OK');
		showError('Fail');

		const { container } = renderComponent(ToastContainer);
		expect(container.querySelector('.hc-toast-success')).toBeInTheDocument();
		expect(container.querySelector('.hc-toast-error')).toBeInTheDocument();
	});

	test('is accessible (axe audit)', async () => {
		showSuccess('Test toast');
		const { container } = renderComponent(ToastContainer);
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});
});
