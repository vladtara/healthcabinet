import axe from 'axe-core';
import { render, waitFor } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/query-core';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import PatternCardTestWrapper from './PatternCardTestWrapper.svelte';

const { mockAuthStore } = vi.hoisted(() => ({
	mockAuthStore: {
		user: {
			id: 'test-user-id',
			email: 'test@example.com',
			role: 'user' as const,
			tier: 'free' as const
		} as {
			id: string;
			email: string;
			role: 'user' | 'admin';
			tier: 'free' | 'paid';
		} | null
	}
}));

vi.mock('$lib/api/ai', () => ({
	getAiPatterns: vi.fn()
}));

vi.mock('$lib/stores/auth.svelte', () => ({
	authStore: mockAuthStore
}));

import { getAiPatterns } from '$lib/api/ai';

const mockGetAiPatterns = vi.mocked(getAiPatterns);

function makeQueryClient() {
	return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderCard() {
	const queryClient = makeQueryClient();
	return render(PatternCardTestWrapper, { props: { queryClient } });
}

function makePatternsResponse() {
	return {
		patterns: [
			{
				description: 'Your ferritin has been lower across two uploads.',
				document_dates: ['2025-01-15', '2025-06-20'],
				recommendation: 'Discuss this pattern with your healthcare provider.'
			},
			{
				description: 'Your TSH has increased across two uploads.',
				document_dates: ['2025-01-15', '2025-06-20'],
				recommendation: 'Discuss this pattern with your healthcare provider.'
			}
		]
	};
}

describe('PatternCard', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockAuthStore.user = {
			id: 'test-user-id',
			email: 'test@example.com',
			role: 'user',
			tier: 'free'
		};
	});

	test('renders nothing when patterns array is empty', async () => {
		mockGetAiPatterns.mockResolvedValue({ patterns: [] });
		const { container } = renderCard();

		await waitFor(() => {
			expect(mockGetAiPatterns).toHaveBeenCalledTimes(1);
		});

		expect(container.querySelector('section')).toBeNull();
		expect(container.textContent?.trim()).toBe('');
	});

	test('does not fetch while the authenticated user profile is unavailable', async () => {
		mockAuthStore.user = null;
		const { container } = renderCard();

		expect(mockGetAiPatterns).not.toHaveBeenCalled();
		expect(container.querySelector('section')).toBeNull();
		expect(container.textContent?.trim()).toBe('');
	});

	test('renders nothing when query is pending', async () => {
		mockGetAiPatterns.mockReturnValue(new Promise(() => {}));
		const { container } = renderCard();

		await waitFor(() => {
			expect(mockGetAiPatterns).toHaveBeenCalledTimes(1);
		});

		expect(container.querySelector('section')).toBeNull();
		expect(container.textContent?.trim()).toBe('');
	});

	test('renders a section for each returned pattern', async () => {
		mockGetAiPatterns.mockResolvedValue(makePatternsResponse());
		const { container, getAllByLabelText, getAllByText, getByText } = renderCard();

		await waitFor(() => {
			expect(getAllByLabelText(/health pattern observation/i)).toHaveLength(2);
		});

		expect(container.querySelectorAll('section')).toHaveLength(2);
		expect(getByText('Your ferritin has been lower across two uploads.')).toBeTruthy();
		expect(getAllByText('Spans: 2025-01-15 · 2025-06-20')).toHaveLength(2);
		expect(getAllByText('Discuss this pattern with your healthcare provider.')).toHaveLength(2);
	});

	test('renders nothing when query is in error state', async () => {
		mockGetAiPatterns.mockRejectedValue(new Error('Network error'));
		const { container } = renderCard();

		await waitFor(() => {
			expect(mockGetAiPatterns).toHaveBeenCalledTimes(1);
		});

		await waitFor(() => {
			expect(container.querySelector('section')).toBeNull();
		});
		expect(container.textContent?.trim()).toBe('');
	});

	test('axe-core audit passes on loaded state', async () => {
		mockGetAiPatterns.mockResolvedValue({ patterns: [makePatternsResponse().patterns[0]] });
		const { container } = renderCard();

		await waitFor(() => {
			expect(container.querySelector('section')).toBeTruthy();
		});

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});
});
