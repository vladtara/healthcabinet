import { afterEach, describe, expect, test, vi } from 'vitest';
import {
	feedbackStore,
	showSuccess,
	showError,
	showWarning,
	dismissToast,
	clearAll
} from './feedback.svelte';

describe('feedback store', () => {
	afterEach(() => {
		clearAll();
		vi.restoreAllMocks();
	});

	test('showSuccess adds a success toast', () => {
		const id = showSuccess('Saved!');
		expect(id).toBeTruthy();
		expect(feedbackStore.toasts).toHaveLength(1);
		expect(feedbackStore.toasts[0].type).toBe('success');
		expect(feedbackStore.toasts[0].message).toBe('Saved!');
	});

	test('showError adds an error toast', () => {
		const id = showError('Failed to save');
		expect(feedbackStore.toasts).toHaveLength(1);
		expect(feedbackStore.toasts[0].type).toBe('error');
		expect(feedbackStore.toasts[0].id).toBe(id);
	});

	test('showWarning adds a warning toast', () => {
		showWarning('Check your input');
		expect(feedbackStore.toasts).toHaveLength(1);
		expect(feedbackStore.toasts[0].type).toBe('warning');
	});

	test('dismissToast removes a specific toast', () => {
		const id1 = showSuccess('First');
		const id2 = showSuccess('Second');
		expect(feedbackStore.toasts).toHaveLength(2);

		dismissToast(id1);
		expect(feedbackStore.toasts).toHaveLength(1);
		expect(feedbackStore.toasts[0].id).toBe(id2);
	});

	test('clearAll removes all toasts', () => {
		showSuccess('One');
		showWarning('Two');
		showError('Three');
		expect(feedbackStore.toasts).toHaveLength(3);

		clearAll();
		expect(feedbackStore.toasts).toHaveLength(0);
	});

	test('success toast auto-dismisses after timeout', () => {
		vi.useFakeTimers();
		showSuccess('Will vanish');
		expect(feedbackStore.toasts).toHaveLength(1);

		vi.advanceTimersByTime(3000);
		expect(feedbackStore.toasts).toHaveLength(0);
		vi.useRealTimers();
	});

	test('error toast does NOT auto-dismiss', () => {
		vi.useFakeTimers();
		showError('Stays put');
		expect(feedbackStore.toasts).toHaveLength(1);

		vi.advanceTimersByTime(10000);
		expect(feedbackStore.toasts).toHaveLength(1);
		vi.useRealTimers();
	});
});
