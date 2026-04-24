import { expect, test } from '@playwright/test';
import { MOCK_USER, MOCK_TOKEN } from './helpers/auth';

// ─── Shared mock payloads ────────────────────────────────────────────────────

const REGISTER_RESPONSE = {
	id: 'user-1',
	email: 'new@example.com',
	access_token: MOCK_TOKEN,
	token_type: 'bearer'
};

const LOGIN_RESPONSE = {
	access_token: MOCK_TOKEN,
	token_type: 'bearer'
};

// ─── Registration ────────────────────────────────────────────────────────────

test.describe('Registration', () => {
	test.beforeEach(async ({ page }) => {
		// Mock auth endpoints needed after successful registration (SPA nav to /onboarding)
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
		// Onboarding page calls getProfile on load
		await page.route('**/api/v1/users/me/profile', (route) =>
			route.fulfill({ status: 404, body: '{}' })
		);
		await page.route('**/api/v1/users/me/onboarding-step', (route) =>
			route.fulfill({ status: 204, body: '' })
		);
	});

	test('renders "Create your account" heading', async ({ page }) => {
		await page.goto('/register');
		await expect(page.getByRole('heading', { name: 'Create your account' })).toBeVisible();
	});

	test('Create Account button is disabled until GDPR consent is checked', async ({ page }) => {
		await page.goto('/register');
		const btn = page.getByRole('button', { name: 'Create Account' });
		await expect(btn).toBeDisabled();

		await page.fill('#email', 'test@example.com');
		await page.fill('#password', 'password123');
		await page.fill('#confirm-password', 'password123');
		await expect(btn).toBeDisabled(); // still disabled without GDPR

		await page.getByRole('checkbox', { name: /consent to health data processing/i }).click();
		await expect(btn).toBeEnabled();
	});

	test('shows email validation error on blur with invalid email', async ({ page }) => {
		await page.goto('/register');
		await page.fill('#email', 'not-an-email');
		await page.locator('#email').blur();
		await expect(page.getByText('Please enter a valid email address')).toBeVisible();
	});

	test('shows password too short error on blur', async ({ page }) => {
		await page.goto('/register');
		await page.fill('#password', 'short');
		await page.locator('#password').blur();
		await expect(page.getByText('Password must be at least 8 characters')).toBeVisible();
	});

	test('shows "Passwords do not match" error on submit', async ({ page }) => {
		await page.goto('/register');
		await page.fill('#email', 'test@example.com');
		await page.fill('#password', 'password123');
		await page.fill('#confirm-password', 'different456');
		await page.getByRole('checkbox', { name: /consent to health data processing/i }).click();
		await page.getByRole('button', { name: 'Create Account' }).click();
		await expect(page.getByText('Passwords do not match')).toBeVisible();
	});

	test('happy path: successful registration redirects to /onboarding', async ({ page }) => {
		await page.route('**/api/v1/auth/register', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(REGISTER_RESPONSE)
			})
		);

		await page.goto('/register');
		await page.fill('#email', 'new@example.com');
		await page.fill('#password', 'password123');
		await page.fill('#confirm-password', 'password123');
		await page.getByRole('checkbox', { name: /consent to health data processing/i }).click();
		await page.getByRole('button', { name: 'Create Account' }).click();

		await page.waitForURL('**/onboarding');
		await expect(page).toHaveURL(/\/onboarding/);
	});

	test('shows "An account with this email already exists" on 409', async ({ page }) => {
		await page.route('**/api/v1/auth/register', (route) =>
			route.fulfill({
				status: 409,
				contentType: 'application/json',
				body: JSON.stringify({ type: 'about:blank', title: 'Conflict', status: 409 })
			})
		);

		await page.goto('/register');
		await page.fill('#email', 'existing@example.com');
		await page.fill('#password', 'password123');
		await page.fill('#confirm-password', 'password123');
		await page.getByRole('checkbox', { name: /consent to health data processing/i }).click();
		await page.getByRole('button', { name: 'Create Account' }).click();

		await expect(page.getByText('An account with this email already exists')).toBeVisible();
	});

	test('shows generic error on server failure', async ({ page }) => {
		await page.route('**/api/v1/auth/register', (route) =>
			route.fulfill({
				status: 500,
				contentType: 'application/json',
				body: JSON.stringify({
					type: 'about:blank',
					title: 'Internal Server Error',
					status: 500,
					detail: 'Registration failed. Please try again.'
				})
			})
		);

		await page.goto('/register');
		await page.fill('#email', 'test@example.com');
		await page.fill('#password', 'password123');
		await page.fill('#confirm-password', 'password123');
		await page.getByRole('checkbox', { name: /consent to health data processing/i }).click();
		await page.getByRole('button', { name: 'Create Account' }).click();

		await expect(page.getByRole('alert')).toBeVisible();
	});

	test('shows "Sign in" link pointing to /login', async ({ page }) => {
		await page.goto('/register');
		await expect(page.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login');
	});

	test('shows security trust badges', async ({ page }) => {
		await page.goto('/register');
		await expect(page.getByText('AES-256 encrypted')).toBeVisible();
		await expect(page.getByText('EU data residency')).toBeVisible();
		await expect(page.getByText('GDPR compliant')).toBeVisible();
	});
});

