import { afterEach, beforeEach, describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { restoreNavigatorLocale, stubNavigatorLocale } from '$lib/test-utils/locale-env';
import { localeStore } from '$lib/stores/locale.svelte';
import LocaleToggle from './locale-toggle.svelte';

describe('LocaleToggle', () => {
	beforeEach(() => {
		window.localStorage.clear();
		localeStore._resetForTests();
		stubNavigatorLocale(['en-US']);
	});
	afterEach(() => {
		window.localStorage.clear();
		localeStore._resetForTests();
		restoreNavigatorLocale();
	});

	test('renders EN / UA buttons with group label', () => {
		const { getByRole, getByTestId } = renderComponent(LocaleToggle);
		const group = getByTestId('locale-toggle');
		expect(group).toBeInTheDocument();
		// Buttons expose accessible names in the current locale (English by default).
		expect(getByRole('button', { name: /english/i })).toBeInTheDocument();
		expect(getByRole('button', { name: /ukrainian/i })).toBeInTheDocument();
	});

	test('reflects current locale via aria-pressed', () => {
		const { getAllByRole } = renderComponent(LocaleToggle);
		const buttons = getAllByRole('button');
		// Two pressed-state buttons; exactly one is pressed (en by default).
		const pressed = buttons.filter((b) => b.getAttribute('aria-pressed') === 'true');
		expect(pressed).toHaveLength(1);
		expect(pressed[0].textContent?.trim()).toBe('EN');
	});

	test('clicking UA sets locale to uk and persists it', () => {
		const { getByRole } = renderComponent(LocaleToggle);
		const ua = getByRole('button', { name: /ukrainian/i });
		ua.click();
		expect(localeStore.locale).toBe('uk');
		expect(window.localStorage.getItem('hc.locale')).toBe('uk');
	});

	test('clicking EN after UA switches back to en', () => {
		const { container } = renderComponent(LocaleToggle);
		// Use structural selectors (first/second button) rather than accessible
		// names, because aria-labels re-translate after each click and the
		// post-switch "english" regex would otherwise rely on un-flushed DOM.
		const [enBtn, ukBtn] = Array.from(
			container.querySelectorAll<HTMLButtonElement>('.hc-locale-toggle-btn')
		);
		ukBtn.click();
		expect(localeStore.locale).toBe('uk');
		enBtn.click();
		expect(localeStore.locale).toBe('en');
	});
});
