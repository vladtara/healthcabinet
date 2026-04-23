import { afterEach, beforeEach, describe, expect, test } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { textSnippet } from '$lib/test-utils/snippet';
import StatusBar from './status-bar.svelte';
import StatusBarField from './status-bar-field.svelte';
import { statusBarStore } from '$lib/stores/status-bar.svelte';
import { localeStore } from '$lib/stores/locale.svelte';
import { restoreNavigatorLocale, stubNavigatorLocale } from '$lib/test-utils/locale-env';

describe('StatusBar', () => {
	test('renders with status-bar and hc-status-bar classes', () => {
		const { container, getByText } = renderComponent(StatusBar, {
			children: textSnippet('Ready')
		});
		const bar = container.querySelector('.status-bar.hc-status-bar');
		expect(bar).toBeInTheDocument();
		expect(bar).toContainElement(getByText('Ready'));
	});

	test('applies custom class', () => {
		const { container } = renderComponent(StatusBar, { class: 'mt-auto' });
		const bar = container.querySelector('.status-bar');
		expect(bar?.classList.contains('mt-auto')).toBe(true);
	});
});

describe('StatusBarField', () => {
	test('renders with status-bar-field class', () => {
		const { container, getByText } = renderComponent(StatusBarField, {
			children: textSnippet('Idle')
		});
		const field = container.querySelector('.status-bar-field');
		expect(field).toBeInTheDocument();
		expect(field).toContainElement(getByText('Idle'));
	});

	test('applies custom class', () => {
		const { container } = renderComponent(StatusBarField, { class: 'flex-1' });
		const field = container.querySelector('.status-bar-field');
		expect(field?.classList.contains('flex-1')).toBe(true);
	});
});

// ── Story 15.6 — statusBarStore sentinel behavior (Review Round 2) ─────────
describe('statusBarStore default sentinel', () => {
	beforeEach(() => {
		window.localStorage.clear();
		stubNavigatorLocale(['en-US']);
		localeStore._resetForTests();
		statusBarStore.reset();
	});
	afterEach(() => {
		window.localStorage.clear();
		localeStore._resetForTests();
		restoreNavigatorLocale();
		statusBarStore.reset();
	});

	test('initial state writes the English sentinel literal, not localized text', () => {
		// Sentinel stays stable across locale changes so AppShell can translate at render time.
		expect(statusBarStore.status).toBe('Ready');
	});

	test('reset() under uk still writes the sentinel (not Ukrainian), so a toggle back to en shows English', () => {
		statusBarStore.set('Готово', []); // simulate a stale localized write
		expect(statusBarStore.status).toBe('Готово');

		localeStore.setLocale('uk');
		statusBarStore.reset();

		// reset always writes the literal sentinel — AppShell translates.
		expect(statusBarStore.status).toBe('Ready');
	});
});
