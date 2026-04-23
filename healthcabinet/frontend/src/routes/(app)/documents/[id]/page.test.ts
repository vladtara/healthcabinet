import axe from 'axe-core';
import { QueryClient } from '@tanstack/query-core';
import { render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import DocumentDetailPageTestWrapper from './DocumentDetailPageTestWrapper.svelte';

const mockPageData = vi.hoisted(() => ({
	params: { id: 'doc-1' },
	url: new URL('http://test/documents/doc-1')
}));

const mockPageStore = vi.hoisted(() => ({
	subscribe: (fn: (value: typeof mockPageData) => void) => {
		fn(mockPageData);
		return () => {};
	}
}));

vi.mock('$app/stores', () => ({
	page: mockPageStore
}));

vi.mock('$lib/api/documents', () => ({
	getDocumentDetail: vi.fn()
}));

vi.mock('$lib/api/client.svelte', () => ({
	apiFetch: vi.fn(),
	apiStream: vi.fn(),
	tokenState: { accessToken: 'mock-token', setToken: vi.fn(), clear: vi.fn() },
	API_BASE: 'http://localhost:8000',
	registerForceLogoutHandler: vi.fn()
}));

import { getDocumentDetail } from '$lib/api/documents';

const mockGetDocumentDetail = vi.mocked(getDocumentDetail);

function renderPage() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } }
	});

	return render(DocumentDetailPageTestWrapper, { props: { queryClient } });
}

describe('Document detail route accessibility', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockPageData.params.id = 'doc-1';
		mockPageData.url = new URL('http://test/documents/doc-1');
		mockGetDocumentDetail.mockResolvedValue({
			id: 'doc-1',
			filename: 'blood_test.pdf',
			file_size_bytes: 45056,
			file_type: 'application/pdf',
			status: 'failed',
			arq_job_id: null,
			keep_partial: null,
			document_kind: 'unknown',
			needs_date_confirmation: false,
			partial_measured_at_text: null,
			created_at: '2026-04-01T12:00:00Z',
			updated_at: '2026-04-01T12:05:00Z',
			health_values: []
		});
	});

	test('passes axe accessibility audit on the loaded route', async () => {
		const { container } = renderPage();

		await waitFor(() => {
			expect(screen.getByRole('heading', { name: 'blood_test.pdf' })).toBeInTheDocument();
		});

		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});
});
