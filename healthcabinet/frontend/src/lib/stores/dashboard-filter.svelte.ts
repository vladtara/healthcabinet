/**
 * Dashboard filter store (Story 15.3).
 *
 * Persists the dashboard's document_kind filter across reloads in
 * localStorage. Default on first visit is 'analysis' so post-15.2 users
 * immediately see the analysis-scoped dashboard. 'unknown' is deliberately
 * not part of the union — the dashboard never surfaces failed/unreadable
 * classifications.
 */

export type DashboardFilter = 'all' | 'analysis' | 'document';

const STORAGE_KEY = 'hc.dashboard.filter';
const DEFAULT_FILTER: DashboardFilter = 'analysis';
const VALID: readonly DashboardFilter[] = ['all', 'analysis', 'document'] as const;

function isDashboardFilter(value: unknown): value is DashboardFilter {
	return typeof value === 'string' && (VALID as readonly string[]).includes(value);
}

function readFromStorage(): DashboardFilter {
	if (typeof window === 'undefined') return DEFAULT_FILTER;
	try {
		const raw = window.localStorage.getItem(STORAGE_KEY);
		if (isDashboardFilter(raw)) return raw;
	} catch {
		// ignore storage access errors (private mode, quota, etc.)
	}
	return DEFAULT_FILTER;
}

function writeToStorage(value: DashboardFilter): void {
	if (typeof window === 'undefined') return;
	try {
		window.localStorage.setItem(STORAGE_KEY, value);
	} catch {
		// ignore storage write errors
	}
}

// SSR-safety: start at the stable DEFAULT_FILTER so server-rendered HTML is
// deterministic and matches the first client render. Hydrate from localStorage
// lazily on first read from a browser context.
let _filter = $state<DashboardFilter>(DEFAULT_FILTER);
let _hydrated = false;

function hydrateFromStorageIfNeeded(): void {
	if (_hydrated || typeof window === 'undefined') return;
	_hydrated = true;
	const stored = readFromStorage();
	if (stored !== _filter) _filter = stored;
}

export const dashboardFilterStore = {
	get filter(): DashboardFilter {
		hydrateFromStorageIfNeeded();
		return _filter;
	},
	setFilter(next: DashboardFilter): void {
		// Re-validate at the boundary — callers with `any` casts or a corrupted
		// upstream value can't smuggle garbage past the Literal type.
		if (!isDashboardFilter(next)) return;
		_hydrated = true;
		_filter = next;
		writeToStorage(next);
	},
	/** Test-only helper — resets the store state and localStorage key. */
	_resetForTests(): void {
		if (typeof window !== 'undefined') {
			try {
				window.localStorage.removeItem(STORAGE_KEY);
			} catch {
				// ignore
			}
		}
		_filter = DEFAULT_FILTER;
		_hydrated = false;
	}
};
