import axe from 'axe-core';
import { fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import AdminShell from './AdminShell.svelte';

const { mockLogout, mockGoto, pageState } = vi.hoisted(() => ({
	mockLogout: vi.fn().mockResolvedValue(undefined),
	mockGoto: vi.fn().mockResolvedValue(undefined),
	pageState: { pathname: '/admin' }
}));

vi.mock('$lib/stores/auth.svelte', () => ({
	authStore: {
		get user() {
			return { id: '1', email: 'admin@example.com', role: 'admin', tier: 'paid' };
		},
		get isAuthenticated() {
			return true;
		},
		logout: mockLogout
	}
}));

vi.mock('$app/navigation', () => ({
	goto: mockGoto
}));

vi.mock('$app/stores', () => {
	const page = {
		subscribe: (fn: (val: unknown) => void) => {
			fn({ url: new URL(`http://localhost${pageState.pathname}`) });
			return () => {};
		}
	};
	return { page };
});

vi.mock('$lib/api/client.svelte', () => ({
	tokenState: { accessToken: 'test', setToken: vi.fn(), clear: vi.fn() },
	apiFetch: vi.fn()
}));

function renderWithPath(pathname: string) {
	pageState.pathname = pathname;
	return renderComponent(AdminShell);
}

describe('AdminShell', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		pageState.pathname = '/admin';
		mockLogout.mockResolvedValue(undefined);
		mockGoto.mockResolvedValue(undefined);
	});

	test('renders header with HealthCabinet brand', () => {
		const { container } = renderWithPath('/admin');
		const brand = container.querySelector('.hc-app-header-brand');
		expect(brand).toBeInTheDocument();
		expect(brand!.textContent).toContain('HealthCabinet');
	});

	test('renders admin nav with Overview, Upload Queue, Users items', () => {
		const { container } = renderWithPath('/admin');
		const navItems = container.querySelectorAll('.hc-admin-nav-item');
		expect(navItems.length).toBe(3);
		const navText = container.querySelector('.hc-admin-left-nav')!.textContent;
		expect(navText).toContain('Overview');
		expect(navText).toContain('Upload Queue');
		expect(navText).toContain('Users');
	});

	test('renders "Back to App" link to /dashboard', () => {
		const { container } = renderWithPath('/admin');
		const backLink = container.querySelector('.hc-admin-nav-back') as HTMLAnchorElement;
		expect(backLink).toBeInTheDocument();
		expect(backLink.textContent).toContain('Back to App');
		expect(backLink.getAttribute('href')).toBe('/dashboard');
	});

	test('renders admin status bar with Admin Panel label', () => {
		const { container } = renderWithPath('/admin');
		const statusBar = container.querySelector('.hc-app-status-bar');
		expect(statusBar).toBeInTheDocument();
		expect(statusBar!.textContent).toContain('Admin Panel');
	});

	test('nav header shows "Admin" text', () => {
		const { container } = renderWithPath('/admin');
		const navHeader = container.querySelector('.hc-admin-nav-header');
		expect(navHeader).toBeInTheDocument();
		expect(navHeader!.textContent).toContain('Admin');
	});

	test('sign-out button calls logout and navigates to /login', async () => {
		const { getByRole } = renderWithPath('/admin');
		const signOutBtn = getByRole('button', { name: /sign out/i });

		expect(signOutBtn).toHaveClass('btn-standard');

		await fireEvent.click(signOutBtn);

		expect(mockLogout).toHaveBeenCalled();

		await waitFor(() => {
			expect(mockGoto).toHaveBeenCalledWith('/login');
		});
	});

	test('Overview nav item is active on /admin (exact match)', () => {
		const { container } = renderWithPath('/admin');
		const navItems = container.querySelectorAll('.hc-admin-nav-item');
		const overview = navItems[0];
		expect(overview).toHaveClass('active');
		expect(overview).toHaveAttribute('aria-current', 'page');
	});

	test('Upload Queue nav item is active on /admin/documents', () => {
		const { container } = renderWithPath('/admin/documents');
		const navItems = container.querySelectorAll('.hc-admin-nav-item');
		const queue = navItems[1];
		expect(queue).toHaveClass('active');
		expect(queue).toHaveAttribute('aria-current', 'page');
		// Overview should NOT be active
		expect(navItems[0]).not.toHaveClass('active');
	});

	test('Users nav item is active on nested route /admin/users/abc', () => {
		const { container } = renderWithPath('/admin/users/00000000-0000-0000-0000-000000000001');
		const navItems = container.querySelectorAll('.hc-admin-nav-item');
		const users = navItems[2];
		expect(users).toHaveClass('active');
		expect(users).toHaveAttribute('aria-current', 'page');
	});

	test('no nav item is active on /dashboard', () => {
		const { container } = renderWithPath('/dashboard');
		const activeItems = container.querySelectorAll('.hc-admin-nav-item.active');
		expect(activeItems.length).toBe(0);
	});

	test('status bar shows "Overview" on /admin', () => {
		const { container } = renderWithPath('/admin');
		const statusBar = container.querySelector('.hc-app-status-bar');
		expect(statusBar!.textContent).toContain('Overview');
	});

	test('status bar shows "Upload Queue" on exact /admin/documents', () => {
		const { container } = renderWithPath('/admin/documents');
		const statusBar = container.querySelector('.hc-app-status-bar');
		expect(statusBar!.textContent).toContain('Upload Queue');
	});

	test('status bar shows "Upload Queue" on /admin/documents/abc', () => {
		const { container } = renderWithPath('/admin/documents/abc');
		const statusBar = container.querySelector('.hc-app-status-bar');
		expect(statusBar!.textContent).toContain('Upload Queue');
	});

	test('status bar shows "Users" on /admin/users', () => {
		const { container } = renderWithPath('/admin/users');
		const statusBar = container.querySelector('.hc-app-status-bar');
		expect(statusBar!.textContent).toContain('Users');
	});

	test('status bar shows "Users" on nested /admin/users/abc', () => {
		const { container } = renderWithPath('/admin/users/00000000-0000-0000-0000-000000000001');
		const statusBar = container.querySelector('.hc-app-status-bar');
		expect(statusBar!.textContent).toContain('Users');
	});

	test('is accessible (axe audit)', async () => {
		const { container } = renderWithPath('/admin');
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	test('no shadcn-svelte primitive imports exist in component source', async () => {
		const source = await import('./AdminShell.svelte?raw');
		expect(source.default).not.toMatch(/from '\$lib\/components\/ui\/button['/]/);
		expect(source.default).not.toMatch(/from '\$lib\/components\/ui\/input['/]/);
		expect(source.default).not.toMatch(/from '\$lib\/components\/ui\/label['/]/);
		expect(source.default).not.toMatch(/from '\$lib\/components\/ui\/textarea['/]/);
	});
});
