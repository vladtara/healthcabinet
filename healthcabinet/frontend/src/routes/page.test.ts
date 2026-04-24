import axe from 'axe-core';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { restoreNavigatorLocale, stubNavigatorLocale } from '$lib/test-utils/locale-env';
import { localeStore } from '$lib/stores/locale.svelte';
import LandingPage from './+page.svelte';

vi.mock('$lib/stores/auth.svelte', () => ({
	authStore: {
		get isAuthenticated() {
			return false;
		}
	}
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

vi.mock('$app/stores', () => ({
	page: {
		subscribe(run: (value: { url: URL }) => void) {
			run({ url: new URL('http://localhost/') });
			return () => {};
		}
	}
}));

vi.mock('$lib/api/client.svelte', () => ({
	tokenState: { accessToken: null, setToken: vi.fn(), clear: vi.fn() },
	apiFetch: vi.fn()
}));

describe('Landing page', () => {
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

	test('renders heading text', () => {
		const { getByRole } = renderComponent(LandingPage);
		const heading = getByRole('heading', { level: 1 });
		expect(heading).toBeInTheDocument();
		expect(heading.textContent).toContain('Your health data,');
		expect(heading.textContent).toContain('finally understood.');
	});

	test('renders CTA button linking to /register', () => {
		const { getByRole } = renderComponent(LandingPage);
		const cta = getByRole('link', { name: /create free account/i });
		expect(cta).toBeInTheDocument();
		expect(cta).toHaveAttribute('href', '/register');
	});

	test('renders Sign In link to /login', () => {
		const { getByRole } = renderComponent(LandingPage);
		const signIn = getByRole('link', { name: /sign in/i });
		expect(signIn).toBeInTheDocument();
		expect(signIn).toHaveAttribute('href', '/login');
	});

	test('renders trust signals', () => {
		const { container } = renderComponent(LandingPage);
		const trustSection = container.querySelector('.hc-landing-trust');
		expect(trustSection).toBeInTheDocument();
		const badges = trustSection!.querySelectorAll('.hc-landing-trust-badge');
		expect(badges).toHaveLength(3);
		expect(trustSection!.textContent).toContain('AES-256 Encrypted');
		expect(trustSection!.textContent).toContain('EU Data Residency');
		expect(trustSection!.textContent).toContain('GDPR Compliant');
	});

	test('renders top bar with brand', () => {
		const { container } = renderComponent(LandingPage);
		const brand = container.querySelector('.hc-landing-brand');
		expect(brand).toBeInTheDocument();
		expect(brand!.textContent).toContain('HealthCabinet');
	});

	test('topbar nav aria label is localized after locale toggle', async () => {
		const { container, getByRole } = renderComponent(LandingPage);
		const topbar = container.querySelector('.hc-landing-topbar');
		expect(topbar).toHaveAttribute('aria-label', 'Main');

		getByRole('button', { name: /ukrainian/i }).click();
		await new Promise((r) => setTimeout(r, 0));

		expect(topbar).toHaveAttribute('aria-label', 'Основна');
	});

	test('renders preview teaser table', () => {
		const { container } = renderComponent(LandingPage);
		const table = container.querySelector('.hc-landing-preview-table');
		expect(table).toBeInTheDocument();
		const overlay = container.querySelector('.hc-landing-preview-overlay-text');
		expect(overlay).toBeInTheDocument();
		expect(overlay!.textContent).toBe('See your health clearly');
	});

	test('renders fullscreen layout with topbar, hero, trust, and preview sections', () => {
		const { container } = renderComponent(LandingPage);
		const landing = container.querySelector('.hc-landing');
		expect(landing).toBeInTheDocument();
		expect(landing!.querySelector('.hc-landing-topbar')).toBeInTheDocument();
		expect(landing!.querySelector('.hc-landing-hero')).toBeInTheDocument();
		expect(landing!.querySelector('.hc-landing-trust')).toBeInTheDocument();
		expect(landing!.querySelector('.hc-landing-preview')).toBeInTheDocument();
	});

	test('landing page is accessible (axe audit)', async () => {
		const { container } = renderComponent(LandingPage);
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	test('redirects to /dashboard when authenticated', async () => {
		const { goto } = await import('$app/navigation');
		vi.mocked(goto).mockResolvedValue(undefined as never);

		vi.spyOn(await import('$lib/stores/auth.svelte'), 'authStore', 'get').mockReturnValue({
			isAuthenticated: true
		} as never);

		renderComponent(LandingPage);
		await vi.waitFor(() => {
			expect(goto).toHaveBeenCalledWith('/dashboard');
		});
	});
});
