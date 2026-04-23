import axe from 'axe-core';
import { describe, expect, test, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import AIChatWindow from './AIChatWindow.svelte';

vi.mock('$lib/api/ai', () => ({
	getDocumentInterpretation: vi.fn(),
	streamAiChat: vi.fn(),
	streamDashboardChat: vi.fn(),
	getDashboardInterpretation: vi.fn(),
	getAiPatterns: vi.fn()
}));

vi.mock('$lib/api/client.svelte', () => ({
	tokenState: { accessToken: 'mock-token', setToken: vi.fn(), clear: vi.fn() },
	apiFetch: vi.fn(),
	apiStream: vi.fn()
}));

function renderChat(documentId: string | null = 'doc-1') {
	return renderComponent(AIChatWindow, { mode: 'document', documentId });
}

function stubScrollMetrics(
	el: HTMLElement,
	metrics: { scrollHeight: number; clientHeight: number; scrollTop?: number }
) {
	Object.defineProperty(el, 'scrollHeight', {
		configurable: true,
		get: () => metrics.scrollHeight
	});
	Object.defineProperty(el, 'clientHeight', {
		configurable: true,
		get: () => metrics.clientHeight
	});
	if (metrics.scrollTop !== undefined) {
		el.scrollTop = metrics.scrollTop;
	}
}

function singleChunkResponse(chunk: string): Response {
	const encoder = new TextEncoder();
	return new Response(
		new ReadableStream<Uint8Array>({
			start(controller) {
				controller.enqueue(encoder.encode(chunk));
				controller.close();
			}
		}),
		{ status: 200 }
	);
}

async function settleStream() {
	// streamDashboardChat resolves in a microtask, then the reader loop posts
	// two more microtasks per chunk (decode + messages mutation + applyStickyScroll).
	// Four flush rounds cover single-chunk responses comfortably.
	for (let i = 0; i < 4; i++) {
		await new Promise((r) => setTimeout(r, 0));
	}
}

describe('AIChatWindow', () => {
	test('renders title bar with Dr. Health', () => {
		const { container } = renderChat();
		const titlebar = container.querySelector('.hc-ai-chat-titlebar-title');
		expect(titlebar).toBeInTheDocument();
		expect(titlebar!.textContent).toContain('Dr. Health');
	});

	test('minimize toggle hides message area', async () => {
		const { container, getByRole } = renderChat();

		const toggleBtn = getByRole('button', { name: /minimize/i });
		expect(container.querySelector('.hc-ai-chat-messages')).toBeVisible();

		toggleBtn.click();
		await new Promise((r) => setTimeout(r, 0));

		// After minimize, the body should be hidden via CSS class
		expect(container.querySelector('.hc-ai-chat')).toHaveClass('hc-ai-chat-minimized');
	});

	test('input field and send button render', () => {
		const { getByRole } = renderChat();
		// contenteditable div, not an input — accessible via role="textbox" with aria-label
		expect(getByRole('textbox', { name: /ask about your health/i })).toBeInTheDocument();
		expect(getByRole('button', { name: /send/i })).toBeInTheDocument();
	});

	test('send button disabled when input empty', () => {
		const { getByRole } = renderChat();
		const sendBtn = getByRole('button', { name: /send/i });
		expect(sendBtn).toBeDisabled();
	});

	test('axe accessibility audit passes', async () => {
		const { container } = renderChat();
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	// ── Story 15.3 — dashboard mode ──────────────────────────────────────────

	test('dashboard mode with hasContext=false disables send and shows inline hint', () => {
		const { container, getByRole, getByTestId } = renderComponent(AIChatWindow, {
			mode: 'dashboard',
			documentKind: 'analysis',
			hasContext: false
		});

		const sendBtn = getByRole('button', { name: /send/i });
		expect(sendBtn).toBeDisabled();

		const hint = getByTestId('dashboard-chat-no-context-hint');
		expect(hint).toBeInTheDocument();
		expect(hint.textContent).toMatch(/at least one interpreted document/i);
		// Title bar still renders so the component remains visible/addressable.
		const titlebar = container.querySelector('.hc-ai-chat-titlebar-title');
		expect(titlebar?.textContent).toContain('Dr. Health');
	});

	test('dashboard mode calls streamDashboardChat when user submits', async () => {
		const { streamDashboardChat } = await import('$lib/api/ai');
		const mockStream = vi.mocked(streamDashboardChat);
		// Return an ok response whose body yields one chunk then closes.
		const encoder = new TextEncoder();
		mockStream.mockResolvedValue(
			new Response(
				new ReadableStream<Uint8Array>({
					start(controller) {
						controller.enqueue(encoder.encode('hello'));
						controller.close();
					}
				}),
				{ status: 200 }
			)
		);

		const { getByRole, container } = renderComponent(AIChatWindow, {
			mode: 'dashboard',
			documentKind: 'all',
			hasContext: true
		});

		const editor = container.querySelector('.hc-ai-chat-editor') as HTMLDivElement;
		// Simulate typing.
		editor.innerText = 'Summarize please';
		editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
		// Allow the reactive $derived/question binding to settle.
		await new Promise((r) => setTimeout(r, 0));

		const sendBtn = getByRole('button', { name: /send/i });
		sendBtn.click();
		// Let the streaming microtasks complete.
		await new Promise((r) => setTimeout(r, 0));
		await new Promise((r) => setTimeout(r, 0));

		expect(mockStream).toHaveBeenCalledWith(
			expect.objectContaining({ document_kind: 'all', question: 'Summarize please' }),
			expect.any(AbortSignal)
		);
	});

	// ── Story 15.5 — layout ownership & sticky-bottom scrolling ──────────────

	test('messages pane is the only history log container in the chat body', () => {
		const { container } = renderChat();
		const shell = container.querySelector('.hc-ai-chat') as HTMLElement;
		const body = container.querySelector('.hc-ai-chat-body') as HTMLElement;
		const messages = container.querySelector('.hc-ai-chat-messages') as HTMLElement;
		const inputbar = container.querySelector('.hc-ai-chat-inputbar') as HTMLElement;
		const hint = container.querySelector('.hc-ai-chat-hint') as HTMLElement;
		const disclaimer = container.querySelector('.hc-ai-chat-disclaimer') as HTMLElement;
		expect(shell).toBeInTheDocument();
		expect(body).toBeInTheDocument();
		expect(messages).toBeInTheDocument();
		expect(shell.querySelectorAll('[role="log"]')).toHaveLength(1);
		expect(messages.parentElement).toBe(body);
		expect(inputbar.parentElement).toBe(body);
		expect(hint.parentElement).toBe(inputbar);
		expect(disclaimer.parentElement).toBe(shell);
		expect(messages.querySelector('.hc-ai-chat-inputbar')).not.toBeInTheDocument();
		expect(messages.querySelector('.hc-ai-chat-disclaimer')).not.toBeInTheDocument();
	});

	test('input bar, hint, and disclaimer remain rendered siblings around messages pane', () => {
		const { container } = renderChat();
		const children = Array.from(
			(container.querySelector('.hc-ai-chat') as HTMLElement).children
		).map((c) => c.className);
		// Title bar → body → disclaimer at the shell level; input bar & hint live
		// inside body alongside the messages pane.
		expect(children[0]).toContain('hc-ai-chat-titlebar');
		expect(children[1]).toContain('hc-ai-chat-body');
		expect(children[2]).toContain('hc-ai-chat-disclaimer');
		expect(container.querySelector('.hc-ai-chat-inputbar')).toBeInTheDocument();
		expect(container.querySelector('.hc-ai-chat-hint')).toBeInTheDocument();
	});

	test('auto-scrolls to bottom when user is near bottom on new chunk', async () => {
		const { streamDashboardChat } = await import('$lib/api/ai');
		const mockStream = vi.mocked(streamDashboardChat);
		mockStream.mockResolvedValue(singleChunkResponse('hi there'));

		const { getByRole, container } = renderComponent(AIChatWindow, {
			mode: 'dashboard',
			documentKind: 'all',
			hasContext: true
		});

		const messagesEl = container.querySelector('.hc-ai-chat-messages') as HTMLElement;
		// Already near the bottom: distance = 200 - 200 - 0 = 0 (sticky).
		stubScrollMetrics(messagesEl, { scrollHeight: 200, clientHeight: 200, scrollTop: 0 });
		messagesEl.dispatchEvent(new Event('scroll'));

		const editor = container.querySelector('.hc-ai-chat-editor') as HTMLDivElement;
		editor.innerText = 'ping';
		editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
		await new Promise((r) => setTimeout(r, 0));

		getByRole('button', { name: /send/i }).click();
		await settleStream();

		// Sticky-bottom was true → scrollTop should be clamped to scrollHeight.
		expect(messagesEl.scrollTop).toBe(200);
	});

	test('does not snap to bottom when user scrolled up before a chunk', async () => {
		const { streamDashboardChat } = await import('$lib/api/ai');
		const mockStream = vi.mocked(streamDashboardChat);
		mockStream.mockResolvedValue(singleChunkResponse('a longer AI answer'));

		const { getByRole, container } = renderComponent(AIChatWindow, {
			mode: 'dashboard',
			documentKind: 'all',
			hasContext: true
		});

		const messagesEl = container.querySelector('.hc-ai-chat-messages') as HTMLElement;
		// User has scrolled up: distance = 2000 - 50 - 200 = 1750, far above threshold.
		stubScrollMetrics(messagesEl, { scrollHeight: 2000, clientHeight: 200, scrollTop: 50 });
		messagesEl.dispatchEvent(new Event('scroll'));

		const editor = container.querySelector('.hc-ai-chat-editor') as HTMLDivElement;
		editor.innerText = 'keep reading';
		editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
		await new Promise((r) => setTimeout(r, 0));

		getByRole('button', { name: /send/i }).click();
		await settleStream();

		// User was NOT sticky → scrollTop must stay where the user left it.
		expect(messagesEl.scrollTop).toBe(50);
	});

	test('sticky-bottom behavior resumes after the user scrolls back down', async () => {
		const { streamDashboardChat } = await import('$lib/api/ai');
		const mockStream = vi.mocked(streamDashboardChat);
		mockStream
			.mockResolvedValueOnce(singleChunkResponse('first'))
			.mockResolvedValueOnce(singleChunkResponse('second'));

		const { getByRole, container } = renderComponent(AIChatWindow, {
			mode: 'dashboard',
			documentKind: 'all',
			hasContext: true
		});

		const messagesEl = container.querySelector('.hc-ai-chat-messages') as HTMLElement;

		// Step 1 — user scrolls up, sticky goes false.
		stubScrollMetrics(messagesEl, { scrollHeight: 1000, clientHeight: 200, scrollTop: 100 });
		messagesEl.dispatchEvent(new Event('scroll'));

		const editor = container.querySelector('.hc-ai-chat-editor') as HTMLDivElement;
		editor.innerText = 'q1';
		editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
		await new Promise((r) => setTimeout(r, 0));
		getByRole('button', { name: /send/i }).click();
		await settleStream();
		expect(messagesEl.scrollTop).toBe(100); // no snap-back

		// Step 2 — user scrolls back to the bottom, sticky returns to true.
		messagesEl.scrollTop = 800; // distance = 1000 - 800 - 200 = 0 ≤ threshold
		messagesEl.dispatchEvent(new Event('scroll'));

		editor.innerText = 'q2';
		editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
		await new Promise((r) => setTimeout(r, 0));
		getByRole('button', { name: /send/i }).click();
		await settleStream();
		// Sticky resumed → scroll pinned to scrollHeight.
		expect(messagesEl.scrollTop).toBe(1000);
	});

	test('identity change clears visible draft and prior message history', async () => {
		const { streamDashboardChat } = await import('$lib/api/ai');
		const mockStream = vi.mocked(streamDashboardChat);
		mockStream.mockResolvedValue(singleChunkResponse('reply'));

		const { getByRole, container, rerender } = renderComponent(AIChatWindow, {
			mode: 'dashboard',
			documentKind: 'all',
			hasContext: true
		});

		const editor = container.querySelector('.hc-ai-chat-editor') as HTMLDivElement;
		editor.innerText = 'question before switch';
		editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
		await new Promise((r) => setTimeout(r, 0));
		getByRole('button', { name: /send/i }).click();
		await settleStream();
		expect(container.querySelectorAll('.hc-ai-chat-msg').length).toBeGreaterThanOrEqual(2);

		editor.innerText = 'draft to clear';
		editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
		await new Promise((r) => setTimeout(r, 0));

		await rerender({ mode: 'dashboard', documentKind: 'analysis', hasContext: true });
		await new Promise((r) => setTimeout(r, 0));

		expect(container.querySelectorAll('.hc-ai-chat-msg')).toHaveLength(0);
		expect((container.querySelector('.hc-ai-chat-editor') as HTMLDivElement).innerText).toBe('');
	});

	test('identity change aborts an in-flight stream', async () => {
		const { streamDashboardChat } = await import('$lib/api/ai');
		const mockStream = vi.mocked(streamDashboardChat);
		let capturedSignal: AbortSignal | undefined;
		mockStream.mockImplementation((_payload, signal) => {
			capturedSignal = signal;
			return new Promise<Response>((_resolve, reject) => {
				const abort = () => reject(new DOMException('Aborted', 'AbortError'));
				if (signal?.aborted) {
					abort();
					return;
				}
				signal?.addEventListener('abort', abort, { once: true });
			});
		});

		const { getByRole, container, rerender } = renderComponent(AIChatWindow, {
			mode: 'dashboard',
			documentKind: 'all',
			hasContext: true
		});

		const editor = container.querySelector('.hc-ai-chat-editor') as HTMLDivElement;
		editor.innerText = 'keep streaming';
		editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
		await new Promise((r) => setTimeout(r, 0));
		getByRole('button', { name: /send/i }).click();
		await new Promise((r) => setTimeout(r, 0));

		expect(capturedSignal).toBeDefined();
		expect(capturedSignal?.aborted).toBe(false);

		await rerender({ mode: 'dashboard', documentKind: 'analysis', hasContext: true });
		await new Promise((r) => setTimeout(r, 0));
		expect(capturedSignal?.aborted).toBe(true);
	});

	test('minimize then restore preserves message history', async () => {
		const { streamDashboardChat } = await import('$lib/api/ai');
		const mockStream = vi.mocked(streamDashboardChat);
		mockStream.mockResolvedValue(singleChunkResponse('answer'));

		const { getByRole, container } = renderComponent(AIChatWindow, {
			mode: 'dashboard',
			documentKind: 'all',
			hasContext: true
		});

		const editor = container.querySelector('.hc-ai-chat-editor') as HTMLDivElement;
		editor.innerText = 'hello';
		editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
		await new Promise((r) => setTimeout(r, 0));
		getByRole('button', { name: /send/i }).click();
		await settleStream();

		// Both user message and AI placeholder-turned-answer should be in DOM.
		const beforeMinimize = container.querySelectorAll('.hc-ai-chat-msg').length;
		expect(beforeMinimize).toBeGreaterThanOrEqual(2);

		// Minimize, then restore — message DOM nodes must survive.
		const minBtn = getByRole('button', { name: /minimize/i });
		minBtn.click();
		await new Promise((r) => setTimeout(r, 0));
		expect(container.querySelector('.hc-ai-chat')).toHaveClass('hc-ai-chat-minimized');

		getByRole('button', { name: /restore/i }).click();
		await new Promise((r) => setTimeout(r, 0));
		expect(container.querySelector('.hc-ai-chat')).not.toHaveClass('hc-ai-chat-minimized');

		const afterRestore = container.querySelectorAll('.hc-ai-chat-msg').length;
		expect(afterRestore).toBe(beforeMinimize);
	});

	test('maximize toggle preserves message history and draft', async () => {
		const { streamDashboardChat } = await import('$lib/api/ai');
		const mockStream = vi.mocked(streamDashboardChat);
		mockStream.mockResolvedValue(singleChunkResponse('reply'));

		const { getByRole, container } = renderComponent(AIChatWindow, {
			mode: 'dashboard',
			documentKind: 'all',
			hasContext: true
		});

		const editor = container.querySelector('.hc-ai-chat-editor') as HTMLDivElement;
		editor.innerText = 'one';
		editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
		await new Promise((r) => setTimeout(r, 0));
		getByRole('button', { name: /send/i }).click();
		await settleStream();

		const beforeMax = container.querySelectorAll('.hc-ai-chat-msg').length;

		// Start a draft, then maximize.
		editor.innerText = 'draft in progress';
		editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
		await new Promise((r) => setTimeout(r, 0));

		getByRole('button', { name: /maximize/i }).click();
		await new Promise((r) => setTimeout(r, 0));
		expect(container.querySelector('.hc-ai-chat')).toHaveClass('hc-ai-chat-maximized');

		// History preserved; draft preserved because the editor node is the same.
		expect(container.querySelectorAll('.hc-ai-chat-msg').length).toBe(beforeMax);
		expect(editor.innerText).toBe('draft in progress');
	});
});
