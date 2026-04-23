import type { Page } from '@playwright/test';

/**
 * Replace the native EventSource with a controllable mock before page load.
 * Must be called before page.goto() via addInitScript.
 */
export async function setupSSEMock(page: Page): Promise<void> {
	await page.addInitScript(() => {
		interface WindowWithSources extends Window {
			__eventSources?: MockEventSource[];
			EventSource: typeof MockEventSource;
		}

		class MockEventSource {
			static CONNECTING = 0;
			static OPEN = 1;
			static CLOSED = 2;

			url: string;
			readyState = MockEventSource.OPEN;
			onmessage: ((event: { data: string }) => void) | null = null;
			onerror: (() => void) | null = null;

			constructor(url: string) {
				this.url = url;
				const win = globalThis as unknown as WindowWithSources;
				win.__eventSources ??= [];
				win.__eventSources.push(this);
			}

			close() {
				this.readyState = MockEventSource.CLOSED;
			}
		}

		(globalThis as unknown as WindowWithSources).EventSource = MockEventSource;
	});
}

/** Wait for the first EventSource to be created, then dispatch a list of document events. */
export async function dispatchSSEEvents(
	page: Page,
	documentId: string,
	events: string[]
): Promise<void> {
	await page.waitForFunction(
		() => (window as Window & { __eventSources?: unknown[] }).__eventSources?.length === 1
	);
	await page.evaluate(
		({ docId, evts }) => {
			const source = (
				window as unknown as Window & {
					__eventSources: Array<{ onmessage: (event: { data: string }) => void }>;
				}
			).__eventSources[0];
			for (const event of evts) {
				source.onmessage({
					data: JSON.stringify({ event, document_id: docId, progress: 1, message: event })
				});
			}
		},
		{ docId: documentId, evts: events }
	);
}

/** Trigger N consecutive onerror calls on the first EventSource. */
export async function triggerSSEErrors(page: Page, count: number): Promise<void> {
	await page.waitForFunction(
		() => (window as Window & { __eventSources?: unknown[] }).__eventSources?.length === 1
	);
	await page.evaluate(
		({ n }) => {
			const source = (
				window as unknown as Window & {
					__eventSources: Array<{ onerror: () => void }>;
				}
			).__eventSources[0];
			for (let i = 0; i < n; i++) source.onerror();
		},
		{ n: count }
	);
}
