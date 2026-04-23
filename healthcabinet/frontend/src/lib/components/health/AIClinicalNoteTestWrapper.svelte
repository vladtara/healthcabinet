<script lang="ts">
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import { QueryClient } from '@tanstack/query-core';
	import AIClinicalNote from './AIClinicalNote.svelte';
	import type { DashboardFilter } from '$lib/stores/dashboard-filter.svelte';

	interface Props {
		queryClient?: QueryClient;
		documentId?: string | null;
		documentKind?: DashboardFilter;
		hasContext?: boolean;
	}

	let {
		queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } }),
		documentId = null,
		documentKind = undefined,
		hasContext = undefined
	}: Props = $props();
</script>

<QueryClientProvider client={queryClient}>
	{#if documentKind !== undefined}
		<AIClinicalNote mode="dashboard" {documentKind} {hasContext} />
	{:else}
		<AIClinicalNote mode="document" {documentId} />
	{/if}
</QueryClientProvider>
