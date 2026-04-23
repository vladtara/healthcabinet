import axe from 'axe-core';
import { QueryClient } from '@tanstack/query-core';
import { render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import DocumentsPageTestWrapper from './DocumentsPageTestWrapper.svelte';

vi.mock('$lib/api/client.svelte', () => ({
	apiFetch: vi.fn(),
	tokenState: { accessToken: 'mock-token' },
	API_BASE: 'http://localhost:8000'
}));

import { apiFetch } from '$lib/api/client.svelte';

const mockApiFetch = vi.mocked(apiFetch);

function renderPage() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } }
	});

	return render(DocumentsPageTestWrapper, { props: { queryClient } });
}

describe('Documents route accessibility', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockApiFetch.mockResolvedValue([
			{
				id: 'doc-1',
				user_id: 'user-1',
				filename: 'blood_test.pdf',
				file_size_bytes: 45056,
				file_type: 'application/pdf',
				status: 'completed',
				arq_job_id: null,
				keep_partial: null,
				created_at: '2026-04-01T12:00:00Z',
				updated_at: '2026-04-01T12:05:00Z'
			}
		]);
	});

	test('passes axe accessibility audit on the loaded route', async () => {
		const { container } = renderPage();

		await waitFor(() => {
			expect(screen.getByText('blood_test.pdf')).toBeInTheDocument();
		});

		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});
});
