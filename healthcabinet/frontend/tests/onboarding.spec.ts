import { expect, test } from '@playwright/test';
import { setupAuth, MOCK_PROFILE } from './helpers/auth';

const EMPTY_PROFILE = { ...MOCK_PROFILE, onboarding_step: 0 };

const COMPLETED_PROFILE = {
	...MOCK_PROFILE,
	age: 30,
	sex: 'female',
	height_cm: 165,
	weight_kg: 60,
	onboarding_step: 3
};

test.describe('Onboarding wizard', () => {
	test.beforeEach(async ({ page }) => {
		await setupAuth(page);

		// Default: fresh user with no profile (step 0)
		await page.route('**/api/v1/users/me/profile', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(EMPTY_PROFILE)
			})
		);
		await page.route('**/api/v1/users/me/onboarding-step', (route) =>
			route.fulfill({ status: 204, body: '' })
		);
		await page.route('**/api/v1/users/me/profile', (route) => {
			if (route.request().method() === 'PUT') {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(COMPLETED_PROFILE)
				});
			}
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(EMPTY_PROFILE)
			});
		});
		// Dashboard mocks for after completion
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

	test('renders "Set up your health profile" heading', async ({ page }) => {
		await page.goto('/onboarding');
		await expect(page.getByRole('heading', { name: 'Set up your health profile' })).toBeVisible();
	});

	test('shows "Step 1 of 3" progress indicator on load', async ({ page }) => {
		await page.goto('/onboarding');
		await expect(page.getByText('Step 1 of 3')).toBeVisible();
	});

	test('step 1 shows "Basic Information" section heading', async ({ page }) => {
		await page.goto('/onboarding');
		await expect(page.getByRole('heading', { name: 'Basic Information' })).toBeVisible();
	});

	test('Continue button advances to step 2', async ({ page }) => {
		await page.goto('/onboarding');
		await page.getByRole('button', { name: 'Continue' }).click();
		await expect(page.getByText('Step 2 of 3')).toBeVisible();
		await expect(page.getByRole('heading', { name: 'Health Conditions' })).toBeVisible();
	});

	test('validates age out of range (> 120) on blur', async ({ page }) => {
		await page.goto('/onboarding');
		await page.fill('#age', '200');
		await page.locator('#age').blur();
		await expect(page.getByText('Age must be between 1 and 120')).toBeVisible();
	});

	test('validates height out of range (< 50 cm) on blur', async ({ page }) => {
		await page.goto('/onboarding');
		await page.fill('#height', '10');
		await page.locator('#height').blur();
		await expect(page.getByText('Height must be between 50 and 300 cm')).toBeVisible();
	});

	test('validates weight out of range (> 500 kg) on blur', async ({ page }) => {
		await page.goto('/onboarding');
		await page.fill('#weight', '600');
		await page.locator('#weight').blur();
		await expect(page.getByText('Weight must be between 10 and 500 kg')).toBeVisible();
	});

	test('step 2: toggling a preset condition marks it as selected', async ({ page }) => {
		await page.goto('/onboarding');
		await page.getByRole('button', { name: 'Continue' }).click();

		const hypertensionBtn = page.getByRole('button', { name: 'Hypertension' });
		await expect(hypertensionBtn).toHaveAttribute('aria-pressed', 'false');
		await hypertensionBtn.click();
		await expect(hypertensionBtn).toHaveAttribute('aria-pressed', 'true');
	});

	test('step 2: toggling a selected condition deselects it', async ({ page }) => {
		await page.goto('/onboarding');
		await page.getByRole('button', { name: 'Continue' }).click();

		const btn = page.getByRole('button', { name: 'Asthma' });
		await btn.click();
		await expect(btn).toHaveAttribute('aria-pressed', 'true');
		await btn.click();
		await expect(btn).toHaveAttribute('aria-pressed', 'false');
	});

	test('step 2: adding a custom condition via Add button', async ({ page }) => {
		await page.goto('/onboarding');
		await page.getByRole('button', { name: 'Continue' }).click();

		await page.getByLabel('Other condition').fill('Lupus');
		await page.getByRole('button', { name: 'Add' }).click();

		await expect(page.getByRole('button', { name: /Lupus/ })).toBeVisible();
	});

	test('step 2: Back button returns to step 1', async ({ page }) => {
		await page.goto('/onboarding');
		await page.getByRole('button', { name: 'Continue' }).click();
		await expect(page.getByText('Step 2 of 3')).toBeVisible();

		await page.getByRole('button', { name: 'Back' }).click();
		await expect(page.getByText('Step 1 of 3')).toBeVisible();
	});

	test('step 3 shows "Family History" heading and "Complete Setup" button', async ({ page }) => {
		await page.goto('/onboarding');
		// Step 1 → 2 → 3
		await page.getByRole('button', { name: 'Continue' }).click();
		await page.getByRole('button', { name: 'Continue' }).click();

		await expect(page.getByRole('heading', { name: 'Family History' })).toBeVisible();
		await expect(page.getByRole('button', { name: 'Complete Setup' })).toBeVisible();
	});

	test('happy path: complete all 3 steps → redirects to /dashboard', async ({ page }) => {
		await page.goto('/onboarding');

		// Step 1: fill basic info and advance
		await page.fill('#age', '30');
		await page.getByRole('button', { name: 'Continue' }).click();

		// Step 2: skip conditions, advance
		await page.getByRole('button', { name: 'Continue' }).click();

		// Step 3: submit
		await page.getByRole('button', { name: 'Complete Setup' }).click();

		await page.waitForURL('**/dashboard');
		await expect(page).toHaveURL(/\/dashboard/);
	});

	test('already-completed profile redirects to /dashboard immediately', async ({ page }) => {
		await page.unroute('**/api/v1/users/me/profile');
		await page.route('**/api/v1/users/me/profile', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(COMPLETED_PROFILE) // onboarding_step: 3
			})
		);

		await page.goto('/onboarding');
		await page.waitForURL('**/dashboard');
		await expect(page).toHaveURL(/\/dashboard/);
	});

	test('skipping all optional fields still allows completion', async ({ page }) => {
		await page.goto('/onboarding');
		// Navigate through all steps without entering any data
		await page.getByRole('button', { name: 'Continue' }).click();
		await page.getByRole('button', { name: 'Continue' }).click();
		await page.getByRole('button', { name: 'Complete Setup' }).click();

		await page.waitForURL('**/dashboard');
		await expect(page).toHaveURL(/\/dashboard/);
	});
});
