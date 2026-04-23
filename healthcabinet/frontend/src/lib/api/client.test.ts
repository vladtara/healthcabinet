import { afterEach, describe, expect, test, vi } from 'vitest';

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

vi.mock('$env/dynamic/public', () => ({
	env: {
		PUBLIC_API_URL: 'http://localhost:8000'
	}
}));

import { apiStream, tokenState } from './client.svelte';

describe('apiStream', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
		vi.clearAllMocks();
		tokenState.clear();
	});

	test('preserves AbortError so callers can treat cancellation separately', async () => {
		const abortError = new DOMException('The operation was aborted.', 'AbortError');
		vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abortError));

		await expect(apiStream('/api/v1/ai/chat', { signal: new AbortController().signal })).rejects.toBe(
			abortError
		);
	});
});
