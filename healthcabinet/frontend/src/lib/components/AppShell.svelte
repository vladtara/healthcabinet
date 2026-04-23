<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { authStore } from '$lib/stores/auth.svelte';
	import { statusBarStore } from '$lib/stores/status-bar.svelte';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';
	import { StatusBar, StatusBarField } from '$lib/components/ui/status-bar';
	import { ToastContainer } from '$lib/components/ui/toast';
	import { LocaleToggle } from '$lib/components/ui/locale-toggle';

	interface Props {
		children: import('svelte').Snippet;
	}
	let { children }: Props = $props();

	const copy = $derived(t(localeStore.locale).appShell);

	const navItems = $derived([
		{ href: '/dashboard', icon: '📊', label: copy.navDashboard },
		{ href: '/documents', icon: '📁', label: copy.navDocuments },
		{ href: '/settings', icon: '⚙', label: copy.navSettings }
	]);

	function isActive(href: string): boolean {
		return $page.url.pathname === href || $page.url.pathname.startsWith(href + '/');
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
	<a href="#main-content" class="hc-skip-link">{copy.skipToContent}</a>
	<!-- Header -->
	<header class="hc-app-header">
		<div class="hc-app-header-brand">
			<span class="hc-app-header-icon" aria-hidden="true">⚕</span>
			<span>{copy.brand}</span>
		</div>
		<div class="hc-app-header-user">
			<LocaleToggle />
			{#if authStore.user?.email}
				<span>{authStore.user.email}</span>
			{/if}
			<button type="button" class="btn-standard" onclick={handleSignOut}>🚪 {copy.signOut}</button>
		</div>
	</header>

	<!-- Body -->
	<div class="hc-app-body">
		<!-- Left Nav -->
		<nav class="hc-app-left-nav" aria-label={copy.mainNavAria}>
			<div class="hc-app-nav-header">
				<span aria-hidden="true">⚕</span>
				{copy.navHeader}
			</div>

			<div class="hc-app-nav-section-label">{copy.navSectionApp}</div>
			{#each navItems as item}
				<a
					href={item.href}
					class="hc-app-nav-item {isActive(item.href) ? 'active' : ''}"
					aria-current={isActive(item.href) ? 'page' : undefined}
				>
					<span aria-hidden="true">{item.icon}</span>
					{item.label}
				</a>
			{/each}

			{#if authStore.user?.role === 'admin'}
				<div class="hc-app-nav-separator"></div>
				<div class="hc-app-nav-section-label">{copy.navSectionAdmin}</div>
				<a
					href="/admin"
					class="hc-app-nav-item {isActive('/admin') ? 'active' : ''}"
					aria-current={isActive('/admin') ? 'page' : undefined}
				>
					<span aria-hidden="true">🔧</span>
					{copy.navAdminConsole}
				</a>
			{/if}
		</nav>

		<!-- Content -->
		<main class="hc-app-content" id="main-content">
			{@render children?.()}
		</main>
	</div>

	<!-- Status Bar -->
	<StatusBar class="hc-app-status-bar">
		<StatusBarField class="hc-app-status-page">
			{statusBarStore.status === 'Ready' ? copy.statusReady : statusBarStore.status}
		</StatusBarField>
		{#each statusBarStore.fields as field}
			<StatusBarField>{field}</StatusBarField>
		{/each}
	</StatusBar>

	<ToastContainer />
</div>
