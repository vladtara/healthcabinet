import { beforeEach, describe, expect, test, vi } from 'vitest';

import { apiFetch } from '$lib/api/client.svelte';

import { getHealthValues } from './health-values';

vi.mock('$lib/api/client.svelte', () => ({
	apiFetch: vi.fn()
}));

const mockApiFetch = vi.mocked(apiFetch);

describe('getHealthValues (Story 15.3 filter)', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockApiFetch.mockResolvedValue([]);
	});

	test('no argument → hits /api/v1/health-values with no query params', async () => {
		await getHealthValues();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/v1/health-values');
	});

	test("'all' → appends ?document_kind=all", async () => {
		await getHealthValues('all');
		expect(mockApiFetch).toHaveBeenCalledWith('/api/v1/health-values?document_kind=all');
	});

	test("'analysis' → appends ?document_kind=analysis", async () => {
		await getHealthValues('analysis');
		expect(mockApiFetch).toHaveBeenCalledWith('/api/v1/health-values?document_kind=analysis');
	});

	test("'document' → appends ?document_kind=document", async () => {
		await getHealthValues('document');
		expect(mockApiFetch).toHaveBeenCalledWith('/api/v1/health-values?document_kind=document');
	});
});
