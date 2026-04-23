import type { Page } from '@playwright/test';

export const MOCK_USER = {
	id: 'user-1',
	email: 'test@example.com',
	role: 'user',
	tier: 'free'
} as const;

export const MOCK_TOKEN = 'playwright-test-token';

export const MOCK_PROFILE = {
	id: 'profile-1',
	user_id: 'user-1',
	age: null,
	sex: null,
	height_cm: null,
	weight_kg: null,
	known_conditions: [],
	medications: [],
	family_history: null,
	onboarding_step: 0,
	created_at: '2026-03-01T00:00:00Z',
	updated_at: '2026-03-01T00:00:00Z'
} as const;

/**
 * Set up auth route mocks so protected routes load without redirecting to /login.
 * Must be called BEFORE page.goto() — (app)/+layout.ts calls authStore.tryRefresh()
 * during page load, which hits POST /api/v1/auth/refresh.
 */
export async function setupAuth(page: Page): Promise<void> {
	await page.route('**/api/v1/auth/refresh', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ access_token: MOCK_TOKEN })
		})
	);
	await page.route('**/api/v1/auth/me', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(MOCK_USER)
		})
	);
}
