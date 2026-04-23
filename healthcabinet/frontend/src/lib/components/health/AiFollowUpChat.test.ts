/**
 * Unit tests for AiFollowUpChat component (AC: #1, #3).
 */

import axe from 'axe-core';
import { fireEvent, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { QueryClient } from '@tanstack/query-core';
import { render } from '@testing-library/svelte';
import AiFollowUpChatTestWrapper from './AiFollowUpChatTestWrapper.svelte';

vi.mock('$lib/api/ai', () => ({
	getDocumentInterpretation: vi.fn(),
	streamAiChat: vi.fn()
}));

import { getDocumentInterpretation, streamAiChat } from '$lib/api/ai';

const mockGetInterpretation = vi.mocked(getDocumentInterpretation);
const mockStreamAiChat = vi.mocked(streamAiChat);

function makeQueryClient() {
	return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderChat(documentId = 'doc-1') {
	const queryClient = makeQueryClient();
	const result = render(AiFollowUpChatTestWrapper, {
		props: { queryClient, documentId }
	});
	return { ...result, queryClient };
}

function makeInterpretationResponse(overrides: Record<string, unknown> = {}) {
	return {
		document_id: 'doc-1',
		interpretation: 'Your glucose is within the normal range.',
		model_version: 'claude-sonnet-4-6',
		generated_at: '2026-03-28T00:00:00Z',
		reasoning: null,
		...overrides
	};
}

function makeStreamResponse(chunks: string[], status = 200): Response {
	const encoder = new TextEncoder();
	let chunkIndex = 0;

	const readable = new ReadableStream({
		pull(controller) {
			if (chunkIndex < chunks.length) {
				controller.enqueue(encoder.encode(chunks[chunkIndex++]));
			} else {
				controller.close();
			}
		}
	});

	return new Response(readable, {
		status,
		headers: { 'Content-Type': 'text/plain; charset=utf-8' }
	});
}

describe('AiFollowUpChat', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	test('hidden when interpretation is unavailable (404)', async () => {
		mockGetInterpretation.mockRejectedValue({
			status: 404,
			title: 'Not Found',
			type: 'about:blank'
		});
		const { container } = renderChat();

		await waitFor(() => {
			// No section should be rendered for unavailable interpretation
			expect(container.querySelector('section')).toBeNull();
		});
	});

	test('renders form when interpretation is available', async () => {
		mockGetInterpretation.mockResolvedValue(makeInterpretationResponse());
		const { getByRole } = renderChat();

		await waitFor(() => {
			expect(getByRole('button', { name: /ask/i })).toBeTruthy();
		});
	});

	test('blank submit is blocked', async () => {
		mockGetInterpretation.mockResolvedValue(makeInterpretationResponse());
		const { getByRole } = renderChat();

		await waitFor(() => {
			expect(getByRole('button', { name: /ask/i })).toBeTruthy();
		});

		const button = getByRole('button', { name: /ask/i });
		expect(button).toBeDisabled();
		expect(mockStreamAiChat).not.toHaveBeenCalled();
	});

	test('submit calls the stream helper with { document_id, question }', async () => {
		mockGetInterpretation.mockResolvedValue(makeInterpretationResponse());
		mockStreamAiChat.mockResolvedValue(makeStreamResponse(['Answer text.']));

		const { getByRole, getByLabelText } = renderChat('doc-42');

		await waitFor(() => {
			expect(getByRole('button', { name: /ask/i })).toBeTruthy();
		});

		const textarea = getByLabelText(/your follow-up question/i);
		await fireEvent.input(textarea, { target: { value: 'What does this mean?' } });
		await fireEvent.click(getByRole('button', { name: /ask/i }));

		await waitFor(() => {
			expect(mockStreamAiChat).toHaveBeenCalledWith(
				{ document_id: 'doc-42', question: 'What does this mean?' },
				expect.any(AbortSignal)
			);
		});
	});

	test('skeleton shows before first chunk and disappears after first chunk', async () => {
		mockGetInterpretation.mockResolvedValue(makeInterpretationResponse());

		let resolveStream!: (value: Response) => void;
		const streamPromise = new Promise<Response>((resolve) => {
			resolveStream = resolve;
		});
		mockStreamAiChat.mockReturnValue(streamPromise);

		const { getByRole, getByLabelText, container } = renderChat();

		await waitFor(() => {
			expect(getByRole('button', { name: /ask/i })).toBeTruthy();
		});

		const textarea = getByLabelText(/your follow-up question/i);
		await fireEvent.input(textarea, { target: { value: 'Tell me more.' } });
		await fireEvent.click(getByRole('button', { name: /ask/i }));

		// While waiting, skeleton should appear
		await waitFor(() => {
			expect(container.querySelector('[aria-busy="true"]')).toBeTruthy();
		});

		// Resolve the stream
		resolveStream(makeStreamResponse(['The answer is here.']));

		// Skeleton should disappear after content loads
		await waitFor(() => {
			expect(container.querySelector('[aria-busy="true"]')).toBeNull();
		});
	});

	test('answer renders after streaming completes', async () => {
		mockGetInterpretation.mockResolvedValue(makeInterpretationResponse());
		mockStreamAiChat.mockResolvedValue(makeStreamResponse(['Your glucose ', 'is normal.']));

		const { getByRole, getByLabelText, getByText } = renderChat();

		await waitFor(() => {
			expect(getByRole('button', { name: /ask/i })).toBeTruthy();
		});

		const textarea = getByLabelText(/your follow-up question/i);
		await fireEvent.input(textarea, { target: { value: 'Tell me more.' } });
		await fireEvent.click(getByRole('button', { name: /ask/i }));

		await waitFor(() => {
			expect(getByText(/your glucose/i)).toBeTruthy();
		});
	});

	test('submit button disables during streaming', async () => {
		mockGetInterpretation.mockResolvedValue(makeInterpretationResponse());

		// Never-resolving stream to keep isStreaming = true
		mockStreamAiChat.mockReturnValue(new Promise(() => {}));

		const { getByRole, getByLabelText } = renderChat();

		await waitFor(() => {
			expect(getByRole('button', { name: /ask/i })).toBeTruthy();
		});

		const textarea = getByLabelText(/your follow-up question/i);
		await fireEvent.input(textarea, { target: { value: 'Tell me more.' } });

		const button = getByRole('button', { name: /ask/i });
		expect(button).not.toBeDisabled();

		await fireEvent.click(button);

		await waitFor(() => {
			expect(getByRole('button', { name: /getting answer/i })).toBeDisabled();
		});
	});

	test('component state resets on documentId change', async () => {
		mockGetInterpretation.mockResolvedValue(makeInterpretationResponse());
		mockStreamAiChat.mockResolvedValue(makeStreamResponse(['Some answer.']));

		const queryClient = makeQueryClient();
		const { getByRole, getByLabelText, rerender } = render(AiFollowUpChatTestWrapper, {
			props: { queryClient, documentId: 'doc-1' }
		});

		await waitFor(() => {
			expect(getByRole('button', { name: /ask/i })).toBeTruthy();
		});

		const textarea = getByLabelText(/your follow-up question/i);
		await fireEvent.input(textarea, { target: { value: 'My question.' } });
		await fireEvent.click(getByRole('button', { name: /ask/i }));

		await waitFor(() => {
			expect(getByRole('button', { name: /ask/i })).toBeTruthy();
		});

		// Navigate to a different document
		await rerender({ queryClient, documentId: 'doc-2' });

		// After navigation, the textarea should be empty
		await waitFor(() => {
			const ta = getByLabelText(/your follow-up question/i) as HTMLTextAreaElement;
			expect(ta.value).toBe('');
		});
	});

	test('inline error shown on 409 / network failure', async () => {
		mockGetInterpretation.mockResolvedValue(makeInterpretationResponse());
		mockStreamAiChat.mockResolvedValue(
			new Response(JSON.stringify({ detail: 'No AI context available.' }), {
				status: 409,
				headers: { 'Content-Type': 'application/json' }
			})
		);

		const { getByRole, getByLabelText, getByText } = renderChat();

		await waitFor(() => {
			expect(getByRole('button', { name: /ask/i })).toBeTruthy();
		});

		const textarea = getByLabelText(/your follow-up question/i);
		await fireEvent.input(textarea, { target: { value: 'Tell me more.' } });
		await fireEvent.click(getByRole('button', { name: /ask/i }));

		await waitFor(() => {
			expect(getByText(/no ai context available/i)).toBeTruthy();
		});
	});

	test('cancels in-flight stream when documentId changes', async () => {
		mockGetInterpretation.mockResolvedValue(makeInterpretationResponse());

		let capturedSignal: AbortSignal | undefined;

		mockStreamAiChat.mockImplementation(async (_payload: unknown, signal?: AbortSignal) => {
			capturedSignal = signal;
			// Return a stream that never closes naturally
			const readable = new ReadableStream({
				start(controller) {
					signal?.addEventListener('abort', () => controller.close());
				}
			});
			return new Response(readable, {
				status: 200,
				headers: { 'Content-Type': 'text/plain; charset=utf-8' }
			});
		});

		const queryClient = makeQueryClient();
		const { getByRole, getByLabelText, rerender } = render(AiFollowUpChatTestWrapper, {
			props: { queryClient, documentId: 'doc-1' }
		});

		await waitFor(() => expect(getByRole('button', { name: /ask/i })).toBeTruthy());

		const textarea = getByLabelText(/your follow-up question/i);
		await fireEvent.input(textarea, { target: { value: 'Tell me more.' } });
		await fireEvent.click(getByRole('button', { name: /ask/i }));

		// Wait until the signal is captured (stream is in-flight)
		await waitFor(() => expect(capturedSignal).toBeDefined());

		// Navigate to a different document — the effect cleanup should abort the stream
		await rerender({ queryClient, documentId: 'doc-2' });

		// The abort signal from the previous fetch must be triggered
		await waitFor(() => {
			expect(capturedSignal?.aborted).toBe(true);
		});
	});

	test('axe-core audit passes on loaded state', async () => {
		mockGetInterpretation.mockResolvedValue(makeInterpretationResponse());
		const { container } = renderChat();

		await waitFor(() => {
			expect(container.querySelector('section')).toBeTruthy();
		});

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});
});
