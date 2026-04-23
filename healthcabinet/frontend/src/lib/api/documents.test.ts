import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import { apiFetch, apiStream } from '$lib/api/client.svelte';

import { confirmDateYear, streamDocumentStatus, type DocumentStatusEvent } from './documents';

vi.mock('$lib/api/client.svelte', () => ({
	apiFetch: vi.fn(),
	apiStream: vi.fn()
}));

const mockApiFetch = vi.mocked(apiFetch);
const mockApiStream = vi.mocked(apiStream);

function makeSseResponse(chunks: string[]): Response {
	const encoder = new TextEncoder();

	return new Response(
		new ReadableStream<Uint8Array>({
			start(controller) {
				for (const chunk of chunks) {
					controller.enqueue(encoder.encode(chunk));
				}
				controller.close();
			}
		}),
		{ status: 200 }
	);
}

describe('streamDocumentStatus', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	test('retries after an unexpected stream close until the caller aborts', async () => {
		const controller = new AbortController();
		const receivedEvents: DocumentStatusEvent[] = [];
		const receivedErrors: Array<'stream-error' | 'auth-error'> = [];

		mockApiStream.mockResolvedValueOnce(makeSseResponse([':\n\n']));
		mockApiStream.mockResolvedValueOnce(
			makeSseResponse([
				'data: {"event":"document.completed","document_id":"doc-1","progress":1,"message":"Done"}\n\n'
			])
		);

		const streamPromise = streamDocumentStatus(
			'doc-1',
			controller.signal,
			(event) => {
				receivedEvents.push(event);
				controller.abort();
			},
			(error) => {
				receivedErrors.push(error);
			}
		);

		await vi.runAllTimersAsync();
		await streamPromise;

		expect(mockApiStream).toHaveBeenCalledTimes(2);
		expect(receivedErrors).toEqual(['stream-error']);
		expect(receivedEvents).toHaveLength(1);
		expect(receivedEvents[0]).toMatchObject({
			event: 'document.completed',
			document_id: 'doc-1'
		});
	});

	test('reports auth failures once and does not retry them', async () => {
		mockApiStream.mockRejectedValue({
			type: 'about:blank',
			title: 'Unauthorized',
			status: 401
		});

		const onEvent = vi.fn();
		const onError = vi.fn();

		await streamDocumentStatus('doc-1', new AbortController().signal, onEvent, onError);

		expect(mockApiStream).toHaveBeenCalledTimes(1);
		expect(onEvent).not.toHaveBeenCalled();
		expect(onError).toHaveBeenCalledTimes(1);
		expect(onError).toHaveBeenCalledWith('auth-error');
	});
});

describe('confirmDateYear', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	test('POSTs to /confirm-date-year with the document id and a JSON-encoded year', async () => {
		const fakeDetail = { id: 'test-doc-id', needs_date_confirmation: false };
		mockApiFetch.mockResolvedValueOnce(fakeDetail);

		const result = await confirmDateYear('test-doc-id', 2026);

		expect(mockApiFetch).toHaveBeenCalledTimes(1);
		const [url, options] = mockApiFetch.mock.calls[0];
		expect(url).toBe('/api/v1/documents/test-doc-id/confirm-date-year');
		expect(options).toMatchObject({
			method: 'POST',
			body: JSON.stringify({ year: 2026 })
		});
		expect(result).toBe(fakeDetail);
	});
});
