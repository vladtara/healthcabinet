/**
 * Locale store (Story 15.6).
 *
 * Persists the user's preferred UI locale across reloads in localStorage.
 * Internal codes are BCP 47 'en' / 'uk' (the visible switch label is EN / UA,
 * but 'uk' is the correct internal code). Bootstrap order on first visit:
 *
 *   1. saved locale in localStorage
 *   2. browser preference (navigator.languages preferred, then navigator.language)
 *   3. 'en' fallback
 *
 * SSR-safe: server-rendered HTML always uses the stable DEFAULT_LOCALE so
 * the server and first client render agree; the store hydrates lazily on the
 * first read from a browser context.
 */

export type Locale = 'en' | 'uk';

export const LOCALES: readonly Locale[] = ['en', 'uk'] as const;
const STORAGE_KEY = 'hc.locale';
const DEFAULT_LOCALE: Locale = 'en';

function isLocale(value: unknown): value is Locale {
	return typeof value === 'string' && (LOCALES as readonly string[]).includes(value);
}

/** Normalize any BCP 47 tag (e.g. 'uk-UA', 'en-US', 'UK') to our internal locale. */
export function normalizeLocaleTag(tag: unknown): Locale | null {
	if (typeof tag !== 'string' || tag.length === 0) return null;
	const base = tag.toLowerCase().split(/[-_]/)[0];
	if (base === 'uk') return 'uk';
	if (base === 'en') return 'en';
	return null;
}

function readBrowserPreference(): Locale | null {
	if (typeof navigator === 'undefined') return null;
	try {
		const langs = Array.isArray(navigator.languages) ? navigator.languages : [];
		for (const tag of langs) {
			const normalized = normalizeLocaleTag(tag);
			if (normalized) return normalized;
		}
		return normalizeLocaleTag(navigator.language);
	} catch {
		// ignore browser-language access errors in hardened environments
		return null;
	}
}

function readFromStorage(): Locale | null {
	if (typeof window === 'undefined') return null;
	try {
		const raw = window.localStorage.getItem(STORAGE_KEY);
		if (isLocale(raw)) return raw;
	} catch {
		// ignore storage access errors (private mode, quota, etc.)
	}
	return null;
}

function writeToStorage(value: Locale): void {
	if (typeof window === 'undefined') return;
	try {
		window.localStorage.setItem(STORAGE_KEY, value);
	} catch {
		// ignore storage write errors
	}
}

function resolveInitialLocale(): Locale {
	return readFromStorage() ?? readBrowserPreference() ?? DEFAULT_LOCALE;
}

// Server-render with the stable default; hydrate eagerly at module load on
// the client so `localeStore.locale` is never written-to from inside a
// `$derived` call path (Svelte 5 forbids `$state` writes during derivation).
let _locale = $state<Locale>(DEFAULT_LOCALE);

function hydrate(): void {
	if (typeof window === 'undefined') return;
	const initial = resolveInitialLocale();
	if (initial !== _locale) _locale = initial;
}

// Module-level hydration runs outside any reactive context — safe for $state writes.
hydrate();

export const localeStore = {
	get locale(): Locale {
		return _locale;
	},
	setLocale(next: Locale): void {
		if (!isLocale(next)) return;
		_locale = next;
		writeToStorage(next);
	},
	/**
	 * Test-only helper — resets in-memory state and re-runs hydration so the
	 * next read picks up the current navigator / localStorage state. This does
	 * NOT clear localStorage; tests that want a clean slate should call
	 * `window.localStorage.clear()` themselves (the suite's beforeEach
	 * typically does this).
	 */
	_resetForTests(): void {
		_locale = DEFAULT_LOCALE;
		hydrate();
	}
};
