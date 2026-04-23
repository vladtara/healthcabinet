import { describe, expect, test, vi, beforeEach } from 'vitest';
import axe from 'axe-core';

// vi.hoisted runs before any vi.mock factory so the writable store reference
// is stable AND subscribers receive subsequent `set()` updates (real Svelte
// store contract, not a fire-once readable).
// See: https://vitest.dev/api/vi.html#vi-hoisted
const mocks = vi.hoisted(() => {
	// Inline tiny writable — cannot import 'svelte/store' inside hoisted block.
	type Subscriber<T> = (value: T) => void;
	const createWritable = <T>(initial: T) => {
		let value = initial;
		const subs = new Set<Subscriber<T>>();
		return {
			subscribe(run: Subscriber<T>) {
				subs.add(run);
				run(value);
				return () => subs.delete(run);
			},
			set(next: T) {
				value = next;
				for (const run of subs) run(value);
			}
		};
	};
	return {
		pageStore: createWritable<{ url: URL }>({ url: new URL('http://localhost:3000/privacy') }),
		goto: vi.fn()
	};
});

vi.mock('$app/stores', () => ({
	page: mocks.pageStore
}));

// Intentional: mock $app/navigation even though the privacy page does not
// import it today. If a future refactor adds a goto() call behind a guard,
// `expect(goto).not.toHaveBeenCalled()` below will catch it.
vi.mock('$app/navigation', () => ({
	goto: mocks.goto
}));

import { renderComponent } from '$lib/test-utils/render';
import PrivacyPage from './+page.svelte';

function setUrl(url: string) {
	mocks.pageStore.set({ url: new URL(url) });
}

describe('Privacy policy stub page (Story 6-3)', () => {
	beforeEach(() => {
		setUrl('http://localhost:3000/privacy');
		mocks.goto.mockClear();
	});

	test('renders the policy heading and default version when query param is missing', () => {
		const { container } = renderComponent(PrivacyPage);

		const heading = container.querySelector('.hc-privacy-heading');
		expect(heading?.textContent).toBe('Privacy Policy');

		const subheading = container.querySelector('[data-testid="privacy-version"]');
		expect(subheading?.textContent).toBe('Version current');
	});

	test('renders the version from the ?version= query param when valid', () => {
		setUrl('http://localhost:3000/privacy?version=1.0');

		const { container } = renderComponent(PrivacyPage);

		const subheading = container.querySelector('[data-testid="privacy-version"]');
		expect(subheading?.textContent).toBe('Version 1.0');
	});

	test('accepts a full SemVer 2.0 string with build metadata', () => {
		// Regression gate for the widened VERSION_PATTERN (`+` allowed, 64-char cap).
		// `+` must be URL-encoded as `%2B` in the query string — an unencoded `+`
		// is form-decoded to a space by URLSearchParams. The settings page link
		// producer is responsible for encoding (tracked in deferred-work.md).
		setUrl('http://localhost:3000/privacy?version=1.0.0-rc.1%2Bbuild.2026');

		const { container } = renderComponent(PrivacyPage);

		const subheading = container.querySelector('[data-testid="privacy-version"]');
		expect(subheading?.textContent).toBe('Version 1.0.0-rc.1+build.2026');
	});

	test('falls back to "current" when ?version= contains disallowed characters', () => {
		// Shape guard (NOT the XSS defense — Svelte auto-escapes text interpolation).
		setUrl('http://localhost:3000/privacy?version=%3Cscript%3Ealert(1)%3C/script%3E');

		const { container } = renderComponent(PrivacyPage);

		const subheading = container.querySelector('[data-testid="privacy-version"]');
		expect(subheading?.textContent).toBe('Version current');
	});

	test('falls back to "current" when ?version= exceeds the length cap', () => {
		setUrl('http://localhost:3000/privacy?version=' + 'a'.repeat(65));

		const { container } = renderComponent(PrivacyPage);

		const subheading = container.querySelector('[data-testid="privacy-version"]');
		expect(subheading?.textContent).toBe('Version current');
	});

	test('renders without triggering navigation or auth redirect', () => {
		// Strengthened check: the route is public AND the component does not
		// programmatically redirect. Note: the (marketing) +layout.server.ts
		// (if ever added) is NOT exercised by this isolated component render —
		// a Playwright e2e covers the layout-level redirect case (see
		// deferred-work.md).
		const { container } = renderComponent(PrivacyPage);

		expect(container.querySelector('.hc-privacy-page')).not.toBeNull();
		expect(mocks.goto).not.toHaveBeenCalled();
	});

	test('axe accessibility audit passes', async () => {
		const { container } = renderComponent(PrivacyPage);
		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});
});
