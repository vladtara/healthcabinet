import { fireEvent } from '@testing-library/svelte';
import axe from 'axe-core';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { restoreNavigatorLocale, stubNavigatorLocale } from '$lib/test-utils/locale-env';
import { localeStore } from '$lib/stores/locale.svelte';
import RegisterPage from './+page.svelte';

vi.mock('$lib/api/client.svelte', () => ({
	apiFetch: vi.fn(),
	tokenState: { accessToken: null },
	API_BASE: 'http://localhost:8000',
	registerForceLogoutHandler: vi.fn()
}));

describe('Register page', () => {
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

	test('submit button disabled when consent unchecked', () => {
		const { getByRole } = renderComponent(RegisterPage);
		const submitButton = getByRole('button', { name: /create account/i });
		expect(submitButton).toBeDisabled();
	});

	test('gdpr consent checkbox uses the migrated visible checkbox primitive', () => {
		const { getByRole } = renderComponent(RegisterPage);
		expect(
			getByRole('checkbox', { name: /i consent to health data processing/i })
		).toHaveClass('hc-checkbox');
	});

	test('email blur shows inline error for invalid format', async () => {
		const { getByLabelText, getByText } = renderComponent(RegisterPage);
		const emailInput = getByLabelText(/email/i);
		await fireEvent.input(emailInput, { target: { value: 'not-an-email' } });
		await fireEvent.blur(emailInput);
		expect(getByText(/please enter a valid email address/i)).toBeInTheDocument();
	});

	test('inline validation error rerenders in active locale after toggle', async () => {
		const { getByLabelText, getByText } = renderComponent(RegisterPage);
		const emailInput = getByLabelText(/email/i);
		await fireEvent.input(emailInput, { target: { value: 'not-an-email' } });
		await fireEvent.blur(emailInput);
		expect(getByText(/please enter a valid email address/i)).toBeInTheDocument();

		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));
		expect(getByText(/вкажіть коректну електронну адресу/i)).toBeInTheDocument();
	});

	test('password blur shows inline error for short password', async () => {
		const { getByLabelText, getByText } = renderComponent(RegisterPage);
		const passwordInput = getByLabelText(/^password$/i);
		await fireEvent.input(passwordInput, { target: { value: 'short' } });
		await fireEvent.blur(passwordInput);
		expect(getByText(/at least 8 characters/i)).toBeInTheDocument();
	});

	test('password blur shows error for overlong multi-byte password', async () => {
		const { getByLabelText, getByText } = renderComponent(RegisterPage);
		const passwordInput = getByLabelText(/^password$/i);
		// "あ" × 25 = 75 bytes (3 bytes each) but only 25 characters — exceeds bcrypt 72-byte limit
		await fireEvent.input(passwordInput, { target: { value: 'あ'.repeat(25) } });
		await fireEvent.blur(passwordInput);
		expect(getByText(/too long/i)).toBeInTheDocument();
	});

	test('form is accessible via keyboard (axe audit)', async () => {
		const { container } = renderComponent(RegisterPage);
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	test('renders auth dialog header with Create Your Account', () => {
		const { getByRole } = renderComponent(RegisterPage);
		const heading = getByRole('heading', { name: /create your account/i });
		expect(heading).toBeInTheDocument();
		expect(heading).toHaveClass('hc-auth-dialog-header');
	});

	test('renders subtitle text', () => {
		const { getByText } = renderComponent(RegisterPage);
		expect(getByText(/securely store, understand, and track your health data/i)).toBeInTheDocument();
	});

	test('renders trust badges below dialog', () => {
		const { container } = renderComponent(RegisterPage);
		const trustBelow = container.querySelector('.hc-auth-trust-below');
		expect(trustBelow).toBeInTheDocument();
		const badges = trustBelow!.querySelectorAll('.hc-landing-trust-badge');
		expect(badges).toHaveLength(3);
		expect(trustBelow!.textContent).toContain('AES-256');
		expect(trustBelow!.textContent).toContain('EU Data');
		expect(trustBelow!.textContent).toContain('GDPR');
	});
});
