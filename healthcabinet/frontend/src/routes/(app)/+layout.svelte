<script module lang="ts">
	import { QueryClient } from '@tanstack/svelte-query';
	// Instantiate once at module load — persists across layout remounts and SPA navigations.
	// If instantiated inside the component script, the cache is discarded on each remount.
	const queryClient = new QueryClient();
</script>

<script lang="ts">
	import { goto } from '$app/navigation';
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import { authStore } from '$lib/stores/auth.svelte';
	import AppShell from '$lib/components/AppShell.svelte';

	interface Props {
		children: import('svelte').Snippet;
	}
	let { children }: Props = $props();

	// Story 15.1: gate redirect on bootstrap state. Previously this effect
	// fired on every unauthenticated frame — including the window between a
	// hard reload (in-memory token cleared) and the refresh round-trip
	// resolving, which caused a spurious /login redirect. Now it only fires
	// after restore definitively resolves to 'anonymous'.
	$effect(() => {
		if (authStore.bootstrapState === 'anonymous') {
			goto('/login');
		}
	});
</script>

{#if authStore.bootstrapState === 'authenticated'}
	<QueryClientProvider client={queryClient}>
		<AppShell>
			{@render children()}
		</AppShell>
	</QueryClientProvider>
{/if}
