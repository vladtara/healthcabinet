<script module lang="ts">
	import { QueryClient } from '@tanstack/svelte-query';
	// Instantiate once at module load — persists across layout remounts and SPA navigations.
	const queryClient = new QueryClient();
</script>

<script lang="ts">
	import { goto } from '$app/navigation';
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import { authStore } from '$lib/stores/auth.svelte';
	import AdminShell from '$lib/components/AdminShell.svelte';

	interface Props {
		children: import('svelte').Snippet;
	}
	let { children }: Props = $props();

	// Story 15.1: redirect only fires after bootstrap resolves. Role is only
	// enforced once we are definitively authenticated — before that, `user`
	// may still be null while restore is in flight, which would have
	// previously tripped the non-admin redirect path.
	$effect(() => {
		if (authStore.bootstrapState === 'anonymous') {
			goto('/login');
			return;
		}
		if (authStore.bootstrapState === 'authenticated' && authStore.user && authStore.user.role !== 'admin') {
			goto('/login');
		}
	});
</script>

{#if authStore.bootstrapState === 'authenticated' && authStore.user?.role === 'admin'}
	<QueryClientProvider client={queryClient}>
		<AdminShell>
			{@render children()}
		</AdminShell>
	</QueryClientProvider>
{:else if authStore.bootstrapState === 'authenticated' && authStore.user === null}
	<div
		data-testid="admin-loading"
		role="status"
		aria-live="polite"
		style="padding: 16px; font-size: 12px;"
	>
		Loading admin profile…
	</div>
{/if}
