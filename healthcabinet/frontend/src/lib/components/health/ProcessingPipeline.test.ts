/**
 * Unit tests for ProcessingPipeline component.
 * Uses mocked streamDocumentStatus (fetch-based SSE) instead of EventSource.
 */

import axe from 'axe-core';
import { waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import ProcessingPipeline from './ProcessingPipeline.svelte';
import type { DocumentStatusEvent } from '$lib/api/documents';

type OnEvent = (event: DocumentStatusEvent) => void;
type OnError = (error: 'stream-error' | 'auth-error') => void;

let capturedOnEvent: OnEvent | null = null;
let capturedOnError: OnError | null = null;
let capturedSignal: AbortSignal | null = null;

vi.mock('$lib/api/documents', () => ({
	streamDocumentStatus: vi.fn(
		(
			_documentId: string,
			signal: AbortSignal,
			onEvent: OnEvent,
			onError: OnError
		): Promise<void> => {
			capturedOnEvent = onEvent;
			capturedOnError = onError;
			capturedSignal = signal;
			// Return a never-resolving promise to simulate an open stream
			return new Promise(() => {});
		}
	)
}));

beforeEach(() => {
	vi.clearAllMocks();
	capturedOnEvent = null;
	capturedOnError = null;
	capturedSignal = null;
});

function sendEvent(eventName: string, message = ''): void {
	capturedOnEvent?.({
		event: eventName,
		document_id: 'test-doc',
		progress: 0,
		message
	});
}

describe('ProcessingPipeline', () => {
	test('renders all stage labels on mount', () => {
		const { getByText } = renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed: vi.fn()
		});

		expect(getByText('Uploading')).toBeTruthy();
		expect(getByText('Reading document')).toBeTruthy();
		expect(getByText('Extracting values')).toBeTruthy();
		expect(getByText('Generating insights')).toBeTruthy();
		expect(getByText('Complete')).toBeTruthy();
	});

	test('role="status" present on container', () => {
		const { container } = renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed: vi.fn()
		});

		expect(container.querySelector('[role="status"]')).toBeTruthy();
	});

	test('aria-live="polite" region exists for screen reader announcements', () => {
		const { container } = renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed: vi.fn()
		});

		expect(container.querySelector('[aria-live="polite"]')).toBeTruthy();
	});

	test('aria-live region text updates when stage changes', async () => {
		const { container } = renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed: vi.fn()
		});

		sendEvent('document.reading', 'Reading document…');

		await waitFor(() => {
			expect(container.querySelector('[aria-live="polite"]')?.textContent).toContain(
				'Reading document'
			);
		});
	});

	test('onComplete callback fires when document.completed received', async () => {
		const onComplete = vi.fn();
		renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete,
			onFailed: vi.fn()
		});

		sendEvent('document.completed', 'Processing complete');

		await waitFor(() => {
			expect(onComplete).toHaveBeenCalledOnce();
		});
	});

	test('onFailed callback fires when document.failed received', async () => {
		const onFailed = vi.fn();
		renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed
		});

		sendEvent('document.failed', 'Processing failed');

		await waitFor(() => {
			expect(onFailed).toHaveBeenCalledWith('failed');
		});
	});

	test('document.partial triggers onFailed and failure announcement', async () => {
		const onFailed = vi.fn();
		const { container } = renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed
		});

		sendEvent('document.partial', 'Partial extraction — some values need review');

		await waitFor(() => {
			expect(onFailed).toHaveBeenCalledWith('partial');
			expect(container.querySelector('[aria-live="polite"]')?.textContent).toContain(
				'Partial extraction'
			);
		});
	});

	test('streamDocumentStatus is called with documentId and AbortSignal', async () => {
		const { streamDocumentStatus } = await import('$lib/api/documents');
		renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed: vi.fn()
		});

		await waitFor(() => {
			expect(streamDocumentStatus).toHaveBeenCalledWith(
				'doc-1',
				expect.any(AbortSignal),
				expect.any(Function),
				expect.any(Function)
			);
		});
	});

	test('AbortController signal is provided to streamDocumentStatus', async () => {
		renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed: vi.fn()
		});

		await waitFor(() => {
			expect(capturedSignal).toBeTruthy();
			expect(capturedSignal?.aborted).toBe(false);
		});
	});

	test('intermediate stage marks prior stages as done', async () => {
		const { container } = renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed: vi.fn()
		});

		sendEvent('document.generating', 'Generating insights…');

		await waitFor(() => {
			expect(container.querySelectorAll('.hc-pipeline-stage-done')).toHaveLength(3);
			expect(container.querySelectorAll('.hc-pipeline-stage-active')).toHaveLength(1);
		});
	});

	test('completed stages show done indicator', async () => {
		const { container } = renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed: vi.fn()
		});

		sendEvent('document.completed', 'Processing complete');

		await waitFor(() => {
			expect(container.querySelectorAll('.hc-pipeline-stage-done')).toHaveLength(5);
		});
	});

	test('three consecutive stream errors close the stream and notify failure', async () => {
		const onFailed = vi.fn();
		renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed
		});

		capturedOnError?.('stream-error');
		capturedOnError?.('stream-error');
		capturedOnError?.('stream-error');

		await waitFor(() => {
			expect(onFailed).toHaveBeenCalledWith('stream-error');
			expect(capturedSignal?.aborted).toBe(true);
		});
	});

	test('auth error aborts immediately and reports failure once', async () => {
		const onFailed = vi.fn();
		renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed
		});

		capturedOnError?.('auth-error');

		await waitFor(() => {
			expect(onFailed).toHaveBeenCalledTimes(1);
			expect(onFailed).toHaveBeenCalledWith('stream-error');
			expect(capturedSignal?.aborted).toBe(true);
		});
	});

	test('auth error calls onAuthError instead of onFailed when queue flow opts in', async () => {
		const onFailed = vi.fn();
		const onAuthError = vi.fn();
		renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed,
			onAuthError
		});

		capturedOnError?.('auth-error');

		await waitFor(() => {
			expect(onAuthError).toHaveBeenCalledTimes(1);
			expect(onFailed).not.toHaveBeenCalled();
			expect(capturedSignal?.aborted).toBe(true);
		});
	});

	test('axe accessibility audit passes', async () => {
		const { container } = renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed: vi.fn()
		});

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	// --- Story 11-4: Progress bar and symbol tests ---

	test('progress bar renders with value=0 and max=100 on mount', () => {
		const { container } = renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed: vi.fn()
		});

		const progress = container.querySelector('progress') as HTMLProgressElement;
		expect(progress).toBeTruthy();
		expect(progress.value).toBe(0);
		expect(progress.max).toBe(100);
	});

	test('progress bar value updates as stages complete', async () => {
		const { container } = renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed: vi.fn()
		});

		// After reading stage (upload_started is done = 1 done stage = 25%)
		sendEvent('document.reading', 'Reading…');

		await waitFor(() => {
			const progress = container.querySelector('progress') as HTMLProgressElement;
			expect(progress.value).toBe(25);
		});

		// After extracting (2 done stages = 50%)
		sendEvent('document.extracting', 'Extracting…');

		await waitFor(() => {
			const progress = container.querySelector('progress') as HTMLProgressElement;
			expect(progress.value).toBe(50);
		});

		// After completed (all 5 done; progress element clamps to max=100)
		sendEvent('document.completed', 'Done');

		await waitFor(() => {
			const progress = container.querySelector('progress') as HTMLProgressElement;
			expect(progress.value).toBe(100);
		});
	});

	test('stage symbols match spec: ✅ done, ⏳ active, ○ pending, ✕ error', async () => {
		const { container } = renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed: vi.fn()
		});

		// Initial state: all pending with ○ symbols
		const symbols = container.querySelectorAll('.hc-pipeline-symbol');
		expect(symbols.length).toBe(5);
		symbols.forEach((s) => expect(s.textContent?.trim()).toBe('○'));

		// Advance to reading stage
		sendEvent('document.reading', 'Reading…');

		await waitFor(() => {
			const updatedSymbols = container.querySelectorAll('.hc-pipeline-symbol');
			// First stage done (✅), second active (⏳), rest pending (○)
			expect(updatedSymbols[0].textContent?.trim()).toBe('✅');
			expect(updatedSymbols[1].textContent?.trim()).toBe('⏳');
			expect(updatedSymbols[2].textContent?.trim()).toBe('○');
		});

		// Simulate failure
		sendEvent('document.failed', 'Failed');

		await waitFor(() => {
			const failedSymbols = container.querySelectorAll('.hc-pipeline-symbol');
			// First done (✅), second still done (was last progressed), third error (✕)
			expect(failedSymbols[0].textContent?.trim()).toBe('✅');
			expect(failedSymbols[1].textContent?.trim()).toBe('✅');
			expect(failedSymbols[2].textContent?.trim()).toBe('✕');
		});
	});

	test('sunken panel container has correct CSS class', () => {
		const { container } = renderComponent(ProcessingPipeline, {
			documentId: 'doc-1',
			onComplete: vi.fn(),
			onFailed: vi.fn()
		});

		expect(container.querySelector('.hc-pipeline-container')).toBeTruthy();
	});
});
