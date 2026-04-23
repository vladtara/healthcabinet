import { fireEvent, waitFor } from '@testing-library/svelte';
import axe from 'axe-core';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { restoreNavigatorLocale, stubNavigatorLocale } from '$lib/test-utils/locale-env';
import { localeStore } from '$lib/stores/locale.svelte';
import LoginPage from './+page.svelte';

vi.mock('$lib/api/auth', () => ({
	login: vi.fn(),
	me: vi.fn().mockResolvedValue({ id: '1', email: 'user@example.com', role: 'user', tier: 'free' })
}));

vi.mock('$lib/stores/auth.svelte', () => ({
	authStore: {
		setAccessToken: vi.fn(),
		setUser: vi.fn(),
		clearAccessToken: vi.fn(),
		get isAuthenticated() {
			return false;
		}
	}
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

vi.mock('$lib/api/client.svelte', () => ({
	tokenState: { accessToken: null, setToken: vi.fn(), clear: vi.fn() },
	apiFetch: vi.fn()
}));

import { login } from '$lib/api/auth';
import { authStore } from '$lib/stores/auth.svelte';
import { goto } from '$app/navigation';

const mockLogin = vi.mocked(login);

describe('Login page', () => {
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

	test('shows "Invalid email or password" on 401 response', async () => {
		mockLogin.mockRejectedValueOnce({ status: 401, detail: 'Invalid email or password' });

		const { getByLabelText, getByText, getByRole } = renderComponent(LoginPage);

		await fireEvent.input(getByLabelText(/email/i), {
			target: { value: 'user@example.com' }
		});
		await fireEvent.input(getByLabelText(/^password$/i), {
			target: { value: 'wrongpassword' }
		});
		await fireEvent.click(getByRole('button', { name: /sign in/i }));

		await waitFor(() => {
			expect(getByText(/invalid email or password/i)).toBeInTheDocument();
		});
	});

	test('shows suspension message on 403 response', async () => {
		mockLogin.mockRejectedValueOnce({ status: 403, detail: 'Account is suspended' });

		const { getByLabelText, getByText, getByRole } = renderComponent(LoginPage);

		await fireEvent.input(getByLabelText(/email/i), {
			target: { value: 'suspended@example.com' }
		});
		await fireEvent.input(getByLabelText(/^password$/i), {
			target: { value: 'validpassword' }
		});
		await fireEvent.click(getByRole('button', { name: /sign in/i }));

		await waitFor(() => {
			expect(getByText(/account has been suspended/i)).toBeInTheDocument();
		});
	});

	test('mapped auth error rerenders in active locale after toggle', async () => {
		mockLogin.mockRejectedValueOnce({ status: 401, detail: 'Invalid email or password' });

		const { getByLabelText, getByText, getByRole } = renderComponent(LoginPage);
		await fireEvent.input(getByLabelText(/email/i), { target: { value: 'user@example.com' } });
		await fireEvent.input(getByLabelText(/^password$/i), { target: { value: 'wrongpassword' } });
		await fireEvent.click(getByRole('button', { name: /sign in/i }));

		await waitFor(() => {
			expect(getByText(/invalid email or password/i)).toBeInTheDocument();
		});

		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));
		expect(getByText(/невірний email або пароль/i)).toBeInTheDocument();
	});

	test('does not differentiate between wrong password and unknown email in error message', async () => {
		mockLogin.mockRejectedValueOnce({ status: 401, detail: 'Invalid email or password' });

		const { getByLabelText, getByText, getByRole } = renderComponent(LoginPage);

		await fireEvent.input(getByLabelText(/email/i), {
			target: { value: 'nobody@example.com' }
		});
		await fireEvent.input(getByLabelText(/^password$/i), {
			target: { value: 'somepassword' }
		});
		await fireEvent.click(getByRole('button', { name: /sign in/i }));

		await waitFor(() => {
			const errorMsg = getByText(/invalid email or password/i);
			expect(errorMsg).toBeInTheDocument();
			// Must not say "email" or "password" individually — single unified message
			const normalizedErrorText = errorMsg.textContent
				?.replace(/\s+/g, ' ')
				.replace('⚠', '')
				.trim();
			expect(normalizedErrorText).toBe('Invalid email or password');
		});
	});

	test('submit button disabled during submission (isSubmitting)', async () => {
		let resolveLogin: (val: unknown) => void;
		const pendingLogin = new Promise((resolve) => {
			resolveLogin = resolve;
		});
		mockLogin.mockReturnValueOnce(pendingLogin as ReturnType<typeof login>);

		const { getByLabelText, getByRole } = renderComponent(LoginPage);

		await fireEvent.input(getByLabelText(/email/i), {
			target: { value: 'user@example.com' }
		});
		await fireEvent.input(getByLabelText(/^password$/i), {
			target: { value: 'password123' }
		});

		const submitButton = getByRole('button', { name: /sign in/i });
		await fireEvent.click(submitButton);

		await waitFor(() => {
			expect(submitButton).toBeDisabled();
		});

		resolveLogin!({ access_token: 'tok', token_type: 'bearer' });
	});

	test('successful login calls setAccessToken with token and navigates to /dashboard', async () => {
		mockLogin.mockResolvedValueOnce({ access_token: 'test-token-xyz', token_type: 'bearer' });

		const { getByLabelText, getByRole } = renderComponent(LoginPage);

		await fireEvent.input(getByLabelText(/email/i), {
			target: { value: 'user@example.com' }
		});
		await fireEvent.input(getByLabelText(/^password$/i), {
			target: { value: 'correctpassword' }
		});
		await fireEvent.click(getByRole('button', { name: /sign in/i }));

		await waitFor(() => {
			expect(vi.mocked(authStore.setAccessToken)).toHaveBeenCalledWith('test-token-xyz');
			expect(vi.mocked(goto)).toHaveBeenCalledWith('/dashboard');
		});
		// No error message should be displayed on success
		expect(document.querySelector('#form-error')).toBeNull();
	});

	test('form is accessible via keyboard (axe audit)', async () => {
		const { container, getByLabelText, getByRole } = renderComponent(LoginPage);

		// Initial render accessibility check
		const initialResults = await axe.run(container);
		expect(initialResults.violations).toHaveLength(0);

		// Error state accessibility check — #form-error with role="alert" must also be accessible.
		// Running axe only on initial render misses non-accessible error markup regressions.
		mockLogin.mockRejectedValueOnce({ status: 401, detail: 'Invalid email or password' });
		await fireEvent.input(getByLabelText(/email/i), { target: { value: 'user@example.com' } });
		await fireEvent.input(getByLabelText(/^password$/i), { target: { value: 'wrongpassword' } });
		await fireEvent.click(getByRole('button', { name: /sign in/i }));
		await waitFor(() => {
			expect(container.querySelector('#form-error')).toBeInTheDocument();
		});
		const errorStateResults = await axe.run(container);
		expect(errorStateResults.violations).toHaveLength(0);
	});

	test('shared input and button primitives apply expected styling on login', () => {
		const { getByLabelText, getByRole } = renderComponent(LoginPage);

		expect(getByLabelText(/email/i)).toHaveClass('hc-input');
		expect(getByRole('button', { name: /sign in/i })).toHaveClass('btn-primary');
	});

	test('renders auth dialog header with Sign In title', () => {
		const { container } = renderComponent(LoginPage);
		const header = container.querySelector('.hc-auth-dialog-header');
		expect(header).toBeInTheDocument();
		expect(header!.textContent).toContain('Sign In');
	});

	test('renders trust footer with encryption message', () => {
		const { container } = renderComponent(LoginPage);
		const trust = container.querySelector('.hc-auth-trust');
		expect(trust).toBeInTheDocument();
		expect(trust!.textContent).toContain('encrypted and stored in the EU');
	});
});
