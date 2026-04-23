import axe from 'axe-core';
import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import Toast from './Toast.svelte';

describe('Toast', () => {
	test('renders success variant with correct role and icon', () => {
		const { container } = renderComponent(Toast, { type: 'success', message: 'Saved!' });
		const toast = container.querySelector('.hc-toast-success');
		expect(toast).toBeInTheDocument();
		expect(toast!.getAttribute('role')).toBe('status');
		expect(toast!.textContent).toContain('Saved!');
		expect(toast!.textContent).toContain('✓');
	});

	test('renders error variant with role="alert"', () => {
		const { container } = renderComponent(Toast, { type: 'error', message: 'Failed!' });
		const toast = container.querySelector('.hc-toast-error');
		expect(toast).toBeInTheDocument();
		expect(toast!.getAttribute('role')).toBe('alert');
		expect(toast!.textContent).toContain('✕');
	});

	test('renders warning variant', () => {
		const { container } = renderComponent(Toast, { type: 'warning', message: 'Check input' });
		const toast = container.querySelector('.hc-toast-warning');
		expect(toast).toBeInTheDocument();
		expect(toast!.getAttribute('role')).toBe('status');
		expect(toast!.textContent).toContain('⚠');
	});

	test('shows dismiss button when onDismiss provided', () => {
		const onDismiss = vi.fn();
		const { container } = renderComponent(Toast, {
			type: 'success',
			message: 'Test',
			onDismiss
		});
		const btn = container.querySelector('.hc-toast-dismiss');
		expect(btn).toBeInTheDocument();
	});

	test('calls onDismiss when dismiss button clicked', async () => {
		const onDismiss = vi.fn();
		const { container } = renderComponent(Toast, {
			type: 'success',
			message: 'Test',
			onDismiss
		});
		const btn = container.querySelector('.hc-toast-dismiss') as HTMLButtonElement;
		await fireEvent.click(btn);
		expect(onDismiss).toHaveBeenCalledOnce();
	});

	test('does not show dismiss button without onDismiss', () => {
		const { container } = renderComponent(Toast, { type: 'success', message: 'Test' });
		expect(container.querySelector('.hc-toast-dismiss')).toBeNull();
	});

	test('success toast is accessible (axe audit)', async () => {
		const { container } = renderComponent(Toast, { type: 'success', message: 'Saved!' });
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	test('error toast is accessible (axe audit)', async () => {
		const { container } = renderComponent(Toast, { type: 'error', message: 'Error!' });
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});
});
