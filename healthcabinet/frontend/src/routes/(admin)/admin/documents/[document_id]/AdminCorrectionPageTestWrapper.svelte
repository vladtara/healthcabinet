<script lang="ts">
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import type { QueryClient } from '@tanstack/query-core';
	import Page from './+page.svelte';

	interface Props {
		queryClient: QueryClient;
	}

	const { queryClient }: Props = $props();
</script>

<QueryClientProvider client={queryClient}>
	<Page />
</QueryClientProvider>
