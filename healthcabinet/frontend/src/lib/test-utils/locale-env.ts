/**
 * Test helper for locale-aware suites (Story 15.6).
 *
 * Stubs `navigator.languages` + `navigator.language` so locale-bootstrap
 * tests do not pick up the jsdom host's implicit default (which can vary
 * between CI and local), and restores the original descriptors afterwards
 * so adjacent suites don't inherit a leaked stub. Pair with
 * `localeStore._resetForTests()` in the same suite lifecycle.
 */

const originalLanguages = Object.getOwnPropertyDescriptor(navigator, 'languages');
const originalLanguage = Object.getOwnPropertyDescriptor(navigator, 'language');

export function stubNavigatorLocale(languages: readonly string[] = ['en-US']): void {
	Object.defineProperty(navigator, 'languages', {
		configurable: true,
		get: () => languages
	});
	Object.defineProperty(navigator, 'language', {
		configurable: true,
		get: () => languages[0] ?? 'en'
	});
}

export function restoreNavigatorLocale(): void {
	if (originalLanguages) {
		Object.defineProperty(navigator, 'languages', originalLanguages);
	} else {
		delete (navigator as { languages?: readonly string[] }).languages;
	}
	if (originalLanguage) {
		Object.defineProperty(navigator, 'language', originalLanguage);
	} else {
		delete (navigator as { language?: string }).language;
	}
}
