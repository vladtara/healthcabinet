<script module lang="ts">
	import { QueryClient } from '@tanstack/svelte-query';
	const queryClient = new QueryClient();
</script>

<script lang="ts">
	import { goto } from '$app/navigation';
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import { authStore } from '$lib/stores/auth.svelte';

	interface Props {
		children: import('svelte').Snippet;
	}
	let { children }: Props = $props();

	// Story 15.1: redirect only after bootstrap resolves to 'anonymous'.
	$effect(() => {
		if (authStore.bootstrapState === 'anonymous') {
			goto('/login');
		}
	});
</script>

{#if authStore.bootstrapState === 'authenticated'}
	<QueryClientProvider client={queryClient}>
		{@render children()}
	</QueryClientProvider>
{/if}
