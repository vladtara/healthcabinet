<script lang="ts">
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import type { QueryClient } from '@tanstack/query-core';
	import PatternCard from './PatternCard.svelte';

	interface Props {
		queryClient: QueryClient;
	}

	const { queryClient }: Props = $props();
</script>

<QueryClientProvider client={queryClient}>
	<PatternCard />
</QueryClientProvider>
