import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { localeStore, normalizeLocaleTag } from './locale.svelte';

const STORAGE_KEY = 'hc.locale';
const originalNavigatorLanguages = Object.getOwnPropertyDescriptor(navigator, 'languages');
const originalNavigatorLanguage = Object.getOwnPropertyDescriptor(navigator, 'language');

function stubNavigatorLanguages(languages: readonly string[]) {
	Object.defineProperty(navigator, 'languages', {
		configurable: true,
		get: () => languages
	});
	Object.defineProperty(navigator, 'language', {
		configurable: true,
		get: () => languages[0] ?? 'en'
	});
}

function restoreNavigatorLanguages() {
	if (originalNavigatorLanguages) {
		Object.defineProperty(navigator, 'languages', originalNavigatorLanguages);
	} else {
		delete (navigator as { languages?: readonly string[] }).languages;
	}
	if (originalNavigatorLanguage) {
		Object.defineProperty(navigator, 'language', originalNavigatorLanguage);
	} else {
		delete (navigator as { language?: string }).language;
	}
}

// Hydration is synchronous on first getter read, so tests can just read the
// getter directly — no async plumbing required.

describe('normalizeLocaleTag', () => {
	test('maps en, en-US, EN, en_US to en', () => {
		expect(normalizeLocaleTag('en')).toBe('en');
		expect(normalizeLocaleTag('en-US')).toBe('en');
		expect(normalizeLocaleTag('EN')).toBe('en');
		expect(normalizeLocaleTag('en_US')).toBe('en');
	});

	test('maps uk, uk-UA, UK to uk', () => {
		expect(normalizeLocaleTag('uk')).toBe('uk');
		expect(normalizeLocaleTag('uk-UA')).toBe('uk');
		expect(normalizeLocaleTag('UK')).toBe('uk');
	});

	test('returns null for unsupported tags and garbage input', () => {
		expect(normalizeLocaleTag('fr')).toBeNull();
		expect(normalizeLocaleTag('')).toBeNull();
		expect(normalizeLocaleTag(undefined)).toBeNull();
		expect(normalizeLocaleTag(42)).toBeNull();
	});

	test('ignores ua (not a BCP 47 tag) and maps nothing for it', () => {
		// 'ua' is a country code; the language tag for Ukrainian is 'uk'. The
		// UI's visible label is 'UA' but the internal code must remain 'uk'.
		expect(normalizeLocaleTag('ua')).toBeNull();
	});
});

describe('localeStore', () => {
	beforeEach(() => {
		window.localStorage.clear();
		localeStore._resetForTests();
		stubNavigatorLanguages(['en-US']);
	});

	afterEach(() => {
		window.localStorage.clear();
		localeStore._resetForTests();
		restoreNavigatorLanguages();
	});

	// Tests that need hydration to pick up a newly-stubbed env call
	// `_resetForTests()` AFTER applying the stub, because module-load
	// hydration already ran once and the beforeEach reset runs before
	// the per-test stub override.

	test('defaults to en when nothing is saved and browser has no preference', () => {
		stubNavigatorLanguages([]);
		localeStore._resetForTests();
		expect(localeStore.locale).toBe('en');
	});

	test('saved locale wins over browser preference', () => {
		window.localStorage.setItem(STORAGE_KEY, 'uk');
		stubNavigatorLanguages(['en-US']);
		localeStore._resetForTests();
		expect(localeStore.locale).toBe('uk');
	});

	test('browser preference uk-UA normalizes to internal uk when nothing saved', () => {
		stubNavigatorLanguages(['uk-UA', 'en-US']);
		localeStore._resetForTests();
		expect(localeStore.locale).toBe('uk');
	});

	test('navigator.languages order is respected (uk comes before en)', () => {
		stubNavigatorLanguages(['uk', 'en-US']);
		localeStore._resetForTests();
		expect(localeStore.locale).toBe('uk');
	});

	test('unsupported browser preferences fall through to en', () => {
		stubNavigatorLanguages(['fr-FR', 'de-DE']);
		localeStore._resetForTests();
		expect(localeStore.locale).toBe('en');
	});

	test('invalid stored value is ignored and bootstrap continues', () => {
		window.localStorage.setItem(STORAGE_KEY, 'banana');
		stubNavigatorLanguages(['uk-UA']);
		localeStore._resetForTests();
		expect(localeStore.locale).toBe('uk');
	});

	test('setLocale updates reactive state and persists to localStorage', () => {
		localeStore.setLocale('uk');
		expect(localeStore.locale).toBe('uk');
		expect(window.localStorage.getItem(STORAGE_KEY)).toBe('uk');
		localeStore.setLocale('en');
		expect(localeStore.locale).toBe('en');
		expect(window.localStorage.getItem(STORAGE_KEY)).toBe('en');
	});

	test('setLocale rejects garbage values at the boundary', () => {
		(localeStore as unknown as { setLocale: (v: unknown) => void }).setLocale('banana');
		expect(localeStore.locale).toBe('en');
		expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
	});

	test('_resetForTests resets in-memory state and re-hydrates from current env', () => {
		localeStore.setLocale('uk');
		expect(window.localStorage.getItem(STORAGE_KEY)).toBe('uk');
		expect(localeStore.locale).toBe('uk');

		// Caller clears storage first for a full clean slate.
		window.localStorage.clear();
		stubNavigatorLanguages(['en-US']);
		localeStore._resetForTests();

		expect(localeStore.locale).toBe('en');
		expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
	});

	test('storage access failures do not break rendering', () => {
		// Simulate a SecurityError from blocked-storage scenarios.
		const getItemSpy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
			throw new Error('SecurityError');
		});
		try {
			expect(localeStore.locale).toBe('en');
		} finally {
			getItemSpy.mockRestore();
		}
	});
});