// ─── Login ───────────────────────────────────────────────────────────────────

test.describe('Login', () => {
	test.beforeEach(async ({ page }) => {
		// After login the app calls /api/v1/auth/me and navigates to /dashboard
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
		// Dashboard calls health-values and baseline
		await page.route('**/api/v1/health-values/baseline', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ recommendations: [], has_uploads: false })
			})
		);
		await page.route('**/api/v1/health-values', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			})
		);
	});

	test('renders "Sign In" heading', async ({ page }) => {
		await page.goto('/login');
		await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible();
	});

	test('happy path: valid credentials redirect to /dashboard', async ({ page }) => {
		await page.route('**/api/v1/auth/login', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(LOGIN_RESPONSE)
			})
		);

		await page.goto('/login');
		await page.fill('#email', 'test@example.com');
		await page.fill('#password', 'password123');
		await page.getByRole('button', { name: 'Sign In' }).click();

		await page.waitForURL('**/dashboard');
		await expect(page).toHaveURL(/\/dashboard/);
	});

	test('shows "Invalid email or password" on 401', async ({ page }) => {
		await page.route('**/api/v1/auth/login', (route) =>
			route.fulfill({
				status: 401,
				contentType: 'application/json',
				body: JSON.stringify({ type: 'about:blank', title: 'Unauthorized', status: 401 })
			})
		);

		await page.goto('/login');
		await page.fill('#email', 'wrong@example.com');
		await page.fill('#password', 'wrongpassword');
		await page.getByRole('button', { name: 'Sign In' }).click();

		await expect(page.getByText('Invalid email or password')).toBeVisible();
	});

	test('shows generic error message on 500', async ({ page }) => {
		await page.route('**/api/v1/auth/login', (route) =>
			route.fulfill({
				status: 500,
				contentType: 'application/json',
				body: JSON.stringify({
					type: 'about:blank',
					title: 'Internal Server Error',
					status: 500
				})
			})
		);

		await page.goto('/login');
		await page.fill('#email', 'test@example.com');
		await page.fill('#password', 'password123');
		await page.getByRole('button', { name: 'Sign In' }).click();

		await expect(page.getByText('Something went wrong, please try again')).toBeVisible();
	});

	test('Submit button shows "Signing in..." while loading', async ({ page }) => {
		let resolveLogin: () => void;
		const loginHeld = new Promise<void>((r) => (resolveLogin = r));

		await page.route('**/api/v1/auth/login', async (route) => {
			await loginHeld; // hold indefinitely until we release
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(LOGIN_RESPONSE)
			});
		});

		await page.goto('/login');
		await page.fill('#email', 'test@example.com');
		await page.fill('#password', 'password123');
		await page.getByRole('button', { name: 'Sign In' }).click();

		await expect(page.getByRole('button', { name: 'Signing in...' })).toBeVisible();
		resolveLogin!();
	});

	test('shows "Register" link pointing to /register', async ({ page }) => {
		await page.goto('/login');
		await expect(page.getByRole('link', { name: 'Register' })).toHaveAttribute('href', '/register');
	});

	test('hard reload on protected route keeps authenticated user on page', async ({ page }) => {
		// Story 15.7 AC3 — regression gate for Story 15.1 (auth bootstrap restore
		// guard). Before the fix, a hard reload on /dashboard could race with the
		// refresh call and redirect to /login while the bootstrap was still in
		// `unknown`/`restoring`. This test confirms the layout guard now waits
		// for bootstrap to resolve before deciding on a redirect.
		await page.route('**/api/v1/auth/login', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(LOGIN_RESPONSE)
			})
		);

		await page.goto('/login');
		await page.fill('#email', 'test@example.com');
		await page.fill('#password', 'password123');
		await page.getByRole('button', { name: 'Sign In' }).click();
		await page.waitForURL('**/dashboard');
		await expect(page).toHaveURL(/\/dashboard/);

		// Hard reload — refresh + me remain mocked at the context level; the
		// layout guard must NOT bounce us to /login during bootstrap.
		await page.reload();
		await expect(page).toHaveURL(/\/dashboard/);
		await expect(page).not.toHaveURL(/\/login/);
	});
});
