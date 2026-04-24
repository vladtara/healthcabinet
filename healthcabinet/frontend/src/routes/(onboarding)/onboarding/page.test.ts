import { fireEvent, waitFor } from '@testing-library/svelte';
import axe from 'axe-core';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import OnboardingPage from './+page.svelte';

vi.mock('$lib/api/users', () => ({
	getProfile: vi.fn().mockResolvedValue(null),
	saveOnboardingStep: vi.fn().mockResolvedValue(undefined),
	updateProfile: vi.fn().mockResolvedValue({
		id: 'profile-1',
		user_id: 'user-1',
		age: null,
		sex: null,
		height_cm: null,
		weight_kg: null,
		known_conditions: [],
		medications: [],
		family_history: null,
		onboarding_step: 3,
		created_at: '2026-03-21T00:00:00Z',
		updated_at: '2026-03-21T00:00:00Z'
	})
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

vi.mock('$lib/api/client.svelte', () => ({
	tokenState: { accessToken: null, setToken: vi.fn(), clear: vi.fn() },
	apiFetch: vi.fn()
}));

import { saveOnboardingStep } from '$lib/api/users';
import { localeStore } from '$lib/stores/locale.svelte';

describe('Onboarding page', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.mocked(saveOnboardingStep).mockResolvedValue(undefined);
		window.localStorage.clear();
		localeStore._resetForTests();
	});

	afterEach(() => {
		window.localStorage.clear();
		localeStore._resetForTests();
	});

	test('step indicator shows correct step number', async () => {
		const { getByRole } = renderComponent(OnboardingPage);
		const progressbar = getByRole('progressbar');
		expect(progressbar).toBeInTheDocument();
		expect(progressbar.textContent).toContain('Step 1 of 3');
	});

	test('sex field renders as select dropdown', () => {
		const { container } = renderComponent(OnboardingPage);
		const select = container.querySelector('select#ob-sex');
		expect(select).toBeInTheDocument();
		const options = select!.querySelectorAll('option');
		expect(options.length).toBe(5); // placeholder + 4 choices
	});

	test('back button absent on step 1, present on steps 2 and 3', async () => {
		const { queryByRole, getByRole } = renderComponent(OnboardingPage);

		// Step 1 — no Back button
		expect(queryByRole('button', { name: /back/i })).toBeNull();

		// Navigate to step 2
		const nextBtn = getByRole('button', { name: /continue/i });
		await fireEvent.click(nextBtn);

		await waitFor(() => {
			expect(getByRole('button', { name: /back/i })).toBeInTheDocument();
		});
	});

	test('checkbox grid toggles condition selection on step 2', async () => {
		const { getByRole, container } = renderComponent(OnboardingPage);

		// Navigate to step 2
		await fireEvent.click(getByRole('button', { name: /continue/i }));

		await waitFor(() => {
			const grid = container.querySelector('.hc-profile-checkbox-grid');
			expect(grid).toBeInTheDocument();
		});

		const checkboxes = container.querySelectorAll(
			'.hc-profile-checkbox-grid input[type="checkbox"]'
		);
		expect(checkboxes.length).toBe(12);

		// Toggle first checkbox
		const firstCheckbox = checkboxes[0] as HTMLInputElement;
		await fireEvent.click(firstCheckbox);
		expect(firstCheckbox.checked).toBe(true);

		await fireEvent.click(firstCheckbox);
		expect(firstCheckbox.checked).toBe(false);
	});

	test('other condition input adds custom condition', async () => {
		const { getByRole, getByLabelText, container } = renderComponent(OnboardingPage);

		// Navigate to step 2
		await fireEvent.click(getByRole('button', { name: /continue/i }));

		await waitFor(() => {
			expect(getByLabelText(/other condition/i)).toBeInTheDocument();
		});

		const otherInput = getByLabelText(/other condition/i);
		await fireEvent.input(otherInput, { target: { value: 'Lupus' } });
		await fireEvent.click(getByRole('button', { name: /^add$/i }));

		await waitFor(() => {
			const customConditions = container.querySelector('.hc-profile-custom-conditions');
			expect(customConditions?.textContent).toContain('Lupus');
		});
	});

	test('all form fields keyboard accessible - axe audit', async () => {
		const { container } = renderComponent(OnboardingPage);

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	test('98.css wizard dialog renders with step indicator and labels', () => {
		const { container, getByText } = renderComponent(OnboardingPage);
		expect(container.querySelector('.hc-wizard-dialog')).toBeInTheDocument();
		expect(container.querySelector('.hc-wizard-header')).toBeInTheDocument();
		expect(container.querySelector('.hc-wizard-step-indicator')).toBeInTheDocument();
		expect(getByText(/step 1 of 3/i)).toBeInTheDocument();
	});

	// ── Story 15.7 — localization ─────────────────────────────────────────────

	test('renders a LocaleToggle in the wizard header', () => {
		const { container } = renderComponent(OnboardingPage);
		const header = container.querySelector('.hc-wizard-header');
		expect(header).toBeInTheDocument();
		expect(header?.querySelector('[data-testid="locale-toggle"]')).toBeInTheDocument();
	});

	test('switching to uk rerenders header, step label, and buttons in Ukrainian', async () => {
		const { container, getByRole } = renderComponent(OnboardingPage);
		const dialog = container.querySelector('.hc-wizard-dialog')!;

		// Baseline — English copy
		expect(dialog.textContent).toContain('Onboarding');
		expect(dialog.textContent).toContain('Basic Information');
		expect(getByRole('button', { name: /continue/i })).toBeInTheDocument();

		// Flip to uk
		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));

		expect(dialog.textContent).toContain('Вступне налаштування');
		expect(dialog.textContent).toContain('Основна інформація');
		expect(dialog.textContent).toContain('Вік');
		expect(dialog.textContent).toContain('Продовжити');
	});

	test('validation errors retranslate when locale flips mid-flow', async () => {
		const { container, getByRole } = renderComponent(OnboardingPage);
		const ageInput = container.querySelector('#ob-age') as HTMLInputElement;

		// Trigger validation in en
		await fireEvent.input(ageInput, { target: { value: '999' } });
		await fireEvent.blur(ageInput);
		await waitFor(() => {
			expect(container.querySelector('#age-error')?.textContent).toContain(
				'Age must be between 1 and 120'
			);
		});

		// Flip locale — error is still present but Ukrainian
		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));
		expect(container.querySelector('#age-error')?.textContent).toContain(
			'Вік має бути від 1 до 120'
		);
		expect(container.querySelector('#age-error')?.textContent).not.toContain('Age must be between');

		// Unrelated assertion — Continue button should remain disabled-agnostic and localized
		expect(getByRole('button', { name: /продовжити/i })).toBeInTheDocument();
	});

	test('preset condition checkboxes retain checked state across locale toggle', async () => {
		const { container, getByRole } = renderComponent(OnboardingPage);

		await fireEvent.click(getByRole('button', { name: /continue/i }));
		await waitFor(() => {
			expect(container.querySelector('.hc-profile-checkbox-grid')).toBeInTheDocument();
		});

		const checkboxes = container.querySelectorAll(
			'.hc-profile-checkbox-grid input[type="checkbox"]'
		);
		const first = checkboxes[0] as HTMLInputElement;
		await fireEvent.click(first);
		expect(first.checked).toBe(true);

		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));

		const refreshedCheckboxes = container.querySelectorAll(
			'.hc-profile-checkbox-grid input[type="checkbox"]'
		);
		expect((refreshedCheckboxes[0] as HTMLInputElement).checked).toBe(true);

		const step2Body = container.querySelector('.hc-wizard-body')!;
		expect(step2Body.textContent).toContain('Діагностовані стани');
		expect(step2Body.textContent).toContain('Діабет 2 типу');
	});
});
