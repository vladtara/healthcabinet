import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

const { apiFetch, apiStream } = vi.hoisted(() => ({
	apiFetch: vi.fn(),
	apiStream: vi.fn()
}));

vi.mock('$lib/api/client.svelte', () => ({
	API_BASE: 'http://localhost:8000',
	apiFetch,
	apiStream,
	tokenState: {
		accessToken: null,
		setToken: vi.fn(),
		clear: vi.fn()
	}
}));

import { exportMyData } from './users';

describe('exportMyData', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.unstubAllGlobals();
	});

	test('downloads the blob through apiStream and revokes the object URL asynchronously', async () => {
		vi.useFakeTimers();

		const anchor = document.createElement('a');
		const clickSpy = vi.spyOn(anchor, 'click').mockImplementation(() => {});
		const removeSpy = vi.spyOn(anchor, 'remove').mockImplementation(() => {});
		vi.spyOn(document, 'createElement').mockReturnValue(anchor);

		const createObjectURL = vi.fn(() => 'blob:export');
		const revokeObjectURL = vi.fn();
		vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });

		const encoder = new TextEncoder();
		const bodyStream = new ReadableStream({
			start(controller) {
				controller.enqueue(encoder.encode('zip-bytes'));
				controller.close();
			}
		});
		apiStream.mockResolvedValue(
			new Response(bodyStream, {
				status: 200,
				headers: {
					'content-disposition': 'attachment; filename="healthcabinet-export-2026-04-02.zip"'
				}
			})
		);

		await exportMyData();

		expect(apiStream).toHaveBeenCalledWith(
			'/api/v1/users/me/export',
			expect.objectContaining({
				method: 'POST',
				credentials: 'include'
			})
		);
		expect(createObjectURL).toHaveBeenCalledTimes(1);
		expect(anchor.download).toBe('healthcabinet-export-2026-04-02.zip');
		expect(clickSpy).toHaveBeenCalledOnce();
		expect(revokeObjectURL).not.toHaveBeenCalled();

		await vi.runAllTimersAsync();

		expect(revokeObjectURL).toHaveBeenCalledWith('blob:export');
		expect(removeSpy).toHaveBeenCalledOnce();
	});

	test('surfaces RFC 7807 error bodies from failed exports', async () => {
		const problem = {
			type: 'about:blank',
			title: 'Export failed',
			status: 500,
			detail: 'zip build failed'
		};
		apiStream.mockResolvedValue(
			new Response(JSON.stringify(problem), {
				status: 500,
				headers: { 'content-type': 'application/problem+json' }
			})
		);

		await expect(exportMyData()).rejects.toEqual(problem);
	});
});
