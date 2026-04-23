<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { authStore } from '$lib/stores/auth.svelte';
	import { StatusBar, StatusBarField } from '$lib/components/ui/status-bar';
	import { ToastContainer } from '$lib/components/ui/toast';

	interface Props {
		children: import('svelte').Snippet;
	}
	let { children }: Props = $props();

	const navItems = [
		{ href: '/admin', icon: '📊', label: 'Overview', exact: true },
		{ href: '/admin/documents', icon: '📤', label: 'Upload Queue' },
		{ href: '/admin/users', icon: '👥', label: 'Users' }
	];

	function isActive(href: string, exact = false): boolean {
		if (exact) return $page.url.pathname === href;
		return $page.url.pathname === href || $page.url.pathname.startsWith(href + '/');
	}

	function activePageName(): string {
		for (const item of navItems) {
			if (isActive(item.href, item.exact)) return item.label;
		}
		return 'Admin';
	}

	async function handleSignOut() {
		try {
			await authStore.logout();
		} catch {
			// Best-effort — proceed to login regardless
		}
		goto('/login').catch(() => {});
	}
</script>

<div class="hc-app-shell">
	<a href="#main-content" class="hc-skip-link">Skip to main content</a>
	<!-- Header -->
	<header class="hc-app-header">
		<div class="hc-app-header-brand">
			<span class="hc-app-header-icon" aria-hidden="true">⚕</span>
			<span>HealthCabinet</span>
		</div>
		<div class="hc-app-header-user">
			{#if authStore.user?.email}
				<span>{authStore.user.email}</span>
			{/if}
			<button type="button" class="btn-standard" onclick={handleSignOut}>🚪 Sign Out</button>
		</div>
	</header>

	<!-- Body -->
	<div class="hc-app-body">
		<!-- Admin Left Nav -->
		<nav class="hc-admin-left-nav" aria-label="Admin navigation">
			<div class="hc-admin-nav-header">
				<span aria-hidden="true">⚙</span> Admin
			</div>

			<div class="hc-admin-nav-section-label">Management</div>
			{#each navItems as item}
				<a
					href={item.href}
					class="hc-admin-nav-item {isActive(item.href, item.exact) ? 'active' : ''}"
					aria-current={isActive(item.href, item.exact) ? 'page' : undefined}
				>
					<span aria-hidden="true">{item.icon}</span>
					{item.label}
				</a>
			{/each}

			<a href="/dashboard" class="hc-admin-nav-back">
				<span aria-hidden="true">←</span>
				Back to App
			</a>
		</nav>

		<!-- Content -->
		<main class="hc-app-content" id="main-content">
			{@render children?.()}
		</main>
	</div>

	<!-- Status Bar -->
	<StatusBar class="hc-app-status-bar">
		<StatusBarField class="hc-app-status-page">{activePageName()}</StatusBarField>
		<StatusBarField>Admin Panel</StatusBarField>
		<StatusBarField>v1.0</StatusBarField>
	</StatusBar>

	<ToastContainer />
</div>
