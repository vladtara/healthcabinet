import axe from 'axe-core';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { restoreNavigatorLocale, stubNavigatorLocale } from '$lib/test-utils/locale-env';
import AppShell from './AppShell.svelte';
import { localeStore } from '$lib/stores/locale.svelte';

vi.mock('$lib/stores/auth.svelte', () => ({
	authStore: {
		get user() {
			return { id: '1', email: 'test@example.com', role: 'user', tier: 'free' };
		},
		get isAuthenticated() {
			return true;
		},
		logout: vi.fn().mockResolvedValue(undefined)
	}
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

vi.mock('$app/stores', () => {
	const page = {
		subscribe: (fn: (val: unknown) => void) => {
			fn({ url: new URL('http://localhost/dashboard') });
			return () => {};
		}
	};
	return { page };
});

vi.mock('$lib/api/client.svelte', () => ({
	tokenState: { accessToken: 'test', setToken: vi.fn(), clear: vi.fn() },
	apiFetch: vi.fn()
}));

describe('AppShell', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		window.localStorage.clear();
		localeStore._resetForTests();
		stubNavigatorLocale(['en-US']);
	});
	afterEach(() => {
		window.localStorage.clear();
		localeStore._resetForTests();
		restoreNavigatorLocale();
	});

	test('renders header with HealthCabinet brand', () => {
		const { container } = renderComponent(AppShell);
		const brand = container.querySelector('.hc-app-header-brand');
		expect(brand).toBeInTheDocument();
		expect(brand!.textContent).toContain('HealthCabinet');
	});

	test('renders left nav with Dashboard, Documents, Settings items', () => {
		const { container } = renderComponent(AppShell);
		const navItems = container.querySelectorAll('.hc-app-nav-item');
		expect(navItems.length).toBeGreaterThanOrEqual(3);
		const navText = container.querySelector('.hc-app-left-nav')!.textContent;
		expect(navText).toContain('Dashboard');
		expect(navText).toContain('Documents');
		expect(navText).toContain('Settings');
	});

	test('renders status bar', () => {
		const { container } = renderComponent(AppShell);
		const statusBar = container.querySelector('.hc-app-status-bar');
		expect(statusBar).toBeInTheDocument();
	});

	test('renders user email in header', () => {
		const { container } = renderComponent(AppShell);
		const userArea = container.querySelector('.hc-app-header-user');
		expect(userArea).toBeInTheDocument();
		expect(userArea!.textContent).toContain('test@example.com');
	});

	test('admin nav section hidden for regular users', () => {
		const { container } = renderComponent(AppShell);
		const navText = container.querySelector('.hc-app-left-nav')!.textContent;
		expect(navText).not.toContain('Admin Console');
	});

	test('Sign Out button is present', () => {
		const { getByRole } = renderComponent(AppShell);
		const signOut = getByRole('button', { name: /sign out/i });
		expect(signOut).toBeInTheDocument();
	});

	test('is accessible (axe audit)', async () => {
		const { container } = renderComponent(AppShell);
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	// ── Story 15.6 — localization ──────────────────────────────────────────────

	test('renders a LocaleToggle in the header', () => {
		const { container } = renderComponent(AppShell);
		expect(container.querySelector('[data-testid="locale-toggle"]')).toBeInTheDocument();
	});

	test('switching to uk rerenders nav labels and Sign Out in Ukrainian', async () => {
		const { container } = renderComponent(AppShell);
		const nav = container.querySelector('.hc-app-left-nav')!;
		const userArea = container.querySelector('.hc-app-header-user')!;

		// Baseline (en) — assert English copy on both sides so a regression
		// that drops the en dictionary cannot pass silently via uk fallback.
		expect(nav.textContent).toContain('Dashboard');
		expect(nav.textContent).toContain('Documents');
		expect(userArea.textContent).toContain('Sign Out');

		// Flip and re-assert — same nodes, different strings.
		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));

		expect(nav.textContent).toContain('Панель');
		expect(nav.textContent).toContain('Документи');
		expect(userArea.textContent).toContain('Вийти');
	});
});
