import { beforeEach, describe, expect, test, vi } from 'vitest';

import { apiFetch, apiStream } from '$lib/api/client.svelte';

import {
	getDashboardInterpretation,
	getDocumentInterpretation,
	streamAiChat,
	streamDashboardChat
} from './ai';

vi.mock('$lib/api/client.svelte', () => ({
	apiFetch: vi.fn(),
	apiStream: vi.fn()
}));

const mockApiFetch = vi.mocked(apiFetch);
const mockApiStream = vi.mocked(apiStream);

describe('AI API client (Story 15.3)', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	test('getDocumentInterpretation targets the per-document endpoint', async () => {
		mockApiFetch.mockResolvedValueOnce({
			document_id: 'doc-1',
			interpretation: '...',
			model_version: 'm',
			generated_at: '2026-04-20T00:00:00Z',
			reasoning: null
		});
		await getDocumentInterpretation('doc-1');
		expect(mockApiFetch).toHaveBeenCalledWith('/api/v1/ai/documents/doc-1/interpretation');
	});

		test('getDashboardInterpretation encodes the kind and hits the dashboard endpoint', async () => {
			mockApiFetch.mockResolvedValueOnce({
				document_id: null,
				document_kind: 'analysis',
				source_document_ids: [],
				interpretation: '',
				model_version: null,
				generated_at: '2026-04-20T00:00:00Z',
				reasoning: null
			});
			await getDashboardInterpretation('analysis');
			expect(mockApiFetch).toHaveBeenCalledWith(
			'/api/v1/ai/dashboard/interpretation?document_kind=analysis'
		);
	});

	test('streamAiChat POSTs the document payload', async () => {
		mockApiStream.mockResolvedValueOnce(new Response(''));
		await streamAiChat({ document_id: 'doc-1', question: 'Hi' });
		expect(mockApiStream).toHaveBeenCalledWith(
			'/api/v1/ai/chat',
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({ document_id: 'doc-1', question: 'Hi' })
			})
		);
	});

	test('streamDashboardChat POSTs the dashboard payload', async () => {
		mockApiStream.mockResolvedValueOnce(new Response(''));
		await streamDashboardChat({ document_kind: 'all', question: 'Summarize' });
		expect(mockApiStream).toHaveBeenCalledWith(
			'/api/v1/ai/dashboard/chat',
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({ document_kind: 'all', question: 'Summarize' })
			})
		);
	});
});
