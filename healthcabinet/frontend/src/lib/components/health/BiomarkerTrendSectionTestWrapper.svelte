<script lang="ts">
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import { QueryClient } from '@tanstack/query-core';
	import BiomarkerTrendSection from './BiomarkerTrendSection.svelte';

	interface Props {
		queryClient?: QueryClient;
		canonicalName: string;
		hasValues: boolean;
	}

	const {
		queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } }),
		canonicalName,
		hasValues
	}: Props = $props();
</script>

<QueryClientProvider client={queryClient}>
	<BiomarkerTrendSection {canonicalName} {hasValues} />
</QueryClientProvider>
