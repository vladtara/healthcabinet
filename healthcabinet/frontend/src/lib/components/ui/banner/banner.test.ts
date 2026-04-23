import axe from 'axe-core';
import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import FeedbackBanner from './FeedbackBanner.svelte';

describe('FeedbackBanner', () => {
	test('renders info variant with correct role', () => {
		const { container } = renderComponent(FeedbackBanner, { type: 'info', message: 'FYI' });
		const banner = container.querySelector('.hc-banner-info');
		expect(banner).toBeInTheDocument();
		expect(banner!.getAttribute('role')).toBe('status');
		expect(banner!.textContent).toContain('FYI');
	});

	test('renders error variant with role="alert"', () => {
		const { container } = renderComponent(FeedbackBanner, {
			type: 'error',
			message: 'Something broke'
		});
		const banner = container.querySelector('.hc-banner-error');
		expect(banner).toBeInTheDocument();
		expect(banner!.getAttribute('role')).toBe('alert');
	});

	test('renders success variant', () => {
		const { container } = renderComponent(FeedbackBanner, {
			type: 'success',
			message: 'Done'
		});
		expect(container.querySelector('.hc-banner-success')).toBeInTheDocument();
	});

	test('renders warning variant', () => {
		const { container } = renderComponent(FeedbackBanner, {
			type: 'warning',
			message: 'Careful'
		});
		expect(container.querySelector('.hc-banner-warning')).toBeInTheDocument();
	});

	test('shows dismiss button when dismissible', () => {
		const { container } = renderComponent(FeedbackBanner, {
			type: 'info',
			message: 'Test',
			dismissible: true
		});
		expect(container.querySelector('.hc-banner-dismiss')).toBeInTheDocument();
	});

	test('hides dismiss button when not dismissible', () => {
		const { container } = renderComponent(FeedbackBanner, {
			type: 'info',
			message: 'Test',
			dismissible: false
		});
		expect(container.querySelector('.hc-banner-dismiss')).toBeNull();
	});

	test('dismiss button hides the banner', async () => {
		const { container } = renderComponent(FeedbackBanner, {
			type: 'info',
			message: 'Bye',
			dismissible: true
		});
		expect(container.querySelector('.hc-banner')).toBeInTheDocument();

		const btn = container.querySelector('.hc-banner-dismiss') as HTMLButtonElement;
		await fireEvent.click(btn);
		expect(container.querySelector('.hc-banner')).toBeNull();
	});

	test('calls onDismiss callback when dismissed', async () => {
		const onDismiss = vi.fn();
		const { container } = renderComponent(FeedbackBanner, {
			type: 'info',
			message: 'Test',
			dismissible: true,
			onDismiss
		});
		const btn = container.querySelector('.hc-banner-dismiss') as HTMLButtonElement;
		await fireEvent.click(btn);
		expect(onDismiss).toHaveBeenCalledOnce();
	});

	test('info banner is accessible (axe audit)', async () => {
		const { container } = renderComponent(FeedbackBanner, { type: 'info', message: 'Info' });
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	test('error banner is accessible (axe audit)', async () => {
		const { container } = renderComponent(FeedbackBanner, {
			type: 'error',
			message: 'Error'
		});
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});
});
