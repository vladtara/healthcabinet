import { afterEach, beforeEach, describe, expect, test } from 'vitest';
import { dashboardFilterStore } from './dashboard-filter.svelte';

const STORAGE_KEY = 'hc.dashboard.filter';

describe('dashboardFilterStore', () => {
	beforeEach(() => {
		window.localStorage.clear();
		dashboardFilterStore._resetForTests();
	});

	afterEach(() => {
		window.localStorage.clear();
		dashboardFilterStore._resetForTests();
	});

	test('defaults to analysis when localStorage is empty', () => {
		expect(dashboardFilterStore.filter).toBe('analysis');
	});

	test('setFilter updates reactive state and writes to localStorage', () => {
		dashboardFilterStore.setFilter('all');
		expect(dashboardFilterStore.filter).toBe('all');
		expect(window.localStorage.getItem(STORAGE_KEY)).toBe('all');
	});

	test('setFilter accepts every valid value', () => {
		dashboardFilterStore.setFilter('document');
		expect(dashboardFilterStore.filter).toBe('document');
		dashboardFilterStore.setFilter('analysis');
		expect(dashboardFilterStore.filter).toBe('analysis');
		dashboardFilterStore.setFilter('all');
		expect(dashboardFilterStore.filter).toBe('all');
	});

	test('garbage in localStorage falls back to default on reinit', async () => {
		window.localStorage.setItem(STORAGE_KEY, 'banana');
		// Reset the module graph, import a fresh singleton to observe init
		// behavior, then restore the original modules before the test returns
		// so follow-up tests see the shared singleton (the suite-wide
		// afterEach's `_resetForTests()` must target the SAME instance that
		// `describe` imported at module-collection time).
		const { vi } = await import('vitest');
		vi.resetModules();
		try {
			const mod = await import('./dashboard-filter.svelte');
			expect(mod.dashboardFilterStore.filter).toBe('analysis');
		} finally {
			vi.resetModules();
			// Re-run the test-file's import so the top-level `dashboardFilterStore`
			// binding points at a fresh, isolated singleton for any follow-up
			// test in this file — but note: the module-level import at the top
			// of the test file still points at the ORIGINAL singleton (imports
			// are cached at collection time). The afterEach `_resetForTests()`
			// on that original singleton remains effective for subsequent tests.
		}
	});

	test('setFilter rejects garbage at runtime (type-system bypass)', () => {
		// Simulate a caller with a loose cast or a corrupted upstream value.
		(dashboardFilterStore as unknown as { setFilter: (v: unknown) => void }).setFilter(
			'banana'
		);
		expect(dashboardFilterStore.filter).toBe('analysis');
		expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
	});

	test('_resetForTests clears both state and storage', () => {
		dashboardFilterStore.setFilter('document');
		expect(window.localStorage.getItem(STORAGE_KEY)).toBe('document');
		dashboardFilterStore._resetForTests();
		expect(dashboardFilterStore.filter).toBe('analysis');
		expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
	});
});
